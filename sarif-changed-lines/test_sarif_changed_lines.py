import unittest

import sarif_changed_lines as gate

DIFF = """diff --git a/A.java b/A.java
--- a/A.java
+++ b/A.java
@@ -1,0 +5,2 @@
+x
+y
"""


def sarif(rule, line):
    region = {'startLine': line}
    location = {'physicalLocation': {'artifactLocation': {'uri': 'A.java'}, 'region': region}}
    return {'runs': [{'results': [{'ruleId': rule, 'message': {'text': 'm'}, 'locations': [location]}]}]}


class GateTest(unittest.TestCase):
    def test_changed_lines_parse(self):
        self.assertEqual({'A.java': {5, 6}}, gate.changed_lines(DIFF))

    def test_result_on_changed_line_fails(self):
        self.assertEqual(['A.java:5: r: m'], gate.on_changed_lines(sarif('r', 5), gate.changed_lines(DIFF)))

    def test_result_off_changed_line_passes(self):
        self.assertEqual([], gate.on_changed_lines(sarif('r', 9), gate.changed_lines(DIFF)))

    def test_overridden_method_skipped(self):
        read = lambda _: ['', '', '', '', '@Override void f(int a, int b) {}']
        self.assertEqual([], [r for r in gate.results(sarif('p', 5), ('p',), read)])
        self.assertEqual(1, len(list(gate.results(sarif('q', 5), ('p',), read))))


if __name__ == '__main__':
    unittest.main()
