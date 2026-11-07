#!/usr/bin/env python3
"""Fail when a function is above a cyclomatic (CCN) or cognitive complexity limit.

CCN counts the paths through a function. Cognitive complexity (lizard -Ecognitive) counts how hard a function
is to read: nesting costs more. A reviewed exception is a `// #lizard forgive` comment inside the function.

Without --base, every function in every tracked file that matches the pathspecs is checked. With --base, only
changed functions count: a function fails when it is new or got worse and ends above a limit. Function moves
and renames count as new.

Usage: lizard_gate.py [--base REF] [--ccn-max N] [--cognitive-max N] [--pathspec GLOB ...] [--extensions EXT ...]
"""
import argparse
import ast
import os
import re
import subprocess
import sys

import lizard


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


MODIFIERS = re.compile(r'\bfinal\b|@ [\w$]+(?: \. [\w$]+)*')
PARAMETER_NAME = re.compile(r' [\w$]+((?: \[ \])*)$')


def parameter_type(parameter):
    """Type of one lizard parameter, without annotations, final, or the name."""
    text = ' ' + MODIFIERS.sub(' ', parameter)
    return ' '.join(PARAMETER_NAME.sub(r'\1', text).split())


SOURCES = ('.py', '.js', '.cjs', '.cs', '.java')


def python_names(source):
    """Map the start line of each Python function to its AST-qualified name, such as `A.judge`."""
    names = {}

    def visit(node, scopes=()):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = (*scopes, child.name)
                if not isinstance(child, ast.ClassDef):
                    names[child.lineno] = '.'.join(name)
                visit(child, name)
            else:
                visit(child, scopes)

    try:
        visit(ast.parse(source))
    except (SyntaxError, ValueError):
        pass
    return names


def signature(function):
    """Qualified name and parameter types, minus parameter names, final, and annotations. long_name gives the scope when it has one; name is used otherwise, since long_name omits the owner of a top-level enum constant body."""
    qualified = function.long_name.split('(')[0].strip()
    if '::' not in qualified:
        qualified = function.name
    types = (parameter_type(parameter) for parameter in function.full_parameters)
    return f"{qualified}({', '.join(types)})"


def complexity(analyzer, rev, path):
    """Map each function signature in one file to its [(CCN, cognitive), start line] versions."""
    try:
        source = git('show', f'{rev}:{path}')
    except subprocess.CalledProcessError:
        return {}
    names = python_names(source) if path.endswith('.py') else {}
    functions = {}
    for function in analyzer.analyze_source_code(path, source).function_list:
        scores = (function.cyclomatic_complexity, function.cognitive_complexity)
        key = names.get(function.start_line) or signature(function)
        functions.setdefault(key, []).append((scores, function.start_line))
    return functions


def ratchet(metrics, path, name, versions, old_versions):
    """Report each metric where a function is new or worse and ends above its limit. A new function's old score is 0."""
    paired = [[0] * len(metrics) for _ in versions]
    for m in range(len(metrics)):
        olds = sorted((scores[m] for scores, _ in old_versions), reverse=True) + [0] * len(versions)
        ranked = sorted(range(len(versions)), key=lambda i: versions[i][0][m], reverse=True)
        for i, old in zip(ranked, olds):
            paired[i][m] = old
    return [f'{path}:{line}: {name} {metric} {paired[i][m]} -> {score} (max {limit})'
            for i, (scores, line) in enumerate(versions)
            for m, ((metric, limit), score) in enumerate(zip(metrics, scores))
            if score > max(limit, paired[i][m])]


def wanted(path, extensions):
    return extensions is None or path.endswith(extensions)


def every_function(analyzer, metrics, pathspecs, extensions):
    bad, checked, skipped = [], 0, 0
    for path in git('ls-files', '--', *pathspecs).splitlines():
        if not wanted(path, extensions):
            skipped += 1
            continue
        checked += 1
        for name, versions in complexity(analyzer, 'HEAD', path).items():
            bad += ratchet(metrics, path, name, versions, ())
    return bad, checked, skipped


def changed_functions(analyzer, metrics, pathspecs, base, extensions):
    base = git('merge-base', base, 'HEAD').strip()
    changes = git('diff', '--name-status', '--find-renames', '--diff-filter=AMR', base, 'HEAD', '--', *pathspecs)
    bad, checked, skipped = [], 0, 0
    for status, *paths in (line.split('\t') for line in changes.splitlines()):
        before, path = paths[0], paths[-1]
        if not wanted(path, extensions):
            skipped += 1
            continue
        checked += 1
        old = complexity(analyzer, base, before) if status[0] != 'A' else {}
        for name, versions in complexity(analyzer, 'HEAD', path).items():
            bad += ratchet(metrics, path, name, versions, old.get(name, ()))
    return bad, checked, skipped


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--base', default='', help='Base ref. Empty checks every function.')
    parser.add_argument('--ccn-max', type=int, default=10)
    parser.add_argument('--cognitive-max', type=int, default=15)
    parser.add_argument('--pathspec', action='append', default=[], help='git pathspec; repeatable. Default *.java')
    parser.add_argument('--extensions', nargs='+', default=list(SOURCES), help="File extensions to check, or '*' for every matched file. Default: %(default)s")
    args = parser.parse_args(argv)
    extensions = None if '*' in args.extensions else tuple(args.extensions)
    pathspecs = args.pathspec or ['*.java']
    metrics = (('CCN', args.ccn_max), ('cognitive', args.cognitive_max))
    analyzer = lizard.FileAnalyzer(lizard.get_extensions(['cognitive']))
    if args.base:
        bad, _checked, skipped = changed_functions(analyzer, metrics, pathspecs, args.base, extensions)
    else:
        bad, _checked, skipped = every_function(analyzer, metrics, pathspecs, extensions)
    print('\n'.join(bad) or 'lizard gate: pass')
    if skipped:
        print(f'lizard gate: skipped {skipped} file(s) not matching --extensions')
    if bad:
        print('Split the function, or add a reviewed `// #lizard forgive` comment inside it.')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
            out.write(f'findings={len(bad)}\n')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
