"""Rejection telemetry over a corpus of Python files.

The frequency table is a roadmap: it says which missing BrittainScript feature
would unlock the most real-world Python.
"""

import pathlib
from collections import Counter

from .translate import translate


class CorpusReport:
    def __init__(self):
        self.translated = 0
        self.verified = 0
        self.rejected = 0
        self.mismatched = 0
        self.feature_counts = Counter()
        self.failures = []

    @property
    def total(self):
        return self.translated + self.rejected

    def rejection_table(self):
        if not self.rejected:
            return []
        rows = []
        for feature, count in self.feature_counts.most_common():
            rows.append((feature, count, 100.0 * count / self.rejected))
        return rows

    def format(self):
        lines = []
        lines.append(f'files scanned:  {self.total}')
        lines.append(f'translated:     {self.translated}')
        lines.append(f'verified ok:    {self.verified}')
        lines.append(f'output differed:{self.mismatched:>3}')
        lines.append(f'rejected:       {self.rejected}')
        rows = self.rejection_table()
        if rows:
            lines.append('')
            lines.append('rejected features, by share of rejections:')
            width = max(len(feature) for feature, _, _ in rows)
            for feature, count, share in rows:
                lines.append(f'  {feature.ljust(width)}  {share:5.1f}%  ({count})')
        if self.failures:
            lines.append('')
            lines.append('output mismatches:')
            for name, detail in self.failures:
                lines.append(f'  {name}: {detail}')
        return '\n'.join(lines)


def run_corpus(directory, verify=True, timeout=10):
    report = CorpusReport()
    paths = sorted(pathlib.Path(directory).rglob('*.py'))
    for path in paths:
        try:
            source = path.read_text()
        except (OSError, UnicodeDecodeError) as error:
            report.rejected += 1
            report.feature_counts['unreadable file'] += 1
            report.failures.append((path.name, str(error)))
            continue
        result = translate(source, verify=verify, timeout=timeout)
        if result.rejected_features:
            report.rejected += 1
            for feature in result.rejected_features:
                report.feature_counts[feature] += 1
            continue
        report.translated += 1
        if not verify:
            continue
        if result.ok:
            report.verified += 1
        else:
            report.mismatched += 1
            report.failures.append((path.name, result.error or 'unknown'))
    return report
