# Google アナリティクス 4（GA4）

Search Console が「検索結果にどれだけ出たか」を見るのに対し、GA4 は「来た人がその後どうしたか」を見る。
`seo-data-sources` のフォルダにあるスクリプトを使う。ほかの skill から呼ぶときは `../seo-data-sources/scripts/ga4_query.py`。

```bash
python3 scripts/ga4_query.py                    # 検索から来た訪問を、最初に開いたページごとに（直近 28 日）
python3 scripts/ga4_query.py --page /blog/      # パスに /blog/ を含むページだけ
python3 scripts/ga4_query.py --channel all      # 検索に限らず、すべての経路
python3 scripts/ga4_query.py --ai               # AI のサービスから来た訪問を、来た元とページごとに
```

出力はタブ区切り。

- 通常: `landing_page, sessions, prev_sessions, engaged_sessions, key_events`
- `--ai`: `source, landing_page, sessions, prev_sessions, engaged_sessions, key_events`

`--page` に渡すのは**パス**（`/blog/` や `/blog/〈記事の名前〉`）。GA4 が持っているのはドメインを除いたパスなので、`https://` から始まる URL を渡すと 1 行も返らない。0 行を「訪問なし」と読む前に、渡した値を確かめる。

## 読み方

- `sessions`: 訪問の数。`prev_sessions` は同じ長さの 1 つ前の期間。
- `engaged_sessions`: 10 秒以上いた、2 ページ以上見た、または重要な行動をした訪問。`engaged_sessions ÷ sessions` が低い記事は、問いと中身が合っていないおそれがある。
- `key_events`: GA4 で「重要」と設定した行動（問い合わせ、申し込み、資料請求など）の回数。**設定されていなければ常に 0**。0 が並ぶときは、設定の有無を人間に確かめる。0 を「成果なし」と読まない。
- `--ai` は、来た元の名前に ChatGPT・Perplexity・Claude・Gemini・Copilot などを含む訪問を集める。AI の回答のリンクを押して来た人の数で、AI の回答に出た回数ではない。来た元を渡さない AI のアプリからの訪問は、ここに入らない。
- 訪問が少ないページは、GA4 が数字を丸めたり出さなかったりする。10 未満の数字で増減を語らない。

## エラー

| 状態 | 意味 |
|---|---|
| `HTTP 403` | サービスアカウントが、GA4 のプロパティの閲覧者に追加されていない。または Analytics Data API が有効になっていない |
| `HTTP 400` と `property` の記述 | `GA4_PROPERTY_ID` が違う。測定 ID（`G-` で始まる）ではなく、数字だけのプロパティ ID を使う |
| `invalid_grant` | 鍵が違う |
