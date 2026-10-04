# -*- coding: utf-8 -*-
"""
EfA: движок раскладки BPMN-диаграммы (дорожки, задачи, шлюзы, события, документы).

Правила (от бизнес-аналитика, по разбору ручной правки модели ТОИР в Sila Union):
  1. Стрелки не пересекаются. Если без пересечений нельзя — их минимум.
  2. Все подписи читаются полностью: высота подписи считается по длине текста,
     подпись не накрывает фигуры, другие подписи и линии.
  3. Поток идёт слева направо по средней линии дорожки; документы — в полосе
     под ней, рядом с тем, кто их создаёт или получает.

Как работает:
  * колонки — по длине пути от старта (слоям); два элемента одной дорожки не
    делят колонку — второй сдвигается вправо (порядок перебирается);
  * для каждой связи строится набор ортогональных маршрутов (через разные
    грани фигур, обходы сверху/снизу, «каналы» под документами);
  * маршруты и места документов выбираются жадно, затем улучшаются
    несколькими проходами; варианты порядка сравниваются по общей цене.
"""
import itertools
import math
import random

# ---------- размеры (как в Sila Union) ----------
SIZE = {'task': (120, 70), 'start': (36, 36), 'end': (36, 36), 'gateway': (36, 36), 'doc': (45, 60)}
POOL_X, POOL_Y = 40, 40
POOL_HEADER = 30           # полоса названия пула
LANE_HEADER = 30           # полоса названия дорожки внутри дорожки
LEFT_PAD = 50              # от полосы названия дорожки до первой колонки
TOP = 125                  # от верха дорожки до оси потока
GAP = 70                   # зазор между соседними колонками
DOC_CY = 112               # центр документа ниже оси потока
LANE_H_DOCS = 380          # высота дорожки, где есть документы
LANE_H_PLAIN = 240         # высота дорожки без документов
OVER = (60, 80, 100)       # уровни обхода сверху (выше оси)
UNDER = (60, 80)           # уровни обхода снизу
CHANNELS = (215, 232, 249)  # «каналы» ассоциаций под подписями документов

# ---------- подписи ----------
CHAR_W = 5.6               # средняя ширина символа подписи, px
LINE_H = 13
LABEL_W = {'start': 100, 'end': 100, 'gateway': 110, 'doc': 90}

# ---------- цена ----------
W_CROSS = 1000
W_OVERLAP = 1500           # линии идут друг по другу
W_NODE = 6000              # линия через фигуру
W_LABEL = 2500             # линия через подпись
W_PORT = 700               # две связи в одной точке фигуры
W_BOX = 6000               # фигура/подпись документа на фигуре или подписи
W_BEND = 18
W_LEN = 0.02
CLEAR_NODE = 12           # зазор линии до чужой фигуры, px
CLEAR_LABEL = 5           # зазор линии до подписи
CLEAR_PARALLEL = 8        # параллельные линии не ближе
MIN_STUB = 20             # первый (выход) и последний (вход) отрезки не короче: стрелка входит по направлению


def wrap_lines(text, width):
    """Сколько строк займёт текст при переносе по словам."""
    if not text.strip():
        return 0
    per = max(1, int((width - 8) / CHAR_W))
    lines, cur = 1, 0
    for w in text.split():
        n = len(w)
        if cur == 0:
            cur = n
        elif cur + 1 + n <= per:
            cur += 1 + n
        else:
            lines += 1
            cur = n
        while cur > per:            # очень длинное слово
            lines += 1
            cur -= per
    return lines


def label_box(kind, x, y, w, h, text):
    """Прямоугольник подписи (x, y, w, h) снаружи фигуры или None."""
    if kind == 'task' or not text.strip():
        return None
    lw = LABEL_W[kind]
    lh = wrap_lines(text, lw) * LINE_H + 10
    cx = x + w / 2
    if kind == 'gateway':              # над ромбом
        return (cx - lw / 2, y - 4 - lh, lw, lh)
    return (cx - lw / 2, y + h + 3, lw, lh)


# ---------- геометрия ----------
def segs(pts):
    return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def is_h(s):
    return abs(s[0][1] - s[1][1]) < 0.5


def seg_cross(s, t):
    """Перпендикулярные отрезки пересекаются во внутренней точке."""
    if is_h(s) == is_h(t):
        return False
    h, v = (s, t) if is_h(s) else (t, s)
    hx1, hx2 = sorted((h[0][0], h[1][0]))
    vy1, vy2 = sorted((v[0][1], v[1][1]))
    vx, hy = v[0][0], h[0][1]
    return hx1 + 0.5 < vx < hx2 - 0.5 and vy1 + 0.5 < hy < vy2 - 0.5


def seg_overlap(s, t):
    if is_h(s) != is_h(t):
        return False
    if is_h(s):
        if abs(s[0][1] - t[0][1]) > CLEAR_PARALLEL:
            return False
        a1, a2 = sorted((s[0][0], s[1][0])); b1, b2 = sorted((t[0][0], t[1][0]))
    else:
        if abs(s[0][0] - t[0][0]) > CLEAR_PARALLEL:
            return False
        a1, a2 = sorted((s[0][1], s[1][1])); b1, b2 = sorted((t[0][1], t[1][1]))
    return min(a2, b2) - max(a1, b1) > 4


def seg_box(s, box, pad=3):
    if box is None:
        return False
    bx, by, bw, bh = box
    x1, x2 = sorted((s[0][0], s[1][0])); y1, y2 = sorted((s[0][1], s[1][1]))
    return x1 < bx + bw - pad and x2 > bx + pad and y1 < by + bh - pad and y2 > by + pad


def box_box(a, b, pad=2):
    if a is None or b is None:
        return False
    return (a[0] < b[0] + b[2] - pad and a[0] + a[2] > b[0] + pad and
            a[1] < b[1] + b[3] - pad and a[1] + a[3] > b[1] + pad)


# ---------- раскладка ----------
class Layout:
    def __init__(self, proc, priority, lane_heights=None, gap=GAP):
        self.proc = proc
        self.nodes = {n['id']: dict(n) for n in proc['nodes']}
        self.lanes_names = proc['lanes']
        self.gap = gap
        self._columns(priority)
        nl = len(self.lanes_names)
        self.lane_h = lane_heights or [LANE_H_DOCS] * nl
        self.lanes = []
        y = POOL_Y
        for i, name in enumerate(self.lanes_names):
            self.lanes.append({'name': name, 'x': POOL_X + POOL_HEADER, 'y': y, 'h': self.lane_h[i]})
            y += self.lane_h[i]
        self._place_nodes()

    def _columns(self, priority):
        preds = {k: [] for k in self.nodes}
        for e in self.proc['edges']:
            preds[e['to']].append(e['from'])
        order, done = [], set()
        rank = {k: i for i, k in enumerate(priority)}
        while len(order) < len(self.nodes):
            ready = [k for k in self.nodes if k not in done and all(p in done for p in preds[k])]
            if not ready:                                   # цикл: берём любой
                ready = [k for k in self.nodes if k not in done]
            k = min(ready, key=lambda z: rank[z])
            order.append(k); done.add(k)
        used, col = set(), {}
        for k in order:
            c = max([col[p] + 1 for p in preds[k] if p in col] or [0])
            while (self.nodes[k]['lane'], c) in used:
                c += 1
            col[k] = c
            used.add((self.nodes[k]['lane'], c))
        self.col = col

    def _place_nodes(self):
        ncol = max(self.col.values()) + 1
        widths = [0] * ncol
        for k, n in self.nodes.items():
            widths[self.col[k]] = max(widths[self.col[k]], SIZE[n['type']][0])
        xs, x = [], self.lanes[0]['x'] + LANE_HEADER + LEFT_PAD
        for c in range(ncol):
            w = widths[c] or 36
            xs.append(x + w / 2)
            x += w + self.gap
        self.col_x = xs
        self.width = x - self.gap + 60 - self.lanes[0]['x']
        self.shapes = {}
        for k, n in self.nodes.items():
            w, h = SIZE[n['type']]
            cx, cy = xs[self.col[k]], self.lanes[n['lane']]['y'] + TOP
            self.add_shape(k, n['type'], n['lane'], cx, cy, n['label'])

    def add_shape(self, k, kind, lane, cx, cy, text):
        w, h = SIZE[kind]
        x, y = cx - w / 2, cy - h / 2
        self.shapes[k] = {'id': k, 'kind': kind, 'lane': lane, 'cx': cx, 'cy': cy, 'x': x, 'y': y,
                          'w': w, 'h': h, 'label': text, 'lbox': label_box(kind, x, y, w, h, text)}

    def row(self, lane):
        return self.lanes[lane]['y'] + TOP

    # ----- порты -----
    def ports(self, s, role):
        """Точки подключения: (x, y, сторона). role: 'out'/'in', 'flow'/'assoc'."""
        x, y, w, h, cx, cy = s['x'], s['y'], s['w'], s['h'], s['cx'], s['cy']
        if s['kind'] == 'task':
            dxs = (0, -30, 30)
            p = [(x + w, cy, 'R'), (x, cy, 'L')]
            p += [(cx + d, y, 'T') for d in dxs] + [(cx + d, y + h, 'B') for d in dxs]
        else:
            p = [(x + w, cy, 'R'), (x, cy, 'L'), (cx, y, 'T'), (cx, y + h, 'B')]
        return p

    # ----- маршруты -----
    def candidates(self, a, b, kind):
        A, B = self.shapes[a], self.shapes[b]
        outs = self.ports(A, 'out')
        ins = self.ports(B, 'in')
        if kind == 'flow':
            outs = [p for p in outs if p[2] != 'L']
            ins = [p for p in ins if p[2] != 'R']
        else:   # ассоциация: у задачи — только верх/низ, боковые грани оставляем потоку
            if A['kind'] == 'task':
                outs = [p for p in outs if p[2] in 'TB']
            if B['kind'] == 'task':
                ins = [p for p in ins if p[2] in 'TB']
        lo_x, hi_x = min(A['cx'], B['cx']) - 200, max(A['cx'], B['cx']) + 200
        xs = {x for x in self.col_x if lo_x <= x <= hi_x}
        for i in range(len(self.col_x) - 1):
            m = (self.col_x[i] + self.col_x[i + 1]) / 2
            if lo_x <= m <= hi_x:
                xs.add(m)
        ys = set()
        for ln in sorted({A['lane'], B['lane']}):
            r = self.row(ln)
            ys.update(r - d for d in OVER)
            ys.update(r + d for d in UNDER)
            ys.update(r + d for d in CHANNELS)
        res = []
        for (x0, y0, s0), (x1, y1, s1) in itertools.product(outs, ins):
            for pts in self._paths(x0, y0, s0, x1, y1, s1, xs, ys):
                res.append(pts)
        return res

    @staticmethod
    def _out_ok(s, p0, p1):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        return {'R': dx > 0.5 and abs(dy) < 0.5, 'L': dx < -0.5 and abs(dy) < 0.5,
                'T': dy < -0.5 and abs(dx) < 0.5, 'B': dy > 0.5 and abs(dx) < 0.5}[s]

    def _paths(self, x0, y0, s0, x1, y1, s1, xs, ys):
        p0, p1 = (x0, y0), (x1, y1)
        out = []
        hor0, hor1 = s0 in 'LR', s1 in 'LR'
        cand = []
        if hor0 and hor1:
            if abs(y0 - y1) < 0.5:
                cand.append([p0, p1])
            for xm in xs | {x1 - 20 if s1 == 'L' else x1 + 20, x0 + 20 if s0 == 'R' else x0 - 20}:
                cand.append([p0, (xm, y0), (xm, y1), p1])
        elif not hor0 and not hor1:
            if abs(x0 - x1) < 0.5:
                cand.append([p0, p1])
            for ym in ys | {y1 - 20 if s1 == 'T' else y1 + 20, y0 + 20 if s0 == 'B' else y0 - 20}:
                cand.append([p0, (x0, ym), (x1, ym), p1])
        elif hor0:
            cand.append([p0, (x1, y0), p1])
        else:
            cand.append([p0, (x0, y1), p1])
        for pts in cand:
            # убрать нулевые отрезки
            clean = [pts[0]]
            for q in pts[1:]:
                if abs(q[0] - clean[-1][0]) > 0.5 or abs(q[1] - clean[-1][1]) > 0.5:
                    clean.append(q)
            if len(clean) < 2:
                continue
            if not self._out_ok(s0, clean[0], clean[1]):
                continue
            # последний отрезок входит в фигуру снаружи
            inward = {'L': 'R', 'R': 'L', 'T': 'B', 'B': 'T'}[s1]
            if not self._out_ok(inward, clean[-2], clean[-1]):
                continue
            ok = all(abs(a[0] - b[0]) < 0.5 or abs(a[1] - b[1]) < 0.5 for a, b in segs(clean))
            # Правило: выход из фигуры и вход в фигуру — отрезком не короче MIN_STUB
            # (иначе Sila рисует наконечник боком вдоль грани).
            if len(clean) > 2:
                first, last = segs(clean)[0], segs(clean)[-1]
                seglen = lambda g: abs(g[0][0] - g[1][0]) + abs(g[0][1] - g[1][1])
                ok = ok and seglen(first) >= MIN_STUB and seglen(last) >= MIN_STUB
            if ok:
                out.append(clean)
        return out


def route_cost(pts, a, b, L, routes, boxes):
    """Цена маршрута pts связи a->b при уже проложенных routes и препятствиях boxes."""
    ss = segs(pts)
    cost = W_BEND * (len(pts) - 2) + W_LEN * sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in ss)
    for key, other in routes.items():
        if key == (a, b):
            continue
        os_ = segs(other)
        for s in ss:
            for t in os_:
                if seg_cross(s, t):
                    cost += W_CROSS
                elif seg_overlap(s, t):
                    cost += W_OVERLAP
        for end in (pts[0], pts[-1]):
            for oend in (other[0], other[-1]):
                if abs(end[0] - oend[0]) < 2 and abs(end[1] - oend[1]) < 2:
                    cost += W_PORT
    xs_ = [p[0] for p in pts]; ys_ = [p[1] for p in pts]
    bb = (min(xs_) - 20, min(ys_) - 20, max(xs_) - min(xs_) + 40, max(ys_) - min(ys_) + 40)
    for sid, s in L.shapes.items():
        box = (s['x'], s['y'], s['w'], s['h'])
        if not box_box(bb, box, pad=0) and not box_box(bb, s['lbox'], pad=0):
            continue
        if sid == a or sid == b:
            # Правило: промежуточные отрезки держат зазор и от своих фигур (источника и цели).
            check = ss[1:] if sid == a else ss[:-1]
            inner = ss[1:-1]
            cost += W_NODE * sum(seg_box(t, box) for t in check)
            cost += W_NODE * sum(seg_box(t, box, pad=-CLEAR_NODE) for t in inner)
        else:
            cost += W_NODE * sum(seg_box(t, box, pad=-CLEAR_NODE) for t in ss)
        cost += W_LABEL * sum(seg_box(t, s['lbox'], pad=-CLEAR_LABEL) for t in ss)
    left = L.lanes[0]['x'] + LANE_HEADER
    if min(p[0] for p in pts) < left:
        cost += W_NODE
    return cost


def doc_candidates(L, d):
    """Места документа: полоса документов дорожки источника или получателя."""
    res = []
    anchors = [x for x in (d.get('producer'), d.get('consumer')) if x]
    for anc in anchors:
        A = L.shapes[anc]
        for lane in {A['lane']} | {L.shapes[x]['lane'] for x in anchors}:
            for dx in (-55, 0, 55, 110):
                res.append((lane, A['cx'] + dx))
    if d.get('producer') and d.get('consumer'):
        P, C = L.shapes[d['producer']], L.shapes[d['consumer']]
        res.append((P['lane'], (P['cx'] + C['cx']) / 2))
    return list(dict.fromkeys(res))


def place_cost(L, did):
    """Цена положения документа: накладки фигуры и подписи на другие фигуры/подписи."""
    s = L.shapes[did]
    me = [(s['x'], s['y'], s['w'], s['h']), s['lbox']]
    cost = 0
    for oid, o in L.shapes.items():
        if oid == did:
            continue
        for m in me:
            if box_box(m, (o['x'], o['y'], o['w'], o['h']), pad=-6):
                cost += W_BOX
            if box_box(m, o['lbox'], pad=-4):
                cost += W_BOX
    return cost


class Solver:
    def __init__(self, proc, priority, lane_heights=None, gap=GAP, seed=0):
        self.proc = proc
        self.L = Layout(proc, priority, lane_heights, gap)
        self.flows = [(e['from'], e['to'], 'flow') for e in proc['edges']]
        self.docs = proc.get('docs', [])
        self.assocs = {}
        for d in self.docs:
            lst = []
            if d.get('producer'):
                lst.append((d['producer'], d['id'], 'assoc'))
            if d.get('consumer'):
                lst.append((d['id'], d['consumer'], 'assoc'))
            self.assocs[d['id']] = lst
        self.routes = {}
        self.cache = {}
        self.rng = random.Random(seed)

    def best_route(self, a, b, kind):
        best, bc = None, math.inf
        for pts in self.L.candidates(a, b, kind):
            c = route_cost(pts, a, b, self.L, self.routes, None)
            if c < bc:
                best, bc = pts, c
        return best, bc

    def place_doc(self, d):
        L = self.L
        for key in [(x[0], x[1]) for x in self.assocs[d['id']]]:
            self.routes.pop(key, None)
        best = None
        for lane, cx in doc_candidates(L, d):
            L.add_shape(d['id'], 'doc', lane, cx, L.row(lane) + DOC_CY, d['name'])
            c = place_cost(L, d['id'])
            # линии, которые документ накрывает
            s = L.shapes[d['id']]
            for key, pts in self.routes.items():
                for t in segs(pts):
                    if seg_box(t, (s['x'], s['y'], s['w'], s['h']), pad=-CLEAR_NODE):
                        c += W_NODE
                    if seg_box(t, s['lbox'], pad=-CLEAR_LABEL):
                        c += W_LABEL
            if best is not None and c >= best[0]:
                continue
            chosen = []
            for a, b, kind in self.assocs[d['id']]:
                pts, rc = self.best_route(a, b, kind)
                c += rc
                chosen.append(((a, b), pts))
                self.routes[(a, b)] = pts
            for k, _ in chosen:
                self.routes.pop(k, None)
            if best is None or c < best[0]:
                best = (c, lane, cx, chosen)
        _, lane, cx, chosen = best
        L.add_shape(d['id'], 'doc', lane, cx, L.row(lane) + DOC_CY, d['name'])
        for k, pts in chosen:
            self.routes[k] = pts

    def solve(self, passes=3):
        for a, b, kind in self.flows:
            self.routes[(a, b)], _ = self.best_route(a, b, kind)
        for d in self.docs:
            self.place_doc(d)
        for _ in range(passes):
            for a, b, kind in self.flows:
                self.routes.pop((a, b))
                self.routes[(a, b)], _ = self.best_route(a, b, kind)
            for d in self.docs:
                self.place_doc(d)
                for a, b, kind in self.assocs[d['id']]:
                    self.routes.pop((a, b))
                    self.routes[(a, b)], _ = self.best_route(a, b, kind)
        return self.improve_pairs()

    def total(self):
        m = self.metrics()
        return (m['crossings'] * W_CROSS + m['overlaps'] * W_OVERLAP + m['node_hits'] * W_NODE +
                m['label_hits'] * W_LABEL + m['doc_overlaps'] * W_BOX + m['cost'] * 0.001)

    def kind_of(self, key):
        for a, b, kind in self.flows:
            if (a, b) == key:
                return kind
        return 'assoc'

    def ranked(self, key, k=12):
        a, b = key
        kind = self.kind_of(key)
        cands = [(route_cost(p, a, b, self.L, self.routes, None), p) for p in self.L.candidates(a, b, kind)]
        cands.sort(key=lambda x: x[0])
        return [p for _, p in cands[:k]]

    def improve_pairs(self, rounds=4):
        """Совместная перекладка пар пересекающихся стрелок и перестановка документов."""
        for _ in range(rounds):
            improved = False
            for k1, k2 in crossing_pairs(self):
                if k1 not in self.routes or k2 not in self.routes:
                    continue
                base = self.total()
                saved = {k1: self.routes[k1], k2: self.routes[k2]}
                best = (base, saved)
                for first, second in ((k1, k2), (k2, k1)):
                    self.routes.pop(first); self.routes.pop(second)
                    for p1 in self.ranked(first):
                        self.routes[first] = p1
                        self.routes[second], _ = self.best_route(second[0], second[1], self.kind_of(second))
                        t = self.total()
                        if t < best[0] - 1e-6:
                            best = (t, {first: p1, second: self.routes[second]})
                        self.routes.pop(second)
                    self.routes.pop(first, None)
                    self.routes.update(saved)
                self.routes.update(best[1])
                if best[0] < base - 1e-6:
                    improved = True
            # документы, участвующие в пересечениях — пробуем все места заново
            for d in self.docs:
                keys = [(a, b) for a, b, _ in self.assocs[d['id']]]
                if not any(k1 in keys or k2 in keys for k1, k2 in crossing_pairs(self)):
                    continue
                base = self.total()
                saved_shape = dict(self.L.shapes[d['id']])
                saved = {k: self.routes[k] for k in keys}
                self.place_doc(d)
                if self.total() < base - 1e-6:
                    improved = True
                else:
                    self.L.shapes[d['id']] = saved_shape
                    self.routes.update(saved)
            if not improved:
                break
        return self

    def metrics(self):
        keys = list(self.routes)
        cross = overlap = node_hits = label_hits = 0
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                for s in segs(self.routes[keys[i]]):
                    for t in segs(self.routes[keys[j]]):
                        cross += seg_cross(s, t)
                        overlap += seg_overlap(s, t)
        for (a, b), pts in self.routes.items():
            ss = segs(pts)
            for sid, s in self.L.shapes.items():
                box = (s['x'], s['y'], s['w'], s['h'])
                if sid in (a, b):
                    node_hits += sum(seg_box(t, box) for t in (ss[1:] if sid == a else ss[:-1]))
                    node_hits += sum(seg_box(t, box, pad=-CLEAR_NODE) for t in ss[1:-1])
                else:
                    node_hits += sum(seg_box(t, box, pad=-CLEAR_NODE) for t in ss)
                label_hits += sum(seg_box(t, s['lbox'], pad=-CLEAR_LABEL) for t in ss)
        box_hits = sum(place_cost(self.L, d['id']) for d in self.docs) // W_BOX
        total = sum(route_cost(p, a, b, self.L, self.routes, None) for (a, b), p in self.routes.items())
        return {'crossings': cross, 'overlaps': overlap, 'node_hits': node_hits,
                'label_hits': label_hits, 'doc_overlaps': box_hits, 'cost': round(total)}


def crossing_pairs(sv):
    keys = list(sv.routes)
    res = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if any(seg_cross(s, t) for s in segs(sv.routes[keys[i]]) for t in segs(sv.routes[keys[j]])):
                res.append((keys[i], keys[j]))
    return res


def solve(proc, tries=40, seed=1):
    """Перебор порядка элементов и зазора; возвращает лучший Solver."""
    base = [n['id'] for n in proc['nodes']]
    rng = random.Random(seed)
    orders = [base]
    for _ in range(tries):
        o = base[:]
        rng.shuffle(o)
        orders.append(o)
    seen, best = set(), None
    for gap in (GAP, GAP + 30):
        for o in orders:
            probe = Layout(proc, o, None, gap)
            sig = (gap, tuple(sorted(probe.col.items())))
            if sig in seen:
                continue
            seen.add(sig)
            sv = Solver(proc, o, None, gap).solve()
            m = sv.metrics()
            score = (m['crossings'], m['node_hits'] + m['label_hits'] + m['doc_overlaps'], m['overlaps'], m['cost'])
            if best is None or score < best[0]:
                best = (score, o, gap, sv)
    # Финал: ужимаем дорожки без документов и прокладываем заново с тем же порядком.
    _, order, gap, sv = best
    doc_lanes = {sv.L.shapes[d['id']]['lane'] for d in proc.get('docs', [])}
    heights = [LANE_H_DOCS if i in doc_lanes else LANE_H_PLAIN for i in range(len(proc['lanes']))]
    final = Solver(proc, order, heights, gap).solve()
    if final.metrics()['crossings'] > sv.metrics()['crossings']:
        final = sv
    return final
