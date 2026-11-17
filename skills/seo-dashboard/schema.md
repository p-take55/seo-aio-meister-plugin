# seo-dashboard.data.json の形

`schema`、`generated_at`、`site` は必須。ほかの節は、無ければ `null` か空の一覧にする。節の中の値も、分からなければ `null` にできる（必須なのは、名前や日付のように行を見分けるための値だけ。何が必須かは `check_data.py` が教える）。知らないキーを足しても画面は壊れないが、表示もされない。

下の例の数字は、形を示すための作りもの。

日付は `YYYY-MM-DD`、`generated_at` は ISO 8601（UTC）。金額はドル。

```jsonc
{
  "schema": 1,
  "generated_at": "2026-11-16T08:40:00Z",
  "site": { "name": "〈サイト名〉", "url": "https://example.com" },

  "stage": { "current": 4, "note": "〈今の状況を 1 文で〉" },        // current: 0〜7（SKILL.md の「段階の番号」）
  "next_action": { "who": "human", "text": "〈次にやること〉" },     // who: "human" | "agent"
  "asks": [ { "title": "〈Ask の題名〉", "waiting_for": "〈人の名前〉", "since": "2026-11-16" } ],
  "sources": [ { "name": "Search Console", "state": "connected", "note": "〈補足〉", "checked_on": "2026-11-16" } ],
            // state: "connected"（接続済み）| "requested"（依頼中）| "not_connected"（未接続）
  "spend": [ { "name": "DataForSEO", "balance_usd": 12.00, "used_usd": 3.00, "checked_on": "2026-11-16" } ],

  "search": {
    "source": "Search Console",
    "period": { "start": "2026-10-17", "end": "2026-11-13" },
    "prev_period": { "start": "2026-09-19", "end": "2026-10-16" },
    "totals": { "clicks": 120, "impressions": 2400, "prev_clicks": 90, "prev_impressions": 2000, "position": 12.5, "prev_position": 14.0 },   // position と prev_position は null でもよい
    "daily": [ { "date": "2026-08-16", "clicks": 0, "impressions": 3 } ],      // 古い順。前回の行を残して足す
    "queries": [ { "query": "〈問い〉", "clicks": 0, "impressions": 0, "prev_impressions": 0, "position": 0.0, "brand": false } ],
    "pages": [ { "page": "https://example.com/", "clicks": 0, "impressions": 0, "prev_impressions": 0, "position": 0.0 } ],
    "note": "〈数字の読み方の注意〉"
  },

  "themes": [ { "name": "〈テーマ名〉", "priority": "高" } ],                  // priority: "高" | "中" | "低"
  "keywords": [ {
    "keyword": "〈検索の言い方〉",                // 必須
    "question": "〈記事が答える問い〉",
    "theme": "〈テーマ名〉",
    "volume": 140, "recent3_avg": 150,           // 数値 | null
    "trend": "up",                               // "up"（伸びている）| "flat"（横ばい）| "down"（減っている）| "unknown"（不明）
    "cpc_usd": 19.73,                            // 数値 | null
    "competition": "MEDIUM",                     // "LOW" | "MEDIUM" | "HIGH" | null（広告の競合）
    "ai_overview": true, "own_cited": false,     // true | false | null（未確認）
    "own_position": null,                        // 自社の順位（Search Console）。数値 | null
    "status": "proposed",                        // "candidate"（候補）| "proposed"（提案中）| "approved"（承認済み）
                                                 // | "briefed"（概要あり）| "drafted"（原稿あり）| "accepted"（確認済み・公開待ち）
                                                 // | "published"（公開済み）| "dropped"（見送り）
    "rank": 1,                                   // おすすめ順。整数 | null
    "reason": "〈勝てる理由〉",
    "source": "DataForSEO", "checked_on": "2026-11-16"
  } ],

  "citation_sources": {                          // AI による概要が引用しているサイト（ai-citation-check の結果を集計）
    "checked_on": "2026-11-16",
    "questions": 30,                             // 確かめた問いの数
    "with_overview": 20,                         // AI による概要が出た問いの数。整数 | null
    "items": [ { "domain": "example.org", "cited": 12, "own": false } ],  // cited: そのサイトを引用していた問いの数
    "unknown": 6,                                // 参照先が読めなかった引用の数（`dataforseo.py serp` の「不明」の行）。無ければ省く
    "note": "〈数字の読み方の注意。無ければ省く〉"
  },

  "ai_visibility": {
    "panel": [ { "id": "q1", "question": "〈定点で見る問い〉" } ],
    "log": [ { "date": "2026-11-16", "engine": "Google AI Overview", "question_id": "q1",
               "overview": true,                 // AI による概要が出たか。true | false | null
               "cited": false,                   // 自社が引用されたか。true | false | null
               "sources": ["example.org"] } ]    // 引用元のドメイン。空でもよい
  },

  "articles": [ {
    "title": "〈記事の題〉",
    "state": "published",                        // "brief"（概要あり）| "draft"（原稿あり）| "in_review"（確認中）| "published"（公開済み）。省くと公開済み
    "url": "https://example.com/blog/…", "published_on": "2026-11-20",   // 公開前は null
    "preview": "articles/〈slug〉.html",          // 省略可。原稿のプレビュー（scripts/article_preview.py で作る）。Project HTML からの相対パス
    "source_url": "https://github.com/…/blob/〈ブランチ〉/…",   // 省略可。原稿の置き場所
    "keyword": "〈狙った言い方〉",
    "clicks": 0, "impressions": 0, "position": null, "ai_cited": null,
    "verdict": "まだ早い"                         // "効いている" | "あと一歩" | "別の問いで出ている" | "出ていない" | "まだ早い"（seo-results-review の区分）。公開前は null
  } ],

  "readiness": {
    "checked_on": "2026-11-16",
    "items": [ { "level": "stop", "title": "〈項目〉", "state": "done", "note": "〈補足〉" } ]
              // level: "stop"（止める）| "improve"（効く）| "optional"（任意）; state: "open"（未）| "done"（済）
  }
}
```
