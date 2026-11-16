---
name: seo-dashboard
description: Project の文書とデータ源の数字を 1 枚の画面（Project HTML）にまとめ、人間がブラウザで状況・検索の実績・キーワード候補・AI での見え方を見られるようにする。Use when asked for a dashboard or to show the analysis, and after any stage that changes the data.
metadata:
  aachat.headline.ja: 状況と数字を、グラフの画面 1 枚にする
  aachat.headline.en: Turn status and numbers into a one-page chart dashboard
  aachat.description.ja: Project の文書とデータ源の数字を、検索の実績・キーワードの候補・AI による概要の引用元・サイトの対応状況のグラフにして、Project HTML に置く。
  aachat.description.en: Publish a Project HTML dashboard with charts of search performance, keyword candidates, AI Overview citation sources and site readiness, built from project documents and data sources.
  aachat.discovery.listed: "false"
---

# 状況と数字を 1 枚の画面にする

文書は判断の記録、画面は人間が見るための写し。画面のために新しい判断や数字を作らない。

## 作るもの

Project HTML に、次の 2 つを置く。置き場所と決まりは、Session の `aachat/contracts/html.md` に従う。

| ファイル | 中身 | 扱い |
|---|---|---|
| `seo-dashboard.html` | 画面。`assets/seo-dashboard.html` の写し | 書き換えない。毎回 `assets/` からそのまま上書きする |
| `seo-dashboard.data.json` | 画面に出すデータ | 更新するのはこれだけ |

画面は、同じ場所の `seo-dashboard.data.json` を読んで表示する。見た目を変えたいときは、この skill の `assets/seo-dashboard.html` を直す。Project に置いた写しは直さない。

`assets/sample-data.json` は、画面の見え方を確かめるための作りもののデータ（架空の店）。Project には置かない。

## 決まり

- **文書とデータ源にある値だけを入れる。** 分からない値は `null`、無い節は `null` か空の一覧にする。画面は「まだありません」と表示する。見栄えのために値を作らない。
- **数字には出どころと確認日を付ける。** キーワードは `source` と `checked_on`、検索の実績は `period`。
- **点数や評価を足さない。** 画面に出すのは、取った値と、その差だけ。
- **古いデータを消さない。** `daily`（日ごとの推移）と `ai_visibility.log` は、前の JSON にある行を残して、新しい行を足す。

## 手順

### 1. 今の JSON を読む

Project HTML に `seo-dashboard.data.json` があれば読む。無ければ新しく作る。

### 2. 節ごとに値を集める

| 節 | 出どころ |
|---|---|
| `stage`、`next_action` | Project の文書から今の段階を決める。番号は下の「段階の番号」 |
| `asks` | Project の開いている Ask（`aachat/contracts/asks.md`）。題名は 1 行に縮める |
| `sources` | `docs/seo-settings.md` のデータ源の欄。つながっている・依頼中・未接続 |
| `spend` | 料金のかかるデータ源の残高（DataForSEO は `dataforseo.py balance`、無料）。使った額は `docs/seo-log.md` の記録。分からなければ `null` |
| `search` | Search Console。下の「検索の実績の取り方」 |
| `themes`、`keywords` | `docs/keyword-strategy.md` と `docs/keyword-candidates.md` |
| `citation_sources` | `ai-citation-check` と `ai-visibility-tracking` で控えた引用元のドメイン。サイトごとに、引用していた問いの数を数える。自社は `own: true` |
| `ai_visibility` | `docs/ai-visibility-panel.md`（問いと番号）と `docs/ai-visibility-log.md`（回ごとの表の、概要・自社の引用・引用元のドメイン） |
| `articles` | `docs/briefs/` と `docs/seo-log.md` にある記事。概要を作った時点から入れる。`state` は概要あり・原稿あり・確認中・公開済み。公開した記事には、`seo-results-review` の区分をそのまま `verdict` に入れる |
| `readiness` | `docs/site-readiness.md`。直ったかどうかは、公開中のページで確かめたものだけ `done` にする |

`dataforseo.py serp` で `domain` が「不明」だった引用は、サイトの数に入れず、その件数を `citation_sources.unknown` に入れる。

引用元の生のデータが手元に残っていないときは、`citation_sources` を `null` にする。文書に残っている数だけで作り直さない。次に `ai-citation-check` を行うときに入れる。

つながっていないデータ源の節は `null` にする。そのためだけに料金のかかる呼び出しをしない。

### 段階の番号

| 番号 | 段階 | そこにいる条件 |
|---|---|---|
| 0 | 準備 | 設定の文書（`docs/seo-settings.md`）がまだ無い |
| 1 | 事業調査 | 事業の概要がまだ無い（未確認の項目が残っていても、文書があれば「ある」とする） |
| 2 | サイト整備 | 事業の概要はあるが、サイトの受け皿の文書がまだ無い |
| 3 | 戦略 | 戦略が承認されていない |
| 4 | キーワード選定 | 戦略は承認済みで、書くと決まった問いの概要がまだ無い（候補を出している間と、最初の記事の承認を待っている間を含む） |
| 5 | 記事作成 | 概要があり、原稿がまだ無い・書いている |
| 6 | 受け入れ確認 | 原稿があり、受け入れの記録がまだ無い |
| 7 | 効果測定 | 公開した記事があり、結果を見ている |

0〜3 は、いくつも当てはまるときは、いちばん小さい番号にする。4 以降は記事ごとに繰り返すので、Project の段階は、いちばん先に進んでいる記事に合わせる。記事ごとの状態は `articles` の `state` に入れる。

サイトの受け皿に「止める」が残っていることは、段階を変えない。

`seo-aio-playbook` があるときは、そちらの表と同じもの。

### 3. 検索の実績の取り方

Search Console がつながっているときだけ。`../seo-data-sources/scripts/gsc_query.py` を使う。

```bash
python3 ../seo-data-sources/scripts/gsc_query.py --by total --days 28   # totals（今の期間と前の期間）
python3 ../seo-data-sources/scripts/gsc_query.py --by date --days 90    # daily（初回。2 回目からは前回の続きの日数だけ）
python3 ../seo-data-sources/scripts/gsc_query.py --by query --days 28   # queries
python3 ../seo-data-sources/scripts/gsc_query.py --by page --days 28    # pages
```

- `brand` は、事業の概要にある社名・製品名（表記ゆれを含む）を含む問いに `true` を付ける。
- `--by total` の `prev` の行の順位は、`totals.prev_position` に入れる。
- 問いごとの合計は、匿名化された検索を含まないので `totals` より小さい。`note` にそう書く。

### 4. JSON を書いて確かめる

形は [schema.md](schema.md) のとおり。書いたら必ず確かめる。

```bash
python3 scripts/check_data.py 〈seo-dashboard.data.json の場所〉
```

`OK` が出るまで直す。エラーのまま置くと、画面が開けなくなる。

### 5. 入口からつなぐ

Project HTML の入口（`index.html`）が最初のままの一覧なら、Pages に 1 行足す。

```html
<li><a href="seo-dashboard.html">SEO / AIO の状況</a></li>
```

「まだページがありません」の段落は消す。入口がほかの成果物に置き換えられていたら触らず、報告に書く。

### 6. 報告する

- 更新した節と、空のままの節（その理由と、何をすれば埋まるか）
- 開き方: Project の「Open HTML」から `seo-dashboard.html`
- 確かめたこと: `check_data.py` の結果

## いつ更新するか

- 人間に「ダッシュボードを見せて」「分析を見たい」と頼まれたとき
- データが変わる作業の最後: 接続の確認、サイトの診断、キーワード選び、記事の作成と受け入れ、結果の確認、AI での見え方の記録

更新するとき、無料で取れる数字（Search Console）は、前に取ってから 1 日以上たっていれば取り直す。料金のかかる数字は、画面のためだけには取り直さない。

Project HTML が使えない Project では行わず、その旨を報告する。

## 外に見せるとき

- 公開のリンク（Share HTML）を出すのは人間。Agent は出せない。
- 公開すると、Project HTML に置いたファイルは**すべて**見える。残高（`spend`）や Ask の題名（`asks`）を外に出したくないときは、その節を `null` にする。どうするかは人間に聞く。
- 鍵・トークン・社外に出せない数字を JSON に入れない。
