#!/usr/bin/env python3
"""Master E2E Test Suite Runner for Dragon Quest XI Matching Decompilation & Disassembly.

Executes all 4 test tiers:
- Tier 1: Feature Coverage (>= 70 tests across 14 features)
- Tier 2: Boundary Value Analysis & Error Handling (>= 70 tests across 14 features)
- Tier 3: Pairwise Combinatorial Cross-Feature Tests (>= 14 tests)
- Tier 4: Real-World End-to-End Scenarios (>= 7 scenarios)

Produces colorized terminal reports and enforces exit codes:
- 0: All suites passed (or skipped pending milestone implementation)
- 1: Failures or errors detected
"""

import argparse
import os
import sys
import time
import unittest
from pathlib import Path

# Optional colorama for ANSI terminal color formatting
try:
    import colorama
    from colorama import Fore, Style

    colorama.init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

    class Fore:
        GREEN = ""
        RED = ""
        YELLOW = ""
        CYAN = ""
        MAGENTA = ""
        WHITE = ""
        RESET = ""

    class Style:
        BRIGHT = ""
        RESET_ALL = ""


TESTS_ROOT = Path(__file__).resolve().parent

TIERS = [
    {
        "id": "tier1",
        "name": "Tier 1: Feature Coverage",
        "dir": TESTS_ROOT / "tier1_features",
        "min_tests": 70,
        "description": "Coverage across all 14 features (>=5 tests per feature)",
    },
    {
        "id": "tier2",
        "name": "Tier 2: Boundary & Corner Cases",
        "dir": TESTS_ROOT / "tier2_boundaries",
        "min_tests": 70,
        "description": "Boundary values, truncated inputs, corrupted padding & headers",
    },
    {
        "id": "tier3",
        "name": "Tier 3: Pairwise Combinations",
        "dir": TESTS_ROOT / "tier3_pairwise",
        "min_tests": 14,
        "description": "Cross-feature interactions across pipeline toolchains",
    },
    {
        "id": "tier4",
        "name": "Tier 4: Real-World Scenarios",
        "dir": TESTS_ROOT / "tier4_real_world",
        "min_tests": 7,
        "description": "End-to-end integration workflows & bit-matching verification",
    },
]


def print_banner():
    header = "=" * 80
    title = " DRAGON QUEST XI (3DS) - MATCHING DECOMPILATION E2E TEST SUITE "
    print(Fore.CYAN + Style.BRIGHT + header)
    print(Fore.CYAN + Style.BRIGHT + f"{title:^80}")
    print(Fore.CYAN + Style.BRIGHT + header)
    print(f"Test Root: {TESTS_ROOT}")
    print(f"Python:    {sys.version.split()[0]}")
    print(header + "\n")


def run_tier(tier_info, verbose=False, failfast=False):
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(tier_info["dir"]),
        pattern="test_*.py",
        top_level_dir=str(TESTS_ROOT.parent),
    )

    runner = unittest.TextTestRunner(
        verbosity=2 if verbose else 1,
        failfast=failfast,
    )

    start_time = time.time()
    result = runner.run(suite)
    elapsed = time.time() - start_time

    return {
        "tier": tier_info,
        "result": result,
        "elapsed": elapsed,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run E2E Test Suite for Dragon Quest XI Matching Decompilation."
    )
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Select specific tier to execute (default: all)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose test execution output",
    )
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Stop on first test failure",
    )
    args = parser.parse_args()

    print_banner()

    tiers_to_run = TIERS
    if args.tier != "all":
        tier_idx = int(args.tier) - 1
        tiers_to_run = [TIERS[tier_idx]]

    tier_results = []
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0
    total_run = 0
    total_elapsed = 0.0

    for tier in tiers_to_run:
        print(Fore.WHITE + Style.BRIGHT + f"\n>>> Executing {tier['name']}...")
        print(Fore.WHITE + f"    {tier['description']} (Threshold: >= {tier['min_tests']} tests)")

        res = run_tier(tier, verbose=args.verbose, failfast=args.failfast)
        tier_results.append(res)

        total_run += res["tests_run"]
        total_passed += res["passed"]
        total_failed += res["failures"]
        total_errors += res["errors"]
        total_skipped += res["skipped"]
        total_elapsed += res["elapsed"]

    # Summary Report Table
    print("\n" + "=" * 80)
    print(Fore.CYAN + Style.BRIGHT + f"{'TEST SUITE EXECUTION SUMMARY':^80}")
    print("=" * 80)
    print(
        f"{'Tier Name':<34} | {'Run':<5} | {'Pass':<5} | {'Skip':<5} | {'Fail':<5} | {'Time (s)':<8} | {'Status':<8}"
    )
    print("-" * 80)

    all_passed = True
    for tr in tier_results:
        t = tr["tier"]
        tier_failed = (tr["failures"] > 0) or (tr["errors"] > 0)
        if tier_failed:
            all_passed = False
            status_str = Fore.RED + Style.BRIGHT + "FAIL" + Style.RESET_ALL
        else:
            status_str = Fore.GREEN + Style.BRIGHT + "PASS" + Style.RESET_ALL

        print(
            f"{t['name']:<34} | {tr['tests_run']:<5} | {tr['passed']:<5} | "
            f"{tr['skipped']:<5} | {tr['failures'] + tr['errors']:<5} | "
            f"{tr['elapsed']:<8.2f} | {status_str}"
        )

    print("-" * 80)
    total_status = (
        Fore.GREEN + Style.BRIGHT + "SUCCESS" + Style.RESET_ALL
        if all_passed
        else Fore.RED + Style.BRIGHT + "FAILURE" + Style.RESET_ALL
    )
    print(
        f"{'TOTALS':<34} | {total_run:<5} | {total_passed:<5} | "
        f"{total_skipped:<5} | {total_failed + total_errors:<5} | "
        f"{total_elapsed:<8.2f} | {total_status}"
    )
    print("=" * 80)

    # Threshold Check
    print(f"\nTotal Test Cases Executed: {total_run} (Required: >= 161)")
    if total_run >= 161:
        print(Fore.GREEN + f"[OK] Coverage threshold met: {total_run} >= 161 test cases.")
    else:
        print(Fore.YELLOW + f"[WARN] Test count {total_run} is below 161 requirement.")

    if all_passed:
        print(Fore.GREEN + Style.BRIGHT + "\nALL TEST TIERS COMPLETED SUCCESSFULLY (Exit Code 0)\n")
        return 0
    else:
        print(Fore.RED + Style.BRIGHT + "\nTEST SUITE REPORTED FAILURES (Exit Code 1)\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
