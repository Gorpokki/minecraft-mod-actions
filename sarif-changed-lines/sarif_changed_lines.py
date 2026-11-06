#!/usr/bin/env python3
"""Fail on SARIF results: all of them, or with --base only results that overlap a line changed since that ref.

Some tools report every finding in each changed file, so this script decides what fails. Results of the rules
named by --skip-overridden-rule do not fail when the flagged declaration is annotated `@Override`, because an
overriding method cannot change its parameters.

Usage: sarif_changed_lines.py --sarif FILE|- [--base REF] [--skip-overridden-rule RULE ...]
"""
import argparse
import json
import os
import re
import subprocess
import sys

FILE = re.compile(r'^diff --git ', re.MULTILINE)
NEW_PATH = re.compile(r'^\+\+\+ b/(.+)$', re.MULTILINE)
HUNK = re.compile(r'^@@ -\S+ \+(\d+)(?:,(\d+))? @@', re.MULTILINE)


def changed_lines(diff):
    """Map each path in a `git diff -U0` to the set of line numbers it adds or changes."""
    changed = {}
    for section in FILE.split(diff)[1:]:
        header, _, hunks = section.partition('\n@@')
        path = NEW_PATH.search(header)
        if path:
            changed[path[1]] = added_lines('@@' + hunks)
    return changed


def added_lines(hunks):
    """The new-side line numbers of each `@@ -a,b +c,d @@` hunk header."""
    spans = ((int(h[1]), int(h[2] or 1)) for h in HUNK.finditer(hunks))
    return {line for start, count in spans for line in range(start, start + count)}


def read_lines(path):
    with open(path, encoding='utf-8') as source:
        return source.read().splitlines()


def overrides(source, start):
    """Whether the declaration starting on 1-based line `start` of `source` is annotated `@Override`."""
    line = start - 1
    if '@Override' in source[line]:
        return True
    line -= 1
    while line >= 0 and source[line].strip().startswith('@'):
        if source[line].strip().startswith('@Override'):
            return True
        line -= 1
    return False


def results(sarif, skip_rules=(), read=read_lines):
    """Each result as (path, its lines, `path:line: rule: message`), leaving out skipped overridden methods."""
    for result in (r for run in sarif['runs'] for r in run['results']):
        location = result['locations'][0]['physicalLocation']
        path, region = location['artifactLocation']['uri'], location['region']
        if result['ruleId'] in skip_rules and overrides(read(path), region['startLine']):
            continue
        lines = range(region['startLine'], region.get('endLine', region['startLine']) + 1)
        yield path, lines, f"{path}:{region['startLine']}: {result['ruleId']}: {result['message']['text']}"


def on_changed_lines(sarif, changed, skip_rules=(), read=read_lines):
    """Each result whose region overlaps a changed line of its file."""
    return [text for path, lines, text in results(sarif, skip_rules, read)
            if changed.get(path, set()).intersection(lines)]


def changed_since(base):
    diff_command = ['git', 'diff', '-U0', '--no-color', f'{base}...HEAD']
    return changed_lines(subprocess.run(diff_command, capture_output=True, text=True, check=True).stdout)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--sarif', required=True, help='SARIF file, or - for standard input.')
    parser.add_argument('--base', default='', help='Base ref. Empty fails on every result.')
    parser.add_argument('--skip-overridden-rule', action='append', default=[])
    args = parser.parse_args(argv)
    if args.sarif == '-':
        sarif = json.load(sys.stdin)
    else:
        with open(args.sarif, encoding='utf-8') as source:
            sarif = json.load(source)
    if args.base:
        found = on_changed_lines(sarif, changed_since(args.base), args.skip_overridden_rule)
    else:
        found = [text for _, _, text in results(sarif, args.skip_overridden_rule)]
    print('\n'.join(found) or 'sarif gate: pass')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
            out.write(f'findings={len(found)}\n')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
