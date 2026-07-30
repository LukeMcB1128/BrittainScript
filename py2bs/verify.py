"""Differential execution: run both programs, compare stdout.

Both run in a subprocess with a timeout so a translated infinite loop cannot
hang the caller. The Python side runs with -I so it ignores the environment and
the user's site-packages.
"""

import os
import subprocess
import sys
import tempfile

DEFAULT_TIMEOUT = 10

# run.py only exists in a source checkout, so drive the interpreter through the
# core package instead -- that works from the repo and from an installed wheel
BS_RUNNER = (
    'import sys; sys.path.insert(0, sys.argv[1]); '
    'from core import main; main.run_file(sys.argv[2])'
)


def core_package_parent():
    import core

    return os.path.dirname(os.path.dirname(os.path.abspath(core.__file__)))


class ExecutionResult:
    def __init__(self, stdout, error=None, timed_out=False):
        self.stdout = stdout
        self.error = error
        self.timed_out = timed_out

    @property
    def ok(self):
        return self.error is None and not self.timed_out


def run_python(source, timeout=DEFAULT_TIMEOUT):
    return _run_source(source, '.py', [sys.executable, '-I'], timeout)


def run_brittainscript(source, timeout=DEFAULT_TIMEOUT):
    command = [sys.executable, '-c', BS_RUNNER, core_package_parent()]
    return _run_source(source, '.bs', command, timeout)


def _run_source(source, suffix, command, timeout):
    handle = tempfile.NamedTemporaryFile('w', suffix=suffix, delete=False)
    try:
        handle.write(source)
        handle.close()
        try:
            completed = subprocess.run(
                command + [handle.name],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir(),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult('', error=f'timed out after {timeout}s', timed_out=True)
        if completed.returncode != 0:
            return ExecutionResult(completed.stdout, error=completed.stderr.strip() or 'non-zero exit')
        return ExecutionResult(completed.stdout)
    finally:
        os.unlink(handle.name)


def compare(python_source, brittainscript_source, timeout=DEFAULT_TIMEOUT):
    python_result = run_python(python_source, timeout)
    bs_result = run_brittainscript(brittainscript_source, timeout)
    if not python_result.ok:
        return False, python_result, bs_result, f'python failed: {python_result.error}'
    if not bs_result.ok:
        return False, python_result, bs_result, f'brittainscript failed: {bs_result.error}'
    # the interpreter reports problems on stdout and keeps going, so a program
    # that "succeeded" may still have printed an error
    for line in bs_result.stdout.splitlines():
        if line.startswith(('Error:', 'Syntax error', 'Undefined ')):
            return False, python_result, bs_result, f'interpreter reported: {line}'
    if python_result.stdout != bs_result.stdout:
        return False, python_result, bs_result, 'stdout mismatch'
    return True, python_result, bs_result, None
