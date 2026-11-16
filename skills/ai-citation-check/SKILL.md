---
name: ai-citation-check
description: ある問いに対して、検索上位と、Google の AI による概要が今どのサイトを引用しているかを調べ、入り込めるかを判断する。Use before finalizing a keyword, and when sizing competition for a strategy theme.
metadata:
  aachat.headline.ja: 検索上位と AI による概要の引用元を調べる
  aachat.headline.en: Check who ranks and who is cited in AI Overviews
  aachat.description.ja: ある問いについて、検索上位と Google の AI による概要が今どのサイトを引用しているかを調べ、入り込めるかを判断する。
  aachat.description.en: For a question, check which sites rank and which are cited in Google AI Overviews today, and judge whether there is room to get in.
  aachat.discovery.listed: "false"
---

# AI による概要と検索上位の現状を見る

問いごとに行う。見るのは、Google の検索結果と、そこに出る AI による概要。ChatGPT などの回答が何を引用するかは、ここでは分からない。

## 1. 現状を取る

`seo-data-sources` で使えるデータ源を確かめ、使えるものを選ぶ。

- **DataForSEO があるとき**: 問いごとに、検索結果と AI による概要の引用元を取る。取り方は `../seo-data-sources/providers/dataforseo.md` の「ある問いの検索結果と、AI による概要の引用元」。
- **ラッコキーワードがあるとき**: 競合のドメインが、どの問いの AI による概要に載っているかをまとめて取れる。テーマの競争を測るときに向く。取り方は `../seo-data-sources/providers/rakko.md` の「AI による概要に載っている問いを調べる」。取得した時点の状態なので、記事にする問いは今の検索結果でも確かめる。
- **どちらも無いとき**: Web 検索でその問いを引き、上位のページを読む。AI による概要は取れないので、「AI の引用は未確認」と記録する。

## 2. 読み取る

- **引用・上位にいるのは誰か**: 公式や大手メディアか、個人の記事や事業会社のブログか
- **内容の古さ**: 公開日・更新日。1 年以上前の記事が残っているか
- **答えの質**: 問いに正面から答えているか。一般論の寄せ集めか、実データや体験があるか
- **抜けている論点**: 上位のどこも書いていないが、読者が知りたいはずのこと

## 3. 判断する

| 判断 | 目安 |
|---|---|
| 入り込める | 上位が古い・浅い・一般論だけ。または、自社だけの根拠で埋められる抜けがある |
| 難しい | 公式や大手が、新しく深い内容で埋めている。自社の根拠でも上回れない |
| AI の概要が出ない | 引用の機会は無いが、通常の検索上位は狙える。その旨を書く |

判断には、見た URL と確認日を付ける。「難しい」問いは選ばない。

## 4. 残す

- 問いごとの結果（概要が出たか、自社が引用されたか）を、`docs/keyword-candidates.md` のその問いの行に書く。
- 引用元のドメインは、問いごとに控えておく。`seo-dashboard` が「引用されているサイト」の集計に使う。生の出力は Session が終わると消えるので、消える前に写す。
