"""SEO の TSV を Project Database に取り込みます（Python 3.9+、標準ライブラリのみ）。"""
import argparse
import csv
from dataclasses import dataclass
from datetime import date
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import List

STATUSES = ('candidate', 'proposed', 'approved', 'briefed', 'drafted', 'accepted', 'published', 'dropped')
COLUMNS = {
    'seo_keyword': ('keyword', 'question', 'theme', 'volume', 'recent3_avg', 'trend',
                    'cpc_usd', 'bid_low_usd', 'bid_high_usd', 'competition',
                    'competition_index', 'monthly', 'status', 'rank', 'reason', 'source', 'checked_on'),
    'seo_serp_check': ('keyword', 'checked_on', 'ai_overview', 'own_cited', 'own_organic_rank',
                       'references_total', 'references_unknown', 'cost_usd'),
    'seo_serp_result': ('keyword', 'checked_on', 'kind', 'position', 'domain', 'url', 'title'),
    'seo_search_daily': ('date', 'clicks', 'impressions', 'position'),
    'seo_spend': ('date', 'source', 'purpose', 'amount_usd', 'balance_usd'),
}
KEYS = {'seo_keyword': ('keyword',), 'seo_serp_check': ('keyword', 'checked_on'),
        'seo_serp_result': ('keyword', 'checked_on', 'kind', 'position'),
        'seo_search_daily': ('date',)}


@dataclass
class Statement:
    sql: str
    params: List[str]
    table: str
    rows: int = 0


def text(value):
    return '' if value is None else str(value)


def required(value, label):
    if value is None or not str(value).strip():
        raise ValueError('{} が空です'.format(label))
    return str(value)


def number(value, label, integer=False, mandatory=False):
    if value is None or value == '':
        if mandatory:
            raise ValueError('{} が空です'.format(label))
        return None
    value = str(value)
    if integer:
        if not re.fullmatch(r'[+-]?\d+', value):
            raise ValueError('{} は整数にしてください: {}'.format(label, value))
        return str(int(value))
    try:
        parsed = float(value)
    except ValueError:
        raise ValueError('{} は数値にしてください: {}'.format(label, value)) from None
    if not math.isfinite(parsed):
        raise ValueError('{} は有限の数値にしてください'.format(label))
    return value


def day(value):
    value = value or date.today().isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('日付は YYYY-MM-DD にしてください: {}'.format(value))
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError('実在する日付を YYYY-MM-DD にしてください: {}'.format(value)) from None
    return value


def upserts(table, rows, overwrite=(), clear=()):
    """Group by supplied columns; identifiers can only come from COLUMNS/KEYS."""
    allowed = COLUMNS[table]
    if not set(overwrite).union(clear).issubset(allowed):
        raise ValueError('許可されていない列です')
    groups = {}
    for row in rows:
        if not row.keys() <= set(allowed):
            raise ValueError('許可されていない列です')
        cols = tuple(col for col in allowed if col in row)
        if not cols:
            raise ValueError('列がありません')
        groups.setdefault(cols, []).append(row)
    statements = []
    for cols, group in groups.items():
        keys = KEYS.get(table, ())
        if not set(keys).issubset(cols):
            raise ValueError('主キーがありません')
        updates = []
        for col in cols:
            if col not in keys:
                value = 'excluded.' + col
                if col not in overwrite and col not in clear:
                    value = 'COALESCE({}, {}.{})'.format(value, table, col)
                updates.append('{}={}'.format(col, value))
        suffix = ''
        if keys:
            suffix = ' ON CONFLICT({}) DO '.format(','.join(keys))
            suffix += 'UPDATE SET ' + ','.join(updates) if updates else 'NOTHING'
        batch_size = 90 // len(cols)
        for start in range(0, len(group), batch_size):
            batch = group[start:start + batch_size]
            placeholders = '(' + ','.join("NULLIF(?, '')" for _ in cols) + ')'
            sql = 'INSERT INTO {} ({}) VALUES {}{}'.format(table, ','.join(cols), ','.join([placeholders] * len(batch)), suffix)
            statements.append(Statement(sql, [text(row[col]) for row in batch for col in cols], table, len(batch)))
    return statements


def read_tsv(path, required_columns, optional_columns=()):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader((line for line in stream if line.strip() and not line.startswith('#')), delimiter='\t')
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(required_columns).issubset(fields) or not set(fields).issubset(set(required_columns) | set(optional_columns)):
            raise ValueError('TSV のヘッダーを確認してください: {}'.format(path))
        rows = list(reader)
        if any(None in row or any(value is None for value in row.values()) for row in rows):
            raise ValueError('TSV の列数が合いません: {}'.format(path))
        return rows


def volume_rows(args):
    fields = ('keyword', 'volume', 'recent3_avg', 'trend', 'competition', 'competition_index', 'cpc_usd', 'bid_low_usd', 'bid_high_usd')
    rows = read_tsv(args.tsv, fields, ('monthly',))
    themes = {}
    if args.themes:
        with Path(args.themes).open(encoding='utf-8', newline='') as stream:
            for row in csv.reader(stream, delimiter='\t'):
                if not row or row[0].startswith('#'):
                    continue
                if len(row) not in (2, 3):
                    raise ValueError('テーマ TSV は keyword、theme、任意の question の順にしてください')
                required(row[0], 'keyword')
                themes[row[0]] = dict(zip(('theme', 'question'), row[1:]))
    checked_on = day(args.date)
    for row in rows:
        required(row['keyword'], 'keyword')
        for col in ('volume', 'recent3_avg', 'competition_index'):
            row[col] = number(row[col], col, integer=True)
        for col in ('cpc_usd', 'bid_low_usd', 'bid_high_usd'):
            row[col] = number(row[col], col)
        ratio = number(row['trend'], 'trend')
        row['trend'] = 'unknown' if ratio is None else 'up' if float(ratio) >= 1.3 else 'down' if float(ratio) <= 0.7 else 'flat'
        row.update(themes.get(row['keyword'], {}))
        row.update(source=required(args.source, 'source'), checked_on=checked_on)
    return rows


def serp_plan(args):
    keyword = required(args.keyword, 'keyword')
    checked_on = day(args.date)
    meta, results, in_results = {}, [], False
    cost = None
    with Path(args.file).open(encoding='utf-8') as stream:
        for line in stream:
            line = line.rstrip('\r\n')
            if line.startswith('# ai_overview_text'):
                break
            if line.startswith('#'):
                match = re.search(r'\bcost_usd=([^\s]+)', line)
                if match:
                    cost = number('' if match[1] == 'None' else match[1], 'cost_usd')
                continue
            if not line:
                continue
            parts = line.split('\t')
            if parts == ['kind', 'rank', 'domain', 'url', 'title']:
                in_results = True
                continue
            if not in_results:
                if len(parts) != 2 or parts[0] in meta:
                    raise ValueError('SERP のヘッダーを確認してください')
                meta[parts[0]] = parts[1]
                continue
            if len(parts) != 5:
                raise ValueError('SERP の結果は 5 列にしてください')
            kind, position, domain, url, title = parts
            if kind == '質問':
                continue
            if kind not in ('引用', '検索'):
                raise ValueError('SERP の種類を確認してください: ' + kind)
            results.append(dict(keyword=keyword, checked_on=checked_on,
                                kind={'引用': 'citation', '検索': 'organic'}[kind],
                                position=number(position, 'rank', integer=True, mandatory=True),
                                domain=None if domain == '不明' else domain, url=url, title=title))
    if meta.get('ai_overview') not in ('あり', 'なし'):
        raise ValueError('SERP の ai_overview がありません')
    cited = meta.get('own_cited', '分からない')
    rank = meta.get('own_organic_rank', '分からない')
    if cited not in ('はい', 'いいえ', '分からない'):
        raise ValueError('SERP の own_cited を確認してください')
    check = dict(keyword=keyword, checked_on=checked_on, ai_overview='1' if meta['ai_overview'] == 'あり' else '0',
                 own_cited={'はい': '1', 'いいえ': '0', '分からない': None}[cited],
                 # 0 は「10 位以内に無い」、NULL は「分からない」
                 own_organic_rank=None if rank == '分からない' else ('0' if rank == '10 位以内に無い' else number(rank, 'own_organic_rank', integer=True, mandatory=True)),
                 references_total=number(meta.get('references'), 'references', integer=True, mandatory=True),
                 references_unknown=number(meta.get('references_unknown'), 'references_unknown', integer=True, mandatory=True), cost_usd=cost)
    # No transaction is available. On any failure the caller stops before later statements.
    plan = upserts('seo_serp_check', [check], overwrite=COLUMNS['seo_serp_check'])
    plan.append(Statement("DELETE FROM seo_serp_result WHERE keyword=NULLIF(?, '') AND checked_on=NULLIF(?, '')", [keyword, checked_on], 'seo_serp_result'))
    return plan + upserts('seo_serp_result', results, overwrite=COLUMNS['seo_serp_result'])


def build_plan(args):
    if args.command == 'volume':
        return upserts('seo_keyword', volume_rows(args))
    if args.command == 'serp':
        return serp_plan(args)
    if args.command == 'gsc-daily':
        rows = read_tsv(args.tsv, COLUMNS['seo_search_daily'])
        for row in rows:
            row['date'] = day(required(row['date'], 'date'))
            for col in ('clicks', 'impressions'):
                row[col] = number(row[col], col, integer=True, mandatory=True)
            row['position'] = number(row['position'], 'position')
        # 取得のスクリプトは、データの無い日を 0 で埋める。最初に表示かクリックがあった日より前は入れない。
        first = next((i for i, row in enumerate(rows) if int(float(row['clicks'] or 0)) or int(float(row['impressions'] or 0))), None)
        rows = [] if first is None else rows[first:]
        return upserts('seo_search_daily', rows, overwrite=COLUMNS['seo_search_daily'])
    if args.command == 'spend':
        row = dict(date=day(args.date), source=required(args.source, 'source'),
                   amount_usd=number(args.amount, 'amount', mandatory=True),
                   purpose=args.purpose, balance_usd=number(args.balance, 'balance'))
        return upserts('seo_spend', [row])
    if args.command == 'set':
        row = {'keyword': required(args.keyword, 'keyword')}
        for col in ('status', 'rank', 'theme', 'question', 'reason'):
            value = getattr(args, col)
            if value is not None:
                if col == 'status' and value not in STATUSES:
                    raise ValueError('status が不正です')
                row[col] = number(value, 'rank', integer=True) if col == 'rank' else value
        if args.clear_rank:
            row['rank'] = None
        return upserts('seo_keyword', [row], clear=('rank',) if args.clear_rank else ())
    if args.command == 'status':
        plan = [Statement('SELECT COUNT(*) AS count FROM ' + table, [], table) for table in COLUMNS]
        plan.append(Statement("SELECT SUM(CASE WHEN NULLIF(TRIM(theme), '') IS NOT NULL THEN 1 ELSE 0 END) AS with_theme, SUM(CASE WHEN NULLIF(TRIM(theme), '') IS NULL THEN 1 ELSE 0 END) AS without_theme, SUM(CASE WHEN cpc_usd IS NOT NULL THEN 1 ELSE 0 END) AS with_cpc, SUM(CASE WHEN cpc_usd IS NULL THEN 1 ELSE 0 END) AS without_cpc, MAX(checked_on) AS latest FROM seo_keyword", [], 'keyword_details'))
        for table, col in (('seo_serp_check', 'checked_on'), ('seo_search_daily', 'date'), ('seo_spend', 'date')):
            plan.append(Statement('SELECT MAX({}) AS latest FROM {}'.format(col, table), [], table + '_latest'))
        return plan
    raise ValueError('サブコマンドを確認してください')


def create_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', default=str(Path.cwd()), help='chat を実行するプロジェクトのルート')
    parser.add_argument('--dry-run', action='store_true', help='実行せず SQL と文字列パラメータを JSON 行で表示')
    parser.add_argument('--chat-bin', default='chat')
    commands = parser.add_subparsers(dest='command', required=True)
    volume = commands.add_parser('volume', help='検索数を取り込む')
    volume.add_argument('--tsv', required=True)
    volume.add_argument('--themes')
    volume.add_argument('--source', default='DataForSEO')
    volume.add_argument('--date')
    serp = commands.add_parser('serp', help='検索結果を取り込む')
    serp.add_argument('--file', required=True)
    serp.add_argument('--keyword', required=True)
    serp.add_argument('--date')
    gsc = commands.add_parser('gsc-daily', help='日別の検索実績を取り込む')
    gsc.add_argument('--tsv', required=True)
    spend = commands.add_parser('spend', help='利用額を記録する')
    for name in ('date', 'source', 'amount'):
        spend.add_argument('--' + name, required=True)
    spend.add_argument('--purpose')
    spend.add_argument('--balance')
    judgement = commands.add_parser('set', help='キーワードの判断を更新する')
    judgement.add_argument('--keyword', required=True)
    judgement.add_argument('--status', choices=STATUSES)
    rank = judgement.add_mutually_exclusive_group()
    rank.add_argument('--rank', type=int)
    rank.add_argument('--clear-rank', action='store_true')
    for name in ('theme', 'question', 'reason'):
        judgement.add_argument('--' + name)
    commands.add_parser('status', help='行数と最新日を確かめる')
    return parser


class ChatError(Exception):
    pass


def run_statement(st, args):
    result = subprocess.run([args.chat_bin, 'db', 'query', '--sql', st.sql, '--params', json.dumps(st.params, ensure_ascii=False)],
                            cwd=args.project_dir, capture_output=True, text=True, encoding='utf-8')
    try:
        payload = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise ChatError('応答の JSON を読めません（終了コード {}）。自動再試行はしません。'.format(result.returncode)) from None
    if not isinstance(payload, dict):
        raise ChatError('応答の形式が不正です。自動再試行はしません。')
    if payload.get('ok') is False:
        error = payload.get('error')
        error = error if isinstance(error, dict) else {}
        code, message = error.get('code', 'UNKNOWN'), error.get('message', '詳細がありません')
        detail = '{}: {}'.format(code, message)
        if code == 'OPERATION_OUTCOME_UNKNOWN':
            detail += '\n書き込みが入ったかどうか分かりません。同じ命令を繰り返さず、status で今の行数を確かめてください。'
        raise ChatError(detail)
    if result.returncode != 0 or payload.get('ok') is not True or not isinstance(payload.get('data'), dict):
        raise ChatError('応答の形式または終了コードが不正です。自動再試行はしません。')
    return payload['data']


def first_row(result):
    # chat db query の答えは data.result_set.{columns, items}。古い形（columns, rows）も読む。
    inner = result.get('result_set')
    source = inner if isinstance(inner, dict) else result
    rows = source.get('items')
    if rows is None:
        rows = source.get('rows')
    if not rows:
        return {}
    if isinstance(rows[0], dict):
        return rows[0]
    return dict(zip(source.get('columns', []), rows[0]))


def main(argv=None):
    args = create_parser().parse_args(argv)
    try:
        plan = build_plan(args)  # Validate the entire input before the first write.
        if args.dry_run:
            for st in plan:
                print(json.dumps({'sql': st.sql, 'params': st.params}, ensure_ascii=False))
            return 0
        counts, calls = {}, {}
        if args.command == 'spend':
            # 同じ額を 2 回入れない（表に一意のキーが無いため、入れる前に確かめる）
            row = plan[0]
            same = run_statement(Statement(
                "SELECT COUNT(*) AS count FROM seo_spend WHERE date = ? AND source = ? AND COALESCE(purpose, '') = ? "
                "AND ABS(amount_usd - CAST(? AS REAL)) < 0.000001",
                [day(args.date), args.source, args.purpose or '', str(args.amount)], 'seo_spend'), args)
            if int(first_row(same).get('count') or 0) > 0:
                print('同じ日付・出どころ・目的・額の行が既にあるので、入れませんでした')
                return 0
        for st in plan:
            result = run_statement(st, args)
            if args.command == 'status':
                row = first_row(result)
                if st.table in COLUMNS:
                    print('{}: {} 行'.format(st.table, row.get('count', 0)))
                elif st.table == 'keyword_details':
                    print('テーマあり {} / なし {}、CPC あり {} / なし {}、検索数の最新日 {}'.format(row.get('with_theme') or 0, row.get('without_theme') or 0, row.get('with_cpc') or 0, row.get('without_cpc') or 0, row.get('latest') or '未記録'))
                else:
                    print('{} 最新日: {}'.format(st.table[:-7], row.get('latest') or '未記録'))
            else:
                counts[st.table] = counts.get(st.table, 0) + st.rows
                calls[st.table] = calls.get(st.table, 0) + 1
        if args.command != 'status':
            if not counts:
                print('取り込む行がありません（0 回の呼び出し）')
            else:
                print('、'.join('{} に {} 行を入れました（{} 回の呼び出し）'.format(table, count, calls[table]) for table, count in counts.items()))
        return 0
    except (ValueError, OSError, ChatError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
