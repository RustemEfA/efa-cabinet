# -*- coding: utf-8 -*-
"""
Шлюз моделей Yandex AI Studio (OpenAI-совместимый endpoint).

Роли, а не модели: агент просит «author» / «mass» / «auditor», шлюз сам знает, какая модель за ролью
и какая запасная. Модель роли меняется переменной окружения, без правки кода:
  EFA_MODEL_AUTHOR=aliceai-llm/latest  EFA_MODEL_MASS=aliceai-llm-flash/latest
  EFA_MODEL_AUDITOR=gpt-oss-120b/latest  EFA_MODEL_FALLBACK=yandexgpt/rc
Для заказчиков «только отечественное ПО» — EFA_MODEL_AUDITOR=aliceai-llm/latest.

Ключи: YC_API_KEY, YC_FOLDER_ID (в рабочей среде — из Lockbox через переменные окружения).
"""
import json
import os
import time
import urllib.error
import urllib.request

URL = 'https://llm.api.cloud.yandex.net/v1/chat/completions'

ROLES = {
    'author': os.environ.get('EFA_MODEL_AUTHOR', 'aliceai-llm/latest'),
    'mass': os.environ.get('EFA_MODEL_MASS', 'aliceai-llm/latest'),   # качество важнее экономии: Flash не используем
    'auditor': os.environ.get('EFA_MODEL_AUDITOR', 'gpt-oss-120b/latest'),
    'fallback': os.environ.get('EFA_MODEL_FALLBACK', 'yandexgpt/rc'),
}

# ₽ за 1000 токенов (вход, выход) — как в финмодели v4; при смене тарифа Yandex поправить здесь и в финмодели
PRICES = {
    'aliceai-llm': (0.5, 1.2),
    'aliceai-llm-flash': (0.1, 0.2),
    'gpt-oss-120b': (0.3, 0.3),
    'yandexgpt': (0.8, 0.8),
    'yandexgpt-lite': (0.2, 0.2),
}

# у Alice AI LLM режим json_object ломает ответ (ключи вида «.processes») — формат JSON просим текстом
NO_JSON_MODE = ('aliceai',)

REFUSALS = ('не могу обсуждать', 'не могу ответить на', 'давайте поговорим о чём-нибудь')


class ModelError(RuntimeError):
    pass


def price(model, tin, tout):
    base = model.split('/')[0]
    pin, pout = PRICES.get(base, (1.2, 1.2))   # неизвестная модель — считаем по верхней цене, чтобы не занизить себестоимость
    return tin / 1000 * pin + tout / 1000 * pout


def _creds():
    key, folder = os.environ.get('YC_API_KEY', '').strip(), os.environ.get('YC_FOLDER_ID', '').strip()
    if not key or not folder:
        raise ModelError('нет YC_API_KEY или YC_FOLDER_ID в окружении')
    return key, folder


def _call(model, messages, max_tokens, temperature):
    key, folder = _creds()
    body = {'model': f'gpt://{folder}/{model}', 'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature}
    if not model.startswith(NO_JSON_MODE):
        body['response_format'] = {'type': 'json_object'}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Api-Key ' + key, 'x-folder-id': folder, 'Content-Type': 'application/json'})
    last = None
    for attempt in range(4):
        try:
            t = time.time()
            r = json.load(urllib.request.urlopen(req, timeout=900))
            text = r['choices'][0]['message'].get('content') or ''
            u = r.get('usage', {})
            return text, int(u.get('prompt_tokens', 0)), int(u.get('completion_tokens', 0)), time.time() - t
        except urllib.error.HTTPError as e:
            last = f'{e.code} {e.read().decode(errors="replace")[:300]}'
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(15 * (attempt + 1))
                continue
            raise ModelError(last)
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            last = str(e)
            if attempt < 3:
                time.sleep(10)
                continue
    raise ModelError(last or 'нет ответа')


def complete(role, messages, max_tokens=8000, temperature=0.3):
    """Ответ модели роли; при отказе сервиса или «отказе отвечать» — один раз запасная модель.
    Возвращает dict: text, model, tin, tout, sec, rub, fallback."""
    model = ROLES[role]
    try:
        text, tin, tout, sec = _call(model, messages, max_tokens, temperature)
        if not any(r in text.lower()[:200] for r in REFUSALS):
            return {'text': text, 'model': model, 'tin': tin, 'tout': tout, 'sec': sec, 'rub': price(model, tin, tout), 'fallback': False}
        spent = (tin, tout, sec, price(model, tin, tout))
    except ModelError:
        if model == ROLES['fallback']:
            raise
        spent = (0, 0, 0.0, 0.0)
    fb = ROLES['fallback']
    text, tin, tout, sec = _call(fb, messages, max_tokens, temperature)
    return {'text': text, 'model': fb, 'tin': tin + spent[0], 'tout': tout + spent[1], 'sec': sec + spent[2],
            'rub': price(fb, tin, tout) + spent[3], 'fallback': True}
