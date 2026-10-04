# -*- coding: utf-8 -*-
"""
Проверки без обращения к моделям: разбор JSON, правки кодом, проверки разделов, раскладка BPMN.
Данные — фикстуры из прогонов на ТехноЛайн (tests/fixtures). Запуск: python -m unittest discover -s tests
"""
import json
import unittest
from pathlib import Path

from efa_agents import harness
from efa_agents.business_architect import pipeline
from efa_agents.business_architect import validators as V

FX = Path(__file__).parent / 'fixtures'
J = lambda n: json.loads((FX / n).read_text(encoding='utf-8'))
INP = J('input_technoline.json')


def arch():
    a = V.Arch(V.Profile(INP))
    a.org = J('org.json')
    a.goals = J('goals.json')['goals']
    a.funcs = J('functions.json')['functions']
    a.procs = []
    for g in J('processes.json')['tree']:
        for x in g['processes']:
            a.procs.append(dict(x, group=g['group']))
    return a


class Parse(unittest.TestCase):
    def test_fence_and_merged_objects(self):
        d, rep = harness.parse('Вот ответ:\n```json\n{"items": [{"a": 1, "b": 2, "a": 3, "b": 4}]}\n```')
        self.assertEqual(d, {'items': [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]})
        self.assertEqual(rep, 1)

    def test_garbage(self):
        self.assertEqual(harness.parse('Я не могу обсуждать эту тему'), (None, 0))


class Validators(unittest.TestCase):
    def setUp(self):
        self.a = arch()

    def test_core_sections_pass(self):
        # в оргструктуре прогона 2 аудитор (прогон 6) нашёл директоров над одним отделом — теперь это ловит код
        errs = V.v_org(self.a)(self.a.org)
        self.assertTrue(errs and all('прямых подчинённых' in e or 'одно подразделение' in e for e in errs), errs)
        self.assertEqual(V.v_goals(self.a)({'goals': self.a.goals}), [])

    def test_headcount_fix(self):
        org = json.loads(json.dumps(self.a.org))
        for d in org['departments']:
            for p in d['positions']:
                p['count'] *= 2
        notes = []
        V.fix_headcount(self.a.p)(org, notes)
        self.assertEqual(V.staff(org), 250)
        self.assertTrue(notes)

    def test_bad_owner_caught(self):
        g = json.loads(json.dumps({'goals': self.a.goals}))
        g['goals'][0]['kpis'][0]['owner'] = 'Менеджер по продажам'
        self.assertTrue(any('не руководитель' in e for e in V.v_goals(self.a)(g)))

    def test_new_sections_and_bpmn(self):
        for kind in ('finance', 'it', 'physical', 'projects', 'products'):
            errs = getattr(V, 'v_' + kind)(self.a)(J(f'NEW_{kind}.json'))
            self.assertIsInstance(errs, list)
        top = J('toir_top.json')
        self.assertEqual(V.v_bpmn(self.a, 14, 5)(top), [])

    def test_finance_profit_center_rule(self):
        # аудитор в прогоне 6 нашёл, что нет центра прибыли — теперь это ловит код
        f = J('NEW_finance.json')
        has = any(V.norm(c.get('type')) == 'центр прибыли' for c in f['cfo'])
        self.assertEqual(has, not any('центра прибыли' in e for e in V.v_finance(self.a)(f)))


    def test_registry_department_regulations(self):
        reg = {'categories': [{'title': 'Орг', 'docs': [{'name': 'Положение об отделе продаж', 'owner': 'Генеральный директор'}]}]}
        errs = ' '.join(V.v_registry(self.a)(reg))
        self.assertIn('нет положений', errs)
        self.assertNotIn('Отдел продаж,', errs)

    def test_registry_processes_and_job_descriptions(self):
        reg = {'categories': [{'title': 'Орг', 'docs': [
            {'name': 'Должностная инструкция генерального директора', 'owner': 'Генеральный директор'}]}]}
        errs = ' '.join(V.v_registry(self.a)(reg))
        self.assertIn('нет регламентов основных процессов', errs)
        self.assertIn('нет должностных инструкций руководителей', errs)
        self.assertNotIn('Генеральный директор,', errs)

    def test_finance_bdr_bdds(self):
        f = {'cfo': [], 'budgets': [{'name': 'Бюджет продаж', 'items': []}], 'cycle': []}
        errs = ' '.join(V.v_finance(self.a)(f))
        self.assertIn('нет БДР', errs)
        self.assertIn('нет БДДС', errs)


class Layout(unittest.TestCase):
    def test_bpmn_layout_subprocess(self):
        r = pipeline.Run(INP, artifact=lambda *a: None)
        r.a = arch()
        top = J('toir_top.json')
        top['id'] = 'flow_top'
        res = r.layout('flow_top', top)
        self.assertTrue(res.get('crossings') is not None, res)


if __name__ == '__main__':
    unittest.main()
