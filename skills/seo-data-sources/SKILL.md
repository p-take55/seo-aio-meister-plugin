---
name: seo-data-sources
description: Search Console・GA4・DataForSEO・ラッコキーワード・Ahrefs のうち、設定されているものを選び、検索数・クリック単価・順位・訪問後の行動・AI による概要のデータを取る手順とスクリプト。Use when another skill needs search or AI-overview data, or when checking which data sources are connected.
metadata:
  aachat.headline.ja: 検索と AI のデータを取るスクリプトと手順
  aachat.headline.en: Scripts and procedures for search and AI Overview data
  aachat.description.ja: Search Console・GA4・DataForSEO・ラッコキーワード・Ahrefs から、検索数、クリック単価、順位、訪問後の行動、AI による概要の引用元を取る。
  aachat.description.en: Fetch search volume, click price, positions, on-site actions and AI Overview citations from Search Console, GA4, DataForSEO, Rakko Keyword and Ahrefs.
  aachat.discovery.listed: "true"
---

# 検索と AI のデータを取る

ほかの skill が数字を必要とするときに使う。何を使うかはここで決め、取り方は `providers/` の各ファイルに従う。

## 使えるデータ源を決める

環境変数の有無で決まる。値は表示しない（名前があるかだけを見る）。

| 環境変数 | データ源 | 費用 | 手順 |
|---|---|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` と `GSC_SITE_URL` | Search Console | 無料 | `providers/search-console.md` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` と `GA4_PROPERTY_ID` | Google アナリティクス 4 | 無料 | `providers/ga4.md` |
| `DATAFORSEO_LOGIN` と `DATAFORSEO_PASSWORD` | DataForSEO | 使った分だけ（前払い） | `providers/dataforseo.md` |
| `RAKKO_API_KEY` | ラッコキーワード | 月額＋クレジット | `providers/rakko.md` |
| `AHREFS_API_KEY` | Ahrefs | 月額＋月ごとの単位 | `providers/ahrefs.md` |

```bash
for v in GOOGLE_SERVICE_ACCOUNT_JSON GSC_SITE_URL GA4_PROPERTY_ID DATAFORSEO_LOGIN DATAFORSEO_PASSWORD RAKKO_API_KEY AHREFS_API_KEY; do
  [ -n "$(printenv $v)" ] && echo "$v: あり" || echo "$v: なし"
done
```

## つながるかを試す

設定されているものを、1 回ずつ試す。どれも料金はかからない。

```bash
python3 scripts/gsc_query.py --days 7 --limit 1                                         # Search Console
python3 scripts/ga4_query.py --days 7 --limit 1                                         # Google アナリティクス 4
python3 scripts/dataforseo.py balance                                                   # DataForSEO（残高）
curl -s -H "X-API-Key: $RAKKO_API_KEY" https://api.rakkokeyword.com/v1/account/info     # ラッコキーワード（残りのクレジット）
curl -s -G https://api.ahrefs.com/v3/keywords-explorer/overview \
  -H "Authorization: Bearer $AHREFS_API_KEY" \
  --data-urlencode "country=us" --data-urlencode "keywords=ahrefs" \
  --data-urlencode "select=keyword,volume"                                              # Ahrefs（この語は単位を使わない）
```

鍵の値は表示しない。応答に残高やクレジットがあれば、数だけ記録する。

## 国と言語

検索数と検索結果は、国と言語で変わる。Project 文書 `docs/seo-settings.md` に決めた値があれば、呼ぶたびにそれを渡す。スクリプトの既定は日本・日本語。設定の文書が無い、または「未定」のときは、取る前に対象の国と言語を決める（`seo-setup` があればそれで。無ければ依頼した人に聞く）。

## 何が、どれで取れるか

| 欲しいもの | 使うデータ源（上から順に、使える最初の 1 つ） |
|---|---|
| 自社サイトが表示された問い・ページの実数と順位 | Search Console |
| 記事に来た人の数と、その後の行動（問い合わせ・申し込み） | Google アナリティクス 4 |
| AI のサービスから来た訪問の数 | Google アナリティクス 4 |
| 任意の問いの検索数と推移 | DataForSEO → ラッコキーワード → Ahrefs |
| 検索広告のクリック単価（買う気の目安） | DataForSEO |
| ある問いの検索結果と、AI による概要の引用元 | DataForSEO |
| 質問文の候補 | ラッコキーワード |
| あるドメインが AI による概要に載っている問い | ラッコキーワード |
| 難易度 | Ahrefs → ラッコキーワード |

ここに無いものは取れない。ChatGPT・Perplexity・Gemini などの回答が、どのサイトを引用したかは取れない（取れるのは、そこから来た訪問の数だけ）。Bing の検索の数字も取れない。

## 決まり

- **検索数のツールは 1 つだけ使う。** 同じ語を 2 つのツールで引かない。費用が二重になり、数字が食い違う。
- **まとめて 1 回で送る。** どのツールも 1 回ごとに最低の料金がある。
- **同じ語を引き直さない。** 取った結果は Project の文書（`docs/keyword-candidates.md`、`docs/ai-visibility-log.md`）に残し、次回はそれを見る。あとで使う生の応答は、Session の作業フォルダに残っているうちに文書へ写す。
- **料金のかかる呼び出しの前後に、残高を見る。** 使った額を、報告と `docs/seo-log.md` の「使った額」に書く（日付、データ源、何に、額、残高）。上限を言われていれば、届く前に止める。
- **取れなかったら次に進む。** 鍵の誤りや残高不足は自分では直せない。起きたことを報告に書く。
- **出どころを必ず付ける。** 数字には、データ源と確認日を付ける。
- **数字を作らない。** どれも使えないときは「データなし」と書き、頼んできた skill の推測の手順に従う。

スクリプトは、この skill のフォルダの `scripts/` にある。ほかの skill から呼ぶときは `../seo-data-sources/scripts/〈名前〉` と書く。依存は Python の標準ライブラリと `openssl`（Google の 2 つだけ）、`curl`。
