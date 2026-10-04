# -*- coding: utf-8 -*-
"""
Проверка готового скрипта Sila Union и предпросмотр диаграммы.

  python3 check_and_preview.py <папка_результата> <id_процесса>

1) Проверяет <id>_sila.groovy по правилам входа/выхода стрелок:
   - первый и последний отрезок связи не короче 20 px (иначе Sila рисует
     наконечник боком вдоль грани фигуры);
   - промежуточные отрезки держат зазор 12 px от фигур-концов связи.
2) Проверяет, что <id>.bpmn — корректный XML.
3) Пишет <id>_preview.html — просмотр .bpmn в bpmn-js (движок bpmn.io).
   Откройте файл в браузере; window.__ok / window.__warn — итог импорта.
Код выхода 1, если есть нарушения.
"""
import json
import re
import sys
import xml.dom.minidom
from pathlib import Path

MIN_STUB, CLEAR = 20, 12

PREVIEW = '''<!doctype html><html><head><meta charset="utf-8"><title>Проверка BPMN</title>
<link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/bpmn-js.css">
<style>html,body{margin:0;height:100%;background:#fff}#c{height:100vh}#err{position:fixed;top:8px;left:8px;color:#b00;font:13px sans-serif;white-space:pre}</style>
</head><body><div id="c"></div><div id="err"></div>
<script src="https://unpkg.com/bpmn-js@17.11.1/dist/bpmn-navigated-viewer.development.js"></script>
<script>
const xml=__XML__;
const v=new BpmnJS({container:'#c'});window.__viewer=v;
v.importXML(xml).then(r=>{window.__warn=r.warnings.map(w=>w.message);document.getElementById('err').textContent=r.warnings.length?('Warnings: '+r.warnings.length+'\\n'+window.__warn.join('\\n')):'';v.get('canvas').zoom('fit-viewport');window.__ok=true;}).catch(e=>{window.__ok=false;document.getElementById('err').textContent='ERROR: '+e.message;});
</script></body></html>'''


def check_groovy(src):
    pool = re.search(r"POOL = \[name: '[^']*', x: ([\d.]+)d, y: ([\d.]+)d", src)
    px, py = float(pool.group(1)), float(pool.group(2))
    lanes = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(
        r"\[id: '(lane\d+)', kind: 'lane', name: '[^']*', x: ([\d.]+)d, y: ([\d.]+)d", src)}
    els = {}
    for m in re.finditer(r"\[id: '(\w+)', kind: '\w+', name: '(?:[^'\\]|\\.)*', lane: '(lane\d+)', "
                         r"x: ([\d.-]+)d, y: ([\d.-]+)d, w: (\d+)d, h: (\d+)d", src):
        i, l, x, y, w, h = m.groups()
        lx, ly = lanes[l]
        els[i] = (px + lx + float(x), py + ly + float(y), float(w), float(h))
    problems, n = [], 0
    for m in re.finditer(r"\[from: '(\w+)', to: '(\w+)', type: '(\w+)'.*?exitX=([\d.]+);exitY=([\d.]+);.*?"
                         r"entryX=([\d.]+);entryY=([\d.]+);.*?wp: \[(.*?)\]\]", src, re.S):
        a, b, _, ex, ey, nx, ny, wp = m.groups()
        n += 1
        A, B = els[a], els[b]
        p0 = (A[0] + float(ex) * A[2], A[1] + float(ey) * A[3])
        p1 = (B[0] + float(nx) * B[2], B[1] + float(ny) * B[3])
        pts = [p0] + [tuple(map(float, q)) for q in re.findall(r"\[([\d.-]+)d, ([\d.-]+)d", wp)] + [p1]
        if len(pts) <= 2:
            continue
        ln = lambda u, v: abs(u[0] - v[0]) + abs(u[1] - v[1])
        if ln(pts[0], pts[1]) < MIN_STUB:
            problems.append('%s→%s: выход короче %d px' % (a, b, MIN_STUB))
        if ln(pts[-2], pts[-1]) < MIN_STUB:
            problems.append('%s→%s: вход короче %d px' % (a, b, MIN_STUB))
        for i in range(1, len(pts) - 2):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            x1, x2 = sorted((x1, x2)); y1, y2 = sorted((y1, y2))
            for bx, by, bw, bh in (A, B):
                if x1 < bx + bw + CLEAR and x2 > bx - CLEAR and y1 < by + bh + CLEAR and y2 > by - CLEAR:
                    problems.append('%s→%s: линия ближе %d px к своей фигуре' % (a, b, CLEAR))
    return n, problems


def main(out_dir, pid):
    out = Path(out_dir)
    src = (out / (pid + '_sila.groovy')).read_text(encoding='utf-8')
    n, problems = check_groovy(src)
    print('Связей проверено: %d, нарушений: %d' % (n, len(problems)))
    for p in problems:
        print('  ' + p)
    bpmn = (out / (pid + '.bpmn')).read_text(encoding='utf-8')
    xml.dom.minidom.parseString(bpmn.encode('utf-8'))
    print('BPMN XML корректен')
    (out / (pid + '_preview.html')).write_text(PREVIEW.replace('__XML__', json.dumps(bpmn)), encoding='utf-8')
    print('Предпросмотр:', out / (pid + '_preview.html'))
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
