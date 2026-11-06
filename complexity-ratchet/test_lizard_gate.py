import unittest

import lizard_gate

METRICS = (('CCN', 10), ('cognitive', 15))


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
