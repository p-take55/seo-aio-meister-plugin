# Search Console

`seo-data-sources` のフォルダにあるスクリプトを使う。ほかの skill から呼ぶときは `../seo-data-sources/scripts/gsc_query.py`。

```bash
python3 scripts/gsc_query.py --days 28                 # 直近 28 日の全体
python3 scripts/gsc_query.py --days 90 --contains "〈語〉"  # 語を含む問いだけ
python3 scripts/gsc_query.py --by page --page "/blog/"   # ページごとの集計（URL に /blog/ を含むもの）
python3 scripts/gsc_query.py --page "〈記事の URL〉"       # その記事が表示された問い
python3 scripts/gsc_query.py --by total --days 28        # サイト全体の合計（今の期間と前の期間）
python3 scripts/gsc_query.py --by date --days 90         # 日ごとの推移
```

出力はタブ区切りで、`query（または page）, clicks, impressions, prev_impressions, position`。
`prev_impressions` は同じ長さの 1 つ前の期間の表示回数。推移は `impressions ÷ prev_impressions` で見る。両方が 10 未満なら「不明」。

- `--by total` の出力は `period（current / prev）, clicks, impressions, position`。匿名化された検索も含むので、問いごとの行を足した数より大きい。サイト全体の数字はこちらを使う。
- `--by date` の出力は `date, clicks, impressions, position`。データの無い日は 0 で出る。
- 新しいサイトは行が出ない。「Search Console にデータなし」と記録する。
- `HTTP 403`: サービスアカウントがプロパティのユーザーに追加されていない。
- `invalid_grant`: 鍵が違う。

鍵は `GOOGLE_SERVICE_ACCOUNT_JSON`、プロパティは `GSC_SITE_URL`。鍵は Google アナリティクス 4 と共通で使える。
