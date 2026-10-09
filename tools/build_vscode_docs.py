"""Build vscode-extension/docs.json, the hover and completion text for the VS Code extension.

The language reference is the source of truth: every table row whose first
cell is a call such as `len(value)` or `ui.button(label, handler)` becomes an
entry. Library functions that the reference does not list fall back to the
comment above their `func` line in libs/*.bs.

Run after changing the reference or a library:
    python3 tools/build_vscode_docs.py
"""

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'Documentation' / 'LANGUAGE_REFERENCE.md'
LIBS = ROOT / 'libs'
OUTPUT = ROOT / 'vscode-extension' / 'docs.json'
GRAMMAR = ROOT / 'vscode-extension' / 'syntaxes' / 'brittainscript.tmLanguage.json'
# block forms are highlighted as keywords instead
NOT_HIGHLIGHTED = {'cond', 'if'}

MODULES = ('math', 'convert', 'io', 'datetime', 'terminal', 'gui', 'json', 'store',
           'http', 'server', 'ui', 'web', 'net')
# example receivers used in the reference's method tables
RECEIVERS = {'text': 'string', 'name': 'string', 'items': 'list', 'record': 'dictionary',
             'vault': 'store', 'problem': 'error', 'separator': 'string'}
CALL = re.compile(r'^([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))?\((.*)\)$')
# shown when hovering over `add name`
SUMMARIES = {
    'math': 'Number helpers: max, min, abs, clamp, factorial, pow.',
    'convert': 'Unit conversions for length, temperature, energy, pressure and weight.',
    'io': 'Read, write, append, check and delete files.',
    'datetime': 'Current date and time, formatting, parsing and date parts.',
    'terminal': 'Text helpers for terminal output: padding, rules, panels and meters.',
    'gui': 'Tkinter desktop windows, widgets and canvas drawing.',
    'json': 'Parse and write JSON text and files.',
    'store': 'Persistent JSON dictionaries saved to a file, with locked updates.',
    'http': 'Send HTTP requests and read status, headers, text and JSON.',
    'server': 'Multithreaded HTTP API server. Needs the server extra.',
    'ui': 'HTML desktop apps: view(state) returns elements, events call your handlers.',
    'web': 'A small HTTP/1.1 server written in BrittainScript.',
    'net': 'Socket primitives that web and ui are built on.',
}
# described in prose rather than a table
EXTRA = {
    ('store', 'open'): ('store.open(path)', 'Open or create a JSON store file and return a store object with get, set, has, delete, keys, snapshot, update and transaction.'),
}


def plain(text):
    """Markdown cell text for a hover: keep code spans, drop link targets."""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text).strip()
    return text[:1].upper() + text[1:]


def table_rows(markdown):
    heading = ''
    for line in markdown.splitlines():
        if line.startswith('#'):
            heading = line.lstrip('#').strip().strip('`')
        elif line.startswith('|') and not re.match(r'^\|\s*-', line):
            cells = [cell.strip() for cell in line.strip().strip('|').split(' | ')]
            if len(cells) >= 2:
                yield heading, cells


def add_entry(bucket, name, signature, doc):
    entries = bucket.setdefault(name, [])
    if not any(entry['signature'] == signature for entry in entries):
        entries.append({'signature': signature, 'doc': doc})


def from_reference(docs):
    for heading, cells in table_rows(REFERENCE.read_text(encoding='utf-8')):
        description = plain(cells[1])
        for code in re.findall(r'`([^`]+)`', cells[0]):
            match = CALL.match(code)
            if not match:
                continue
            first, second, _ = match.groups()
            if second is None:
                if re.match(r'^\w+\("', code):
                    continue  # datetime("now") style command rows
                add_entry(docs['builtins'], first, code, description)
            elif first in MODULES:
                add_entry(docs['modules'].setdefault(first, {}), second, code, description)
            elif first in RECEIVERS:
                kind = RECEIVERS[first]
                entries = docs['methods'].setdefault(second, [])
                if not any(entry['signature'] == code for entry in entries):
                    entries.append({'signature': code, 'doc': description, 'kind': kind})


def from_libraries(docs):
    for path in sorted(LIBS.glob('*.bs')):
        module = path.stem
        lines = path.read_text(encoding='utf-8').splitlines()
        functions = docs['modules'].setdefault(module, {})
        for index, line in enumerate(lines):
            match = re.match(r'^func\s+([A-Za-z]\w*)\s*\(([^)]*)\)', line)
            if not match or match.group(1) in functions:
                continue
            comment = []
            back = index - 1
            while back >= 0 and lines[back].startswith('#'):
                comment.insert(0, lines[back].lstrip('#').strip())
                back -= 1
            name, params = match.groups()
            text = ' '.join(comment) or 'Function from the ' + module + ' library.'
            add_entry(functions, name, f'{module}.{name}({params.strip()})', text[:1].upper() + text[1:])


def main():
    docs = {'builtins': {}, 'modules': {}, 'methods': {}, 'libraries': {}}
    from_reference(docs)
    from_libraries(docs)
    for (module, name), (signature, doc) in EXTRA.items():
        add_entry(docs['modules'].setdefault(module, {}), name, signature, doc)
    docs['libraries'] = dict(SUMMARIES)
    OUTPUT.write_text(json.dumps(docs, indent=1, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    grammar = json.loads(GRAMMAR.read_text(encoding='utf-8'))
    names = sorted(set(docs['builtins']) - NOT_HIGHLIGHTED)
    grammar['repository']['builtins']['match'] = '\\b(' + '|'.join(names) + ')\\b(?=\\s*\\()'
    GRAMMAR.write_text(json.dumps(grammar, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    counts = (len(docs['builtins']), sum(len(funcs) for funcs in docs['modules'].values()), len(docs['methods']))
    print(f'Wrote {OUTPUT.relative_to(ROOT)}: {counts[0]} built-ins, {counts[1]} library functions, {counts[2]} methods')


if __name__ == '__main__':
    main()
