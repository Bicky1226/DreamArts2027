import argparse
import random
import sys
import time
from collections import deque

TIME_LIMIT = None
EXACT_RATIO = 0.6

# 入力をリストへ格納
def parse_input(text):
    edges = []
    for line in text.splitlines():
        parts = line.split(",")
        if len(parts) != 3:
            continue
        try:
            edges.append((int(parts[0]), int(parts[1]), float(parts[2])))
        except ValueError:
            continue
    return edges

# 隣接リストから経路の距離を計算する
def build_graph(edges):
    id_set = set()
    pair_top2 = {}
    loop = None
    for a, b, w in edges:
        id_set.add(a)
        id_set.add(b)
        if a == b:
            if loop is None or w > loop[0]:
                loop = (w, [a, a])
            continue
        key = (a, b) if a < b else (b, a)
        tops = pair_top2.setdefault(key, [])
        tops.append(w)
        tops.sort(reverse=True)
        del tops[2:]
    round_trip = None
    for (a, b), tops in pair_top2.items():
        if len(tops) >= 2 and (round_trip is None or tops[0] + tops[1] > round_trip[0]):
            round_trip = (tops[0] + tops[1], [a, b, a])
    ids = sorted(id_set)
    idx = {v: i for i, v in enumerate(ids)}
    adj_w = [{} for _ in ids]
    for (a, b), tops in pair_top2.items():
        adj_w[idx[a]][idx[b]] = tops[0]
        adj_w[idx[b]][idx[a]] = tops[0]
    adj = [sorted(d.items(), key=lambda p: -p[1]) for d in adj_w]
    return ids, adj, adj_w, round_trip, loop

# 厳密解を求める
def exact_search(n, adj, deadline):
    top1 = [0.0] * n
    top2sum = [0.0] * n
    for v in range(n):
        ws = [w for _, w in adj[v][:2]]
        if ws:
            top1[v] = ws[0]
            top2sum[v] = sum(ws)
    best_dist = 0.0
    best_path = [0]
    total_top2 = sum(top2sum)
    ops = 0
    for s in sorted(range(n), key=lambda v: -top1[v]):
        path = [s]
        visited = bytearray(n)
        visited[s] = 1
        rem = total_top2 - top2sum[s]
        dist = 0.0
        stack = [[s, 0, 0.0]]
        while stack:
            ops += 1
            if ops % 2048 == 0 and time.monotonic() > deadline:
                return False, best_dist, best_path
            frame = stack[-1]
            v, i = frame[0], frame[1]
            av = adj[v]
            if i < len(av):
                frame[1] = i + 1
                u, w = av[i]
                if visited[u]:
                    if u == s and len(path) >= 3 and dist + w > best_dist:
                        best_dist = dist + w
                        best_path = path + [s]
                    continue
                nd = dist + w
                if nd > best_dist:
                    best_dist = nd
                    best_path = path + [u]
                nrem = rem - top2sum[u]
                if nd + (top1[u] + nrem + top1[s]) * 0.5 <= best_dist:
                    continue
                visited[u] = 1
                rem = nrem
                dist = nd
                path.append(u)
                stack.append([u, 0, w])
            else:
                stack.pop()
                if stack:
                    visited[v] = 0
                    rem += top2sum[v]
                    dist -= frame[2]
                    path.pop()
    return True, best_dist, best_path

# 経路の距離を計算する  
def local_search(n, adj, adj_w, deadline, best_dist, best_path):
    rng = random.Random(0)
    while time.monotonic() < deadline:
        if len(best_path) > 1 and rng.random() < 0.7:
            base = best_path[:-1] if best_path[0] == best_path[-1] else best_path[:]
            if rng.random() < 0.5:
                base.reverse()
            seq = base[: rng.randint(1, len(base))]
        else:
            seq = [rng.randrange(n)]
        visited = set(seq)
        dist = 0.0
        for a, b in zip(seq, seq[1:]):
            dist += adj_w[a][b]
        path = deque(seq)
        steps = 0
        while True:
            extended = False
            for head in (False, True):
                v = path[0] if head else path[-1]
                cands = [p for p in adj[v] if p[0] not in visited]
                if not cands:
                    continue
                if len(cands) == 1 or rng.random() < 0.7:
                    u, w = cands[0]
                else:
                    u, w = cands[rng.randrange(min(3, len(cands)))]
                if head:
                    path.appendleft(u)
                else:
                    path.append(u)
                visited.add(u)
                dist += w
                extended = True
            steps += 1
            if not extended or (steps % 1024 == 0 and time.monotonic() > deadline):
                break
        if dist > best_dist:
            best_dist = dist
            best_path = list(path)
        if len(path) >= 3:
            w = adj_w[path[-1]].get(path[0])
            if w is not None and dist + w > best_dist:
                best_dist = dist + w
                best_path = list(path) + [path[0]]
    return best_dist, best_path

# 総距離、駅IDの経路、厳密解かどうかを返す
def solve(edges, time_limit=TIME_LIMIT):
    t0 = time.monotonic()
    ids, adj, adj_w, round_trip, loop = build_graph(edges)
    n = len(ids)
    optimal = True
    dist = 0.0
    path = []
    if n:
        exact_deadline = (float("inf") if time_limit is None
                          else t0 + time_limit * EXACT_RATIO)
        finished, d, p = exact_search(n, adj, exact_deadline)
        if not finished:
            optimal = False
            d, p = local_search(n, adj, adj_w, t0 + time_limit, d, p)
        dist = d
        path = [ids[v] for v in p]
    for cand in (round_trip, loop):
        if cand is not None and cand[0] > dist:
            dist, path = cand[0], list(cand[1])
    return dist, path, optimal

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-limit", type=float, default=TIME_LIMIT,
                    help="近似解へ切り替えるまでを含む制限時間(秒)")
    args = ap.parse_args()
    t0 = time.monotonic()
    edges = parse_input(sys.stdin.read())
    dist, path, optimal = solve(edges, args.time_limit)
    # エラー回避のため改行はCRLF指定
    sys.stdout.buffer.write("".join("%d\r\n" % v for v in path).encode())
    print("[info] dist=%.6g stops=%d %s (%.2fs)"
          % (dist, len(path), "exact" if optimal else "approx",
             time.monotonic() - t0), file=sys.stderr)

if __name__ == "__main__":
    main()
