"""py2bs -- translate a subset of Python into BrittainScript.

The public entry point is translate(). Set verify=True to run both programs
and compare their stdout, which is what makes a translation trustworthy.
"""

from .errors import UnsupportedFeature
from .translate import TranslationResult, translate

__all__ = ['translate', 'TranslationResult', 'UnsupportedFeature']
