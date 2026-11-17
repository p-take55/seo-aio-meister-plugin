---
name: seo-database
description: 検索数・クリック単価・検索結果と引用元・Search Console の日ごとの数字・使った額を、Project のデータベースに行として残し、あとから取り直さずに読めるようにする。Use right after fetching volume, SERP or Search Console data, when recording spend or a keyword's status, and when checking whether a keyword was already handled.
metadata:
  aachat.headline.ja: SEO の数字を、Project のデータベースにためる
  aachat.headline.en: Keep SEO numbers in the Project Database
  aachat.description.ja: 検索数、クリック単価、検索結果と引用元、Search Console の日ごとの数字、使った額を表にためる。取った数字が消えず、画面はデータベースを直接読む。
  aachat.description.en: Store search volume, click price, SERP citations, daily Search Console numbers and spend as tables, so fetched numbers are never lost and the dashboard reads the database directly.
  aachat.discovery.listed: "false"
---

# SEO の数字を、データベースにためる

たまっていく数字は、Project のデータベースに置く。文書に書き写した表は、列を落としたり、取り直しのときに消えたりする。データベースに行として入れておけば、取った数字は消えず、画面（`seo-dashboard`）がそのまま読む。

判断と文脈は、これまでどおり文書に書く。データベースに入れるのは数字と状態だけ。

| データベースに置く | 文書のまま |
|---|---|
| キーワードの候補と、検索数・単価・状態・順 | 事業の概要、キーワード戦略 |
| 問いごとの検索結果と引用元 | 記事の概要、受け入れ確認の指摘 |
| Search Console の日ごとの数字 | サイトの受け皿と直し方 |
| 使った額 | 設定、記録（判断と経緯） |

操作の決まりは、Session の `aachat/contracts/database.md` に従う。`chat db` は、Project のフォルダ（`aachat/teams/〈team〉/projects/〈project〉`）を今いる場所にして実行する。

## 1. 表を用意する（最初の 1 回）

```bash
cd 〈Project のフォルダ〉
chat db schema          # 今の表を見る
head -1 db/schema.sql   # 今の版（root か sha256:…）
```

- `seo_keyword` などの表が既にあれば、何もしない。
- 無ければ、この skill の `migrations/seo_core_v1.sql` を `db/migrations/seo_core_v1.sql` に写す。**今の版が `root` でなければ、写したファイルの 1 行目 `-- aachat-parent: root` の `root` を、今の版にそのまま置き換える。**
- `chat db migrate db/migrations/seo_core_v1.sql` で適用し、`chat db schema` で表ができたことを確かめる。写した直後は、ファイルがまだサーバーに届いておらず `conflict`（この migration がまだ無い）と返ることがある。10 秒ほど待って、同じ命令をもう一度流す。

表は 5 つ。名前はどれも `seo_` で始まる。

| 表 | 1 行が表すもの |
|---|---|
| `seo_keyword` | 検索の言い方 1 つ。テーマ、検索数、推移、単価、状態、おすすめ順、勝てる理由 |
| `seo_serp_check` | ある問いを、ある日に調べた結果。AI による概要が出たか、自社が引用されたか（1・0、分からなければ空）、自社の順位（0 は「10 位以内に無い」、空は「分からない」） |
| `seo_serp_result` | その調べで出た、引用元と検索上位の 1 件ずつ |
| `seo_search_daily` | Search Console の 1 日ぶんのクリックと表示回数 |
| `seo_spend` | 料金のかかる呼び出し 1 回ぶんの額と残高 |

データベースが使えない Project（権限が無い、表を作れない）では、この skill を飛ばし、これまでどおり文書に残す。その旨を報告に書く。

## 2. 取ったら、その場で入れる

数字を取るスクリプトの出力をファイルに受け、`scripts/db_upsert.py` で入れる。`--project-dir` に Project のフォルダを渡す。

```bash
P=〈Project のフォルダ〉

# 検索数と単価。themes.tsv は「言い方<TAB>テーマ<TAB>問い（省ける）」
python3 ../seo-data-sources/scripts/dataforseo.py volume --monthly --file words.txt > vol.tsv
python3 scripts/db_upsert.py --project-dir "$P" volume --tsv vol.tsv --themes themes.tsv

# 検索結果と引用元（問いごと）
python3 ../seo-data-sources/scripts/dataforseo.py serp "〈問い〉" --own 〈自社のドメイン〉 > serp.tsv
python3 scripts/db_upsert.py --project-dir "$P" serp --file serp.tsv --keyword "〈問い〉"

# Search Console の日ごとの数字
python3 ../seo-data-sources/scripts/gsc_query.py --by date --days 90 > daily.tsv
python3 scripts/db_upsert.py --project-dir "$P" gsc-daily --tsv daily.tsv

# 使った額
python3 scripts/db_upsert.py --project-dir "$P" spend --date YYYY-MM-DD --source DataForSEO --purpose "〈何に〉" --amount 0.09 --balance 〈残高〉
```

- **語を送る前に、語の一覧（words.txt）と、テーマの対応（themes.tsv）を作る。** 語の一覧は、今回広げた候補に、データベースに既にある語（`SELECT keyword FROM seo_keyword`）を足したもの。どのテーマの候補として広げた語かは、広げた時点でしか分からないので、その場で書く。どのテーマにも入らない語は、テーマを空にして、状態を見送りにする。
- 入れるときの呼び出しは、8 語ほどごとに 1 回になる（1 回に渡せる値の数に上限があるため）。200 語なら 30 回前後で、数十秒かかる。料金はかからない。
- 同じ言い方をもう一度入れると、新しい数字で上書きされる。テーマ・状態・順・勝てる理由は、入力に無ければ前の値が残る。
- Search Console の日ごとの数字は、取れるだけ長く取ってよい（`--days 480`）。取得のスクリプトはデータの無い日を 0 で埋めるが、最初に表示かクリックがあった日より前の行は、入れるときに自動で省かれる。
- 使った額は、同じ日付・出どころ・目的・額の行が既にあれば入らない。同じ命令を 2 回流しても重ならない。同じ日に同じ額の呼び出しを分けて記録するときは、目的に問いの名前などを入れて区別する。
- 検索結果の「関連する質問」は、データベースに入らない。要るものは、概要や候補の文書に書く。
- `serp` は、その問い・その日の行を消してから入れ直す。途中で失敗したら、同じファイルでもう一度流す。
- `--dry-run` を付けると、実行せずに命令を表示する。
- 入れたあと `python3 scripts/db_upsert.py --project-dir "$P" status` で、行の数と、テーマや単価が空の行の数を確かめる。

## 3. 状態と順を直す

人間の承認や、作業の進みで変わるものは、その場で直す。

```bash
python3 scripts/db_upsert.py --project-dir "$P" set --keyword "〈言い方〉" --status proposed --rank 1 --reason "〈勝てる理由〉"
python3 scripts/db_upsert.py --project-dir "$P" set --keyword "〈言い方〉" --status dropped --clear-rank --reason "〈見送った理由〉"
```

状態は `candidate`（候補）・`proposed`（提案中）・`approved`（承認済み）・`briefed`（概要あり）・`drafted`（原稿あり）・`accepted`（確認済み・公開待ち）・`published`（公開済み）・`dropped`（見送り）。

## 4. 読む

前に扱った語か、候補のどれが強いかは、文書を読み通さずにデータベースに聞く。

```bash
cd "$P"
chat db query --sql 'SELECT keyword, status, checked_on FROM seo_keyword WHERE keyword = ?' --params '["〈言い方〉"]'
chat db query --sql 'SELECT keyword, theme, volume, cpc_usd FROM seo_keyword WHERE status = ? ORDER BY cpc_usd DESC LIMIT 20' --params '["candidate"]'
chat db query --sql 'SELECT domain, COUNT(DISTINCT keyword) AS n FROM seo_serp_result WHERE kind = ? AND domain IS NOT NULL GROUP BY domain ORDER BY n DESC LIMIT 20' --params '["citation"]'
```

1 回の結果は 1,000 行まで。多いときは `LIMIT` と `OFFSET` で分けて読む。

## 5. 文書と画面との関係

- `docs/keyword-candidates.md` には、おすすめする問いと、その理由だけを書く。全部の語の表は書かない。全体はデータベースにある、と 1 行添える。
- 画面は、メンバーが開いたときはデータベースを読む。問いごとの調べ（`seo_serp_check`）がまだ無い語は、JSON に残っている「AI による概要」の値をそのまま表示する。**外に出す公開のリンクではデータベースを読めない**ので、`seo-dashboard.data.json` に同じ内容を書き出しておく（`seo-dashboard` の手順）。外に見せる予定が無ければ、JSON のキーワードの節は、おすすめの問いだけでよい。

## 決まり

- 書き込みが「入ったかどうか分からない」と返ったら（`OPERATION_OUTCOME_UNKNOWN`）、同じ命令を繰り返さない。`status` で今の行数を確かめてから決める。
- 表の形を自分で変えない。足りない列があれば、報告に書く。
- 鍵・個人の情報・社外に出せない数字を入れない。
