"""CLI entry point for running as module.

Usage:
    python -m app.eval_runtime [options]
"""

from app.eval_runtime.cli import main

if __name__ == "__main__":
    exit(main())