import random
import subprocess
import sys
import unittest
from pathlib import Path

import longest_path as lp

# 問題文の入力例
SAMPLE = [(1, 2, 8.54), (2, 3, 3.11), (3, 1, 2.19), (3, 4, 4.0), (4, 1, 1.4)]
SAMPLE_BEST = 17.05

# 経路が反則していないかチェックしつつ総距離を返す
def route_dist(edges, path):
    if not path:
        return 0.0
    pair_ws = {}
    for a, b, w in edges:
        key = (a, b) if a <= b else (b, a)
        pair_ws.setdefault(key, []).append(w)
    for ws in pair_ws.values():
        ws.sort(reverse=True)
    inner = path[:-1] if len(path) > 1 and path[0] == path[-1] else path
    assert len(inner) == len(set(inner)), "同じ駅を2回通っている: %r" % (path,)
    total = 0.0
    used = {}
    for a, b in zip(path, path[1:]):
        key = (a, b) if a <= b else (b, a)
        ws = pair_ws.get(key)
        k = used.get(key, 0)
        assert ws is not None and len(ws) > k, "無い辺を使っている: %s-%s" % (a, b)
        total += ws[k]
        used[key] = k + 1
    return total

class TestParseInput(unittest.TestCase):
    def test_whitespace_and_crlf(self):
        edges = lp.parse_input("  1 ,  2 ,  8.54 \r\n2,3,3.11\r\n\r\n")
        self.assertEqual(edges, [(1, 2, 8.54), (2, 3, 3.11)])

    def test_integer_distance(self):
        self.assertEqual(lp.parse_input("3, 4, 4\r\n"), [(3, 4, 4.0)])

    def test_broken_lines(self):
        edges = lp.parse_input("1, 2, 3.0\r\nabc, 2, 3\r\n1, 2\r\n")
        self.assertEqual(edges, [(1, 2, 3.0)])

    def test_empty(self):
        self.assertEqual(lp.parse_input(""), [])
class TestSolve(unittest.TestCase):
    def check(self, edges, expected, time_limit=2.0):
        dist, path, optimal = lp.solve(edges, time_limit)
        self.assertAlmostEqual(route_dist(edges, path), dist, places=9)
        self.assertAlmostEqual(dist, expected, places=9)
        return path, optimal

    def test_sample(self):
        path, optimal = self.check(SAMPLE, SAMPLE_BEST)
        self.assertTrue(optimal)
        self.assertEqual(len(path), 5)
        self.assertEqual(path[0], path[-1])

    def test_chain(self):
        path, optimal = self.check([(1, 2, 1.0), (2, 3, 2.0), (3, 4, 3.0)], 6.0)
        self.assertTrue(optimal)
        self.assertEqual(len(path), 4)

    def test_square_cycle(self):
        path, optimal = self.check(
            [(1, 2, 1.0), (2, 3, 1.0), (3, 4, 1.0), (4, 1, 1.0)], 4.0)
        self.assertTrue(optimal)
        self.assertEqual(len(path), 5)
        self.assertEqual(path[0], path[-1])

    def test_parallel_edges_round_trip(self):
        path, _ = self.check([(1, 2, 5.0), (2, 1, 7.0)], 12.0)
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0], path[-1])

    def test_self_loop_only(self):
        path, _ = self.check([(7, 7, 4.5)], 4.5)
        self.assertEqual(path, [7, 7])

    def test_self_loop_vs_edge(self):
        path, _ = self.check([(7, 7, 4.5), (7, 8, 10.0)], 10.0)
        self.assertEqual(sorted(path), [7, 8])

    def test_disconnected(self):
        path, _ = self.check([(1, 2, 10.0), (2, 3, 10.0), (4, 5, 5.0)], 20.0)
        self.assertEqual(sorted(path), [1, 2, 3])

    def test_empty(self):
        self.assertEqual(lp.solve([], 1.0), (0.0, [], True))

# 大規模グラフのテスト
class TestLargeGraph(unittest.TestCase):
    def test_random_sparse_graph(self):
        rng = random.Random(1)
        n = 400
        edges = []
        for v in range(2, n + 1):
            edges.append((rng.randint(1, v - 1), v, round(rng.uniform(1, 100), 2)))
        for _ in range(n // 2):
            a, b = rng.randint(1, n), rng.randint(1, n)
            if a != b:
                edges.append((a, b, round(rng.uniform(1, 100), 2)))
        dist, path, _ = lp.solve(edges, time_limit=3.0)
        self.assertAlmostEqual(route_dist(edges, path), dist, places=6)
        self.assertGreater(len(path), 10)

class TestEndToEnd(unittest.TestCase):
    def test_sample_via_stdin(self):
        script = Path(__file__).with_name("longest_path.py")
        stdin = (b"1, 2, 8.54\r\n"
                 b" 2 ,3, 3.11\r\n"
                 b"3, 1, 2.19\r\n"
                 b"3, 4, 4\r\n"
                 b"4, 1, 1.4\r\n")
        proc = subprocess.run(
            [sys.executable, str(script), "--time-limit", "2"],
            input=stdin, capture_output=True)
        self.assertEqual(proc.returncode, 0)
        path = [int(t) for t in proc.stdout.decode().split("\r\n") if t]
        self.assertAlmostEqual(route_dist(SAMPLE, path), SAMPLE_BEST, places=9)

if __name__ == "__main__":
    unittest.main()
