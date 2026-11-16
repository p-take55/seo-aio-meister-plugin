---
name: seo-data-connect
description: Search Console・Google アナリティクス 4・検索数のツール（DataForSEO・ラッコキーワード・Ahrefs）のうち、次につなぐものを 1 つ勧め、人間に手順を渡し、つながったかを確かめる。Use when asked to connect or set up analytics and SEO tools（「分析ツールの連携を進めて」）, when a needed data source is missing, or when a requested connection needs to be verified.
metadata:
  aachat.headline.ja: Search Console や検索数のツールをつなぐ
  aachat.headline.en: Connect Search Console and keyword data tools
  aachat.description.ja: 次につなぐデータ源を 1 つ勧め、人間に手順を渡し、つながったかを確かめる。鍵の発行や契約は人間が行う。
  aachat.description.en: Recommend the single next data source to connect, hand the human step-by-step instructions, and verify the connection. Keys and contracts stay with the human.
  aachat.discovery.listed: "false"
---

# データ源をつなぐ

鍵の発行、契約、入金は人間が行う。自分がやるのは、どれをつなぐかを勧めること、手順を渡すこと、つながったかを確かめること。

## 1. 次につなぐものを 1 つ勧める

足りないものを全部並べて頼まない。今の段階でいちばん効くものを 1 つ選び、理由を付けて勧める。

既に持っているツールがあるかを、勧める前に 1 回聞く。持っていれば、それを先に使う。Search Console の手順は、有料のツールの有無で変わらないので、この答えを待たずに渡してよい。

上から順に見て、最初に当てはまるものを勧める。

| 状況 | 勧めるもの | 理由 |
|---|---|---|
| Search Console が未設定 | Search Console | 無料で、自社の実数が取れる唯一の手段。記事が 0 本でも、つないでおけば公開した日から数字がたまる |
| GA4 が未設定で、サイトに GA4 のタグが入っている | Google アナリティクス 4 | 無料。Search Console と同じ鍵で読めるので、手間は閲覧者の追加だけ |
| 検索数のツールが未設定で、既に Ahrefs かラッコキーワードを契約している | その鍵の登録 | 新しい契約が要らない |
| 検索数のツールが未設定 | DataForSEO | 月額が無く、使った分だけ払う。検索数・クリック単価・問いごとの AI による概要の引用元が、1 つの契約で取れる |
| 検索数のツールはあるが、問いごとの AI による概要を取れない | DataForSEO | 引用されているかを問いごとに追うのに要る |
| 日本語のサイトで、質問文をまとめて集めたい | ラッコキーワード | 質問文の収集と、あるドメインが AI による概要に載っている問いの調査ができる |

- サイトに GA4 のタグが入っているかは、repo と公開中のページの両方で見る。ページの HTML に `googletagmanager.com/gtag/js` や `G-` で始まる ID があれば入っている。入っていなければ、タグを入れる開発の作業が先に要るので、別に伝える。
- 費用がかかるものは、費用の形（月額、従量、最低の入金）を書き、契約するかどうかは人間に決めてもらう。**料金の額は自分で言い切らない。** 公式の料金表を見てもらうか、見た日付と出どころを付けて伝える。
- 月額のツールと使った分だけ払うツールは、1 年ぶんで比べる。記事を出す数が少ないうちは、使う量も少ない。

## 2. 手順を渡す

勧めたものについて、人間がやることを番号つきで Ask に書く。1 回の Ask に、つなぐもの 1 つぶんだけを書く。

分かっている事実は決め打ちで書く。「無ければ追加」「種類によって書き方が変わる」のような分かれ道を残さない。あとで前提が分かったら、分かれ道を外した Ask を新しく出し、古い Ask は置き換え先を理由に書いて取り消す。

**Search Console と Google アナリティクス 4（鍵は共通）**

1. Google Cloud でプロジェクトを開き、「Search Console API」と「Google Analytics Data API」を有効にする。
2. 「IAM と管理 > サービス アカウント」でサービスアカウントを作り、「鍵 > 鍵を追加 > JSON」で鍵を発行する。役割は付けなくてよい。
3. Search Console の「設定 > ユーザーと権限」で、サービスアカウントのメールアドレスを「制限付き」で追加する。
4. GA4 の「管理 > プロパティのアクセス管理」で、同じメールアドレスを「閲覧者」で追加する。
5. Tools > Secrets に次を登録し、この Agent に使用を許可する。
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: 鍵の JSON の中身。1 行しか入らない欄なら、base64 にしたものでよい
   - `GSC_SITE_URL`: Search Console のプロパティ（ドメインなら `sc-domain:example.com`、URL なら `https://example.com/`）
   - `GA4_PROPERTY_ID`: GA4 の「管理 > プロパティの詳細」にある数字の ID（`G-` で始まる測定 ID ではない）

片方だけつなぐときは、その分の手順だけを書く。Search Console が登録済みかを聞くときは、プロパティの種類と、サイトマップを送ってあるかも一緒に聞く。

**DataForSEO**

1. dataforseo.com でアカウントを作り、管理画面に出るメールアドレスと電話番号の確認を最後まで済ませる。確認が済むまで、検索数と検索結果は呼べない。
2. 管理画面の「API Access」で、API 用のログインとパスワードを確かめる（サイトに入るときのパスワードとは別のもの）。
3. Tools > Secrets に `DATAFORSEO_LOGIN` と `DATAFORSEO_PASSWORD` を登録し、この Agent に使用を許可する。
4. 入金は、つながったことを確かめてからでよい。入金の前に、料金のかからない試験用の場所で接続を確かめる（`../seo-data-sources/providers/dataforseo.md` の「初めてつないだとき」）。

入金を聞く前に、残高を見る（無料）。新しいアカウントには試用の残高が入っていることがある。「入金する」「試用の残高で始める」「入金しない」の中から選んでもらう。

**ラッコキーワード・Ahrefs**

1. それぞれの管理画面で API キーを発行する（API が使えるプランかどうかは、公式の案内で確かめてもらう）。
2. Tools > Secrets に登録し、この Agent に使用を許可する。名前は `seo-data-sources` の表のとおり。

画面の名前は変わることがある。手順どおりに進まないと言われたら、公式の案内を確かめて直す。

Tools > Secrets に欄が出るのは、この Agent の `environment.yaml` に、その名前の宣言があるときだけ。つなぐデータ源の名前（`seo-data-sources` の表にある環境変数）が宣言に無ければ、手順を渡す前に、名前と用途だけを `config.env` に足して push する（書き方は `aachat/contracts/environment.md`）。値は書かない。

鍵やパスワードを、Ask の回答やチャットに貼ってもらわない。貼られたら、Secret に登録し直して、貼った鍵は作り直すよう伝える。

## 3. つながったかを確かめる

手順を渡したら、`docs/seo-settings.md` のデータ源の表で、そのデータ源の状態を「依頼中」にし、`docs/seo-log.md` の「データ源の接続」に 1 行足す。

次に動くとき、依頼中のものがあれば、最初につながるかを試す（試し方は `seo-data-sources` の「つながるかを試す」）。

- つながった → 状態を「接続済み」に直し、記録に 1 行足す。取れるようになったデータで、止めていた作業（推測のままの検索数、未確認の引用）をやり直す。
- エラー → エラーの内容から原因を 1 つに絞って伝える（例: 「Search Console に、サービスアカウントがユーザーとして追加されていないようです」）。
- 未設定のまま → 催促は 1 回だけにする。それでも進まなければ、無いままで続け、報告に残す。
