---
name: seo-business-research
description: 事業・顧客・競合・自社だけの根拠を調べ、事業の概要を作る。Use when a Project has no business profile yet, or when the business has changed and the profile needs a refresh.
metadata:
  aachat.headline.ja: 事業を調べて、事業の概要を作る
  aachat.headline.en: Research the business and write a business profile
  aachat.description.ja: 事業・顧客・競合・自社だけの根拠を調べ、確かめた事実だけで事業の概要を作る。足りないことは具体的に聞く。
  aachat.description.en: Research the business, customers, competitors and unique evidence, and write a profile from verified facts only. Ask specific questions for what is missing.
  aachat.discovery.listed: "true"
---

# 事業を調べる

キーワード戦略の土台になる「事業の概要」を作る。書くのは確かめた事実だけ。

## 1. 手元の材料を読む

- Project の PROJECT.md、Project 文書、Team の Wiki（読み方は `aachat/contracts/wiki.md`）
- Project の repo（サイトの本文、LP、料金、導入事例、既存の記事）
- 人間が渡した資料

## 2. 外を調べる（Web 検索）

- 競合サービスと、その訴求・料金・記事のテーマ
- 顧客が今使っている代わりの手段（手作業、表計算、無料ツール、外注）
- 顧客が困りごとを語る言葉（Q&A サイト、SNS、レビュー、コミュニティ）

## 3. 足りないことを人間に聞く

Ask は 1 回にまとめ、3〜5 問にする。具体的な事実を名指しして聞く。

- 良い例: 「サイトに『〈数〉社以上に導入』とあります。多い業種と会社の規模を教えてください」
- 悪い例: 「御社の強みは何ですか」

## 4. 事業の概要を書く

Project 文書 `docs/business-profile.md` に置く。次の 5 節で書く。各項目に出どころ（ファイル、URL、Ask の回答）を付ける。

1. **事業**: 何を、誰に、いくらで売っているか。顧客が得るもの。
2. **顧客**: どんな立場の人が、どんな言葉で困りごとを語るか。知る → 比べる → 決める、の各段階で何を調べるか。
3. **競合と代わりの手段**: 名前、訴求、強い領域。
4. **自社だけの根拠**: 独自のデータ、実績、現場の経験、作り手の経歴。記事で「他が書けないこと」になる材料。
5. **サイトの現状**: 既存の記事とテーマ、公開からの期間、分かる範囲の流入。

確かめられなかった項目は「未確認」と書いて残す。推測で埋めない。
