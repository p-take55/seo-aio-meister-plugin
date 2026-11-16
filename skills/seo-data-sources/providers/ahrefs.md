# Ahrefs

仕様の正本: https://docs.ahrefs.com/ （Keywords Explorer の OpenAPI は `/reference/keywords-explorer.json`）。
認証はヘッダー `Authorization: Bearer $AHREFS_API_KEY`。API が使えるプランかどうかは、公式の案内で確かめてもらう。

クリック単価は、この手順では取らない。買う気の目安が要るときは「データなし」と書く。

## 検索数・推移・難易度

```bash
curl -s -G https://api.ahrefs.com/v3/keywords-explorer/overview \
  -H "Authorization: Bearer $AHREFS_API_KEY" \
  --data-urlencode "country=〈国。日本は jp〉" \
  --data-urlencode "keywords=〈語1〉,〈語2〉" \
  --data-urlencode "select=keyword,volume,volume_monthly,difficulty"
```

応答は `{"keywords":[{...}]}`。

- `volume`: 直近 12 か月の月間検索数の平均。
- `volume_monthly`: 直近 1 か月の検索数。`volume_monthly ÷ volume` で推移を見る。
- `difficulty`: 上位 10 位に入る難しさ（0〜100）。
- 語はカンマで区切るので、カンマを含む語は送れない。
- `country` は小文字の 2 文字（日本は `jp`、アメリカは `us`）。値は Project 文書 `docs/seo-settings.md` に決めたものを使う。

## 費用

- 1 回の最低 50 単位。上の 4 項目だと 1 語あたり 31 単位（`volume`・`volume_monthly`・`difficulty` が各 10、`keyword` が 1）。
- 難易度が要らなければ `difficulty` を外すと 21 単位になる。月に使える単位はプランで決まるので、大きな調査の前に残りを人間に確かめる。
- 実際に使った単位は、応答ヘッダー `x-api-units-cost-total-actual` で分かる（`curl -i` で見る）。
- キーの確認は `keywords=ahrefs` で引く。この語だけなら単位を使わない。
