#!/usr/bin/env python3
"""
Compact color-coded runner for the FlintParser/FlintNPC test suite.

Prints exactly one line per test case (status + test id, truncated to
fit under 80 columns) instead of unittest's default verbose output,
which wraps long dotted test names across multiple terminal lines.

Usage:
    python3 tests/run_tests.py
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_WIDTH = 79

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"
USE_COLOR = sys.stdout.isatty()


def _color(text, code):
    return f"{code}{text}{RESET}" if USE_COLOR else text


def _short_id(test):
    """<ClassName>.<method>, dropping the module prefix."""
    parts = test.id().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else test.id()


def _fit(label, prefix_width):
    budget = MAX_WIDTH - prefix_width
    if len(label) <= budget:
        return label
    return "\u2026" + label[-(budget - 1):]


class CompactResult(unittest.TextTestResult):
    def _emit(self, test, tag, color):
        prefix = f"{tag} "
        label = _fit(_short_id(test), len(prefix))
        self.stream.writeln(f"{_color(tag, color)} {label}")

    def addSuccess(self, test):
        super().addSuccess(test)
        self._emit(test, "OK  ", GREEN)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._emit(test, "FAIL", RED)

    def addError(self, test, err):
        super().addError(test, err)
        self._emit(test, "ERR ", RED)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._emit(test, "SKIP", YELLOW)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._emit(test, "OK  ", GREEN)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._emit(test, "FAIL", RED)


class CompactRunner(unittest.TextTestRunner):
    resultclass = CompactResult


def main():
    suite = unittest.TestLoader().discover(str(ROOT / "tests"))
    result = CompactRunner(verbosity=0).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
