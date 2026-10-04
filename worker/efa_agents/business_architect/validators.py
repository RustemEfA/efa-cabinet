# -*- coding: utf-8 -*-
"""
Проверки разделов бизнес-архитектуры кодом. Перенесены из тестовых прогонов (run_ba2/3/4) и обобщены:
численность, обязательные подразделения и учётные системы берутся из анкеты клиента (Profile), а не из ТехноЛайн.
Каждая проверка возвращает список замечаний — их текст уходит модели при повторе, поэтому формулировки конкретные.
"""
import re

from ..harness import js, norm, similar

# обязательные подразделения: ключ → регулярное выражение по названиям подразделений
UNITS_BASE = {'продажи': r'продаж|коммер', 'финансы': r'финанс|бухгалт', 'персонал': r'персонал|кадр'}
UNITS_EXTRA = {'производство': r'производ|цех', 'сервис': r'сервис', 'снабжение': r'снабж|закуп', 'склад': r'склад',
               'ИТ': r'\bит\b|информац|ит-', 'юридическое': r'юрид|правов', 'АХО': r'административ|хозяйств',
               'качество': r'качеств|отк', 'логистика': r'логист|транспорт|доставк', 'маркетинг': r'маркет'}
EXTERNAL_ROLES = ('клиент', 'поставщик', 'перевозчик', 'заказчик', 'покупатель')
MGMT = r'план|бюджет|контрол|совещ|встреч|анализ|стратег|отчет|эффектив|качеств|аудит|мотивац|цел'


class Profile:
    """Что известно о компании из анкеты; задаёт пороги проверок."""

    def __init__(self, inp):
        self.company = inp.get('company') or 'Компания'
        self.headcount = int(inp.get('headcount') or 0)
        self.systems = [s for s in inp.get('systems') or []]
        self.units = dict(UNITS_BASE)
        for u in inp.get('units') or []:
            self.units[u] = UNITS_EXTRA.get(u, re.escape(norm(u))[:8])

    @property
    def hc_range(self):
        h = self.headcount
        d = max(2, round(h * 0.04))
        return h - d, h + d


class Arch:
    """Текущее состояние архитектуры: разделы, на которые ссылаются проверки."""

    def __init__(self, profile):
        self.p = profile
        self.org = None
        self.goals = []
        self.funcs = []
        self.procs = []

    # должности
    def leaders(self, org=None):
        o = org or self.org or {}
        s = {norm(o.get('ceo'))} | {norm(d.get('head')) for d in o.get('departments', [])}
        s |= {norm(x.get('title')) for x in o.get('directors', [])}
        return s - {''}

    def positions(self, org=None):
        o = org or self.org or {}
        return self.leaders(o) | {norm(p.get('title')) for d in o.get('departments', []) for p in d.get('positions', [])}

    def depts(self):
        return {norm(d.get('name')) for d in (self.org or {}).get('departments', [])}

    def kpi_names(self):
        return ' | '.join(norm(k.get('name')) for g in self.goals for k in g.get('kpis', []))


# ---------------------------------------------------------------- оргструктура
def staff(o):
    return sum(int(p.get('count') or 0) for d in o.get('departments', []) for p in d.get('positions', []))


def fix_headcount(profile):
    """Модель не держит сумму численности — масштабируем кодом до численности из анкеты."""
    def fix(o, notes):
        lo, hi = profile.hc_range
        if not profile.headcount:
            return o
        pos = [p for d in o.get('departments', []) for p in d.get('positions', [])]
        tot = sum(int(p.get('count') or 0) for p in pos)
        if tot and not lo <= tot <= hi:
            k = profile.headcount / tot
            for p in pos:
                p['count'] = max(1, round(int(p.get('count') or 0) * k))
            big = max(pos, key=lambda p: p['count'])
            big['count'] += profile.headcount - sum(p['count'] for p in pos)
            notes.append(f'численность пересчитана кодом: {tot} → {profile.headcount}')
        return o
    return fix


def v_org(a):
    def v(o):
        e = []
        if not isinstance(o.get('departments'), list) or not o['departments']:
            return ['нет массива departments']
        if a.p.headcount:
            lo, hi = a.p.hc_range
            n = staff(o)
            if not lo <= n <= hi:
                e.append(f'сумма count по всем должностям = {n}, а должна быть {lo}–{hi}. Добавь или убери людей в должностях')
        names = ' | '.join(norm(d.get('name')) for d in o['departments'])
        miss = [k for k, rx in a.p.units.items() if not re.search(rx, names)]
        if miss:
            e.append('нет подразделений: ' + ', '.join(miss))
        if a.p.headcount >= 100 and len([x for x in o.get('directors', []) if 'директор' in norm(x.get('title'))]) < 2:
            e.append('нет уровня директоров по направлениям (массив directors: минимум два директора)')
        ceo = norm(o.get('ceo'))
        direct = [x.get('title') for x in o.get('directors', []) if norm(x.get('reports_to')) == ceo]
        direct += [d.get('head') for d in o['departments'] if norm(d.get('reports_to')) == ceo]
        if len(direct) > 7:
            e.append(f'у генерального директора {len(direct)} прямых подчинённых, допустимо не больше 7 — подчини часть руководителей директорам')
        for x in o.get('directors', []):
            n = sum(1 for d in o['departments'] if norm(d.get('reports_to')) == norm(x.get('title')))
            if n == 0:
                e.append(f'у «{x.get("title")}» нет ни одного подразделения в подчинении')
            elif n == 1 and a.p.headcount < 500:
                e.append(f'у «{x.get("title")}» в подчинении одно подразделение — объедини уровень директора с руководителем подразделения или передай ему ещё направления')
        known = a.leaders(o)
        for d in o['departments']:
            if not d.get('head'):
                e.append(f'у подразделения «{d.get("name")}» нет руководителя')
            if norm(d.get('reports_to')) not in known:
                e.append(f'«{d.get("name")}» подчиняется «{d.get("reports_to")}», а такой руководящей должности нет в оргструктуре')
        return e[:12]
    return v


# ---------------------------------------------------------------- цели
def v_goals(a):
    def v(g):
        e = []
        goals = g.get('goals') or []
        lead = a.leaders()
        persp = {}
        for x in goals:
            persp[norm(x.get('perspective'))] = persp.get(norm(x.get('perspective')), 0) + 1
            for k in x.get('kpis') or []:
                if norm(k.get('owner')) not in lead:
                    e.append(f'владелец показателя «{k.get("name")}» — «{k.get("owner")}»: это не руководитель из оргструктуры (допустимы: {", ".join(sorted(lead))})')
                if not k.get('target') or not k.get('formula'):
                    e.append(f'у показателя «{k.get("name")}» нет формулы или целевого значения')
        if len(persp) < 4 or min(persp.values() or [0]) < 2:
            e.append(f'нужно 4 перспективы по 2–3 цели в каждой; сейчас {persp}')
        ids = {x.get('id') for x in goals}
        for x in goals:
            bad = [s for s in x.get('supports') or [] if s not in ids]
            if bad:
                e.append(f'цель {x.get("id")} ссылается на несуществующие цели {bad}')
        return e[:12]
    return v


# ---------------------------------------------------------------- функции и процессы
def v_funcs(a, group, existing=()):
    def v(f):
        e = []
        fs = f.get('functions') or []
        for x in fs:
            twin = [y for y in existing if similar(x.get('name'), y)]
            if twin:
                e.append(f'функция «{x.get("name")}» повторяет уже описанную «{twin[0]}» из другой группы — замени её на другую или убери')
        o = a.org
        units = a.depts() | {norm(x.get('title')) for x in o.get('directors', [])} | {norm(o.get('ceo'))}
        pos = a.positions()
        if not 3 <= len(fs) <= 8:
            e.append(f'в группе «{group}» нужно 3–8 функций, сейчас {len(fs)}')
        for x in fs:
            if norm(x.get('department')) not in units:
                e.append(f'функция «{x.get("name")}»: подразделение «{x.get("department")}» не найдено в оргструктуре — укажи название подразделения буква в букву')
            subs = x.get('subfunctions') or []
            if len(subs) < 3:
                e.append(f'у функции «{x.get("name")}» меньше 3 подфункций')
            for s in subs:
                if norm(s.get('owner')) not in pos:
                    e.append(f'подфункция «{s.get("name")}»: должность «{s.get("owner")}» не найдена в оргструктуре')
        return e[:12]
    return v


def v_procs(a, group='', existing=()):
    def v(p):
        e = []
        ps = p.get('processes') or []
        for x in ps:
            twin = [y for y in existing if similar(x.get('name'), y)]
            if twin:
                e.append(f'процесс «{x.get("name")}» повторяет уже описанный «{twin[0]}» — в этой группе нужны другие процессы')
            if group == 'управления' and not re.search(MGMT, norm(x.get('name'))):
                e.append(f'«{x.get("name")}» не процесс управления: здесь нужны процессы планирования, бюджетирования, контроля, регулярных встреч, анализа результатов')
        fnames = {norm(x['name']) for x in a.funcs}
        subnames = {norm(s['name']) for x in a.funcs for s in x.get('subfunctions', [])}
        fids = {x['id'] for x in a.funcs}
        lead = a.leaders()
        if len(ps) < 3:
            e.append(f'нужно минимум 3 процесса, сейчас {len(ps)}')
        ids = [x.get('id') for x in ps]
        if len(ids) != len(set(ids)):
            e.append('номера (id) процессов повторяются — сделай их уникальными')
        for x in ps:
            nm = norm(x.get('name'))
            if nm in fnames or nm in subnames:
                e.append(f'процесс «{x.get("name")}» повторяет название функции/подфункции — назови процесс по сквозной цепочке «от … до …»')
            for fld in ('trigger', 'result', 'inputs', 'outputs'):
                if not x.get(fld):
                    e.append(f'у процесса «{x.get("name")}» не заполнено поле {fld}')
            if norm(x.get('owner')) not in lead:
                e.append(f'владелец процесса «{x.get("name")}» — «{x.get("owner")}» не является руководителем из оргструктуры')
            if x.get('function_id') not in fids:
                e.append(f'процесс «{x.get("name")}» ссылается на несуществующую функцию «{x.get("function_id")}»')
            subs = [norm(s.get('name')) for s in x.get('subprocesses') or []]
            if len(subs) < 3:
                e.append(f'у процесса «{x.get("name")}» меньше 3 подпроцессов')
            if subs and sum(1 for s in subs if s in subnames) >= 2:
                e.append(f'подпроцессы «{x.get("name")}» повторяют подфункции — опиши этапы процесса по порядку')
        return e[:12]
    return v


def v_flow(a):
    """Детальный ключевой процесс (шаги с исполнителями и документами)."""
    def v(t):
        e = []
        t = t.get('flow', t)
        steps = t.get('steps') or []
        pos = a.positions()
        if not 10 <= len(steps) <= 20:
            e.append(f'в процессе {len(steps)} шагов, нужно 10–16: ' + ('объедини мелкие шаги' if len(steps) > 20 else 'детализируй'))
        need = {'n', 'role', 'action', 'input_doc', 'output_doc', 'system', 'decision'}
        for s in steps:
            miss = need - set(s)
            if miss:
                e.append(f'в шаге {s.get("n", "?")} нет полей {sorted(miss)} (поля строго: n, role, action, input_doc, output_doc, system, decision)')
                break
        for s in steps:
            if norm(s.get('role')) not in pos and norm(s.get('role')) not in EXTERNAL_ROLES:
                e.append(f'шаг {s.get("n")}: исполнитель «{s.get("role")}» не найден в оргструктуре — бери должность буква в букву')
            if not s.get('input_doc') and not s.get('output_doc'):
                e.append(f'шаг {s.get("n")}: нет ни входного, ни выходного документа')
        if sum(1 for s in steps if s.get('decision')) < 2:
            e.append('нужно минимум 2 развилки (decision)')
        if a.p.systems and not any(s.get('system') for s in steps):
            e.append('ни в одном шаге не указана учётная система — укажи, где шаг фиксируется (' + ', '.join(a.p.systems) + ')')
        return e[:12]
    return v


# ---------------------------------------------------------------- риски
def v_risks(a):
    def v(r):
        e = []
        rs = r.get('risks') or []
        lead = a.leaders()
        if len(rs) < 15:
            e.append(f'рисков {len(rs)}, нужно 15–20')
        for x in rs:
            if len(str(x.get('cause', ''))) < 25 or len(str(x.get('effect', ''))) < 25:
                e.append(f'риск «{x.get("risk")}»: причина и последствие должны быть конкретными (по 1 предложению про эту компанию)')
            if norm(x.get('owner')) not in lead:
                e.append(f'владелец риска «{x.get("risk")}» — «{x.get("owner")}» не руководитель из оргструктуры')
        sol = norm(js(r.get('automation')))
        for s in a.p.systems:
            if re.search(r'внедрени\w* ' + re.escape(norm(s)) + r'|внедрить ' + re.escape(norm(s)), sol):
                e.append(f'в анкете сказано, что {s} уже есть: не предлагай внедрять — предлагай доработки и ИИ-агентов поверх')
        if len(r.get('automation') or []) < 4:
            e.append('нужно минимум 4 решения автоматизации')
        return e[:12]
    return v


# ---------------------------------------------------------------- паспорта, встречи, НМД
def kpis_of(a, title):
    return [k['name'] for g in a.goals for k in g.get('kpis', []) if norm(k.get('owner')) == norm(title)]


def v_passport(a, title):
    def v(p):
        e = []
        if len(p.get('functionGroups') or []) < 2 or any(len(g.get('items') or []) < 2 for g in p.get('functionGroups') or []):
            e.append('нужно минимум 2 группы функций, в каждой минимум 2 функции с описанием')
        ks = p.get('kpis') or []
        if len(ks) < 2:
            e.append('нужно минимум 2 показателя должности')
        if any(not k.get('target') for k in ks):
            e.append('у каждого показателя должно быть целевое значение')
        have = ' | '.join(norm(k.get('name')) for k in ks)
        miss = [k for k in kpis_of(a, title) if not similar(k, have) and norm(k) not in have]
        if miss:
            e.append('эта должность — владелец показателей стратегии, они обязательно должны быть в паспорте (название как есть): ' + '; '.join(miss))
        if len(p.get('documents') or []) < 2:
            e.append('укажи минимум 2 документа, с которыми работает должность')
        if len(p.get('requirements') or []) < 2:
            e.append('нужно минимум 2 блока требований (образование и опыт; знания и навыки)')
        return e
    return v


def v_meetings(a):
    def v(r):
        e = []
        ms = r.get('meetings') or []
        if not 3 <= len(ms) <= 5:
            e.append(f'встреч {len(ms)}, нужно 3–5')
        pos = a.positions()
        allk = a.kpi_names()
        for m in ms:
            nm = m.get('name') or '?'
            for f in ('purpose', 'periodicity', 'duration', 'chair', 'participants', 'agenda', 'inputs', 'outputs'):
                if not m.get(f):
                    e.append(f'«{nm}»: не заполнено поле {f}')
            bad = [p for p in (m.get('participants') or []) + [m.get('chair')] if norm(p) not in pos]
            if bad:
                e.append(f'«{nm}»: участники не из оргструктуры (бери должности буква в букву): ' + ', '.join(map(str, bad)))
            if len(m.get('agenda') or []) < 4:
                e.append(f'«{nm}»: в повестке нужно минимум 4 пункта с регламентом времени')
            if not any(similar(k, allk) or norm(k) in allk for k in m.get('kpis_reviewed') or []):
                e.append(f'«{nm}»: в kpis_reviewed укажи показатели стратегии, которые разбираются на встрече (названия как в целях)')
        return e[:12]
    return v


_GENERIC5 = {'отдел', 'служб', 'депар', 'управ', 'подра', 'полож', 'должн', 'инстр', 'по', 'и'}


def _st5(t):
    """Основы слов по 5 букв без общих слов: «Начальник отдела продаж» ⊆ «Должностная инструкция начальника отдела продаж»."""
    return {w[:5] for w in re.findall(r'[а-яa-z]{2,}', norm(t))} - _GENERIC5


def v_registry(a):
    def v(r):
        e = []
        docs = [d for c in r.get('categories') or [] for d in c.get('docs') or []]
        if not 30 <= len(docs) <= 80:
            e.append(f'документов {len(docs)}, нужно 30–80')
        if len(r.get('categories') or []) < 5:
            e.append('нужно минимум 5 категорий')
        pn = ' | '.join(norm(p['name']) for p in a.procs)
        pos = a.positions()
        regs = [d.get('name') for d in docs if 'положени' in norm(d.get('name'))]
        miss = [x['name'] for x in a.org['departments'] if _st5(x['name']) and not any(_st5(x['name']) <= _st5(r) for r in regs)]
        if miss:
            e.append('нет положений о подразделениях: ' + ', '.join(miss) + ' — добавь «Положение о …» для каждого подразделения')
        rules = [d for d in docs if 'регламент' in norm(d.get('name'))]
        miss = [p['name'] for p in a.procs if p.get('group') == 'основные' and not any(
            norm(d.get('process')) == norm(p['name']) or similar(d.get('name'), p['name']) for d in rules)]
        if miss:
            e.append('нет регламентов основных процессов: ' + '; '.join(f'«{m}»' for m in miss) +
                     ' — добавь «Регламент процесса …» для каждого, в поле process — название процесса буква в букву')
        dis = [d.get('name') for d in docs if 'должностн' in norm(d.get('name'))]
        heads = [a.org.get('ceo')] + [x.get('title') for x in a.org.get('directors', [])] + [x.get('head') for x in a.org['departments']]
        miss = [h for h in dict.fromkeys(heads) if h and _st5(h) and not any(_st5(h) <= _st5(d) for d in dis)]
        if miss:
            e.append('нет должностных инструкций руководителей: ' + ', '.join(miss) + ' — добавь «Должностная инструкция …» для каждого')
        for d in docs:
            if norm(d.get('owner')) not in pos:
                e.append(f'документ «{d.get("name")}»: владелец «{d.get("owner")}» не из оргструктуры')
            if d.get('process') and norm(d['process']) not in pn:
                e.append(f'документ «{d.get("name")}»: процесс «{d.get("process")}» не найден — бери название из списка процессов или null')
        return e[:12]
    return v


def v_doc(a):
    def v(d):
        e = []
        blocks = d.get('blocks') or []
        if len(blocks) < 15:
            e.append(f'в документе {len(blocks)} блоков, нужно 15–40')
        if sum(1 for b in blocks if b.get('type') == 'h2') < 4:
            e.append('нужно минимум 4 раздела (h2)')
        txt = ' '.join(str(b.get('text', '')) + ' ' + ' '.join(map(str, b.get('items', []) or [])) for b in blocks)
        if len(txt) < 3500:
            e.append(f'текст слишком короткий ({len(txt)} символов), нужно не меньше 3500 — конкретика для этой компании')
        if not any(p in norm(txt) for p in a.positions() if len(p) > 8):
            e.append('в тексте должны быть должности из оргструктуры')
        return e
    return v


# ---------------------------------------------------------------- финансы, ИТ, объекты, проекты, продукты
def v_finance(a):
    def v(f):
        e = []
        cfo = f.get('cfo') or []
        lead = a.leaders()
        for c in cfo:
            if norm(c.get('head')) not in lead:
                e.append(f'ЦФО «{c.get("name")}»: руководитель «{c.get("head")}» не руководитель из оргструктуры')
            if norm(c.get('type')) not in ('центр доходов', 'центр затрат', 'центр прибыли', 'центр инвестиций'):
                e.append(f'ЦФО «{c.get("name")}»: тип должен быть «центр доходов|центр затрат|центр прибыли|центр инвестиций»')
        if not any(norm(c.get('type')) == 'центр прибыли' for c in cfo):
            e.append('нет центра прибыли (компания в целом или генеральный директор)')
        covered = {norm(d) for c in cfo for d in c.get('departments') or []}
        miss = [d['name'] for d in a.org['departments'] if norm(d['name']) not in covered]
        if miss:
            e.append('подразделения не входят ни в один ЦФО: ' + ', '.join(miss))
        bn = ' | '.join(norm(b.get('name')) for b in f.get('budgets') or [])
        if not re.search(r'бдр|доходов и расходов', bn):
            e.append('нет БДР (бюджета доходов и расходов) — добавь его отдельным бюджетом')
        if not re.search(r'бддс|движения денежных средств', bn):
            e.append('нет БДДС (бюджета движения денежных средств) — добавь его отдельным бюджетом')
        if len(f.get('budgets') or []) < 6:
            e.append('нужно минимум 6 бюджетов (продаж, закупок, ФОТ, БДР, БДДС, инвестиционный …)')
        items = [i for b in f.get('budgets') or [] for i in b.get('items') or []]
        if len(items) < 20:
            e.append(f'статей бюджета {len(items)}, нужно минимум 20')
        if len(f.get('cycle') or []) < 5:
            e.append('бюджетный цикл: минимум 5 этапов со сроками и ответственными')
        return e[:12]
    return v


def v_it(a):
    def v(t):
        e = []
        apps = {norm(x.get('name')) for x in t.get('applications') or []}
        for s in a.p.systems:
            if not any(norm(s) in x for x in apps):
                e.append(f'в приложениях должна быть существующая система {s}')
        for i in t.get('integrations') or []:
            for k in ('from', 'to'):
                if norm(i.get(k)) not in apps:
                    e.append(f'интеграция «{i.get("from")} → {i.get("to")}»: «{i.get(k)}» нет в списке приложений (название буква в букву)')
        ents = t.get('data') or []
        if len(ents) < 10:
            e.append(f'сущностей данных {len(ents)}, нужно минимум 10')
        for d in ents:
            if norm(d.get('master')) not in apps:
                e.append(f'сущность «{d.get("entity")}»: система-мастер «{d.get("master")}» не из списка приложений')
        allk = a.kpi_names()
        reps = t.get('reports') or []
        if len(reps) < 6:
            e.append('нужно минимум 6 отчётов/дашбордов')
        if sum(1 for r in reps for k in r.get('kpis') or [] if similar(k, allk) or norm(k) in allk) < 5:
            e.append('отчёты должны показывать показатели стратегии (названия как в целях)')
        return e[:12]
    return v


def v_physical(a):
    def v(p):
        e = []
        sites = p.get('sites') or []
        if not sites:
            return ['нет площадок']
        n = sum(len(o.get('zones') or []) for s in sites for o in s.get('objects') or [])
        if n < 5:
            e.append(f'зон/участков всего {n}, нужно минимум 5')
        depts = a.depts()
        for s in sites:
            for o in s.get('objects') or []:
                if norm(o.get('responsible')) not in depts:
                    e.append(f'объект «{o.get("name")}»: ответственное подразделение «{o.get("responsible")}» не из оргструктуры')
        return e[:12]
    return v


def v_projects(a):
    def v(p):
        e = []
        if len(p.get('criteria') or []) < 3:
            e.append('нужно минимум 3 критерия «что считается проектом»')
        if len(p.get('roles') or []) < 3:
            e.append('нужно минимум 3 роли (спонсор, руководитель проекта, проектный офис)')
        if len(p.get('lifecycle') or []) < 4:
            e.append('нужно минимум 4 этапа жизненного цикла с контрольной точкой и документами')
        ids = {g['id'] for g in a.goals}
        lead = a.leaders()
        reg = p.get('registry') or []
        if len(reg) < 5:
            e.append('в реестре нужно минимум 5 проектов')
        for x in reg:
            if x.get('goal') not in ids:
                e.append(f'проект «{x.get("name")}»: цель «{x.get("goal")}» не из стратегии (id цели)')
            if norm(x.get('sponsor')) not in lead:
                e.append(f'проект «{x.get("name")}»: спонсор «{x.get("sponsor")}» не руководитель из оргструктуры')
        return e[:12]
    return v


def v_products(a):
    def v(p):
        e = []
        lines = p.get('portfolio') or []
        if len(lines) < 3:
            e.append('нужно минимум 3 продуктовые линейки')
        s = 0.0
        for x in lines:
            num = re.sub(r'[^0-9.,]', '', str(x.get('revenue_share', 0))).replace(',', '.')
            try:
                s += float(num or 0)
            except ValueError:
                e.append(f'линейка «{x.get("name")}»: доля выручки «{x.get("revenue_share")}» — укажи одно число в процентах')
        if not 95 <= s <= 105:
            e.append(f'сумма долей выручки = {s:.0f}%, должна быть ≈ 100%')
        lead = a.leaders()
        for x in lines:
            if norm(x.get('owner')) not in lead:
                e.append(f'линейка «{x.get("name")}»: владелец «{x.get("owner")}» не руководитель из оргструктуры')
        if len(p.get('lifecycle') or []) < 5:
            e.append('нужно минимум 5 этапов жизненного цикла продукта')
        if len(p.get('classification') or []) < 3:
            e.append('нужно минимум 3 класса продуктов')
        return e[:12]
    return v


# ---------------------------------------------------------------- BPMN
def fix_bpmn_docs(p, notes):
    """Документ, привязанный к событию или развилке, — отвязываем кодом: генератор рисует связи документов только с задачами."""
    kind = {n.get('id'): n.get('type') for n in p.get('nodes') or []}
    for d in p.get('docs') or []:
        for k in ('producer', 'consumer'):
            if d.get(k) is not None and kind.get(d[k]) != 'task':
                notes.append(f'документ {d.get("id")}: связь {k} с «{d[k]}» ({kind.get(d[k])}) убрана кодом')
                d[k] = None
    return p


def v_bpmn(a, max_nodes, max_lanes):
    def v(p):
        e = []
        lanes, nodes, edges = p.get('lanes') or [], p.get('nodes') or [], p.get('edges') or []
        ids = {n.get('id') for n in nodes}
        kind = {n.get('id'): n.get('type') for n in nodes}
        if sum(1 for n in nodes if n.get('type') == 'start') != 1:
            e.append('нужно ровно одно стартовое событие')
        if not any(n.get('type') == 'end' for n in nodes):
            e.append('нет конечного события')
        for n in nodes:
            if n.get('type') not in ('start', 'task', 'gateway', 'end'):
                e.append(f'узел {n.get("id")}: тип «{n.get("type")}» недопустим')
            if not isinstance(n.get('lane'), int) or not 0 <= n['lane'] < len(lanes):
                e.append(f'узел {n.get("id")}: дорожка {n.get("lane")} вне списка lanes')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', str(n.get('id'))):
                e.append(f'узел «{n.get("id")}»: id только латиницей, цифрами и _')
        for ed in edges:
            if ed.get('from') not in ids or ed.get('to') not in ids:
                e.append(f'связь {ed.get("from")}→{ed.get("to")} ссылается на несуществующий узел')
        for d in p.get('docs') or []:
            for k in ('producer', 'consumer'):
                if d.get(k) is not None and kind.get(d[k]) != 'task':
                    e.append(f'документ {d.get("id")}: {k} «{d[k]}» должен быть id задачи (task)')
        start = [n['id'] for n in nodes if n.get('type') == 'start']
        seen, st = set(start), list(start)
        while st:
            x = st.pop()
            for ed in edges:
                if ed.get('from') == x and ed.get('to') not in seen:
                    seen.add(ed['to'])
                    st.append(ed['to'])
        lost = ids - seen
        if lost:
            e.append(f'узлы недостижимы от старта: {sorted(lost)}')
        for n in nodes:
            out = [ed for ed in edges if ed.get('from') == n.get('id')]
            if n.get('type') == 'gateway' and len(out) > 1 and any(not ed.get('label') for ed in out):
                e.append(f'у развилки {n["id"]} подпиши выходы (Да/Нет или условие)')
            if n.get('type') in ('task', 'start') and not out:
                e.append(f'из узла {n["id"]} нет выхода')
        pos = a.positions()
        bad = [l for l in lanes if norm(l) not in pos and norm(l) not in EXTERNAL_ROLES]
        if bad:
            e.append('дорожки не из оргструктуры: ' + ', '.join(bad))
        if len(nodes) > max_nodes:
            e.append(f'узлов {len(nodes)}, допустимо не больше {max_nodes} — вынеси детали в подпроцессы')
        if len(lanes) > max_lanes:
            e.append(f'дорожек {len(lanes)}, допустимо не больше {max_lanes}')
        return e[:12]
    return v
