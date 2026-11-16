---
name: seo-results-review
description: 公開した記事の検索と AI での結果を見て、効いたテーマ・直す記事・戦略の変更を決める。Use on a regular review cycle（4 週間に 1 回）, or when asked how the published articles are performing.
metadata:
  aachat.headline.ja: 公開した記事の結果を見て、次の手を決める
  aachat.headline.en: Review published article results and decide next steps
  aachat.description.ja: 公開した記事の表示・順位・訪問後の行動・AI による概要での引用を見て、記事を区分し、直す記事と戦略の変更を提案する。
  aachat.description.en: Review impressions, positions, on-site actions and AI Overview citations of published articles, classify them, and propose rewrites and strategy changes.
  aachat.discovery.listed: "false"
---

# 結果を見て、次の手を決める

4 週間に 1 回行う。`ai-visibility-tracking` と同じ回にまとめると、同じ問いを二度引かずに済む。記事が 1 本も公開されていなければ、行わずにその旨を報告する。

## 1. 公開した記事を並べる

`docs/seo-log.md`、`docs/briefs/` と repo の記事フォルダから、記事ごとに URL・公開日・狙った問い・戦略のテーマを一覧にする。

## 2. 数字を取る

Search Console が使えるとき（取り方は `../seo-data-sources/providers/search-console.md`）:

```bash
python3 ../seo-data-sources/scripts/gsc_query.py --by page --page "〈記事フォルダの URL。例 https://example.com/blog/〉" --days 28   # 記事ごと
python3 ../seo-data-sources/scripts/gsc_query.py --page "〈記事の URL〉" --days 28                                               # その記事が出た問い
```

使えないときは、狙った問いを Web 検索して順位を目で確かめ、「Search Console なし。目視」と記録する。数字を作らない。

Google アナリティクス 4 が使えるとき（取り方は `../seo-data-sources/providers/ga4.md`）:

```bash
python3 ../seo-data-sources/scripts/ga4_query.py --page "〈記事フォルダのパス。例 /blog/〉" --days 28   # 検索から来た訪問と、その後の行動
```

GA4 に渡すのはパス（`/blog/`）で、Search Console に渡すのは URL。取り違えると 1 行も返らない。

記事ごとに、訪問の数、しっかり読まれた割合、重要な行動の回数を控える。重要な行動が GA4 に設定されていなければ、その旨を書いて人間に確かめる。

AI による概要での引用は、同じ回の `ai-visibility-tracking` の記録にある問いは、その結果を使う。記録に無い問いだけ、`ai-citation-check` の方法で取る。同じ問いを同じ日に二度引かない。

## 3. 記事を分ける

| 区分 | 目安 | 次の手 |
|---|---|---|
| まだ早い | 公開から 8 週間たっていない。または、4 週間たっていない | 判断しない。次の回に見る。ただし下の「検索に載っているか」は 2 週間で確かめる |
| 効いている | 狙った問いで 7 位以内、または AI による概要に引用されている | 同じテーマの隣の問いを候補に足す。重要な行動につながっている記事は、テーマの優先度を上げる材料にする |
| あと一歩 | 狙った問いで 8〜30 位 | 直す。上位にあって自社に無い論点、古い記述、足せる自社の根拠を挙げる |
| 別の問いで出ている | 狙っていない問いでの表示のほうが多い | その問いに合わせて直すか、別の記事にするかを決める |
| 出ていない | 8 週間たっても、表示がほぼ無いか 31 位以下 | 原因を 1 つに絞る（検索に載っていない・問いに需要が無い・競争が強い・内容が問いに答えていない） |

公開から 4〜8 週間の記事は、7 位以内か引用があれば「効いている」、それ以外は「まだ早い」にする。

### 検索に載っているか

公開から 2 週間たった記事は、区分とは別に確かめる。載っていない記事は、中身を直しても結果が出ない。

1. Search Console で、その記事の URL の表示が 1 回でもあれば、載っている。
2. 無ければ、Web 検索で `site:〈記事の URL〉` を引く。出れば載っている。
3. どちらでも出なければ「検索に載っていない」とし、サイトマップにその URL があるか、noindex が付いていないかを `site-readiness-audit` のスクリプトで見る。問題が無ければ、Search Console の「URL 検査」で登録を頼むよう人間に伝える。

## 4. テーマごとにまとめる

戦略のテーマごとに、記事の本数と区分の内訳を出す。

- 効いている記事が多いテーマ → 優先度を上げる提案
- 3 本以上出して、どれも「出ていない」テーマ → 止めるか、狙う問いを狭める提案
- 「別の問いで出ている」が続く → 戦略に無い有望なテーマの候補

## 5. 動く

- **戦略の変更**（優先度、テーマの追加・削除）は、根拠の数字を付けて Ask で提案する。承認されるまで `docs/keyword-strategy.md` を変えない。
- **記事を直す提案**は、`article-brief` の「書き直す記事の概要」にして渡す。
- **次に選ぶ問い**への反映は、戦略の範囲内なら承認を待たずに行ってよい。

## 6. 記録する

Project 文書 `docs/seo-log.md` に追記する。

- 確認日、期間、データ源
- 記事ごとの区分と主な数字（表示回数、順位、引用の有無、訪問と重要な行動）
- テーマごとのまとめ
- 出した提案と、その状態（承認待ち・承認済み・見送り）
- 次に見る日
