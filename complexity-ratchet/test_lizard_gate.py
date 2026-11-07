import contextlib
import io
import os
import subprocess
import tempfile
import unittest

import lizard_gate

METRICS = (('CCN', 10), ('cognitive', 15))


def java(int_decl='int x', var='x', overload_ifs=11, string_value=0):
    ifs = ''.join(f' if ({var} == {i}) {{ return {i}; }}' for i in range(overload_ifs))
    return ('class A {\n'
            f'  int f({int_decl}) {{{ifs} return 0; }}\n'
            f'  int f(String s) {{ return {string_value}; }}\n'
            '}\n')


def enum_java(y_ifs=0, y_return=0, simple_z=False):
    x_ifs = ''.join(f' if (x == {i}) {{ return {i}; }}' for i in range(11))
    y_body = ''.join(f' if (x == {i}) {{ return {i}; }}' for i in range(y_ifs))
    z = '  Z { int g(int x) { return 0; } },\n' if simple_z else ''
    return ('enum E {\n'
            f'  X {{ int g(int x) {{{x_ifs} return 0; }} }},\n'
            f'{z}'
            f'  Y {{ int g(int x) {{{y_body} return {y_return}; }} }};\n'
            '}\n')


class OverloadRatchetTest(unittest.TestCase):
    def setUp(self):
        cwd = os.getcwd()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(os.chdir, cwd)
        os.chdir(tmp.name)
        subprocess.run(['git', 'init', '-q'], check=True)

    def commit(self, source):
        with open('A.java', 'w', encoding='utf-8') as f:
            f.write(source)
        subprocess.run(['git', 'add', 'A.java'], check=True)
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'x'], check=True)

    def gate(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = lizard_gate.main(['--base', 'HEAD~1'])
        return code, out.getvalue()

    def test_unchanged_complex_overload_passes_when_sibling_overload_changes(self):
        self.commit(java(overload_ifs=11, string_value=0))
        self.commit(java(overload_ifs=11, string_value=1))
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_renamed_or_final_parameter_of_unchanged_complex_overload_passes(self):
        self.commit(java(int_decl='int x', var='x'))
        self.commit(java(int_decl='final int count', var='count'))
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_added_annotation_on_parameter_of_unchanged_complex_overload_passes(self):
        self.commit(java(int_decl='int x', var='x'))
        self.commit(java(int_decl='@Nullable int x', var='x'))
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_c_style_array_parameter_renamed_on_unchanged_complex_overload_passes(self):
        self.commit(java(int_decl='int[] x', var='x'))
        self.commit(java(int_decl='int count[]', var='count'))
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_unchanged_duplicate_signature_passes_when_sibling_changes(self):
        self.commit(enum_java(y_return=0))
        self.commit(enum_java(y_return=1))
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_unchanged_complex_duplicate_passes_when_simple_duplicate_is_added(self):
        self.commit(enum_java())
        self.commit(enum_java(simple_z=True))
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_duplicate_signature_that_got_worse_fails(self):
        self.commit(enum_java(y_ifs=0))
        self.commit(enum_java(y_ifs=11))
        code, out = self.gate()
        self.assertEqual(1, code)
        self.assertIn('E::g(int) CCN 1 -> 12', out)

    def test_changed_complex_overload_worse_than_before_fails(self):
        self.commit(java(overload_ifs=11))
        self.commit(java(overload_ifs=12))
        code, out = self.gate()
        self.assertEqual(1, code)
        self.assertIn('CCN 12 -> 13', out)


def judges(a_ifs, b_ifs):
    def body(n):
        return ''.join(f'        if x == {i}:\n            return {i}\n' for i in range(n)) + '        return 0\n'
    return f'class A:\n    def judge(self, x):\n{body(a_ifs)}\n\nclass B:\n    def judge(self, x):\n{body(b_ifs)}'


WAIT_FOR = '\n'.join(
    ['jobs:', '  boot:', '    steps:', '      - run: |', '          wait_for() {']
    + [f'            if [ "$1" = {i} ]; then echo {i}; fi' for i in range(12)]
    + ['          }', ''])


class RepoTest(unittest.TestCase):
    def setUp(self):
        cwd = os.getcwd()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.addCleanup(os.chdir, cwd)
        os.chdir(tmp.name)
        subprocess.run(['git', 'init', '-q'], check=True)

    def commit(self, **files):
        for name, text in files.items():
            os.makedirs(os.path.dirname(name) or '.', exist_ok=True)
            with open(name, 'w', encoding='utf-8') as f:
                f.write(text)
            subprocess.run(['git', 'add', name], check=True)
        subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'x'], check=True)

    def gate(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = lizard_gate.main(['--base', 'HEAD~1', '--pathspec', '.', *args])
        return code, out.getvalue()


class ExtensionTest(RepoTest):
    def test_complex_shell_in_yaml_is_not_scored(self):
        self.commit(**{'a.py': 'x = 1\n'})
        self.commit(**{'.github/workflows/server-boot.yml': WAIT_FOR})
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_extensions_input_selects_files(self):
        self.commit(**{'a.py': 'x = 1\n'})
        self.commit(**{'.github/workflows/server-boot.yml': WAIT_FOR})
        code, out = self.gate('--extensions', '.yml')
        self.assertEqual(1, code)
        self.assertIn('wait_for() CCN 0 -> 13', out)

    def test_every_function_mode_skips_other_extensions(self):
        self.commit(**{'.github/workflows/server-boot.yml': WAIT_FOR})
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = lizard_gate.main(['--pathspec', '.'])
        self.assertEqual(0, code, out.getvalue())

    def test_star_extension_checks_every_matched_file(self):
        self.commit(**{'a.py': 'x = 1\n'})
        self.commit(**{'.github/workflows/server-boot.yml': WAIT_FOR})
        code, out = self.gate('--extensions', '*')
        self.assertEqual(1, code, out)
        self.assertIn('wait_for() CCN 0 -> 13', out)
        self.assertNotIn('skipped', out)

    def test_pass_names_skipped_count_when_no_file_matches_extensions(self):
        self.commit(**{'a.py': 'x = 1\n'})
        self.commit(**{'.github/workflows/server-boot.yml': WAIT_FOR, 'notes.md': 'x\n'})
        code, out = self.gate()
        self.assertEqual(0, code, out)
        self.assertIn('skipped 2', out)

    def test_mixed_run_names_skipped_count(self):
        self.commit(**{'a.py': 'x = 1\n'})
        self.commit(**{'a.py': 'x = 2\n', 'notes.md': 'x\n'})
        code, out = self.gate()
        self.assertEqual(0, code, out)
        self.assertIn('skipped 1', out)


def nested_builders(server_ifs, client_ifs):
    def build(n):
        return 'void build(int x) {' + ''.join(f' if (x == {i}) {{ return; }}' for i in range(n)) + ' }'
    return ('class Config {\n'
            f'  static class Server {{ static class Builder {{ {build(server_ifs)} }} }}\n'
            f'  static class Client {{ static class Builder {{ {build(client_ifs)} }} }}\n'
            '}\n')


def judge_after_nested(nested, ifs):
    body = ''.join(f' if (x == {i}) {{ return {i}; }}' for i in range(ifs))
    nest = 'static class S {}\n  ' if nested else ''
    return f'class O {{\n  {nest}int judge(int x) {{{body} return 0; }}\n}}\n'


def two_classes_after_nested(o_ifs, p_ifs):
    def judge(n):
        return 'int judge(int x) {' + ''.join(f' if (x == {i}) {{ return {i}; }}' for i in range(n)) + ' return 0; }'
    return (f'class O {{ static class S {{}} {judge(o_ifs)} }}\n'
            f'class P {{ static class S {{}} {judge(p_ifs)} }}\n')


def namespaced_judges(n_ifs, m_ifs):
    def judge(n):
        return 'int Judge(int x) {' + ''.join(f' if (x == {i}) {{ return {i}; }}' for i in range(n)) + ' return 0; }'
    return (f'namespace N {{ class A {{ {judge(n_ifs)} }} }}\n'
            f'namespace M {{ class A {{ {judge(m_ifs)} }} }}\n')


class QualifiedNameTest(RepoTest):
    def test_nested_java_classes_with_same_method_name_are_not_paired_by_rank(self):
        self.commit(**{'Config.java': nested_builders(server_ifs=4, client_ifs=18)})
        self.commit(**{'Config.java': nested_builders(server_ifs=18, client_ifs=4)})
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn('Config::Server::Builder::build(int) CCN 5 -> 19 (max 10)', out)

    def test_unchanged_method_after_nested_class_passes_when_nested_class_is_added(self):
        self.commit(**{'O.java': judge_after_nested(nested=False, ifs=13)})
        self.commit(**{'O.java': judge_after_nested(nested=True, ifs=13)})
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_method_after_nested_class_is_not_paired_by_rank_with_sibling_class(self):
        self.commit(**{'O.java': two_classes_after_nested(o_ifs=4, p_ifs=18)})
        self.commit(**{'O.java': two_classes_after_nested(o_ifs=18, p_ifs=4)})
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn('O::judge(int) CCN 5 -> 19 (max 10)', out)

    def test_same_class_name_in_two_csharp_namespaces_is_not_paired_by_rank(self):
        self.commit(**{'A.cs': namespaced_judges(n_ifs=4, m_ifs=18)})
        self.commit(**{'A.cs': namespaced_judges(n_ifs=18, m_ifs=4)})
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn('N::A::Judge(int) CCN 5 -> 19 (max 10)', out)

    def test_same_method_name_in_two_classes_is_not_paired_by_rank(self):
        self.commit(**{'j.py': judges(a_ifs=18, b_ifs=4)})
        self.commit(**{'j.py': judges(a_ifs=4, b_ifs=18)})
        code, out = self.gate()
        self.assertEqual(1, code, out)
        self.assertIn('B.judge CCN 5 -> 19 (max 10)', out)

    def test_unchanged_python_method_passes_when_sibling_class_changes(self):
        self.commit(**{'j.py': judges(a_ifs=18, b_ifs=4)})
        self.commit(**{'j.py': judges(a_ifs=18, b_ifs=5)})
        code, out = self.gate()
        self.assertEqual(0, code, out)


class UnparseablePythonTest(RepoTest):
    def test_unchanged_function_in_unparseable_file_passes_when_line_above_moves(self):
        body = ''.join(f'    if x == {i}:\n        return {i}\n' for i in range(11))
        self.commit(**{'legacy.py': f'print "legacy"\ndef f(x):\n{body}    return 0\n'})
        self.commit(**{'legacy.py': f'import os\nprint "legacy"\ndef f(x):\n{body}    return 0\n'})
        code, out = self.gate()
        self.assertEqual(0, code, out)

    def test_null_byte_in_python_source_does_not_crash_the_gate(self):
        self.commit(**{'nul.py': 'x = 1\x00\n'})
        self.commit(**{'nul.py': 'x = 2\x00\n'})
        code, out = self.gate()
        self.assertEqual(0, code, out)


class RatchetTest(unittest.TestCase):
    def test_new_function_above_limit_fails(self):
        self.assertEqual(1, len(lizard_gate.ratchet(METRICS, 'A.java', 'f', [((11, 0), 3)], ())))

    def test_new_function_below_limit_passes(self):
        self.assertEqual([], lizard_gate.ratchet(METRICS, 'A.java', 'f', [((10, 15), 3)], ()))

    def test_old_function_not_worse_passes(self):
        self.assertEqual([], lizard_gate.ratchet(METRICS, 'A.java', 'f', [((12, 0), 3)], [((12, 0), 3)]))

    def test_old_function_worse_fails(self):
        found = lizard_gate.ratchet(METRICS, 'A.java', 'f', [((13, 0), 3)], [((12, 0), 3)])
        self.assertEqual(['A.java:3: f CCN 12 -> 13 (max 10)'], found)


if __name__ == '__main__':
    unittest.main()
