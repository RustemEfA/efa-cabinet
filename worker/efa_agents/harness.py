# -*- coding: utf-8 -*-
"""
Обвязка агента: запрос → разбор JSON → правки кодом → проверки кодом → повтор с конкретными замечаниями (до 3 попыток).
Перенесено из тестовых прогонов 03_yandex/ba_test/run_ba2.py без изменения логики; глобальные переменные заменены сессией.
"""
import json
import re
import threading

from . import gateway


# ---------------------------------------------------------------- текст
def js(x):
    return json.dumps(x, ensure_ascii=False)


def norm(s):
    return re.sub(r'\s+', ' ', str(s or '').lower().replace('ё', 'е').replace('‑', '-').replace('‐', '-').replace(' ', ' ')).strip()


_STOP = ('управление', 'обеспечение', 'процесс', 'деятельности', 'компании')


def stems(t):
    return {w[:6] for w in re.findall(r'[а-яa-z]{4,}', norm(t)) if w not in _STOP}


def similar(a, b):
    sa, sb = stems(a), stems(b)
    return bool(sa and sb) and len(sa & sb) / min(len(sa), len(sb)) >= 0.6


def slug(s, n=40):
    return re.sub(r'[^a-zа-я0-9]+', '_', norm(s))[:n]


# ---------------------------------------------------------------- разбор ответа
def _dup_hook(kv):
    keys = [k for k, _ in kv]
    if len(keys) != len(set(keys)):
        return {'__kv__': kv}       # модель слила несколько объектов в один — разрежем в _split
    return dict(kv)


def _split(o, repairs):
    """Объект с повторяющимися ключами режем на последовательность объектов: новый объект начинается, когда ключ повторился."""
    if isinstance(o, dict):
        if '__kv__' in o:
            parts, cur = [], {}
            for k, v in o['__kv__']:
                if k in cur:
                    parts.append(cur)
                    cur = {}
                cur[k] = _split(v, repairs)
            parts.append(cur)
            repairs.append(len(parts))
            return {'__split__': parts}
        return {k: _split(v, repairs) for k, v in o.items()}
    if isinstance(o, list):
        out = []
        for v in o:
            v = _split(v, repairs)
            out += v['__split__'] if isinstance(v, dict) and '__split__' in v else [v]
        return out
    return o


def parse(text):
    """JSON из ответа модели: как есть, из блока ```json или первый {...}. Возвращает (данные или None, число разрезанных слияний)."""
    fence = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text or '', re.S)
    loose = re.search(r'\{.*\}', text or '', re.S)
    for cand in (text, fence and fence.group(1), loose and loose.group(0)):
        if not cand:
            continue
        repairs = []
        try:
            d = _split(json.loads(cand, object_pairs_hook=_dup_hook), repairs)
        except ValueError:
            continue
        if isinstance(d, dict) and '__split__' in d:
            d = d['__split__'][0]
        return d, len(repairs)
    return None, 0


# ---------------------------------------------------------------- сессия
class Session:
    """Один запуск агента: системный промпт, журнал шагов (токены, ₽, ошибки), сообщение о ходе работы."""

    def __init__(self, system, on_step=None, artifacts=None):
        self.system = system
        self.log = []
        self.on_step = on_step          # callback(rec) — запись хода работы в базу
        self.artifacts = artifacts      # callback(name, text) — сырые ответы модели для разбора (не обязателен)
        self._lock = threading.Lock()

    @property
    def rub(self):
        return sum(x['rub'] for x in self.log)

    def totals(self):
        return {'steps': len(self.log), 'requests': sum(len(x['attempts']) for x in self.log),
                'tokens_in': sum(x['in'] for x in self.log), 'tokens_out': sum(x['out'] for x in self.log),
                'rub': round(self.rub, 2), 'sec': round(sum(x['sec'] for x in self.log)),
                'errors_left': sum(len(x['final_errors']) for x in self.log),
                'fallback_used': sum(1 for x in self.log if x['fallback'])}

    def ask(self, step, user, validator=None, role='author', max_tokens=8000, tries=3, fix=None):
        """Запрос с проверками. validator(data) → список ошибок; fix(data, notes) → data (правки кодом, notes — список строк)."""
        validator = validator or (lambda d: [])
        base = [{'role': 'system', 'content': self.system}, {'role': 'user', 'content': user}]
        msgs = list(base)
        rec = {'step': step, 'role': role, 'model': None, 'attempts': [], 'in': 0, 'out': 0, 'sec': 0.0, 'rub': 0.0,
               'fallback': False, 'code_fixes': [], 'split_repairs': 0}
        data, best, best_errs = None, None, None
        for n in range(tries):
            r = gateway.complete(role, msgs, max_tokens)
            rec['model'] = r['model']
            rec['fallback'] = rec['fallback'] or r['fallback']
            rec['in'] += r['tin']
            rec['out'] += r['tout']
            rec['sec'] += r['sec']
            rec['rub'] += r['rub']
            text = r['text']
            data, rep = parse(text)
            rec['split_repairs'] += rep
            if data is not None and fix:
                data = fix(data, rec['code_fixes'])
            try:
                errs = ['ответ не является корректным JSON-объектом'] if not isinstance(data, dict) else validator(data)
            except Exception as e:  # проверка упала на неожиданной структуре — это тоже ошибка формата
                errs = [f'структура ответа не по схеме ({type(e).__name__}: {e})']
            rec['attempts'].append(errs)
            if self.artifacts:
                self.artifacts(f'raw/{step}.try{n + 1}.txt', text)
            if isinstance(data, dict) and (best_errs is None or len(errs) < len(best_errs)):
                best, best_errs = data, errs
            if not errs:
                break
            if not isinstance(data, dict) and n + 1 < tries:
                msgs = list(base)       # ответ не JSON или отказ — повторяем исходный запрос, без мусора в истории
                continue
            msgs += [{'role': 'assistant', 'content': text},
                     {'role': 'user', 'content': 'Проверка нашла ошибки:\n- ' + '\n- '.join(errs) +
                      '\nИсправь их и верни ПОЛНЫЙ исправленный JSON по той же схеме.'}]
        rec['final_errors'] = rec['attempts'][-1] if best_errs is None else best_errs
        rec['sec'] = round(rec['sec'], 1)
        rec['rub'] = round(rec['rub'], 2)
        with self._lock:
            self.log.append(rec)
        if self.on_step:
            self.on_step(rec)
        return best   # лучшая попытка (меньше всего ошибок), даже если ошибки остались — их видно в журнале

