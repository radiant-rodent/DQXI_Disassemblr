# Rebuild the readable, named DQXI native source from YOUR OWN ROM dump plus the
# mappings committed in this repository.
#
#   powershell -ExecutionPolicy Bypass -File backup\restore_from_rom.ps1 -Rom D:\dumps\DQXI.3ds
#   ... -SkipGhidra   (re-apply names only, Ghidra export already present)
#
# Needs: Python 3.12 (+ pip install capstone numpy pillow), Ghidra 12.1.x + JDK 21
# (found under %LOCALAPPDATA%\Programs\opencode-tools or analyzeHeadless.bat on PATH),
# and for the bit-match build the ARM toolchain from tools\setup_arm_toolchain.ps1.
#
# Nothing here downloads game data. The ROM is only read.
param(
    [Parameter(Mandatory = $true)][string]$Rom,
    [switch]$SkipGhidra,
    [int]$Workers = 8
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Run([string]$Label, [scriptblock]$Body) {
    Write-Host "`n=== $Label ===" -ForegroundColor Cyan
    & $Body
    if ($LASTEXITCODE -ne 0) { throw "step failed (exit $LASTEXITCODE): $Label" }
}

if (-not (Test-Path $Rom)) { throw "ROM not found: $Rom" }

# 1. unpack the cartridge and check it is the same revision the mappings were made on
Run "extract ROM containers" { python tools/extract_rom.py --rom $Rom --out original }
Run "compare with the reference hashes" {
    $want = @{}; Get-Content backup\rom_hashes.sha256 | ForEach-Object {
        $h, $p = $_ -split '\s+', 2; $want[$p.Trim()] = $h }
    $bad = 0
    foreach ($p in @("exefs/code.decompressed.bin", "exheader.bin")) {
        $got = (Get-FileHash -Algorithm SHA256 (Join-Path original $p)).Hash.ToLower()
        if ($got -ne $want[$p]) { Write-Warning "$p differs from the reference dump"; $bad++ }
    }
    if ($bad) { throw "This is not the CTR-P-BTZJ revision the names were made for (or it is still encrypted - dump it decrypted with GodMode9)." }
    $global:LASTEXITCODE = 0
}

# 2. full disassembly + bit-matching rebuild (proves the asm is exact)
Run "disassemble executable (asm/)" { python tools/disasm.py }
Run "reassemble and bit-match code.bin" { python tools/build.py }

# 3. Ghidra decompilation, then put the committed catalogue back on top
$catalog = @("decomp/ghidra/functions.jsonl", "decomp/ghidra/functions_merged.jsonl",
             "decomp/ghidra/functions_index.json", "decomp/native_names.json",
             "symbols.json", "symbols_recovered.json")
$keep = Join-Path $env:TEMP "dqxi_catalog_keep"
New-Item -ItemType Directory -Force -Path $keep | Out-Null
foreach ($f in $catalog) { Copy-Item $f (Join-Path $keep ($f -replace '[\\/]', '__')) -Force }

if (-not $SkipGhidra) {
    $tools = Join-Path $env:LOCALAPPDATA "Programs\opencode-tools"
    $jdk = Get-ChildItem $tools -Directory -Filter "jdk-*" -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    $gh = Get-ChildItem $tools -Directory -Filter "ghidra_*_PUBLIC" -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
    if ($jdk) { $env:JAVA_HOME = $jdk.FullName }
    $headless = if ($gh) { Join-Path $gh.FullName "support\analyzeHeadless.bat" } else { (Get-Command analyzeHeadless.bat -ErrorAction SilentlyContinue).Source }
    if (-not $headless) { throw "Ghidra analyzeHeadless.bat not found" }
    New-Item -ItemType Directory -Force -Path decomp\ghidra_project | Out-Null
    Run "Ghidra import + auto-analysis (slow)" {
        & $headless decomp/ghidra_project DQXI -import original/exefs/code.decompressed.bin `
            -processor ARM:LE:32:v6 -cspec default -loader BinaryLoader -loader-baseAddr 0x00100000 -overwrite }
    Run "Ghidra export, one .c per entry point" {
        & $headless decomp/ghidra_project DQXI -process code.decompressed.bin -noanalysis `
            -scriptPath tools/ghidra_scripts -postScript ExportDQXI.java $Root (Join-Path $Root "decomp\ghidra") }
    Run "Ghidra recover missing entry points" {
        & $headless decomp/ghidra_project DQXI -process code.decompressed.bin -noanalysis `
            -scriptPath tools/ghidra_scripts -postScript DiagnoseMissing.java $Root (Join-Path $Root "decomp\ghidra\missing_result.jsonl") }
    Run "organise Ghidra export" { python tools/organize_ghidra.py }
}

foreach ($f in $catalog) { Copy-Item (Join-Path $keep ($f -replace '[\\/]', '__')) $f -Force }
Write-Host "restored committed catalogue over the fresh export" -ForegroundColor Green

# 4. apply the names, then the struct/global/local types, then the readable pass
Run "merge names (writes decomp/readable)" { python tools/merge_names.py --refine --workers $Workers }
Run "struct evidence db"   { python -m tools.typedb.struct_db --workers $Workers }
Run "globals/locals inventory" { python -m tools.typedb.inventory --workers $Workers }
Run "merge type answers"   { python -m tools.typedb.apply --merge }
Run "readable C with types" { python -m tools.readable_c --workers $Workers }

Write-Host "`nDone. Named source: decomp\readable\   asm: asm\   catalogue: decomp\ghidra\" -ForegroundColor Green
Write-Host "Assets/editor data (optional, ~10 GB): powershell -File tools\regen_all.ps1 -SkipGhidra"
