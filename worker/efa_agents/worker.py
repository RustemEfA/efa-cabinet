# -*- coding: utf-8 -*-
"""
Обработчик очереди: забирает задание из agent_jobs, запускает агента, пишет ход, результат, файлы и расход.

  python -m efa_agents.worker

Окружение: DATABASE_URL, YC_API_KEY, YC_FOLDER_ID (+ необязательные EFA_MODEL_* — см. gateway.py), TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID для уведомлений.
Несколько обработчиков можно запускать параллельно: задание забирает ровно один (FOR UPDATE SKIP LOCKED).
"""
import json
import os
import threading
import time
import traceback
import urllib.parse
import urllib.request

from . import store
from .business_architect import pipeline as business_architect

AGENTS = {'business_architect': business_architect.run}
POLL_SEC = 5


def notify(text):
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        return
    try:
        data = urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode()
        urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=data, timeout=10)
    except Exception:
        pass


def run_job(job):
    conn = store.connect()      # своё соединение: агент пишет ход из нескольких потоков
    lock = threading.Lock()

    def progress(stage, info=None):
        with lock:
            store.progress(conn, job['id'], dict(info or {}, stage=stage, at=time.strftime('%H:%M:%S')))

    def artifact(name, body, ctype='text/plain'):
        with lock:
            store.artifact(conn, job['id'], name, body, ctype)

    inp = dict(job['input'])
    if inp.get('previous_job_id') and not inp.get('previous'):
        inp['previous'] = store.load_result(conn, inp['previous_job_id'])
        if not inp['previous']:
            raise RuntimeError('нет результата предыдущей итерации')
    out = AGENTS[job['agent']](inp, progress, artifact)
    log = out.pop('log', [])
    with lock:
        store.usage(conn, job['id'], log)
        store.finish(conn, job['id'], out, out['usage'])
    conn.close()
    return out


def main():
    conn = store.connect()
    print('обработчик', store.WORKER_ID, 'запущен', flush=True)
    while True:
        store.requeue_stale(conn)
        job = store.claim(conn)
        if job is None:
            time.sleep(POLL_SEC)
            continue
        t = time.time()
        print('задание', job['id'], job['agent'], flush=True)
        try:
            if job['agent'] not in AGENTS:
                raise RuntimeError(f'неизвестный агент {job["agent"]}')
            out = run_job(job)
            u = out['usage']
            notify(f'✅ {job["agent"]}: готово за {round((time.time() - t) / 60)} мин, себестоимость {u["rub"]} ₽, '
                   f'замечаний консультанту {len(out["for_consultant"])}, неисправленных ошибок {len(out["errors_left"])}')
        except Exception as e:
            traceback.print_exc()
            store.fail(conn, job['id'], f'{type(e).__name__}: {e}')
            notify(f'❌ {job["agent"]}: ошибка — {type(e).__name__}: {str(e)[:300]}')


if __name__ == '__main__':
    main()
