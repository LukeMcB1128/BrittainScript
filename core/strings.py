"""Scan explicit interpolated strings without changing ordinary string values."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpressionText:
    text: str
    offset: int


@dataclass(frozen=True)
class CompiledPart:
    tree: object
    offset: int


@dataclass(frozen=True)
class StringTemplate:
    parts: tuple


class StringSyntaxError(ValueError):
    def __init__(self, message, offset):
        super().__init__(message)
        self.offset = offset


def decode_string(body):
    return body.encode('latin-1', 'backslashreplace').decode('unicode_escape')


def _quoted_end(source, start):
    index = start + 1
    while index < len(source):
        if source[index] == '\\':
            index += 2
        elif source[index] == '"':
            return index + 1
        else:
            index += 1
    raise StringSyntaxError('Unterminated string', start)


def _expression_end(source, start):
    closing = ['}']
    index = start
    pairs = {'(': ')', '[': ']', '{': '}'}
    while index < len(source):
        char = source[index]
        if char in 'fF' and source[index:index + 2].endswith('"'):
            _, index = scan_template(source, index)
            continue
        if char == '"':
            index = _quoted_end(source, index)
            continue
        if char in pairs:
            closing.append(pairs[char])
        elif char in ')]}':
            if char != closing[-1]:
                raise StringSyntaxError('Mismatched interpolation delimiter', index)
            closing.pop()
            if not closing:
                return index
        index += 1
    raise StringSyntaxError('Unterminated interpolation', start - 2)


def scan_template(source, start):
    index = start + 2
    literal, parts = [], []
    while index < len(source):
        char = source[index]
        if char == '\\':
            if index + 1 >= len(source):
                break
            # Escaping $ prevents interpolation; other escapes use normal rules.
            literal.append('$' if source[index + 1] == '$' else source[index:index + 2])
            index += 2
            continue
        if char == '"':
            parts.append(decode_string(''.join(literal)))
            return StringTemplate(tuple(parts)), index + 1
        if source[index:index + 2] == '${':
            parts.append(decode_string(''.join(literal)))
            literal.clear()
            end = _expression_end(source, index + 2)
            text = source[index + 2:end]
            if not text.strip():
                raise StringSyntaxError('Interpolation needs an expression', index + 2)
            parts.append(ExpressionText(text, index + 2))
            index = end + 1
            continue
        literal.append(char)
        index += 1
    raise StringSyntaxError('Unterminated interpolated string', start)


def code_mask(source):
    """Keep source positions, but mask strings for statement/comment scanning."""
    chars = list(source)
    index = 0
    while index < len(source):
        start = index
        try:
            if source[index:index + 2] in ('f"', 'F"'):
                _, index = scan_template(source, index)
            elif source[index] == '"':
                index = _quoted_end(source, index)
            else:
                index += 1
                continue
        except (StringSyntaxError, UnicodeError):
            # The lexer reports errors when this statement executes. Block
            # collection must not evaluate or validate skipped statements.
            index = len(source)
        chars[start:index] = ' ' * (index - start)
    return ''.join(chars)
