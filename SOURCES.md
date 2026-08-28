# Sources & Provenance

All raw inputs are stored under `raw/` (git-ignored). Re-derivation steps below.

## Delisting records

| Market | Source | What was used | Notes |
|---|---|---|---|
| US (2008–2026) | GitHub `royelee/delist-detection` → `raw/us/delist_classifications.csv`, `raw/us/dlret.csv`, `raw/us/web_verification.csv` | 461 delisted tickers with CIK, observed delisting date, delisting bucket (merger / exchange transfer / compliance failure / liquidation / expiration), filing form (25/25-NSE), filing date, resolved company name, payout per share, exchange | Author's pipeline analyzes SEC EDGAR Form 25 (exchange delisting) and Form 15 (deregistration) filings + 8-K M&A items. Snapshot pulled 2026-08-28. |
| US (1990–2008) | Curated (`data/curated/us_pre_2009.json`) | ~50 notable delistings (AOL, Enron, WorldCom, GM, Lehman, Lucent, Compaq, …) | Compiled from public record; each row carries its own note. |
| HK (all eras) | HKEX official page `https://di.hkex.com.hk/di/NSDelistedStockList.aspx?lang=EN` → `raw/hk/hkex_delisted.txt` | Complete delisted stock-name list: stock code + stock name(s). A code appearing twice = the code was re-issued to a different company | Fetched 2026-08-28 (3 pages). No dates published by HKEX in this list. |
| JP (2015–2026) | GitHub `nogamoga/jp-delisted-codes` → `raw/jp/nogamoga_2015.json … nogamoga_2026.json` | Annual lists of delisted JPX security codes with delisting dates | Codes only (no names). |
| JP (2023–2026 names/reasons) | GitHub `learningihara1-arch/japan-delisted-companies-database` → `raw/jp/jp_delisted_rows.json` (embedded in the repo's HTML) | 342 records: code, name, market segment, delisting date, reason category (MBO / acquisition / failed listing standards / …) | Joined to the codes by 4-digit code. |
| JP (1990–2022 notables) | Curated (`data/curated/jp_1990_2022.json`) + ja.wikipedia "東京証券取引所で上場廃止となった企業一覧" (snippet) | Bank-failure era (Aozora, Shinsei, Ashikaga, Kobe Shoko, Hokkaido Takushoku, Shinano, Saitama, Tokyo Shoko, Kumamoto, Hiroshima Shoko, Kyushu, Kashima, Shonan, Nihon Kodo, Nokan Bank, Ashiya, …), Daiichi Pharma, Sanyo, Elpida, Suisden, NIS, Silver Seiko, Laitex, Yahoo! Japan (4689), DMM.com (5022), Nippon Sanso (4090) | Entries with `verify` in notes are lower-confidence. |
| KR | GitHub `kt3472/kospi_delisted` → `raw/kr/raw_data.xlsx` (sheet `Sheet1`, `Target == 1`) | 374 delisted KOSPI companies: KRX symbol, Korean company name, last fiscal year (1994–2018) | Delisting year approximated from last fiscal year. |
| CA/UK/DE/FR/NL/CH/AU/CN/IN | Curated files in `data/curated/` | See per-market notes in `notes`/`source` fields | India undated rows come from the Scribd document "List of Delisted Companies in India" (doc 750401811) snippet; BSE dated rows from Moneycontrol's BSE delistings page; CN 2022 rows from maigoo.com and cofool.com 2022 lists. |

## Current-listing references (ticker-recycle checks)

| Market | Source | File | Snapshot |
|---|---|---|---|
| US | GitHub `rreichel3/US-Stock-Symbols` (auto-updated mirror of NASDAQ Trader symbol files) | `raw/current/us_nyse_full.json`, `us_nasdaq_full.json`, `us_amex_full.json` | 2026-08-28 |
| HK | HKEX List of Securities (via GitHub mirror `LondonMarket/Global-Stock-Symbols`) | `raw/current/hk_current.xlsx` | 2025-06-30 |
| JP | JPX security code list (via same mirror) | `raw/current/jp_current.xlsx` | 2024-06-28 |
| DE | Deutsche Börse listed-company sheets (via same mirror) | `raw/current/de_current.xlsx` | 2024-10-01 |
| UK | LSE instrument list (via same mirror) | `raw/current/uk_current.xlsx` | 2022-11-30 |
| AU | ASX listed companies list (via same mirror) | `raw/current/asx_current.csv` | 2025-06-07 |

## How raw/ was produced (if you need to re-derive)

```bash
# GitHub-hosted files (via API blob download, base64-decoded):
gh api repos/royelee/delist-detection/git/blobs/<sha> --jq .content | base64 -d > raw/us/delist_classifications.csv
gh api repos/nogamoga/jp-delisted-codes/git/blobs/<sha> --jq .content | base64 -d > raw/jp/nogamoga_<year>.json
gh api repos/learningihara1-arch/japan-delisted-companies-database/git/blobs/<sha> --jq .content | base64 -d > raw/jp/jp_delisted_full.html   # then extract `RawCompaniesData` array
gh api repos/kt3472/kospi_delisted/git/blobs/<sha> --jq .content | base64 -d > raw/kr/raw_data.xlsx
gh api repos/rreichel3/US-Stock-Symbols/git/blobs/<sha> --jq .content | base64 -d > raw/current/us_*_full.json
gh api repos/LondonMarket/Global-Stock-Symbols/git/blobs/<sha> --jq .content | base64 -d > raw/current/{hk_current.xlsx,jp_current.xlsx,de_current.xlsx,uk_current.xlsx,asx_current.csv}
# HKEX delisted name list: fetch https://di.hkex.com.hk/di/NSDelistedStockList.aspx?lang=EN (3 pages) → transcribe to raw/hk/hkex_delisted.txt
```

The `scripts/build_dataset.py` pipeline is deterministic: it re-reads `raw/` + `data/curated/` and
regenerates `data/delisted_equity_data.json` and `data/delisted_equity_data.xlsx`.
