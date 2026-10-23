"""Shared constants, helpers, and verification utilities for E2E tests."""

import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import List, Optional, Tuple

# Project root paths
PROJECT_ROOT = Path(".")
REFERENCE_PROJECT = Path("../reference project")
REFERENCE_ROM = REFERENCE_PROJECT / "DQXI.3ds"
REFERENCE_CODE_BIN = REFERENCE_PROJECT / "workspace" / "extracted" / "exefs" / "code.bin"
REFERENCE_CODE_DECOMPRESSED = (
    REFERENCE_PROJECT / "workspace" / "extracted" / "exefs" / "code.decompressed.bin"
)

# Workspace output directories
ORIGINAL_DIR = PROJECT_ROOT / "original"
TOOLS_DIR = PROJECT_ROOT / "tools"
ASM_DIR = PROJECT_ROOT / "asm"
SRC_DIR = PROJECT_ROOT / "src"
INCLUDE_DIR = PROJECT_ROOT / "include"
BUILD_DIR = PROJECT_ROOT / "build"
SYMBOLS_FILE = PROJECT_ROOT / "symbols.json"
SECTIONS_LD_FILE = PROJECT_ROOT / "sections.ld"

# Documented Authoritative Hashes
EXPECTED_HASHES = {
    "rom": "0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74",
    "code_decompressed": "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8",
    "code_compressed": "ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f",
    "romfs": "8c108be136c23c57749fba24443038b71a30ffddf66f028d05f9252d1c4822bc",
    "exheader": "2e3524a5f34e1a809cf97576fab9da39ca0111c6d1af2bf45923b907896e5529",
    "exheader_sci_aci": "29fcfa7cb27fd3eb116b5f47cfa0e7a055c00f07e8d953fa01dc72ddf26d158d",
    "logo": "dd8c470edf60553b03fd5a42304923b47625409ae04d61a3208122547edc5150",
    "plain": "bdb97f48884f106df2b4db49303cd0742451acf41fac5ff4f9413a376b67831a",
    "exefs_header": "9f7d0958c2cf466e84f5728030807b64c74098534e568577226d1c8aabafb7e6",
    "banner": "d69bad5c4f9cf590e9b30b3315a5b5995117e3103e41dd0f73ac0d4c75281e44",
    "icon": "d5f3e27a4056c8d93b46f5d8aa70f5b9aaee24e2bc13ce03fc549c2522cffaa7",
    "manual_ncch": "af34d70b35352b65c8d3da81f74c5e748666bc7265e60f01b34f63967a26bee1",
    "update_n3ds_ncch": "f2a671c5fced8246bfaae5637219f5a6881a81a4fa3d6f43c63b19f9364ce724",
    "update_o3ds_ncch": "8039aa3d6e18bc5d2d53c6e4587044174e8764eb98c6a5650d9e2c4ce5274bdc",
}

# Documented Authoritative Sizes
EXPECTED_SIZES = {
    "rom": 4294967296,
    "code_decompressed": 7090176,
    "code_compressed": 3920924,
    "romfs": 2679185408,
    "exheader": 2048,
    "logo": 8192,
    "plain": 512,
    "banner": 458832,
    "icon": 14016,
    "manual_ncch": 1507328,
    "update_n3ds_ncch": 3653632,
    "update_o3ds_ncch": 33390592,
}

# Memory Map Specifications
MEMORY_MAP = {
    "text": {
        "start": 0x00100000,
        "end": 0x0072403C,
        "size": 0x0062403C,
        "tail_pad": 4036,
        "page_end": 0x00725000,
    },
    "rodata": {
        "start": 0x00725000,
        "end": 0x0079AA18,
        "size": 0x00075A18,
        "tail_pad": 1512,
        "page_end": 0x0079B000,
    },
    "data": {
        "start": 0x0079B000,
        "end": 0x007C2D24,
        "size": 0x00027D24,
        "tail_pad": 732,
        "page_end": 0x007C3000,
    },
    "bss": {
        "start": 0x007C3000,
        "end": 0x00839BC0,
        "size": 0x00076BC0,
    },
}

# Startup InitBss 24-byte golden machine code
INIT_BSS_HEX = "14009fe514109fe50020a0e3010050e104208034fcffff3a1eff2fe1242d7c00e4988300"
INIT_BSS_BYTES = bytes.fromhex(INIT_BSS_HEX)


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file in 1MB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hex digest of bytes in memory."""
    return hashlib.sha256(data).hexdigest()


def run_python_tool(
    script_path: Path, args: List[str], timeout: int = 60
) -> Tuple[int, str, str]:
    """Execute a python script with given arguments and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, str(script_path)] + args
    res = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return res.returncode, res.stdout, res.stderr


def tool_exists(tool_name: str) -> bool:
    """Check if a tool script exists in tools/ directory."""
    return (TOOLS_DIR / tool_name).is_file()


def require_tool(tool_name: str):
    """Decorator or check to skip test if tool is not yet implemented (progressive testability)."""
    p = TOOLS_DIR / tool_name
    return unittest.skipUnless(
        p.is_file(), f"Tool {tool_name} not yet implemented (Milestone dependency pending)"
    )


def require_file(file_path: Path, description: str = ""):
    """Skip test if file does not exist."""
    desc = description or str(file_path)
    return unittest.skipUnless(
        file_path.exists(), f"Required file '{desc}' is pending creation"
    )


def reference_snapshot() -> dict:
    """State of the read-only reference project that our tools could disturb.

    HEAD, a content hash of every modified/untracked file and the translation
    database's size and mtime. The reference project is also the user's own
    working copy, so it may legitimately be dirty: the invariant we test is
    that *this* project never changes it, i.e. the snapshot stays the same
    while our tools and tests run.
    """
    import hashlib
    import subprocess

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REFERENCE_PROJECT),
                          capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                            cwd=str(REFERENCE_PROJECT), capture_output=True, text=True).stdout
    files = {}
    for line in status.splitlines():
        name = line[3:].strip().strip('"').replace("\\", "/")
        path = REFERENCE_PROJECT / name
        files[name] = hashlib.sha1(path.read_bytes()).hexdigest() if path.is_file() else "<missing>"
    db = REFERENCE_PROJECT / "workspace" / "project.db"
    db_state = (db.stat().st_size, db.stat().st_mtime_ns) if db.is_file() else None
    return {"head": head, "files": files, "db": db_state}


# Taken when the test package is first imported, i.e. before any test runs.
REFERENCE_SNAPSHOT_AT_START = reference_snapshot() if (REFERENCE_PROJECT / ".git").is_dir() else None


def reference_changes_since_start() -> list[str]:
    """Human-readable differences between the reference project now and at start."""
    if REFERENCE_SNAPSHOT_AT_START is None:
        return []
    now = reference_snapshot()
    start = REFERENCE_SNAPSHOT_AT_START
    out = []
    if now["head"] != start["head"]:
        out.append(f"HEAD moved {start['head'][:10]} -> {now['head'][:10]}")
    for name in sorted(set(now["files"]) | set(start["files"])):
        if now["files"].get(name) != start["files"].get(name):
            out.append(f"changed: {name}")
    if now["db"] != start["db"]:
        out.append("workspace/project.db changed")
    return out


# Pre-existing modifications in reference project before this project was initiated
# (kept for reference; the invariant tests use the snapshot above instead)
BASELINE_TRACKED_MODIFICATIONS = {
    "dq11tool/bflyt.py",
    "dq11tool/codestr.py",
    "dq11tool/export.py",
    "dq11tool/fixes.py",
    "dq11tool/grammar.py",
    "dq11tool/grammar_asm.py",
    "dq11tool/grammar_code.py",
    "dq11tool/namefix.py",
    "dq11tool/project.py",
    "dq11tool/server.py",
    "dq11tool/texlabel.py",
    "dq11tool/textcodec.py",
    "dq11tool/web/app.js",
    "dq11tool/web/index.html",
    "emutest/grammartest.py",
}

