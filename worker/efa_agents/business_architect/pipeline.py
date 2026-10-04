# -*- coding: utf-8 -*-
"""
Агент «Бизнес-архитектор»: сборка первой итерации и итерации по замечаниям клиента.

Порядок первой сборки (как в прогонах 2–6, обобщено):
  1. Оргструктура → аудит → цели → аудит → функции по 3 группам → аудит → процессы по 3 группам → аудит.
     Ядро проверяется сразу: от него зависят все остальные разделы.
  2. Параллельно: детальный ключевой процесс, риски, реестр НМД, регулярные встречи, финансы, ИТ, объекты, проекты, продукты,
     паспорта руководителей; каждый раздел — проверки кода, затем аудит и исправление подтверждённых замечаний.
  3. Тексты документов (регламент ключевого процесса, положение о подразделении-владельце).
  4. BPMN ключевого процесса с декомпозицией: верхний уровень ≤ 14 узлов / 5 дорожек + подпроцессы ≤ 12 / 4,
     раскладка движком efa_layout → .bpmn и скрипт Sila Union.

Вход (dict): company, brief (анкета/досье текстом), headcount, systems [..], units [..] (доп. обязательные подразделения),
             flagship (ключевой процесс, необязательно), options {passports: heads|all|none, bpmn: bool, documents: bool}.
Итерация: те же поля + previous (результат прошлой итерации) + remarks (замечания клиента текстом).
"""
import json
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .. import auditor
from ..bpmn import check as bpmn_check
from ..harness import Session, js, norm, slug
from . import prompts as P
from . import validators as V

BPMN_DIR = Path(__file__).resolve().parent.parent / 'bpmn'
PARALLEL = 5


class Run:
    def __init__(self, inp, progress=None, artifact=None):
        self.inp = inp
        self.opts = dict({'passports': 'heads', 'bpmn': True, 'documents': True, 'audit': True}, **(inp.get('options') or {}))
        self.profile = V.Profile(inp)
        self.a = V.Arch(self.profile)
        self.s = Session(P.SYSTEM, on_step=self._on_step)
        self.progress = progress or (lambda stage, info=None: None)
        self.artifact = artifact or (lambda name, body, ctype='text/plain': None)
        self.sections = {}
        self.audits = []
        self.stage = ''

    def _on_step(self, rec):
        self.progress(self.stage, {'step': rec['step'], 'model': rec['model'], 'rub_total': round(self.s.rub, 2),
                                   'errors_left': len(rec['final_errors'])})

    # ---------------------------------------------------------------- контекст
    @property
    def brief(self):
        sys_line = ('\n- Учётные системы: ' + ', '.join(self.profile.systems)) if self.profile.systems else ''
        hc = f'\n- Численность: {self.profile.headcount} сотрудников' if self.profile.headcount else ''
        return f'Компания: {self.profile.company}.{hc}{sys_line}\nАнкета и вводные клиента:\n{self.inp.get("brief", "")}'

    def ctx(self, goals=False, funcs=False, procs=False):
        t = self.brief + '\n\nОргструктура:\n' + js(self.a.org)
        if goals:
            t += '\n\nЦели и показатели:\n' + js(self.a.goals)
        if funcs:
            t += '\n\nФункции (id, название, группа):\n' + js([{'id': f['id'], 'name': f['name'], 'group': f.get('group')} for f in self.a.funcs])
        if procs:
            t += '\n\nПроцессы:\n' + js([p['name'] for p in self.a.procs])
        return t

    def linked(self):
        """Связанные разделы для аудитора — чтобы он не «ругался» на то, чего не видит."""
        return self.ctx(goals=True, funcs=True, procs=True)

    def checked(self, name, kind, data, validator, schema):
        """Аудит и исправление раздела (если включено)."""
        if not self.opts['audit'] or data is None:
            return data
        data, rep = auditor.audit_and_fix(self.s, name, P.AUDIT_Q[kind], data, self.linked(), validator, schema)
        self.audits.append(rep)
        return data

    # ---------------------------------------------------------------- ядро
    def build_org(self):
        org = self.s.ask('org', self.brief + f"""

Задача: построй оргструктуру компании.
Схема ответа:
{P.ORG_SCHEMA}
Обязательные подразделения: {', '.join(self.profile.units)}; добавь другие, нужные для деятельности из анкеты.""" +
                         (f' Численность: сумма count по всем должностям {self.profile.hc_range[0]}–{self.profile.hc_range[1]} (руководители подразделений входят в положения своих подразделений).' if self.profile.headcount else ''),
                         V.v_org(self.a), fix=V.fix_headcount(self.profile))
        if org is None:
            raise RuntimeError('модель не построила оргструктуру')
        self.a.org = org
        self.a.org = self.checked('org', 'org', org, V.v_org(self.a), P.ORG_SCHEMA)

    def build_goals(self):
        g = self.s.ask('goals', self.ctx() + f"""

Задача: стратегические цели на 3 года по сбалансированной системе показателей: 4 перспективы (Финансы, Клиенты, Процессы, Развитие), по 2–3 цели в каждой, у цели 1–2 показателя.
Схема ответа:
{P.GOALS_SCHEMA}""", V.v_goals(self.a))
        g = self.checked('goals', 'goals', g, V.v_goals(self.a), P.GOALS_SCHEMA)
        self.a.goals = (g or {}).get('goals', [])

    def build_functions(self):
        funcs, done = [], []
        for grp, hint in P.FUNC_GROUPS:
            f = self.s.ask('functions_' + grp, self.ctx() + f"""

Задача: {grp} функции верхнего уровня ({hint}) — 3–8 функций, у каждой 3–5 подфункций с ответственной должностью.
Схема ответа:
{P.FUNC_SCHEMA}
{P.EX_FUNC}
Уже описанные функции других групп (НЕ повторяй их): {js(done) if done else 'пока нет'}""", V.v_funcs(self.a, grp, list(done)))
            for x in (f or {}).get('functions', []):
                x['group'] = grp
                funcs.append(x)
                done.append(x['name'])
        self.a.funcs = funcs
        fixed = self.checked('functions', 'functions', {'functions': funcs}, self._v_funcs_all, P.FUNC_SCHEMA)
        self.a.funcs = fixed['functions']

    def _v_funcs_all(self, f):
        groups = [g for g, _ in P.FUNC_GROUPS]
        e = [f'у функции «{x.get("name")}» поле group должно быть одним из: {", ".join(groups)}' for x in f.get('functions', []) if x.get('group') not in groups]
        for grp, _ in P.FUNC_GROUPS:
            part = {'functions': [x for x in f.get('functions', []) if x.get('group') == grp]}
            e += [x for x in V.v_funcs(self.a, grp)(part) if 'нужно 3–8' not in x]
        return e[:12]

    def build_processes(self):
        procs, done = [], []
        for grp in P.PROC_GROUPS:
            p = self.s.ask('processes_' + grp, self.ctx(funcs=True) + f"""

Задача: {grp} бизнес-процессы компании — 3–6 сквозных процессов. Процесс ≠ функция: у процесса есть событие-старт, результат, входы, выходы и этапы по порядку.
Схема ответа:
{P.PROC_SCHEMA}
{P.EX_PROC}
Уже описанные процессы других групп (НЕ повторяй их): {js(done) if done else 'пока нет'}""", V.v_procs(self.a, grp, list(done)))
            for x in (p or {}).get('processes', []):
                x['group'] = grp
                procs.append(x)
                done.append(x['name'])
        # сквозная нумерация: модель по группам начинает номера заново
        for i, x in enumerate(procs, 1):
            x['id'] = str(i)
        self.a.procs = procs
        fixed = self.checked('processes', 'processes', {'processes': procs}, self._v_procs_all, P.PROC_SCHEMA)
        self.a.procs = fixed['processes']

    def _v_procs_all(self, d):
        e = [f'у процесса «{x.get("name")}» поле group должно быть одним из: {", ".join(P.PROC_GROUPS)}' for x in d.get('processes', []) if x.get('group') not in P.PROC_GROUPS]
        return (e + [x for x in V.v_procs(self.a)(d) if 'минимум 3' not in x])[:12]

    # ---------------------------------------------------------------- остальные разделы
    def flagship_name(self):
        if self.inp.get('flagship'):
            return self.inp['flagship']
        core = [p for p in self.a.procs if p.get('group') == 'основные'] or self.a.procs
        return core[0]['name'] if core else 'Основной процесс компании'

    def build_flow(self):
        name = self.flagship_name()
        t = self.s.ask('flow', self.ctx(procs=True) + f"""

Задача: детально распиши процесс «{name}»: 10–16 шагов, с документами на каждом шаге, учётом в системах компании, развилками.
Схема ответа:
{P.FLOW_SCHEMA}""", V.v_flow(self.a), max_tokens=10000)
        t = self.checked('flow', 'flow', t, V.v_flow(self.a), P.FLOW_SCHEMA)
        return (t or {}).get('flow', t)

    def build_risks(self):
        r = self.s.ask('risks', self.ctx(goals=True) + f"""

Задача: риски компании (стратегические, операционные, финансовые, кадровые, ИТ) — 15–20, конкретные для этой компании и болей из анкеты; и решения: ИИ-агенты и автоматизация поверх существующих систем, организационные изменения.
Схема ответа:
{P.RISKS_SCHEMA}""", V.v_risks(self.a))
        return self.checked('risks', 'risks', r, V.v_risks(self.a), P.RISKS_SCHEMA)

    def build_registry(self):
        r = self.s.ask('registry', self.ctx(procs=True) + f"""

Задача: реестр нормативно-методической документации компании — 30–80 документов в 5–8 категориях (организационные, регламенты процессов, положения о подразделениях, должностные инструкции, финансы, персонал, ИТ и отраслевые). Обязательно: положение о КАЖДОМ подразделении, регламент КАЖДОГО основного процесса (поле process — его название), должностная инструкция КАЖДОГО руководителя (генеральный, директора, руководители подразделений).
Схема ответа: {P.REGISTRY_SCHEMA}""", V.v_registry(self.a), max_tokens=10000)
        return self.checked('registry', 'registry', r, V.v_registry(self.a), P.REGISTRY_SCHEMA)

    def build_meetings(self):
        m = self.s.ask('meetings', self.ctx(goals=True) + f"""

Задача: система регулярных встреч управления — 3–5 встреч (стратегическая, оперативная руководства, по ключевым направлениям из анкеты) с полными регламентами.
Схема ответа:
{P.MEETINGS_SCHEMA}""", V.v_meetings(self.a), max_tokens=10000)
        return self.checked('meetings', 'meetings', m, V.v_meetings(self.a), P.MEETINGS_SCHEMA)

    def build_section(self, kind):
        extra = kind in ('it', 'projects', 'finance')
        v = getattr(V, 'v_' + kind)(self.a)
        d = self.s.ask(kind, self.ctx(goals=extra) + f"\n\nЗадача: {P.SECTION_TASKS[kind]}. Где данных нет — отраслевое допущение с пометкой.\nСхема ответа:\n{P.SECTION_SCHEMAS[kind]}",
                       v, max_tokens=12000)
        return self.checked(kind, kind, d, v, P.SECTION_SCHEMAS[kind])

    def positions_list(self):
        o = self.a.org
        out = [(o['ceo'], None, None)]
        out += [(d['title'], None, d.get('reports_to')) for d in o.get('directors', [])]
        heads = {norm(d['head']) for d in o['departments']}
        for d in o['departments']:
            out.append((d['head'], d['name'], d.get('reports_to')))
            for p in d['positions']:
                out.append((p['title'], d['name'], d['head'] if norm(p['title']) != norm(d['head']) else d.get('reports_to')))
        seen, res = set(), []
        for t, dep, rep in out:
            if norm(t) in seen:
                continue
            seen.add(norm(t))
            if self.opts['passports'] == 'heads' and norm(t) not in heads and dep is not None:
                continue
            res.append({'title': t, 'department': dep, 'reports_to': rep})
        return res

    def passport(self, pos):
        title = pos['title']
        own = [f['name'] + ': ' + ', '.join(s['name'] for s in f.get('subfunctions', []) if norm(s.get('owner')) == norm(title))
               for f in self.a.funcs if any(norm(s.get('owner')) == norm(title) for s in f.get('subfunctions', [])) or norm(f.get('department')) == norm(pos.get('department'))]
        k = V.kpis_of(self.a, title)
        p = self.s.ask('passport_' + slug(title), self.ctx() + f"""

Должность: {title}. Подразделение: {pos.get('department') or 'руководство компании'}. Подчиняется: {pos.get('reports_to') or 'собственникам / совету директоров'}.
Связанные функции и подфункции: {js(own[:6])}
Показатели стратегии, владельцем которых является эта должность: {js(k) if k else 'нет'}

Задача: паспорт должности.
Схема ответа:
{P.PASSPORT_SCHEMA.format(title=title)}""", V.v_passport(self.a, title), max_tokens=6000)
        return self.checked('passport_' + slug(title, 30), 'passport', p, V.v_passport(self.a, title), P.PASSPORT_SCHEMA.format(title=title))

    def document(self, title, flow):
        return self.s.ask('doc_' + slug(title), self.ctx(procs=True) + '\n\nКлючевой процесс:\n' + js(flow) + f"""

Задача: полный текст документа «{title}» для {self.profile.company} — готовый к утверждению, конкретный (должности, сроки, документы, системы), 15–40 блоков.
Схема ответа: {P.DOC_SCHEMA.format(title=title)}""", V.v_doc(self.a), max_tokens=12000)

    # ---------------------------------------------------------------- BPMN
    def bpmn(self, flow):
        name = flow.get('name') or self.flagship_name()
        top = self.s.ask('bpmn_top', self.ctx() + '\n\nПроцесс (шаги):\n' + js(flow) + f"""

Задача: схема ВЕРХНЕГО уровня процесса «{name}» в формате генератора BPMN: не больше 14 узлов и 5 дорожек. Крупные блоки (3–4) оформи задачами-подпроцессами: у такой задачи поле "subprocess" = id подпроцесса (латиницей, начинается с sp_), а её детали будут отдельными схемами.
{P.BP_RULES}
Схема ответа: {P.BP_SCHEMA}""", V.v_bpmn(self.a, 14, 5), max_tokens=8000, fix=V.fix_bpmn_docs)
        if not top:
            return {'error': 'модель не построила схему верхнего уровня'}
        subs = [n for n in top.get('nodes', []) if n.get('subprocess')]

        def one(n):
            sid = re.sub(r'[^a-z0-9_]', '_', str(n['subprocess']).lower())
            return sid, self.s.ask('bpmn_' + sid, self.ctx() + '\n\nПроцесс (шаги):\n' + js(flow) + f"""

Задача: детальная схема подпроцесса «{n['label']}» (id {sid}) — часть процесса «{name}», только шаги этого блока: от входа в блок до выхода из него. Не больше 12 узлов и 4 дорожек.
{P.BP_RULES}
Схема ответа: {P.BP_SCHEMA}""", V.v_bpmn(self.a, 12, 4), max_tokens=8000, fix=V.fix_bpmn_docs)
        with ThreadPoolExecutor(3) as ex:
            parts = dict(ex.map(one, subs))
        diagrams = [('flow_top', top)] + [('flow_' + k, v) for k, v in parts.items() if v]
        for pid, d in diagrams:
            d['id'] = pid
            for nd in d.get('nodes', []):
                if nd.get('subprocess') and not str(nd.get('label', '')).startswith('▸'):
                    nd['label'] = '▸ ' + nd['label']
        with ThreadPoolExecutor(4) as ex:
            layout = list(ex.map(lambda x: self.layout(*x), diagrams))
        return {'diagrams': {pid: d for pid, d in diagrams}, 'layout': layout}

    def layout(self, pid, proc):
        """Раскладка в отдельном процессе: движок тяжёлый (минуты на схему), таймаут не должен ронять весь запуск."""
        t = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / f'{pid}.json'
            src.write_text(json.dumps(proc, ensure_ascii=False), encoding='utf-8')
            code = f"import sys; sys.path.insert(0, {str(BPMN_DIR)!r}); import efa_bpmn_generator as G; G.main({str(src)!r}, {tmp!r}, tries=6)"
            try:
                r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=1500)
            except subprocess.TimeoutExpired:
                return {'id': pid, 'ok': False, 'error': 'раскладка не уложилась в 25 минут', 'sec': round(time.time() - t)}
            out = Path(tmp)
            if r.returncode != 0 or not (out / f'{pid}.bpmn').exists():
                return {'id': pid, 'ok': False, 'error': (r.stderr or r.stdout)[-500:], 'sec': round(time.time() - t)}
            bpmn = (out / f'{pid}.bpmn').read_text(encoding='utf-8')
            groovy = (out / f'{pid}_sila.groovy').read_text(encoding='utf-8')
            lay = (out / f'{pid}_layout.txt').read_text(encoding='utf-8')
        n, problems = bpmn_check.check_groovy(groovy)
        self.artifact(f'bpmn/{pid}.bpmn', bpmn, 'application/xml')
        self.artifact(f'bpmn/{pid}_sila.groovy', groovy, 'text/plain')
        self.artifact(f'bpmn/{pid}.json', json.dumps(proc, ensure_ascii=False, indent=1), 'application/json')
        cr = re.search(r'Пересечений стрелок: (\d+)', lay)
        return {'id': pid, 'ok': not problems, 'crossings': int(cr.group(1)) if cr else None, 'edges_checked': n,
                'sila_problems': problems[:10], 'sec': round(time.time() - t)}

    # ---------------------------------------------------------------- сборка
    def first(self):
        st = self.sections
        for stage, fn in (('Оргструктура', self.build_org), ('Цели и показатели', self.build_goals),
                          ('Функции', self.build_functions), ('Процессы', self.build_processes)):
            self.stage = stage
            fn()
        st['org'], st['goals'], st['functions'], st['processes'] = self.a.org, self.a.goals, self.a.funcs, self.a.procs

        self.stage = 'Разделы'
        jobs = {'flow': self.build_flow, 'risks': self.build_risks, 'registry': self.build_registry, 'meetings': self.build_meetings}
        jobs.update({k: (lambda k=k: self.build_section(k)) for k in P.SECTION_TASKS})
        with ThreadPoolExecutor(PARALLEL) as ex:
            futs = {k: ex.submit(fn) for k, fn in jobs.items()}
            pos = self.positions_list() if self.opts['passports'] != 'none' else []
            pfuts = [ex.submit(self.passport, p) for p in pos]
            for k, f in futs.items():
                st[k] = f.result()
            st['passports'] = [f.result() for f in pfuts]

        flow = st.get('flow') or {}
        if self.opts['documents'] and flow:
            self.stage = 'Документы'
            owner = next((p.get('owner') for p in self.a.procs if norm(p.get('name')) == norm(flow.get('name'))), None)
            dept = next((d['name'] for d in self.a.org['departments'] if owner and norm(d.get('head')) == norm(owner)), None)
            if not dept:   # ключевого процесса нет в дереве — берём подразделение, чьи сотрудники чаще всего исполнители шагов
                roles = [norm(s.get('role')) for s in flow.get('steps', [])]
                score = {d['name']: sum(r in {norm(d['head'])} | {norm(p['title']) for p in d['positions']} for r in roles) for d in self.a.org['departments']}
                dept = max(score, key=score.get) if score and max(score.values()) else None
            titles = ['Регламент процесса «' + (flow.get('name') or self.flagship_name()) + '»'] + ([f'Положение о подразделении «{dept}»'] if dept else [])
            with ThreadPoolExecutor(2) as ex:
                st['documents'] = list(ex.map(lambda t: self.document(t, flow), titles))
        if self.opts['bpmn'] and flow:
            self.stage = 'BPMN'
            st['bpmn'] = self.bpmn(flow)
        return self.result()

    # ---------------------------------------------------------------- итерация по замечаниям
    SECTION_KEYS = ['org', 'goals', 'functions', 'processes', 'flow', 'risks', 'registry', 'meetings', 'finance', 'it', 'physical',
                    'projects', 'products', 'passports', 'documents']

    def validators(self):
        return {'org': V.v_org(self.a), 'goals': lambda d: V.v_goals(self.a)({'goals': d}), 'functions': lambda d: self._v_funcs_all({'functions': d}),
                'processes': lambda d: self._v_procs_all({'processes': d}),
                'flow': lambda d: V.v_flow(self.a)({'flow': d}), 'risks': V.v_risks(self.a), 'registry': V.v_registry(self.a),
                'meetings': V.v_meetings(self.a), **{k: getattr(V, 'v_' + k)(self.a) for k in P.SECTION_TASKS}}

    def iterate(self):
        prev = self.inp['previous']['sections'] if 'sections' in self.inp['previous'] else self.inp['previous']
        st = self.sections = json.loads(json.dumps(prev))
        self.a.org, self.a.goals, self.a.funcs, self.a.procs = st['org'], st['goals'], st['functions'], st['processes']
        remarks = self.inp['remarks']
        self.stage = 'Разбор замечаний'
        route = self.s.ask('route', self.brief + '\n\nРазделы бизнес-архитектуры: ' + ', '.join(self.SECTION_KEYS) + f"""

Замечания клиента:
{remarks}

Задача: определи, какие разделы нужно изменить по этим замечаниям, и что именно в каждом.
Схема ответа: {{"changes": [{{"section": "ключ раздела из списка", "what": "что изменить"}}]}}""",
                           lambda r: [f'раздел «{c.get("section")}» не из списка' for c in r.get('changes') or [] if c.get('section') not in self.SECTION_KEYS] or
                                     ([] if r.get('changes') else ['нет ни одного изменения']))
        changes = {}
        for c in (route or {}).get('changes', []):
            changes.setdefault(c['section'], []).append(c['what'])
        vals = self.validators()
        before = {k: len(vals[k](st[k])) for k in vals if st.get(k) is not None}
        self.stage = 'Правки по замечаниям'
        for key in [k for k in self.SECTION_KEYS if k in changes]:
            if key in ('passports', 'documents'):
                continue            # пересобираются целиком ниже
            data = st.get(key)
            wrap = key in ('goals', 'functions', 'processes', 'flow')
            body = {key: data} if wrap else data
            v = (lambda d, key=key, wrap=wrap: vals[key](d[key] if wrap and key in d else d))
            fixed = self.s.ask('remark_' + key, self.linked() + f'\n\nРаздел «{key}»:\n' + js(body) + '\n\nЗамечания клиента к этому разделу:\n- ' + '\n- '.join(changes[key]) +
                               '\n\nЗадача: исправь раздел по замечаниям, остальное сохрани. Верни ПОЛНЫЙ раздел в той же структуре (те же поля верхнего уровня).',
                               v, max_tokens=12000, fix=(V.fix_headcount(self.profile) if key == 'org' else None))
            if fixed is not None:
                st[key] = fixed[key] if wrap and key in fixed else fixed
                if key == 'org':
                    self.a.org = st['org']
                elif key in ('goals', 'functions', 'processes'):
                    setattr(self.a, {'goals': 'goals', 'functions': 'funcs', 'processes': 'procs'}[key], st[key])
                vals = self.validators()
        # каскад: правка ядра могла сломать ссылки в зависимых разделах (владельцы, подразделения, id целей)
        self.stage = 'Согласование разделов'
        broken = {k: vals[k](st[k]) for k in vals if st.get(k) is not None and k not in changes}
        broken = {k: e for k, e in broken.items() if len(e) > before.get(k, 0)}
        for key, errs in broken.items():
            wrap = key in ('goals', 'functions', 'processes', 'flow')
            body = {key: st[key]} if wrap else st[key]
            v = (lambda d, key=key, wrap=wrap: vals[key](d[key] if wrap and key in d else d))
            fixed = self.s.ask('cascade_' + key, self.linked() + f'\n\nРаздел «{key}»:\n' + js(body) + '\n\nПосле изменений в других разделах проверка нашла ошибки:\n- ' + '\n- '.join(errs) +
                               '\n\nЗадача: исправь только эти ошибки, остальное сохрани. Верни ПОЛНЫЙ раздел в той же структуре.', v, max_tokens=12000)
            if fixed is not None:
                st[key] = fixed[key] if wrap and key in fixed else fixed
        touched = set(changes) | set(broken)
        if self.opts['audit']:
            self.stage = 'Аудит изменённых разделов'
            kinds = [k for k in touched if k in P.AUDIT_Q and st.get(k) is not None]
            with ThreadPoolExecutor(PARALLEL) as ex:
                self.audits += list(ex.map(lambda k: auditor.audit(self.s, k, P.AUDIT_Q[k], st[k], self.linked()), kinds))
        if 'passports' in changes or 'org' in changes:
            self.stage = 'Паспорта'
            with ThreadPoolExecutor(PARALLEL) as ex:
                st['passports'] = list(ex.map(self.passport, self.positions_list()))
        if self.opts['bpmn'] and ('flow' in touched or 'org' in changes):
            self.stage = 'BPMN'
            st['bpmn'] = self.bpmn(st['flow'])
        return self.result(changes=changes, cascade=list(broken))

    # ---------------------------------------------------------------- итог
    def result(self, **extra):
        st = self.sections
        missing = [k for k in ('flow', 'risks', 'registry', 'meetings', *P.SECTION_TASKS) if st.get(k) is None]
        consultant = [dict(i, section=a['section'], kind='спорное — цитата не найдена в разделе') for a in self.audits for i in a.get('disputed', [])]
        consultant += [dict(i, section=a['section'], kind='исправление не принято') for a in self.audits if a.get('fix_rejected') for i in a['confirmed']]
        left = [{'step': x['step'], 'errors': x['final_errors']} for x in self.s.log if x['final_errors'] and not x['step'].startswith(('AUDIT_', 'route'))]
        return {'sections': st, 'audit': self.audits, 'for_consultant': consultant, 'errors_left': left, 'missing': missing,
                'usage': self.s.totals(), **extra}


def run(inp, progress=None, artifact=None):
    r = Run(inp, progress, artifact)
    out = r.iterate() if inp.get('previous') and inp.get('remarks') else r.first()
    out['log'] = r.s.log
    return out
