# ラッコキーワード

仕様の正本: https://api.rakkokeyword.com/docs （OpenAPI は `/api-docs.json`）。
認証はヘッダー `X-API-Key: $RAKKO_API_KEY`。制限は 60 回 / 60 秒。応答の `meta.consumedCredit` に使ったクレジットが入る。

残高は無料で見られる。大きな調査の前に確かめる。

```bash
curl -s -H "X-API-Key: $RAKKO_API_KEY" https://api.rakkokeyword.com/v1/account/info
```

クレジットの数は変わることがある。下に書いた数は目安で、実際に使った数は応答の `meta.consumedCredit` で確かめる。

## 検索数と推移（1 語 0.03 クレジット、1 回の最低 15 クレジット）

登録 → 完了待ち → 結果取得の 3 段階なので、`seo-data-sources` のフォルダにあるスクリプトを使う。

```bash
python3 scripts/rakko_volume.py "〈語1〉" "〈語2〉"
python3 scripts/rakko_volume.py --file words.txt
python3 scripts/rakko_volume.py --request-id 〈番号〉   # 時間切れのときの取り直し。クレジットを使わない
```

日本・日本語が既定。変えるときは `--location 〈国の名前〉 --language 〈言語の名前〉` を付ける（英語の名前。例 `--location "United States" --language English`）。対応している国と言語は、仕様の正本で確かめる。値は Project 文書 `docs/seo-settings.md` に決めたものを使う。

出力はタブ区切りで、`keyword, volume, change_3m, change_12m, competition, source`。

- `volume` は月間検索数の年平均。空欄はデータなし。
- `change_12m` は、直近月が 12 か月平均からどれだけ増減したかの比率（0.3 = +30%）。0.3 以上で「伸びている」、-0.3 以下で「減っている」。
- 1 語でも 15 クレジットかかる。候補を全部まとめて 1 回で送る。
- 時間切れ（終了コード 2）になったら、同じ語を登録し直さず、表示された `--request-id` で取り直す。

## 問いを集める（候補出しで使う。各 1.5 クレジット）

AI や検索に投げられる質問文を、需要の高い順に返す。相対需要は 1〜100 で、同じ検索の中でだけ比べられる。

```bash
curl -s -X POST https://api.rakkokeyword.com/v1/question-search \
  -H "X-API-Key: $RAKKO_API_KEY" -H "Content-Type: application/json" \
  -d '{"keyword":"〈語〉","limit":100}'
```

サジェストを検索数つきで取るときは `/v1/suggest-keywords`（本文は `{"keyword":"〈語〉","limit":200}`）。

## AI による概要に載っている問いを調べる（1 回 4.5 クレジット）

競合や自社のドメインが、どの問いの AI による概要で情報源になっているかを返す。

```bash
curl -s -X POST https://api.rakkokeyword.com/v1/influx-aio \
  -H "X-API-Key: $RAKKO_API_KEY" -H "Content-Type: application/json" \
  -d '{"targets":[{"url":"〈競合のドメイン〉","matchType":"sub_domain"}],"limit":100}'
```

`items[].keyword` が問い、`items[].aio.placement` が載り方（`body_link` 本文のリンク / `citation` 引用 / `both`）。
ラッコが取得した時点の状態で、今の表示とは違うことがある。記事にする問いは、実際の検索結果でも確かめる。

## エラー

| 状態 | 意味 |
|---|---|
| 402 | クレジット不足。やり直しても直らない |
| 403 | キーが無効、またはプランが API の対象外。対象のプランは公式の案内で確かめてもらう |
| 429 | 制限を超えた。1 分待つ |
