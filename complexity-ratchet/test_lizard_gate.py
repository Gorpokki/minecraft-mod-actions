import contextlib
import io
import os
import subprocess
import tempfile
import unittest

import lizard_gate

METRICS = (('CCN', 10), ('cognitive', 15))


def java(overload_ifs=11, string_value=0):
    ifs = ''.join(f' if (x == {i}) {{ return {i}; }}' for i in range(overload_ifs))
    return ('class A {\n'
            f'  int f(int x) {{{ifs} return 0; }}\n'
            f'  int f(String s) {{ return {string_value}; }}\n'
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

    def test_changed_complex_overload_worse_than_before_fails(self):
        self.commit(java(overload_ifs=11))
        self.commit(java(overload_ifs=12))
        code, out = self.gate()
        self.assertEqual(1, code)
        self.assertIn('CCN 12 -> 13', out)


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
