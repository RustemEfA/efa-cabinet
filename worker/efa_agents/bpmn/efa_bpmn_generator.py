# -*- coding: utf-8 -*-
"""
EfA → Sila Union: генератор диаграммы бизнес-процесса из одного описания.

Вход: JSON процесса (дорожки, шаги с номером дорожки, связи, документы).
Колонки, места документов и маршруты стрелок считает движок efa_layout.py
(минимум пересечений стрелок, подписи читаются полностью).

Выход (в папке out/):
  1) <id>.bpmn         — BPMN 2.0 XML с координатами (DI): bpmn.io, Camunda Modeler,
                          скрипт Sila Union «Импорт BPMN».
  2) <id>_sila.groovy  — скрипт для Sila Union: строит модель BPMN 2.0 (m_bpmn).
  3) <id>_layout.txt   — отчёт о раскладке: пересечения, накладки.

Запуск:  python3 efa_bpmn_generator.py <процесс.json> [папка_для_результата]
         (по умолчанию результат — в папке out/ рядом с JSON)
"""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from . import efa_layout as E
except ImportError:  # запуск файлом
    import efa_layout as E

# ---------- методология Sila Union (пресет default «Стандартный пресет») ----------
SILA = {
    'model_type': 'm_bpmn',
    'pool': ('o_sila_FUNCTION', 's_bpmn_horizontal_pool'),
    'lane': ('o_sila_ROLE', 's_bpmn_horizontal_lane'),
    'task': ('o_sila_FUNCTION', 's_bpmn_user_task'),
    'start': ('o_sila_EVENT', 's_bpmn_none_start_event'),
    'end': ('o_sila_EVENT', 's_bpmn_none_end_event'),
    'gateway': ('o_sila_LOGIC', 's_bpmn_exclusive_gateway_with_marker'),
    'doc': ('o_sila_DATA', 's_bpmn_data_object'),
    'flow': 'c_bpmn_seq_flow',          # Поток управления
    'assoc': 'c_bpmn_as',               # Ассоциативная связь (направленная): пунктир со стрелкой
}

TASK_LABEL = (110, 60, 5, 5)          # подпись внутри задачи (как в символе методологии)
LABEL_STYLE = 'strokeColor=none;silaText=1;fillColor=none;'
EDGE_STYLE = {
    'flow': 'edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;',
    'assoc': ('edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;'
              'endArrow=openThin;dashed=1;dashPattern=1 2;startArrow=none;'),
}


def q(s):
    return escape(s, {'"': '&quot;'})


def edge_list(proc):
    """Все связи: (from, to, kind, label)."""
    res = [(e['from'], e['to'], 'flow', e.get('label', '')) for e in proc['edges']]
    for d in proc.get('docs', []):
        if d.get('producer'):
            res.append((d['producer'], d['id'], 'assoc', ''))
        if d.get('consumer'):
            res.append((d['id'], d['consumer'], 'assoc', ''))
    return res


# ---------- BPMN 2.0 XML ----------
def to_bpmn(proc, sv):
    L, routes = sv.L, sv.routes
    pid = 'Process_' + proc['id']
    tag = {'task': 'userTask', 'start': 'startEvent', 'end': 'endEvent', 'gateway': 'exclusiveGateway'}
    flows = {(e['from'], e['to']): ('Flow_%d' % i, e) for i, e in enumerate(proc['edges'], 1)}
    incoming, outgoing = {}, {}
    for (s, t), (fid, _) in flows.items():
        outgoing.setdefault(s, []).append(fid)
        incoming.setdefault(t, []).append(fid)
    doc_in, doc_out = {}, {}
    for d in proc.get('docs', []):
        if d.get('consumer'):
            doc_in.setdefault(d['consumer'], []).append(d['id'])
        if d.get('producer'):
            doc_out.setdefault(d['producer'], []).append(d['id'])

    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
         'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
         'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
         'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
         'id="Defs_%s" targetNamespace="https://ef-a.ru/bpmn" exporter="EfA Business Architect" exporterVersion="0.2">'
         % proc['id'],
         '  <bpmn:collaboration id="Collab_%s">' % proc['id'],
         '    <bpmn:participant id="Pool_%s" name="%s" processRef="%s" />' % (proc['id'], q(proc['pool']), pid),
         '  </bpmn:collaboration>',
         '  <bpmn:process id="%s" name="%s" isExecutable="false">' % (pid, q(proc['title'])),
         '    <bpmn:laneSet id="LaneSet_1">']
    for i, name in enumerate(proc['lanes']):
        x.append('      <bpmn:lane id="Lane_%d" name="%s">' % (i, q(name)))
        x += ['        <bpmn:flowNodeRef>%s</bpmn:flowNodeRef>' % n['id'] for n in proc['nodes'] if n['lane'] == i]
        x.append('      </bpmn:lane>')
    x.append('    </bpmn:laneSet>')
    for n in proc['nodes']:
        t = tag[n['type']]
        x.append('    <bpmn:%s id="%s" name="%s">' % (t, n['id'], q(n['label'])))
        x += ['      <bpmn:incoming>%s</bpmn:incoming>' % f for f in incoming.get(n['id'], [])]
        x += ['      <bpmn:outgoing>%s</bpmn:outgoing>' % f for f in outgoing.get(n['id'], [])]
        if n['type'] == 'task':
            for d in doc_in.get(n['id'], []):
                x.append('      <bpmn:property id="Prop_%s_%s" name="__targetRef_placeholder" />' % (n['id'], d))
            for d in doc_in.get(n['id'], []):
                x += ['      <bpmn:dataInputAssociation id="DIA_%s_%s">' % (d, n['id']),
                      '        <bpmn:sourceRef>%s</bpmn:sourceRef>' % d,
                      '        <bpmn:targetRef>Prop_%s_%s</bpmn:targetRef>' % (n['id'], d),
                      '      </bpmn:dataInputAssociation>']
            for d in doc_out.get(n['id'], []):
                x += ['      <bpmn:dataOutputAssociation id="DOA_%s_%s">' % (n['id'], d),
                      '        <bpmn:targetRef>%s</bpmn:targetRef>' % d,
                      '      </bpmn:dataOutputAssociation>']
        x.append('    </bpmn:%s>' % t)
    for d in proc.get('docs', []):
        x.append('    <bpmn:dataObject id="DO_%s" />' % d['id'])
        x.append('    <bpmn:dataObjectReference id="%s" name="%s" dataObjectRef="DO_%s" />' % (d['id'], q(d['name']), d['id']))
    for (s, t), (fid, e) in flows.items():
        name = ' name="%s"' % q(e['label']) if e.get('label') else ''
        x.append('    <bpmn:sequenceFlow id="%s"%s sourceRef="%s" targetRef="%s" />' % (fid, name, s, t))
    x.append('  </bpmn:process>')

    def bounds(bx, by, bw, bh):
        return '<dc:Bounds x="%.0f" y="%.0f" width="%.0f" height="%.0f" />' % (bx, by, bw, bh)

    pool_h = sum(l['h'] for l in L.lanes)
    x += ['  <bpmndi:BPMNDiagram id="Diagram_%s">' % proc['id'],
          '    <bpmndi:BPMNPlane id="Plane_%s" bpmnElement="Collab_%s">' % (proc['id'], proc['id']),
          '      <bpmndi:BPMNShape id="Pool_%s_di" bpmnElement="Pool_%s" isHorizontal="true">%s</bpmndi:BPMNShape>'
          % (proc['id'], proc['id'], bounds(E.POOL_X, E.POOL_Y, E.POOL_HEADER + L.width, pool_h))]
    for i, lane in enumerate(L.lanes):
        x.append('      <bpmndi:BPMNShape id="Lane_%d_di" bpmnElement="Lane_%d" isHorizontal="true">%s</bpmndi:BPMNShape>'
                 % (i, i, bounds(lane['x'], lane['y'], L.width, lane['h'])))
    for sid, s in L.shapes.items():
        extra = ' isMarkerVisible="true"' if s['kind'] == 'gateway' else ''
        lbl = '<bpmndi:BPMNLabel>%s</bpmndi:BPMNLabel>' % bounds(*s['lbox']) if s['lbox'] else ''
        x.append('      <bpmndi:BPMNShape id="%s_di" bpmnElement="%s"%s>%s%s</bpmndi:BPMNShape>'
                 % (sid, sid, extra, bounds(s['x'], s['y'], s['w'], s['h']), lbl))
    for (s, t), (fid, e) in flows.items():
        pts = routes[(s, t)]
        wps = ''.join('<di:waypoint x="%.0f" y="%.0f" />' % p for p in pts)
        lbl = ''
        if e.get('label'):
            (x1, y1), (x2, y2) = pts[0], pts[1]
            lx, ly = (x1 + 8, y1 - 20) if abs(y1 - y2) < 0.5 else (x1 + 6, y1 + 4 if y2 > y1 else y1 - 22)
            lbl = '<bpmndi:BPMNLabel>%s</bpmndi:BPMNLabel>' % bounds(lx, ly, 30, 16)
        x.append('      <bpmndi:BPMNEdge id="%s_di" bpmnElement="%s">%s%s</bpmndi:BPMNEdge>' % (fid, fid, wps, lbl))
    kind = {n['id']: n['type'] for n in proc['nodes']}
    for d in proc.get('docs', []):
        for (a, b), eid, node in (((d['id'], d.get('consumer')), 'DIA_%s_%s' % (d['id'], d.get('consumer')), d.get('consumer')),
                                  ((d.get('producer'), d['id']), 'DOA_%s_%s' % (d.get('producer'), d['id']), d.get('producer'))):
            # связи данных в BPMN XML есть только у задач: документ у события/шлюза рисовать нельзя — иначе «висячая» ссылка
            if (a, b) in routes and kind.get(node) == 'task':
                wps = ''.join('<di:waypoint x="%.0f" y="%.0f" />' % p for p in routes[(a, b)])
                x.append('      <bpmndi:BPMNEdge id="%s_di" bpmnElement="%s">%s</bpmndi:BPMNEdge>' % (eid, eid, wps))
    x += ['    </bpmndi:BPMNPlane>', '  </bpmndi:BPMNDiagram>', '</bpmn:definitions>']
    return '\n'.join(x) + '\n'


# ---------- Groovy-скрипт для Sila Union ----------
def gstr(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def edge_style(kind, A, B, pts):
    """Стиль связи с точными точками выхода/входа (доли ширины/высоты фигуры)."""
    def frac(s, p):
        return round((p[0] - s['x']) / s['w'], 3), round((p[1] - s['y']) / s['h'], 3)
    ex, ey = frac(A, pts[0])
    nx, ny = frac(B, pts[-1])
    return (EDGE_STYLE[kind] + 'exitX=%s;exitY=%s;exitDx=0;exitDy=0;exitPerimeter=0;'
            'entryX=%s;entryY=%s;entryDx=0;entryDy=0;entryPerimeter=0;' % (ex, ey, nx, ny))


def to_groovy(proc, sv):
    L, routes = sv.L, sv.routes
    lines = []
    for i, lane in enumerate(L.lanes):
        lines.append("  [id: 'lane%d', kind: 'lane', name: %s, x: %dd, y: %dd, w: %dd, h: %dd]"
                     % (i, gstr(lane['name']), E.POOL_HEADER, lane['y'] - E.POOL_Y, L.width, lane['h']))
    for sid, s in L.shapes.items():
        lane = L.lanes[s['lane']]
        if s['lbox']:
            bx, by, bw, bh = s['lbox']
            lw, lh, lx, ly = bw, bh, bx - s['x'], by - s['y']
        elif s['kind'] == 'task':
            lw, lh, lx, ly = TASK_LABEL
        else:
            lw, lh, lx, ly = 0, 0, 0, 0
        lines.append("  [id: %s, kind: '%s', name: %s, lane: 'lane%d', x: %.0fd, y: %.0fd, w: %dd, h: %dd, "
                     "lw: %.0fd, lh: %.0fd, lx: %.0fd, ly: %.0fd]"
                     % (gstr(sid), s['kind'], gstr(s['label']), s['lane'], s['x'] - lane['x'], s['y'] - lane['y'],
                        s['w'], s['h'], lw, lh, lx, ly))
    edges = []
    for a, b, kind, name in edge_list(proc):
        pts = routes[(a, b)]
        wps = ', '.join('[%.0fd, %.0fd]' % p for p in pts[1:-1])
        edges.append("  [from: %s, to: %s, type: '%s', name: %s,\n   style: %s,\n   wp: [%s]]"
                     % (gstr(a), gstr(b), SILA[kind], gstr(name),
                        gstr(edge_style(kind, L.shapes[a], L.shapes[b], pts)), wps))
    types = ',\n'.join("  %s: [%s, %s]" % (k, gstr(v[0]), gstr(v[1])) for k, v in SILA.items() if isinstance(v, tuple))
    pool_h = sum(l['h'] for l in L.lanes)
    tpl = Path(__file__).with_name('sila_build_model.groovy.tpl').read_text(encoding='utf-8')
    return (tpl.replace('/*TITLE*/', gstr(proc['title']))
               .replace('/*POOL*/', "[name: %s, x: %dd, y: %dd, w: %dd, h: %dd]"
                        % (gstr(proc['pool']), E.POOL_X, E.POOL_Y, E.POOL_HEADER + L.width, pool_h))
               .replace('/*TYPES*/', types)
               .replace('/*LABEL_STYLE*/', gstr(LABEL_STYLE))
               .replace('/*MODEL_TYPE*/', gstr(SILA['model_type']))
               .replace('/*ELEMENTS*/', ',\n'.join(lines))
               .replace('/*EDGES*/', ',\n'.join(edges)))


def report(proc, sv):
    m = sv.metrics()
    out = ['Раскладка: %s' % proc['title'],
           'Пересечений стрелок: %d' % m['crossings'],
           'Линий через фигуры: %d, через подписи: %d, наложений документов: %d, линий друг по другу: %d'
           % (m['node_hits'], m['label_hits'], m['doc_overlaps'], m['overlaps'])]
    for k1, k2 in E.crossing_pairs(sv):
        out.append('  пересекаются: %s→%s и %s→%s' % (k1 + k2))
    return '\n'.join(out) + '\n'


def main(path, out_dir=None, tries=10):
    proc = json.loads(Path(path).read_text(encoding='utf-8'))
    sv = E.solve(proc, tries=tries)
    out = Path(out_dir) if out_dir else Path(path).parent / 'out'
    out.mkdir(exist_ok=True)
    (out / (proc['id'] + '.bpmn')).write_text(to_bpmn(proc, sv), encoding='utf-8')
    (out / (proc['id'] + '_sila.groovy')).write_text(to_groovy(proc, sv), encoding='utf-8')
    rep = report(proc, sv)
    (out / (proc['id'] + '_layout.txt')).write_text(rep, encoding='utf-8')
    print(rep)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'toir_process.json',
         sys.argv[2] if len(sys.argv) > 2 else None)
