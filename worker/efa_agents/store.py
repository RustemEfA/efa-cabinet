# -*- coding: utf-8 -*-
"""Очередь заданий в Postgres (таблицы из миграции 0005_agent_jobs.sql). Подключение — DATABASE_URL."""
import json
import os
import socket

import psycopg
from psycopg.types.json import Jsonb

WORKER_ID = f'{socket.gethostname()}:{os.getpid()}'
MAX_ATTEMPTS = 2
STALE_MIN = 30          # нет сигнала от обработчика 30 минут — задание считается брошенным


def connect():
    return psycopg.connect(os.environ['DATABASE_URL'], autocommit=True)


def requeue_stale(conn):
    conn.execute("""update agent_jobs set status = case when attempts >= %s then 'failed' else 'queued' end,
                           error = case when attempts >= %s then 'обработчик остановился во время работы' else error end,
                           locked_by = null
                    where status = 'running' and heartbeat_at < now() - make_interval(mins => %s)""", (MAX_ATTEMPTS, MAX_ATTEMPTS, STALE_MIN))


def claim(conn):
    row = conn.execute("""update agent_jobs set status = 'running', started_at = now(), heartbeat_at = now(),
                                  locked_by = %s, attempts = attempts + 1
                           where id = (select id from agent_jobs where status = 'queued' order by created_at
                                       for update skip locked limit 1)
                           returning id, agent, input, project_id""", (WORKER_ID,)).fetchone()
    return None if row is None else {'id': row[0], 'agent': row[1], 'input': row[2], 'project_id': row[3]}


def load_result(conn, job_id):
    row = conn.execute('select result from agent_jobs where id = %s', (job_id,)).fetchone()
    return row[0] if row else None


def progress(conn, job_id, info):
    conn.execute('update agent_jobs set progress = %s, heartbeat_at = now() where id = %s and locked_by = %s',
                 (Jsonb(info), job_id, WORKER_ID))


def artifact(conn, job_id, name, body, ctype):
    conn.execute("""insert into agent_artifacts (job_id, name, content_type, body) values (%s, %s, %s, %s)
                    on conflict (job_id, name) do update set body = excluded.body, content_type = excluded.content_type""",
                 (job_id, name, ctype, body))


def usage(conn, job_id, log):
    with conn.cursor() as cur:
        cur.executemany("""insert into agent_usage (job_id, step, role, model, tokens_in, tokens_out, cost_rub, sec, attempts, errors_left, fallback)
                           values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        [(job_id, x['step'], x['role'], x['model'], x['in'], x['out'], x['rub'], x['sec'], len(x['attempts']),
                          len(x['final_errors']), x['fallback']) for x in log])


def finish(conn, job_id, result, usage_totals):
    conn.execute("""update agent_jobs set status = 'done', result = %s, finished_at = now(), cost_rub = %s,
                           tokens_in = %s, tokens_out = %s, locked_by = null where id = %s""",
                 (Jsonb(result), usage_totals['rub'], usage_totals['tokens_in'], usage_totals['tokens_out'], job_id))


def fail(conn, job_id, error, cost=None):
    conn.execute("""update agent_jobs set status = case when attempts >= %s then 'failed' else 'queued' end,
                           error = %s, cost_rub = coalesce(cost_rub, 0) + coalesce(%s, 0), locked_by = null,
                           finished_at = case when attempts >= %s then now() else null end
                    where id = %s""", (MAX_ATTEMPTS, error[:2000], cost, MAX_ATTEMPTS, job_id))


def dumps(x):
    return json.dumps(x, ensure_ascii=False)
