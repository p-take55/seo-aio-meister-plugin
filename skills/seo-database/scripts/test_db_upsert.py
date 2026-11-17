"""Run with python3 test_db_upsert.py; no network or chat installation needed."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import db_upsert as db


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        migration = Path(__file__).resolve().parents[1] / 'migrations/seo_core_v1.sql'
        self.conn.executescript(migration.read_text(encoding='utf-8').split('\n', 1)[1])

    def plan(self, *args):
        return db.build_plan(db.create_parser().parse_args(list(args)))

    def file(self, name, text):
        path = self.root / name
        path.write_text(text, encoding='utf-8')
        return str(path)

    def execute(self, statements):
        for st in statements:
            self.assertLessEqual(len(st.params), 90)
            self.assertTrue(all(isinstance(p, str) for p in st.params))
            self.conn.execute(st.sql, st.params)

    def volume(self, rows, extra_header='', *options):
        header = 'keyword\tvolume\trecent3_avg\ttrend\tcompetition\tcompetition_index\tcpc_usd\tbid_low_usd\tbid_high_usd'
        return self.plan('volume', '--tsv', self.file('volume.tsv', '# cost_usd=0.1\n' + header + extra_header + '\n' + rows), *options)

    def test_volume_types_trend_and_parameter_limit(self):
        rows = ''.join('k{}\t100\t120\t{}\tLOW\t20\t1.25\t\t2.5\n'.format(i, ratio)
                       for i, ratio in enumerate(['1.3', '0.7', '1.0', ''] * 30))
        statements = self.volume(rows)
        self.assertGreater(len(statements), 1)
        self.execute(statements)
        self.assertEqual(self.conn.execute('SELECT typeof(volume),typeof(cpc_usd),typeof(bid_low_usd) FROM seo_keyword LIMIT 1').fetchone(), ('integer', 'real', 'null'))
        self.assertEqual([self.conn.execute('SELECT trend FROM seo_keyword WHERE keyword=?', ('k'+str(i),)).fetchone()[0] for i in range(4)], ['up', 'down', 'flat', 'unknown'])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM seo_keyword').fetchone()[0], 120)

    def test_volume_preserves_judgements_and_empty_existing_values(self):
        self.execute(self.plan('set', '--keyword', 'seo', '--theme', 'theme', '--status', 'approved', '--rank', '2', '--reason', 'reason', '--question', 'question'))
        self.execute(self.volume('seo\t100\t90\t1.2\tLOW\t10\t2.5\t1\t3\t2026-10:10,2026-11:20\n', '\tmonthly'))
        self.execute(self.volume('seo\t200\t\t\t\t\t\t\t\n'))
        self.assertEqual(self.conn.execute('SELECT theme,status,rank,reason,question,volume,cpc_usd,monthly FROM seo_keyword').fetchone(), ('theme', 'approved', 2, 'reason', 'question', 200, 2.5, '2026-10:10,2026-11:20'))

    def test_themes_only_update_present_fields(self):
        self.execute(self.plan('set', '--keyword', 'seo', '--question', 'original'))
        themes = self.file('themes.tsv', 'seo\tsearch\nother\tother-theme\tother-question\n')
        self.execute(self.volume('seo\t100\t90\t1.2\tLOW\t10\t2.5\t1\t3\nother\t1\t1\t1\tLOW\t1\t1\t1\t1\n', '', '--themes', themes, '--source', 'test', '--date', '2026-11-17'))
        self.assertEqual(self.conn.execute('SELECT theme,question,source,checked_on FROM seo_keyword WHERE keyword="seo"').fetchone(), ('search', 'original', 'test', '2026-11-17'))
        self.assertEqual(self.conn.execute('SELECT question FROM seo_keyword WHERE keyword="other"').fetchone()[0], 'other-question')

    def serp(self, cited='分からない', rank='分からない', body=None):
        text = '# cost_usd=0.002 question=seo\nai_overview\tあり\nreferences\t2\nreferences_unknown\t1\n'
        if cited is not None:
            text += 'own_cited\t{}\nown_organic_rank\t{}\n'.format(cited, rank)
        text += '\nkind\trank\tdomain\turl\ttitle\n'
        text += body if body is not None else '引用\t1\t不明\t\tunknown\n引用\t2\texample.com\thttps://example.com\ttitle\n検索\t1\tsearch.test\thttps://search.test\tresult\n質問\t\t\t\tquestion\n'
        text += '\n# ai_overview_text\narbitrary text is not a row\n'
        return self.plan('serp', '--file', self.file('serp.tsv', text), '--keyword', 'seo', '--date', '2026-11-17')

    def test_serp_unknown_types_and_rerun_replaces(self):
        self.execute(self.serp())
        self.assertEqual(self.conn.execute('SELECT ai_overview,own_cited,own_organic_rank,references_total,references_unknown,cost_usd FROM seo_serp_check').fetchone(), (1, None, None, 2, 1, 0.002))
        self.assertIsNone(self.conn.execute('SELECT domain FROM seo_serp_result WHERE kind="citation" AND position=1').fetchone()[0])
        self.execute(self.serp('はい', '3', '検索\t3\tnew.test\thttps://new.test\tnew\n'))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM seo_serp_result').fetchone()[0], 1)
        self.assertEqual(self.conn.execute('SELECT own_cited,own_organic_rank FROM seo_serp_check').fetchone(), (1, 3))
        self.execute(self.serp('いいえ', '10 位以内に無い', ''))
        # 0 は「10 位以内に無い」。「分からない」の NULL と区別する
        self.assertEqual(self.conn.execute('SELECT own_cited,own_organic_rank FROM seo_serp_check').fetchone(), (0, 0))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM seo_serp_result').fetchone()[0], 0)

    def test_serp_missing_optional_overwrites_old_values(self):
        self.execute(self.serp('はい', '1'))
        self.execute(self.serp(None))
        self.assertEqual(self.conn.execute('SELECT own_cited,own_organic_rank FROM seo_serp_check').fetchone(), (None, None))

    def test_first_row_reads_chat_result_set(self):
        self.assertEqual(db.first_row({'result_set': {'columns': ['count'], 'items': [[186]]}}), {'count': 186})
        self.assertEqual(db.first_row({'columns': ['count'], 'rows': [[3]]}), {'count': 3})
        self.assertEqual(db.first_row({'result_set': {'columns': ['count'], 'items': []}}), {})

    def test_new_statuses(self):
        for status in ('drafted', 'accepted'):
            self.execute(self.plan('set', '--keyword', 'kw ' + status, '--status', status))
        self.assertEqual(self.conn.execute("SELECT count(*) FROM seo_keyword WHERE status IN ('drafted','accepted')").fetchone()[0], 2)

    def test_serp_batches(self):
        self.execute(self.serp(body=''.join('引用\t{}\tx.test\thttps://x.test\tx\n'.format(i) for i in range(1, 100))))
        self.assertEqual(self.conn.execute('SELECT count(*) FROM seo_serp_result').fetchone()[0], 99)

    def test_gsc_overwrites_zero_and_null(self):
        def daily(row):
            return self.plan('gsc-daily', '--tsv', self.file('gsc.tsv', '# period=test\ndate\tclicks\timpressions\tposition\n' + row))
        self.execute(daily('2026-11-17\t10\t100\t2.5\n'))
        # 最初に数字があった日より後の 0 の日は、上書きする
        self.execute(daily('2026-11-16\t3\t30\t4.0\n2026-11-17\t0\t0\t\n'))
        self.assertEqual(self.conn.execute("SELECT clicks,impressions,position FROM seo_search_daily WHERE date='2026-11-17'").fetchone(), (0, 0, None))
        # 最初に数字があった日より前の、埋められた 0 の日は入れない
        self.execute(daily('2026-11-01\t0\t0\t\n2026-11-02\t0\t0\t\n2026-11-03\t0\t7\t9.1\n'))
        self.assertEqual([r[0] for r in self.conn.execute('SELECT date FROM seo_search_daily ORDER BY date')], ['2026-11-03', '2026-11-16', '2026-11-17'])
        self.assertEqual(daily('2026-11-01\t0\t0\t\n'), [])
        with self.assertRaises(ValueError):
            daily('2026-11-17\t\t0\t\n')

    def test_set_enum_clear_rank_and_insert(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.plan('set', '--keyword', 'seo', '--status', 'invented')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.plan('set', '--keyword', 'seo', '--rank', '1', '--clear-rank')
        self.execute(self.plan('set', '--keyword', "quote'; DROP TABLE seo_keyword;--", '--status', 'briefed', '--rank', '1'))
        self.execute(self.plan('set', '--keyword', "quote'; DROP TABLE seo_keyword;--", '--clear-rank', '--theme', 'theme'))
        self.assertEqual(self.conn.execute('SELECT status,rank,theme FROM seo_keyword').fetchone(), ('briefed', None, 'theme'))
        self.execute(self.plan('set', '--keyword', 'bare'))
        self.assertEqual(self.conn.execute('SELECT status FROM seo_keyword WHERE keyword="bare"').fetchone()[0], 'candidate')

    def test_spend_and_bad_numbers(self):
        self.execute(self.plan('spend', '--date', '2026-11-17', '--source', 'test', '--amount', '0.25'))
        self.assertEqual(self.conn.execute('SELECT amount_usd,balance_usd FROM seo_spend').fetchone(), (0.25, None))
        for bad in ('nan', 'inf', 'not-a-number'):
            with self.assertRaises(ValueError):
                self.volume('seo\t100\t90\t1\tLOW\t10\t'+bad+'\t1\t3\n')

    def test_invalid_inputs_rejected_before_writes(self):
        with self.assertRaises(ValueError):
            self.plan('volume', '--tsv', self.file('bad.tsv', 'keyword\tunexpected\nfoo\tbar\n'))
        with self.assertRaises(ValueError):
            self.plan('spend', '--date', '2026-02-30', '--source', 'test', '--amount', '1')

    def test_dry_run_emits_only_json_lines(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = db.main(['--dry-run', 'set', '--keyword', 'seo', '--rank', '2'])
        self.assertEqual(result, 0)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(records), 1)
        self.assertTrue(all(isinstance(p, str) for p in records[0]['params']))
        self.conn.execute(records[0]['sql'], records[0]['params'])

    def test_unknown_outcome_never_retries(self):
        response = type('Response', (), {'returncode': 1, 'stdout': json.dumps({'ok': False, 'error': {'code': 'OPERATION_OUTCOME_UNKNOWN', 'message': 'lost'}}), 'stderr': ''})()
        errors = io.StringIO()
        with patch.object(db.subprocess, 'run', return_value=response) as run, contextlib.redirect_stderr(errors):
            result = db.main(['--project-dir', str(self.root), '--chat-bin', 'custom-chat', 'serp', '--file', self.file('input.tsv', 'ai_overview\tなし\nreferences\t0\nreferences_unknown\t0\n\nkind\trank\tdomain\turl\ttitle\n'), '--keyword', 'seo'])
        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][:3], ['custom-chat', 'db', 'query'])
        self.assertEqual(run.call_args.kwargs['cwd'], str(self.root))
        self.assertIn('OPERATION_OUTCOME_UNKNOWN', errors.getvalue())
        self.assertIn('同じ命令を繰り返さず', errors.getvalue())

    def test_cli_success_summary_and_status(self):
        def local_query(argv, **kwargs):
            sql = argv[argv.index('--sql') + 1]
            params = json.loads(argv[argv.index('--params') + 1])
            self.assertTrue(all(isinstance(p, str) for p in params))
            cursor = self.conn.execute(sql, params)
            data = {'columns': [c[0] for c in cursor.description] if cursor.description else [],
                    'rows': cursor.fetchall() if cursor.description else []}
            return type('Response', (), {'returncode': 0, 'stdout': json.dumps({'ok': True, 'data': data}), 'stderr': ''})()
        output = io.StringIO()
        with patch.object(db.subprocess, 'run', side_effect=local_query), contextlib.redirect_stdout(output):
            self.assertEqual(db.main(['set', '--keyword', 'seo', '--theme', 'search']), 0)
            self.assertEqual(db.main(['status']), 0)
        self.assertIn('seo_keyword に 1 行を入れました（1 回の呼び出し）', output.getvalue())
        self.assertIn('seo_keyword: 1 行', output.getvalue())
        self.assertIn('テーマあり 1 / なし 0、CPC あり 0 / なし 1', output.getvalue())

    def test_cli_error_code_and_malformed_json_stop(self):
        for payload, expected in [(json.dumps({'ok': False, 'error': {'code': 'DATABASE_NOT_INITIALIZED', 'message': '未初期化'}}), 'DATABASE_NOT_INITIALIZED: 未初期化'), ('invalid JSON', 'JSON を読めません')]:
            response = type('Response', (), {'returncode': 1, 'stdout': payload, 'stderr': ''})()
            errors = io.StringIO()
            with patch.object(db.subprocess, 'run', return_value=response) as run, contextlib.redirect_stderr(errors):
                result = db.main(['set', '--keyword', 'seo'])
            self.assertEqual(result, 1)
            self.assertEqual(run.call_count, 1)
            self.assertIn(expected, errors.getvalue())

    def test_status_executes_readonly_queries(self):
        plan = self.plan('status')
        self.assertGreater(len(plan), 1)
        for st in plan:
            self.assertTrue(st.sql.startswith('SELECT'))
            self.conn.execute(st.sql, st.params)


if __name__ == '__main__':
    unittest.main()
