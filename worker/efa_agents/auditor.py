# -*- coding: utf-8 -*-
"""
Аудитор качества раздела (версия 3 по итогам прогонов 4–6).

  1. Проверки кодом уже прошли в обвязке.
  2. Аудитор (роль auditor, по умолчанию gpt-oss-120b) отвечает на КОНКРЕТНЫЕ вопросы чек-листа: «да» / «нет» + точная цитата.
     Версия 1 («найди ошибки») давала ~50% ложных замечаний, версия 2 («пустой список — нормально») одобряла всё.
  3. «нет» с найденной в разделе цитатой — подтверждённое замечание: автор (Alice) исправляет только его, затем снова проверки кода.
     Если после исправления проверок кода стало больше — исправление отбрасывается, остаётся исходный раздел.
  4. «нет» без найденной цитаты — спорное: не исправляем, отдаём консультанту на решение.
"""
from .harness import js, norm


def evidence_ok(ev, data):
    ev = norm(ev)
    if len(ev) < 4:
        return False
    hay = norm(js(data))
    return ev in hay or ev[:40] in hay


def audit(session, name, questions, data, context, step_prefix='AUDIT'):
    qs = questions
    rep = session.ask(f'{step_prefix}_{name}', context + f'\n\nРаздел «{name}»:\n' + js(data) + """

Ты — аудитор качества бизнес-архитектуры EfA. Ответь на каждый вопрос чек-листа строго по содержанию раздела и связанных разделов.
На каждый вопрос: answer «да» или «нет»; evidence — точная цитата (5–15 слов) из раздела, подтверждающая ответ; если «нет» — problem (в чём ошибка) и fix (как исправить).
Отвечай «нет» только при реальном нарушении, которое видно по цитате.
Вопросы:
""" + '\n'.join(f'{i + 1}. {q}' for i, q in enumerate(qs)) + """
Схема ответа: {"answers": [{"q": номер, "answer": "да|нет", "evidence": "цитата", "problem": "…или null", "fix": "…или null"}]}""",
                      lambda r: [] if isinstance(r.get('answers'), list) and len(r['answers']) >= len(qs) else [f'нужно ответить на все {len(qs)} вопросов'],
                      role='auditor', max_tokens=8000)
    confirmed, disputed = [], []
    for a in (rep or {}).get('answers', []):
        if norm(a.get('answer')) != 'нет':
            continue
        qn = a.get('q')
        q = qs[int(qn) - 1] if str(qn).isdigit() and 0 < int(qn) <= len(qs) else str(qn)
        item = {'question': q, 'evidence': a.get('evidence'), 'problem': a.get('problem'), 'fix': a.get('fix')}
        (confirmed if evidence_ok(a.get('evidence'), data) else disputed).append(item)
    return {'section': name, 'questions': len(qs), 'answered': len((rep or {}).get('answers', [])),
            'confirmed': confirmed, 'disputed': disputed}


def audit_and_fix(session, name, questions, data, context, validator, schema_hint):
    """Аудит → исправление подтверждённых замечаний → проверки кода. Возвращает (итоговые данные, отчёт аудита)."""
    report = audit(session, name, questions, data, context)
    report['fixed'] = False
    if not report['confirmed']:
        return data, report
    before = len(validator(data))
    fixed = session.ask(f'FIX_{name}', context + f'\n\nРаздел «{name}»:\n' + js(data) + '\n\nПодтверждённые замечания аудитора:\n' + js(report['confirmed']) +
                        f'\n\nЗадача: исправь только эти замечания, остальное сохрани без изменений. Верни ПОЛНЫЙ раздел в той же структуре:\n{schema_hint}',
                        validator, max_tokens=12000)
    if fixed is not None and len(validator(fixed)) <= before:
        report['fixed'] = True
        return fixed, report
    report['fix_rejected'] = 'исправление ухудшило проверки кода — оставлен исходный раздел' if fixed is not None else 'модель не вернула раздел'
    return data, report
