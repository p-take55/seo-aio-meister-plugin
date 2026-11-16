---
name: keyword-discovery
description: 承認済みの戦略のテーマから、候補の問いを広く出して絞る。Use when asked to pick keywords for new articles.
metadata:
  aachat.headline.ja: 戦略のテーマから、候補の問いを広げて絞る
  aachat.headline.en: Expand and narrow candidate questions from the strategy themes
  aachat.description.ja: 承認済みの戦略のテーマごとに、人が実際に検索や AI に投げる言い方を広く集め、重なりを除いて絞る。
  aachat.description.en: For each approved theme, gather the phrasings people actually use in search and AI, remove overlaps, and narrow the list.
  aachat.discovery.listed: "false"
---

# 候補の問いを出す

前提: `docs/keyword-strategy.md` が承認済み。そうでなければ `keyword-strategy` に戻る。

## 1. テーマを選ぶ

優先度と、これまでの記事の偏りを見て、今回扱うテーマを決める。

## 2. 問いを広げる

テーマごとに 10〜20 個出す。出どころは次のとおり。

- Google のサジェスト: `https://suggestqueries.google.com/complete/search?client=firefox&hl=〈言語〉&oe=utf-8&q=〈語〉` を、語の後ろに、調べる言い方（日本語なら「 とは」「 やり方」「 比較」「 できない」「 おすすめ」や五十音）を付けて引く。`hl` は `docs/seo-settings.md` の値を使う
- 検索結果の「他の人はこちらも質問」と関連語（Web 検索）
- 顧客の言葉（Q&A サイト、SNS、レビュー）
- Search Console（設定されていれば）: 自社サイトが既に表示されている問い。表示が多く順位が 8〜30 位のものを優先する。取り方は `../seo-data-sources/providers/search-console.md`
- ラッコキーワード（`RAKKO_API_KEY` があれば）: 質問文を需要の高い順に集める。取り方は `../seo-data-sources/providers/rakko.md` の「問いを集める」
- 事業の概要にある顧客の困りごと

人が実際に打つ・聞く言い方のまま記録する。きれいに言い換えない。どのテーマの候補として広げたかを、問いごとに一緒に記録する。

製品やサービスの終了・統合・改名のように、期限のある出来事がテーマの中にあれば、それについての問いも広げる。上位は公式の告知とニュースで埋まるが、「その後どうするか」の問いは空いていることが多い。期限があるので、見つけたら早く出す候補にする。

## 3. 重なりを除く

- 過去に扱ったキーワード: `docs/seo-log.md`、`docs/keyword-candidates.md`、`docs/briefs/` と、記事作成の Workflow があればその Run の履歴を最後まで照合する。履歴を読み切れなかったら「未確認」と記録し、新しい Run を起動しない。
- 既存の記事: Project の repo の記事フォルダ（作業ブランチも見る）

同じ答えになる問いは 1 つにまとめ、代表の言い方を選ぶ。

## 4. 絞る

検索数を取るのは、広げた候補の全部でよい（1 回で送れば料金は同じ）。その結果を見て、依頼された数の 2〜3 倍まで絞り、`ai-citation-check` に渡す。絞る基準は次のとおり。

- **戦略の外は選ばない。** 戦略に無いテーマは、検索数が多くても選ばない。有望なら、戦略の見直しとして人間に提案する。
- **問いで選ぶ。** 人が検索や AI に実際に投げる言い方を単位にする。
- **買う気の強い言い方も入れる。** 調べる問い（「〜とは」「〜 やり方」）だけに寄せず、「〜 ツール」「〜 比較」「〜 料金」「〜 会社」のような、導入に近い言い方も候補に残す。どれが強いかは `keyword-evidence` のクリック単価で確かめる。
- **勝てる理由が引けるものだけ。** その問いに、この会社が他より良く答えられる根拠（独自のデータ、実績、現場の経験、製品の機能）を、事業の概要から引けること。
