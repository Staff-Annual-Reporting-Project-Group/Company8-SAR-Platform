"""
Custom test runner for the SAR Platform.

Runs unit and integration tests in clearly labelled sections and prints each
test's docstring so the terminal output reads like a plain-English test report.

Usage:
    python manage.py test --testrunner=test_runner.SARTestRunner
    python manage.py test users.tests --testrunner=test_runner.SARTestRunner
"""

import unittest
from django.test.runner import DiscoverRunner


# ── colour helpers (ANSI — work in bash/PowerShell) ─────────────────────────

RESET  = '\033[0m'
BOLD   = '\033[1m'
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
WHITE  = '\033[97m'
DIM    = '\033[2m'


def _c(text, *codes):
    return ''.join(codes) + text + RESET


# ── custom result ─────────────────────────────────────────────────────────────

class SARTestResult(unittest.TestResult):
    """
    Prints a one-line description for every test, then PASS / FAIL / ERROR
    on the same line once it finishes.
    """

    separator = _c('  ' + '-' * 68, DIM)

    def __init__(self, stream, verbosity=2):
        super().__init__(stream, True, verbosity)
        self.stream = stream
        self._current_desc = ''

    # called before each test
    def startTest(self, test):
        super().startTest(test)
        doc  = test.shortDescription() or ''
        name = test._testMethodName
        self._current_desc = doc or name
        label = f'  {_c(self._current_desc, WHITE)}'
        self.stream.write(f'{label:<80}')
        self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.write(_c('PASS', GREEN) + '\n')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.write(_c('FAIL', RED) + '\n')

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.write(_c('ERROR', YELLOW) + '\n')

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.stream.write(_c(f'SKIP ({reason})', DIM) + '\n')

    def printErrors(self):
        """Print full tracebacks for failures/errors after the run."""
        if self.failures or self.errors:
            self.stream.write('\n' + _c('FAILURES / ERRORS', BOLD + RED) + '\n')
            self.stream.write(_c('=' * 70, RED) + '\n')
        for test, err in self.failures:
            self.stream.write(
                _c(f'\nFAIL: {test._testMethodName}', BOLD + RED) + '\n'
                + _c(test.shortDescription() or '', DIM) + '\n'
                + err + '\n'
            )
        for test, err in self.errors:
            self.stream.write(
                _c(f'\nERROR: {test._testMethodName}', BOLD + YELLOW) + '\n'
                + _c(test.shortDescription() or '', DIM) + '\n'
                + err + '\n'
            )


# ── section banner helper ─────────────────────────────────────────────────────

def _print_banner(stream, title):
    width = 70
    stream.write('\n')
    stream.write(_c('=' * width, CYAN) + '\n')
    stream.write(_c(f'  {title}', BOLD + CYAN) + '\n')
    stream.write(_c('=' * width, CYAN) + '\n')


def _print_summary(stream, result, label):
    total  = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    colour = GREEN if failed == 0 else RED
    stream.write(
        f'\n  {_c(label, BOLD)}  '
        f'{_c(str(passed), GREEN)} passed  '
        f'{_c(str(failed), colour)} failed  '
        f'({total} total)\n'
    )


# ── runner ────────────────────────────────────────────────────────────────────

class SARTestRunner(DiscoverRunner):
    """
    Discovers tests under  <app>/tests/unit/  and  <app>/tests/integration/
    and runs them in two clearly labelled sections.
    """

    # Apps whose tests we manage
    APPS = ['users', 'reports', 'administration']

    def build_suite(self, test_labels=None, **kwargs):
        return super().build_suite(test_labels or [], **kwargs)

    def _collect(self, pattern):
        """Return a TestSuite for all tests matching dotted-path pattern.

        Uses discover() on the subpackage directory so all test_*.py files
        inside unit/ or integration/ are picked up.  Silently skips apps
        that haven't adopted the split layout yet.
        """
        import importlib, os
        loader = unittest.TestLoader()
        suite  = unittest.TestSuite()
        for app in self.APPS:
            label = f'{app}.tests.{pattern}'
            try:
                pkg = importlib.import_module(label)
                pkg_dir = os.path.dirname(pkg.__file__)
                app_pkg = importlib.import_module(app)
                top_level_dir = os.path.dirname(os.path.dirname(app_pkg.__file__))
                found = loader.discover(start_dir=pkg_dir, pattern='test_*.py',
                                        top_level_dir=top_level_dir)
                suite.addTests(found)
            except (ModuleNotFoundError, AttributeError, ImportError):
                pass
        return suite

    def run_tests(self, test_labels, **kwargs):
        self.setup_test_environment()
        old_config = self.setup_databases()

        import sys
        stream = sys.stderr

        total_failures = 0

        for section_title, pattern in [
            ('UNIT TESTS  —  models, properties, isolated logic', 'unit'),
            ('INTEGRATION TESTS  —  HTTP requests, views, database', 'integration'),
        ]:
            suite = self._collect(pattern)
            if suite.countTestCases() == 0:
                continue

            _print_banner(stream, section_title)
            stream.write(
                _c(f'  {suite.countTestCases()} test(s) found\n', DIM)
            )
            stream.write('\n')

            result = SARTestResult(stream)
            suite.run(result)
            result.printErrors()
            _print_summary(stream, result, section_title.split('—')[0].strip())
            total_failures += len(result.failures) + len(result.errors)

        # final overall line
        stream.write('\n' + _c('=' * 70, CYAN) + '\n')
        if total_failures == 0:
            stream.write(_c('  ALL TESTS PASSED\n', BOLD + GREEN))
        else:
            stream.write(_c(f'  {total_failures} TEST(S) FAILED\n', BOLD + RED))
        stream.write(_c('=' * 70, CYAN) + '\n\n')

        self.teardown_databases(old_config)
        self.teardown_test_environment()
        return total_failures
