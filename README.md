# SEO・AIO マイスター（Plugin）

自分の Agent に、SEO と AIO（AI の回答で引用されること）の一巡を足す Plugin です。
事業を調べ、サイトを整え、戦略を決め、書くべき問いを選び、記事を書き、確かめ、結果を測って戦略を直します。

同じ中身を、すぐ使える 1 体の Agent としても公開しています（SEO・AIO マイスター）。新しく Agent を増やしたいならそちらを、既にいる Agent に足したいならこの Plugin を使ってください。両方入れる必要はありません。

## 入っているもの

skill が 16 個です。最初に読まれるのは `seo-aio-playbook` で、今どの段階にいるかを Project の文書から見分け、次に使う skill を決めます。

| 段階 | すること | skill |
|---|---|---|
| 進め方 | 段階の見分け方、文書の置き場所、判断の基準 | `seo-aio-playbook` |
| 0. 準備 | サイトの URL、対象の国と言語、書き手、データ源を確かめる。データ源をつなぐ | `seo-setup`、`seo-data-connect` |
| 1. 事業調査 | 事業・顧客・競合・自社だけの根拠を整理する | `seo-business-research` |
| 2. サイト整備 | 検索と AI のクローラーが読める状態かを調べる | `site-readiness-audit` |
| 3. 戦略 | 狙うテーマと記事の組み方を決め、承認を求める | `keyword-strategy` |
| 4. キーワード選定 | 検索数、買う気の強さ、AI による概要の現状から問いを選ぶ | `keyword-discovery`、`keyword-evidence`、`ai-citation-check` |
| 5. 記事作成 | 根拠つきの概要を作り、原稿を書いて作業ブランチに置く | `article-brief`、`article-writing` |
| 6. 受け入れ確認 | 原稿を、概要・事実・引用されやすさで確かめる | `article-acceptance-check` |
| 7. 効果測定 | 記事の結果と、AI による概要での引用を追う | `seo-results-review`、`ai-visibility-tracking` |
| 共通 | データを取るスクリプト、グラフの画面 | `seo-data-sources`、`seo-dashboard` |

記事を書くことと、その記事を確かめて通すことは、必ず別の Session で行います。

## 測れること、測れないこと

| | 測れるか | 要るもの |
|---|---|---|
| 自社サイトの表示回数・クリック・順位 | 測れる | Search Console（無料） |
| 任意の問いの検索数と推移 | 測れる | DataForSEO、ラッコキーワード、Ahrefs のどれか |
| 買う気の強さ（検索広告のクリック単価） | 測れる | DataForSEO |
| Google の「AI による概要」に、問いごとに誰が引用されているか | 測れる | DataForSEO |
| ChatGPT・Perplexity などから来た訪問の数 | 測れる | Google アナリティクス 4（無料） |
| ChatGPT・Perplexity などの回答が、どの問いで自社を引用したか | **測れない** | — |
| Bing の検索の数字 | **測れない** | — |

データ源が何も無くても動きますが、検索数は推測に、AI による概要の引用は「未確認」になります。

## 入れる前に

- **skill の名前が重なると、元からあるほうが使われます。** 入れる Agent に、上の表と同じ名前の skill（`article-brief`、`keyword-strategy` など）が既にあると、この Plugin の同じ名前の skill は読まれません。重なる名前があれば、どちらを残すかを先に決めてください。
- **実行環境に `python3`、`openssl`、`curl` が要ります。**
- **環境変数の宣言は、Plugin には付いてきません。** データ源をつなぐとき、`seo-data-connect` が、入れた Agent の `environment.yaml` に必要な名前を足します。使う名前は次の 7 つです: `GOOGLE_SERVICE_ACCOUNT_JSON`、`GSC_SITE_URL`、`GA4_PROPERTY_ID`、`DATAFORSEO_LOGIN`、`DATAFORSEO_PASSWORD`、`RAKKO_API_KEY`、`AHREFS_API_KEY`。鍵は自分で契約したものを、Tools > Secrets に登録します。
- **スクリプトの既定は日本・日本語です。** ほかの国や言語は、最初の準備で値を決めます。日本以外では、まだ十分に試していません。
- DataForSEO と Search Console は本物の鍵で確かめています。ラッコキーワード、Ahrefs、Google アナリティクス 4 は、公式の仕様に合わせて作ってありますが、本物の鍵ではまだ試していません。

## 頼み方

入れたあと、新しい Session で頼みます。

```text
このサイト（https://example.com、日本・日本語）について、SEO・AIO の準備を確かめて、事業を調べてキーワード戦略を作ってください。
```

```text
サイトが検索と AI に読まれる状態か、調べてください。
```

```text
キーワードを 1 つ選んで、概要を作り、記事の原稿を書いてください。料金のかかる呼び出しは 1 ドルまでにしてください。
```

```text
〈ブランチや PR〉の記事を、公開する前に確かめてください。
```

```text
公開した記事の結果と、AI での見え方を見て、次の手を提案してください。
```

```text
ダッシュボードを更新してください。
```

## 作るもの

すべて Project の文書です。Plugin の中には書きません。

設定 `docs/seo-settings.md`、事業の概要 `docs/business-profile.md`、サイトの受け皿 `docs/site-readiness.md`、戦略 `docs/keyword-strategy.md`、候補 `docs/keyword-candidates.md`、概要 `docs/briefs/`、記録 `docs/seo-log.md`、AI での見え方 `docs/ai-visibility-panel.md`・`docs/ai-visibility-log.md`、画面 Project HTML の `seo-dashboard.html`。

## ライセンス

MIT License。`LICENSE` を見てください。
