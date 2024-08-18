from unittest import TestCase

from staticsite import toposort


class TestTopoSort(TestCase):
    def test_nodeps(self):
        graph = {}
        graph["a"] = set()
        graph["b"] = set()
        graph["c"] = set()
        self.assertEqual(toposort.sort(graph), ["a", "b", "c"])

    def test_singledeps(self):
        graph = {}
        graph["a"] = set()
        graph["a"] = {"b"}
        graph["b"] = {"c"}
        self.assertEqual(toposort.sort(graph), ["c", "b", "a"])

    def test_cycle(self):
        graph = {}
        graph["b"] = {"a"}
        graph["c"] = {"b"}
        graph["a"] = {"c"}
        with self.assertRaises(ValueError) as e:
            self.assertEqual(toposort.sort(graph), ["a", "c", "b"])
        self.assertEqual(
            str(e.exception), "('nodes are in a cycle', ['b', 'c', 'a', 'b'])"
        )
