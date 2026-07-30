"""The public entry point."""

from .emitter import emit
from .errors import UnsupportedFeature
from .frontend import parse_and_validate
from .lowering import lower
from .verify import compare


class TranslationResult:
    def __init__(self):
        self.ok = False
        self.brittainscript = None
        self.rejected_features = []
        self.python_stdout = None
        self.bs_stdout = None
        self.error = None

    def __repr__(self):
        state = 'ok' if self.ok else f'failed ({self.error})'
        return f'<TranslationResult {state}>'


def translate(python_source, verify=True, timeout=10):
    result = TranslationResult()
    try:
        tree = parse_and_validate(python_source)
    except UnsupportedFeature as rejection:
        result.rejected_features = [rejection.feature]
        result.error = str(rejection)
        return result

    try:
        result.brittainscript = emit(lower(tree))
    except UnsupportedFeature as rejection:
        result.rejected_features = [rejection.feature]
        result.error = str(rejection)
        return result

    if not verify:
        result.ok = True
        return result

    matched, python_result, bs_result, error = compare(
        python_source, result.brittainscript, timeout
    )
    result.python_stdout = python_result.stdout
    result.bs_stdout = bs_result.stdout
    result.ok = matched
    result.error = error
    return result
