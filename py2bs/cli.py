"""Command line front end: bs-from-python"""

import argparse
import os
import sys

from .report import run_corpus
from .translate import translate


def build_parser():
    parser = argparse.ArgumentParser(
        prog='bs-from-python',
        description='Translate a subset of Python into BrittainScript.',
    )
    parser.add_argument('path', help='a .py file, or a directory to report on')
    parser.add_argument('--out', help='write the BrittainScript here instead of stdout')
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='skip running both programs and comparing their output',
    )
    parser.add_argument(
        '--timeout', type=int, default=10, help='seconds allowed per program (default 10)'
    )
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    verify = not arguments.no_verify

    if os.path.isdir(arguments.path):
        report = run_corpus(arguments.path, verify=verify, timeout=arguments.timeout)
        print(report.format())
        return 0

    try:
        with open(arguments.path) as handle:
            source = handle.read()
    except OSError as error:
        print(f'Error: could not read {arguments.path}: {error}', file=sys.stderr)
        return 2

    result = translate(source, verify=verify, timeout=arguments.timeout)

    if result.brittainscript is None:
        print(f'Error: cannot translate {arguments.path}', file=sys.stderr)
        print(f'  {result.error}', file=sys.stderr)
        return 1

    if arguments.out:
        with open(arguments.out, 'w') as handle:
            handle.write(result.brittainscript)
        print(f'wrote {arguments.out}')
    else:
        sys.stdout.write(result.brittainscript)

    if verify and not result.ok:
        print(f'Error: verification failed: {result.error}', file=sys.stderr)
        if result.python_stdout is not None:
            print('--- python stdout ---', file=sys.stderr)
            sys.stderr.write(result.python_stdout)
            print('--- brittainscript stdout ---', file=sys.stderr)
            sys.stderr.write(result.bs_stdout or '')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
