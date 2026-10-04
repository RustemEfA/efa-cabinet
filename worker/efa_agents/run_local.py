# -*- coding: utf-8 -*-
"""
Запуск агента без базы — для проверки и отладки.

  python -m efa_agents.run_local <вход.json> <папка_результата> [--env keys.env]

Вход — то же, что input задания (см. pipeline.py). Для итерации: добавьте "previous": путь к result.json прошлого запуска и "remarks".
В папку пишутся result.json, log.json, progress.txt и файлы (bpmn/…).
"""
import json
import os
import sys
import time
from pathlib import Path

from .business_architect import pipeline


def main():
    args = sys.argv[1:]
    if '--env' in args:
        i = args.index('--env')
        for line in Path(args[i + 1]).read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
        args = args[:i] + args[i + 2:]
    inp = json.loads(Path(args[0]).read_text(encoding='utf-8'))
    out = Path(args[1])
    out.mkdir(parents=True, exist_ok=True)
    if isinstance(inp.get('previous'), str):
        inp['previous'] = json.loads(Path(inp['previous']).read_text(encoding='utf-8'))
    plog = open(out / 'progress.txt', 'a', encoding='utf-8')

    def progress(stage, info=None):
        line = f'{time.strftime("%H:%M:%S")} {stage} {json.dumps(info or {}, ensure_ascii=False)}'
        print(line, flush=True)
        plog.write(line + '\n')
        plog.flush()

    def artifact(name, body, ctype='text/plain'):
        p = out / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding='utf-8')

    t = time.time()
    res = None
    try:
        res = pipeline.run(inp, progress, artifact)
    finally:
        if res is not None:
            log = res.pop('log', [])
            (out / 'log.json').write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
            (out / 'result.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    u = res['usage']
    print(f'Готово за {round((time.time() - t) / 60)} мин: шагов {u["steps"]}, запросов {u["requests"]}, токены {u["tokens_in"]} → {u["tokens_out"]}, '
          f'{u["rub"]} ₽, неисправленных ошибок {len(res["errors_left"])}, консультанту {len(res["for_consultant"])}, нет разделов: {res["missing"] or "—"}')


if __name__ == '__main__':
    main()
