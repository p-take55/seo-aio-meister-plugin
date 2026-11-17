-- aachat-parent: root
CREATE TABLE seo_keyword (
  keyword TEXT PRIMARY KEY,
  question TEXT, theme TEXT,
  volume INTEGER, recent3_avg INTEGER, trend TEXT,
  cpc_usd REAL, bid_low_usd REAL, bid_high_usd REAL,
  competition TEXT, competition_index INTEGER,
  monthly TEXT,
  status TEXT NOT NULL DEFAULT 'candidate',
  rank INTEGER, reason TEXT, source TEXT, checked_on TEXT
);
CREATE TABLE seo_serp_check (
  keyword TEXT NOT NULL, checked_on TEXT NOT NULL,
  ai_overview INTEGER, own_cited INTEGER, own_organic_rank INTEGER,
  references_total INTEGER, references_unknown INTEGER, cost_usd REAL,
  PRIMARY KEY (keyword, checked_on)
);
CREATE TABLE seo_serp_result (
  keyword TEXT NOT NULL, checked_on TEXT NOT NULL,
  kind TEXT NOT NULL,
  position INTEGER NOT NULL, domain TEXT, url TEXT, title TEXT,
  PRIMARY KEY (keyword, checked_on, kind, position)
);
CREATE TABLE seo_search_daily (
  date TEXT PRIMARY KEY, clicks INTEGER NOT NULL, impressions INTEGER NOT NULL, position REAL
);
CREATE TABLE seo_spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL, source TEXT NOT NULL, purpose TEXT, amount_usd REAL NOT NULL, balance_usd REAL
);
CREATE INDEX seo_keyword_theme ON seo_keyword(theme);
CREATE INDEX seo_keyword_status ON seo_keyword(status);
CREATE INDEX seo_serp_result_domain ON seo_serp_result(domain);
CREATE INDEX seo_serp_result_keyword_checked_on ON seo_serp_result(keyword, checked_on);
