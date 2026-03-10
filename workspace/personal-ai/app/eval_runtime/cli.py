"""Evaluation CLI Module.

Command-line interface for running evaluation tests.

Usage:
    # Run single test
    python -m app.eval_runtime --test td_help

    # Run all critical tests
    python -m app.eval_runtime --severity critical

    # Run all TouchDesigner tests
    python -m app.eval_runtime --domain touchdesigner

    # Run all tests with output
    python -m app.eval_runtime --output data/eval_reports/full_eval.json

    # Check for regressions
    python -m app.eval_runtime --baseline data/eval_reports/baseline.json
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.eval_runtime.models import EvalDomain, EvalSeverity, EvalSuiteReport
from app.eval_runtime.registry import EVAL_TESTS, list_test_names
from app.eval_runtime.regression import RegressionDetector
from app.eval_runtime.runner import EvalSuiteRunner


class EvalCLI:
    """Command-line interface for evaluation."""

    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create argument parser.

        Returns:
            Configured ArgumentParser
        """
        parser = argparse.ArgumentParser(
            prog="python -m app.eval_runtime",
            description="Run personal-ai evaluation tests",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run all tests
  python -m app.eval_runtime

  # Run specific test
  python -m app.eval_runtime --test td_help

  # Run critical tests only
  python -m app.eval_runtime --severity critical

  # Run Houdini tests
  python -m app.eval_runtime --domain houdini

  # Save report to file
  python -m app.eval_runtime --output eval_report.json

  # Check for regressions against baseline
  python -m app.eval_runtime --baseline data/eval_reports/baseline.json

  # Set current report as new baseline
  python -m app.eval_runtime --set-baseline data/eval_reports/baseline.json
            """,
        )

        parser.add_argument(
            "--test",
            type=str,
            metavar="NAME",
            help="Run specific test by name (e.g., 'td_help')",
        )

        parser.add_argument(
            "--domain",
            type=str,
            choices=["touchdesigner", "houdini", "vfx", "general"],
            help="Run tests for specific domain",
        )

        parser.add_argument(
            "--severity",
            type=str,
            choices=["critical", "high", "medium", "low"],
            help="Run tests with minimum severity level",
        )

        parser.add_argument(
            "--output",
            type=str,
            metavar="FILE",
            default="data/eval_reports/eval_{timestamp}.json",
            help="Output report file path (default: data/eval_reports/eval_{timestamp}.json)",
        )

        parser.add_argument(
            "--sequential",
            action="store_true",
            help="Run tests sequentially instead of parallel",
        )

        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Verbose output with progress",
        )

        parser.add_argument(
            "--baseline",
            type=str,
            metavar="FILE",
            help="Compare against baseline report for regression detection",
        )

        parser.add_argument(
            "--set-baseline",
            type=str,
            metavar="FILE",
            help="Save current report as new baseline",
        )

        parser.add_argument(
            "--list",
            action="store_true",
            help="List all available tests",
        )

        parser.add_argument(
            "--quick",
            action="store_true",
            help="Run quick check (critical tests only)",
        )

        return parser

    @staticmethod
    async def run_from_args(args: argparse.Namespace) -> EvalSuiteReport:
        """Run evaluation based on CLI args.

        Args:
            args: Parsed command-line arguments

        Returns:
            EvalSuiteReport with results
        """
        runner = EvalSuiteRunner(verbose=args.verbose)

        # Handle --list
        if args.list:
            print("\nAvailable tests:")
            print("-" * 50)
            for name in sorted(list_test_names()):
                test = EVAL_TESTS[name]
                print(f"  {name:20s} [{test.domain.value:15s}] {test.severity.value:8s}")
                print(f"    {test.description}")
            print()
            return EvalSuiteReport.empty()

        # Handle --quick
        if args.quick:
            args.severity = "critical"

        # Run tests
        if args.test:
            # Run single test
            if args.test not in EVAL_TESTS:
                print(f"[EVAL] Test not found: {args.test}")
                print(f"[EVAL] Available tests: {', '.join(list_test_names())}")
                sys.exit(1)

            print(f"[EVAL] Running single test: {args.test}")
            report = await runner.run_all_tests(test_names=[args.test])

        else:
            # Run suite with filters
            domain = EvalDomain(args.domain) if args.domain else None
            severity = EvalSeverity(args.severity) if args.severity else None

            report = await runner.run_all_tests(
                domain=domain,
                severity=severity,
                parallel=not args.sequential,
            )

        return report

    @staticmethod
    def process_output(
        args: argparse.Namespace,
        report: EvalSuiteReport,
    ) -> None:
        """Process output and save reports.

        Args:
            args: Parsed command-line arguments
            report: Evaluation report
        """
        # Print summary
        print(report.summary())

        # Handle baseline comparison
        if args.baseline:
            detector = RegressionDetector(baseline_report_path=args.baseline)
            regression_report = detector.detect_regressions(report)

            print(regression_report.summary())

            if regression_report.has_critical_regressions:
                print("[EVAL] CRITICAL REGRESSIONS DETECTED!")

        # Save report
        if args.output:
            output_path = args.output.replace(
                "{timestamp}",
                datetime.now().strftime("%Y%m%d_%H%M%S"),
            )
            report.to_file(output_path)

        # Set as new baseline
        if args.set_baseline:
            report.to_file(args.set_baseline)
            print(f"[EVAL] New baseline saved: {args.set_baseline}")


def main() -> int:
    """Main entry point for CLI.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = EvalCLI.create_parser()
    args = parser.parse_args()

    # Run evaluation
    report = asyncio.run(EvalCLI.run_from_args(args))

    # Skip output for --list
    if args.list:
        return 0

    # Process output
    EvalCLI.process_output(args, report)

    # Exit with appropriate code
    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())