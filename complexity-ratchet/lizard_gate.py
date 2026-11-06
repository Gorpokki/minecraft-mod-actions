#!/usr/bin/env python3
"""Fail when a function is above a cyclomatic (CCN) or cognitive complexity limit.

CCN counts the paths through a function. Cognitive complexity (lizard -Ecognitive) counts how hard a function
is to read: nesting costs more. A reviewed exception is a `// #lizard forgive` comment inside the function.

Without --base, every function in every tracked file that matches the pathspecs is checked. With --base, only
changed functions count: a function fails when it is new or got worse and ends above a limit. Function moves
and renames count as new.

Usage: lizard_gate.py [--base REF] [--head REF] [--ccn-max N] [--cognitive-max N] [--pathspec GLOB ...]
"""
import argparse
import os
import subprocess
import sys

import lizard


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


def signature(function):
    """Name and parameter types, the identity of a function across revisions."""
    types = (' '.join(token for token in parameter.split()[:-1] if token != 'final')
             for parameter in function.full_parameters)
    return f"{function.name}({', '.join(types)})"


def complexity(analyzer, rev, path):
    """Map each function signature in one file to its [(CCN, cognitive), start line] versions."""
    try:
        source = git('show', f'{rev}:{path}')
    except subprocess.CalledProcessError:
        return {}
    functions = {}
    for function in analyzer.analyze_source_code(path, source).function_list:
        scores = (function.cyclomatic_complexity, function.cognitive_complexity)
        functions.setdefault(signature(function), []).append((scores, function.start_line))
    return functions


def ratchet(metrics, path, name, versions, old_versions):
    """Report each metric where a function is new or worse and ends above its limit. A new function's old score is 0."""
    old = old_versions[0][0] if len(versions) == len(old_versions) == 1 else (0,) * len(metrics)
    return [f'{path}:{line}: {name} {metric} {was} -> {score} (max {limit})'
            for scores, line in versions
            for (metric, limit), score, was in zip(metrics, scores, old)
            if score > max(limit, was)]


def every_function(analyzer, metrics, pathspecs):
    bad = []
    for path in git('ls-files', '--', *pathspecs).splitlines():
        for name, versions in complexity(analyzer, 'HEAD', path).items():
            bad += ratchet(metrics, path, name, versions, ())
    return bad


def changed_functions(analyzer, metrics, pathspecs, base, head):
    base = git('merge-base', base, head).strip()
    changes = git('diff', '--name-status', '--find-renames', '--diff-filter=AMR', base, head, '--', *pathspecs)
    bad = []
    for status, *paths in (line.split('\t') for line in changes.splitlines()):
        before, path = paths[0], paths[-1]
        old = complexity(analyzer, base, before) if status[0] != 'A' else {}
        for name, versions in complexity(analyzer, head, path).items():
            bad += ratchet(metrics, path, name, versions, old.get(name, ()))
    return bad


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--base', default='', help='Base ref. Empty checks every function.')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--ccn-max', type=int, default=10)
    parser.add_argument('--cognitive-max', type=int, default=15)
    parser.add_argument('--pathspec', action='append', default=[], help='git pathspec; repeatable. Default *.java')
    args = parser.parse_args(argv)
    pathspecs = args.pathspec or ['*.java']
    metrics = (('CCN', args.ccn_max), ('cognitive', args.cognitive_max))
    analyzer = lizard.FileAnalyzer(lizard.get_extensions(['cognitive']))
    if args.base:
        bad = changed_functions(analyzer, metrics, pathspecs, args.base, args.head)
    else:
        bad = every_function(analyzer, metrics, pathspecs)
    print('\n'.join(bad) or 'lizard gate: pass')
    if bad:
        print('Split the function, or add a reviewed `// #lizard forgive` comment inside it.')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
            out.write(f'findings={len(bad)}\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
