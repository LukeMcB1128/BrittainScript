#!/usr/bin/env python3
"""Translate every Python file under a folder into BrittainScript.

Walks a source tree, runs each .py file through py2bs, and writes the ones that
translate (and verify) into an output folder, mirroring the directory layout so
same-named files do not collide. Writes a REPORT.md next to them saying what was
rejected and why.

    python3 tools/build_bs_corpus.py
    python3 tools/build_bs_corpus.py --root ~/some/project --out ~/tmp/corpus
    python3 tools/build_bs_corpus.py --no-verify

Verification runs each translated program in both languages and compares their
output, which means it EXECUTES the Python. py2bs rejects imports, open(),
input() and eval() before that point, so anything reaching execution is inert,
but use --no-verify if you would rather nothing ran at all.

This file reads and decodes sources itself rather than handing a directory to
py2bs.report, so it behaves the same on any released version of py2bs.
"""

import argparse
import json
import pathlib
import sys
from collections import Counter

try:
    from py2bs import translate
except ImportError:
    sys.exit("Error: py2bs is not installed. Try: pip install -U brittainscript")

DEFAULT_ROOT = pathlib.Path.home() / 'Downloads' / 'Coding'
DEFAULT_OUT = DEFAULT_ROOT / 'bs-corpus'

# vendored or generated code: thousands of files, none of it yours
SKIP_DIRECTORIES = {
    '.git', '.hg', '.svn', '__pycache__', '.mypy_cache', '.pytest_cache',
    '.ruff_cache', '.tox', 'node_modules', 'site-packages', 'dist-info',
    'venv', '.venv', 'env', '.env', 'build', 'dist', 'egg-info',
    '.claude', '.idea', '.vscode',
}

MAX_BYTES = 500_000


def should_skip(path, output_root):
    if output_root in path.parents or path == output_root:
        return True
    for part in path.parts:
        if part in SKIP_DIRECTORIES or part.endswith('.egg-info'):
            return True
    return False


def read_source(path):
    try:
        if path.stat().st_size > MAX_BYTES:
            return None, 'file too large'
        return path.read_text(encoding='utf-8'), None
    except UnicodeDecodeError:
        return None, 'not utf-8'
    except OSError as error:
        return None, f'unreadable: {error}'


def build(root, output_root, verify, timeout):
    root = root.resolve()
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    rejections = Counter()
    mismatches = []
    written = []

    for path in sorted(root.rglob('*.py')):
        if should_skip(path, output_root):
            counts['skipped'] += 1
            continue

        source, problem = read_source(path)
        if source is None:
            counts['unreadable'] += 1
            rejections[problem] += 1
            continue

        counts['scanned'] += 1
        try:
            result = translate(source, verify=verify, timeout=timeout)
        except Exception as error:
            # a translator crash must not end the sweep
            counts['errored'] += 1
            rejections[f'py2bs error: {type(error).__name__}'] += 1
            continue

        if result.brittainscript is None:
            counts['rejected'] += 1
            for feature in result.rejected_features or ['unknown']:
                rejections[feature] += 1
            continue

        if not result.brittainscript.strip():
            # empty or comments-only source; nothing worth keeping
            counts['empty'] += 1
            continue

        if verify and not result.ok:
            counts['mismatched'] += 1
            mismatches.append((str(path.relative_to(root)), result.error or 'unknown'))
            continue

        relative = path.relative_to(root).with_suffix('.bs')
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result.brittainscript)
        counts['written'] += 1
        written.append(str(relative))

    return counts, rejections, mismatches, written


def format_report(root, counts, rejections, mismatches, written, verify):
    lines = []
    lines.append('# bs-corpus')
    lines.append('')
    lines.append(f'Source tree: `{root}`')
    lines.append(f'Verification: {"on" if verify else "off"}')
    lines.append('')
    lines.append('| | count |')
    lines.append('|---|---|')
    lines.append(f'| files scanned | {counts["scanned"]} |')
    lines.append(f'| written to bs-corpus | {counts["written"]} |')
    lines.append(f'| translated but empty | {counts["empty"]} |')
    if verify:
        lines.append(f'| output did not match | {counts["mismatched"]} |')
    lines.append(f'| rejected | {counts["rejected"]} |')
    lines.append(f'| unreadable | {counts["unreadable"]} |')
    lines.append(f'| vendored paths skipped | {counts["skipped"]} |')

    total_rejections = sum(rejections.values())
    if total_rejections:
        lines.append('')
        lines.append('## Why files were rejected')
        lines.append('')
        lines.append('The top row is the BrittainScript feature that would unlock the most code.')
        lines.append('')
        lines.append('| feature | share | count |')
        lines.append('|---|---|---|')
        for feature, count in rejections.most_common():
            share = 100.0 * count / total_rejections
            lines.append(f'| {feature} | {share:.1f}% | {count} |')

    if mismatches:
        lines.append('')
        lines.append('## Translated but output differed')
        lines.append('')
        for name, detail in mismatches[:40]:
            lines.append(f'- `{name}` — {detail}')

    if written:
        lines.append('')
        lines.append('## Written')
        lines.append('')
        for name in written:
            lines.append(f'- `{name}`')

    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=pathlib.Path, default=DEFAULT_ROOT)
    parser.add_argument('--out', type=pathlib.Path, default=None)
    parser.add_argument('--no-verify', action='store_true')
    parser.add_argument('--timeout', type=int, default=10)
    arguments = parser.parse_args(argv)

    root = arguments.root.expanduser()
    if not root.is_dir():
        sys.exit(f'Error: {root} is not a directory')
    output_root = (arguments.out or (root / 'bs-corpus')).expanduser()
    verify = not arguments.no_verify

    print(f'scanning {root} ...')
    counts, rejections, mismatches, written = build(
        root, output_root, verify, arguments.timeout
    )

    report = format_report(root, counts, rejections, mismatches, written, verify)
    (output_root / 'REPORT.md').write_text(report)
    (output_root / 'manifest.json').write_text(
        json.dumps(
            {
                'root': str(root),
                'verified': verify,
                'counts': dict(counts),
                'rejections': dict(rejections),
                'written': written,
            },
            indent=2,
        )
        + '\n'
    )

    print(f'scanned   {counts["scanned"]}')
    print(f'written   {counts["written"]}  -> {output_root}')
    print(f'empty     {counts["empty"]}')
    if verify:
        print(f'mismatch  {counts["mismatched"]}')
    print(f'rejected  {counts["rejected"]}')
    print(f'report    {output_root / "REPORT.md"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
