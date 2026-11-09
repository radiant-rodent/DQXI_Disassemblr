# Regenerate every generated output of the DQXI 3DS project from the retail ROM.
#
#   powershell -ExecutionPolicy Bypass -File tools\regen_all.ps1
#   powershell -ExecutionPolicy Bypass -File tools\regen_all.ps1 -Jobs 12 -SkipPacks
#
# The order below is the one the generated data was actually produced with:
# containers -> verified native build -> decompilation -> extracted game data ->
# standard-format assets -> editor/patched-ROM smoke test -> naming batches ->
# the same tests a human would run.  Nothing in ..\3DS_Translate is
# modified; the ROM is only read.
#
# Fast local re-runs: -SkipPacks keeps an existing game_data/ tree, -SkipGhidra
# keeps an existing decomp/ghidra tree, -SkipAssets keeps game_assets/.
param(
    [int]$Jobs = 8,
    [switch]$SkipPacks,
    [switch]$SkipGhidra,
    [switch]$SkipAssets,
    [switch]$FullTextureAudit
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$LogDir = Join-Path $Root "orchestration\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Step([string]$Label, [scriptblock]$Body) {
    Write-Host ""
    Write-Host "=== $Label ===" -ForegroundColor Cyan
    $start = Get-Date
    & $Body
    if ($LASTEXITCODE -ne 0) {
        throw "step failed (exit $LASTEXITCODE): $Label"
    }
    Write-Host ("    ok ({0:n1}s)" -f ((Get-Date) - $start).TotalSeconds) -ForegroundColor Green
}

function Py([string]$Label, [string[]]$Arguments) {
    Step $Label { & python @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $LogDir ("regen_" + ($Label -replace '[^A-Za-z0-9]+', '_') + ".log")) }
}

# ---------------------------------------------------------------------------
# 0. preflight
# ---------------------------------------------------------------------------
$Rom = "..\3DS_Translate\DQXI.3ds"
if (-not (Test-Path $Rom)) { throw "retail ROM not found: $Rom" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "python is not on PATH" }
Write-Host "regenerating from $Rom" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 1. containers + cryptographic baseline
# ---------------------------------------------------------------------------
Py "extract ROM containers" @("tools/extract_rom.py")
Py "verify extracted container hashes" @("tools/verify.py")

# ---------------------------------------------------------------------------
# 2. bit-matching native build
#    disasm.py recreates asm/ from the decompressed executable, build.py
#    reassembles it; recompile_game.py repacks the full cartridge and refuses
#    to pass unless every hash matches retail.
# ---------------------------------------------------------------------------
Py "disassemble executable (asm/)" @("tools/disasm.py")
Py "reassemble code.bin" @("tools/build.py")
Py "compile C replacements" @("tools/build_c_replacement.py")
Py "reassemble with C replacements overlaid" @("tools/build.py")
Py "recompile + verify full 4 GiB ROM" @("tools/recompile_game.py")

# ---------------------------------------------------------------------------
# 3. Ghidra decompilation (18,787 entry points) + readable views
# ---------------------------------------------------------------------------
if (-not $SkipGhidra) {
    $tools = Join-Path $env:LOCALAPPDATA "Programs\opencode-tools"
    $jdk = Get-ChildItem $tools -Directory -Filter "jdk-*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    $ghidra = Get-ChildItem $tools -Directory -Filter "ghidra_*_PUBLIC" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($jdk) { $env:JAVA_HOME = $jdk.FullName }
    $headless = if ($ghidra) { Join-Path $ghidra.FullName "support\analyzeHeadless.bat" } else { $null }
    if (-not $headless -or -not (Test-Path $headless)) {
        $found = Get-Command analyzeHeadless.bat -ErrorAction SilentlyContinue
        $headless = if ($found) { $found.Source } else { $null }
    }
    if (-not $headless) {
        Write-Warning "Ghidra (analyzeHeadless.bat) not found: native C will not be regenerated."
    } else {
        New-Item -ItemType Directory -Force -Path (Join-Path $Root "decomp\ghidra_project") | Out-Null
        # decomp/function_seed.tsv lists the same 18,787 prologues the disassembler uses.
        Py "build function seeds" @("tools/make_naming_batches.py", "--seeds-only")
        Step "Ghidra import (auto-analysis, several minutes)" {
            & $headless decomp/ghidra_project DQXI -import original/exefs/code.decompressed.bin `
                -processor ARM:LE:32:v6 -cspec default -loader BinaryLoader -loader-baseAddr 0x00100000 -overwrite `
                2>&1 | Tee-Object -FilePath (Join-Path $LogDir "regen_ghidra_import.log")
        }
        Step "Ghidra export one .c per entry point" {
            & $headless decomp/ghidra_project DQXI -process code.decompressed.bin -noanalysis `
                -scriptPath tools/ghidra_scripts `
                -postScript ExportDQXI.java $Root (Join-Path $Root "decomp\ghidra") `
                2>&1 | Tee-Object -FilePath (Join-Path $LogDir "regen_ghidra_export.log")
        }
        Step "Ghidra diagnose missing entry points" {
            & $headless decomp/ghidra_project DQXI -process code.decompressed.bin -noanalysis `
                -scriptPath tools/ghidra_scripts `
                -postScript DiagnoseMissing.java $Root (Join-Path $Root "decomp\ghidra\missing_result.jsonl") `
                2>&1 | Tee-Object -FilePath (Join-Path $LogDir "regen_ghidra_missing.log")
        }
        Py "organise Ghidra export" @("tools/organize_ghidra.py")
        Py "recover native names from binding tables" @("tools/recover_native_names.py")
        # recover_native_names.py writes the names back to functions.jsonl, so a
        # second organise keeps them and the by_subsystem filenames are real names.
        Py "organise again with recovered names" @("tools/organize_ghidra.py")
        Py "readable C pass" @("tools/readable_c.py")
    }
    # Legacy register-level tree, kept for comparison (README "Two trees").
    Py "legacy decomp/functions pseudo-C" @("tools/decompile_native.py")
}

# ---------------------------------------------------------------------------
# 4. extracted game data (exact RomFS + exploded archives)
# ---------------------------------------------------------------------------
if (-not $SkipPacks) {
    Py "extract RomFS + PACK/PACA members" @("tools/extract_game_data.py", "--all", "--workers", "$Jobs")
    Py "explode SARC UI archives" @("tools/extract_arcs.py")
}

# ---------------------------------------------------------------------------
# 5. SPICA-verified model manifests (material + skin), needed by the exporter
# ---------------------------------------------------------------------------
if (-not $SkipAssets) {
    $spica = Join-Path $Root "tools\spica_ref\bin\Release\net9.0\SpicaRef.exe"
    if (-not (Test-Path $spica)) {
        Step "build SPICA reference dumper" { & dotnet build tools/spica_ref -c Release --no-restore }
    }
    Step "material/skin manifests" {
        $code = @'
import gzip, os, pathlib, shutil, subprocess
root = pathlib.Path.cwd()
exe = root / "tools/spica_ref/bin/Release/net9.0/SpicaRef.exe"
paths = sorted(p.as_posix() for p in pathlib.Path("game_data").rglob("*.bch"))
pathlib.Path("build").mkdir(exist_ok=True)
pathlib.Path("build/all_bch.txt").write_text("\n".join(paths) + "\n", encoding="utf-8")
os.makedirs("game_assets/models", exist_ok=True)
for command, out, gz in (("materials", "build/material_map.json", "game_assets/models/material_map.json.gz"),
                         ("skin", "build/skin_map.json", "game_assets/models/skin_map.json.gz")):
    subprocess.run([str(exe), command, "build/all_bch.txt", out, "."], check=True)
    with open(out, "rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst, 1 << 20)
    print(f"{gz}: {os.path.getsize(gz):,} bytes, {len(paths):,} BCH")
'@
        $code | python -
    }

    # -----------------------------------------------------------------------
    # 6. standard-format assets
    # -----------------------------------------------------------------------
    Py "convert assets (textures/layouts/models/scripts/tables/audio)" @(
        "tools/convert_assets.py", "--all", "--workers", "$Jobs")
    Py "decompile Squirrel scripts" @("tools/squirrel_decompile.py", "--all", "--workers", "$Jobs")
    Py "decode level maps" @("tools/map_tool.py", "export", "--all")
    Py "in-game model/area names" @("tools/build_model_names.py")
    Py "face expression catalogue" @("tools/face_expressions.py", "scan")
    Py "audio catalogue" @("tools/audio_catalog.py")
    Py "game font glyph sheets (layout preview)" @("tools/font_tool.py", "export")
}

# ---------------------------------------------------------------------------
# 7. audits
# ---------------------------------------------------------------------------
Py "forensic audit (manifest + pack inventory)" @("tools/audit_project.py", "--packs", "--jobs", "$Jobs")
Py "verify asset tree" @("tools/verify_assets.py")
Py "verify model textures" @("tools/verify_model_textures.py")
if ($FullTextureAudit) {
    Py "pixel-exact model texture audit (slow, needs .NET 9)" @("tools/audit_model_textures.py", "--workers", "$Jobs")
}

# ---------------------------------------------------------------------------
# 8. editor binary + patched-ROM smoke test (the checked-in b001_101a edit)
# ---------------------------------------------------------------------------
Step "build Rust editor" { & cargo build --release --offline --manifest-path viewer_rs/Cargo.toml }
Py "apply smoke edit" @("tools/map_tool.py", "patch", "editor_projects/b001_101a.json")
Py "rebuild patched ROM (IVFC hashes verified)" @("tools/patch_game.py", "--map", "b001_101a")

# ---------------------------------------------------------------------------
# 9. naming batches for the P1 workers
# ---------------------------------------------------------------------------
Py "naming batches + seeds" @("tools/make_naming_batches.py", "--batch-size", "150")

# ---------------------------------------------------------------------------
# 10. the checks a human runs
# ---------------------------------------------------------------------------
Py "test suite tiers 1-4" @("tests/run_all.py")
Py "asset round-trip checks" @("-m", "unittest", "tests.test_asset_roundtrip", "-v")
# tests.test_asset_roundtrip rewrites game_assets/maps/b001_101a/level3d.patched.bxon
# with its own one-float sample; restore the checked-in smoke edit so the ROM and
# the BXON in the tree describe the same edit.
Py "restore smoke edit after round-trip test" @("tools/map_tool.py", "patch", "editor_projects/b001_101a.json")
Py "rebuild patched ROM after round-trip test" @("tools/patch_game.py", "--map", "b001_101a")
Py "one-shot project verification" @("tools/verify_project.py")
Step "viewer/editor unit tests" { & cargo test --offline --manifest-path viewer_rs/Cargo.toml }

Write-Host ""
Write-Host "regeneration complete: build/, decomp/, game_data/, game_assets/, audit/ and asm/" -ForegroundColor Green
Write-Host "evidence: orchestration/logs/regen_*.log and audit/PROJECT_VERIFICATION.json" -ForegroundColor Green
