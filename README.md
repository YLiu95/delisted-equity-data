# Delisted Equity Data — 13 Markets, Since 1990 (Exhaustive Best-Effort)

Cross-market dataset of **delisted equity tickers and the company names that used them**,
covering **US, Canada (CA), UK, Germany (DE), France (FR), Netherlands (NL), Switzerland (CH),
Australia (AU), China (CN, A-shares), Hong Kong (HK), Japan (JP), Korea (KR), India (IN)** since 1990.

For every record we answer:

1. **What ticker was delisted, and which company used it?**
2. **Is the ticker being recycled today?** — i.e. is it currently listed again, and if so by whom?

## Files

| File | Description |
|---|---|
| `data/delisted_equity_data.json` | Full dataset: metadata + one record per delisted ticker/company |
| `data/delisted_equity_data.xlsx` | Same data, formatted: README sheet, `All delisted`, one sheet per market, and a `Recycled tickers` overview |
| `data/curated/*.json` | Curated per-market delisting lists (source data for the "curated" records) |
| `scripts/build_dataset.py` | Rebuilds both outputs from raw sources + curated files |
| `SOURCES.md` | Provenance: every source, snapshot date, and how to re-derive raw inputs |

### Record fields

| Field | Meaning |
|---|---|
| `market` | US / CA / UK / DE / FR / NL / CH / AU / CN / HK / JP / KR / IN |
| `exchange` | Exchange where the ticker was delisted |
| `ticker` | Delisted ticker symbol |
| `company_name` | Company name **at the time of delisting** (empty only when no source resolved a name — see JP note) |
| `delisting_date` | `YYYY-MM-DD`, or `YYYY`, or `YYYY (approx. …)` where sources are imprecise; empty when the source publishes no date (HK) |
| `delisting_type` | Delisting type: merger/acquisition, take-private, bankruptcy/insolvency, failed listing standards (non-compliance), exchange transfer, voluntary deregistration, administration/compulsory purchase, listing move (re-list on another exchange), etc. |
| `ticker_recycled` | `yes` — ticker is listed today (name given in `current_company_name`); `no` — ticker not currently listed; `unknown` — no current-listing reference for that market, or delisted after the reference snapshot date |
| `current_company_name` | Today's company holding the recycled ticker (snapshot-dated) |
| `notes` | Provenance/verification caveats |
| `source` | Where the record came from |

## Coverage by market (best-effort, see also XLSX README sheet)

| Market | Records | Coverage |
|---|---|---|
| US | ~515 | 2008–2026: 461 tickers from an SEC EDGAR Form 25/15-based analysis (delisting date, type, exchange, CIK, payout). 1990–2008: curated notable delistings. A truly exhaustive US list since 1990 requires licensed CRSP/Compustat data — see "Limitations". |
| HK | ~795 | **Complete official HKEX delisted stock-name list** (all delisted HK stocks; the source publishes no delisting dates, and the list includes pre-1990 delistings). |
| JP | ~910 | 2015–2026: official annual delisting codes (JPX, with dates). Names+reasons for 2023–2026 from a delisting database; 1990–2022 notable delistings (bank-failure era, Yahoo! Japan, DMM, Nippon Sanso, Sanyo, Elpida …) curated. ⚠️ ~400 codes from 2015–2022 have no resolved company name (no free bulk name source reachable in this environment). |
| KR | 374 | Delisted KOSPI companies (dataset of delisted vs. listed; delisting year ≈ last fiscal year in source, 1994–2018). |
| UK | ~20 | Curated notable LSE delistings (BSkyB, Marconi, O2, GKN, John Lewis, M&G, Railtrack, …). |
| DE | ~7 | Curated notable Xetra delistings (Air Berlin, KUKA, Porsche AG, TUI AG, Villeroy & Boch, Wincor Nixdorf, Alcatel FSE listing). |
| FR | ~8 | Curated notable Euronext Paris delistings (GDF, Suez, Alcatel, M6, Lafarge, Parmalat Paris listing, …). |
| NL | ~3 | Curated notable Euronext Amsterdam delistings (Ahold, Unilever NV, Shell Dutch listing). |
| CH | ~5 | Curated notable SIX delistings (Credit Suisse, Actelion, Ciba, Landis+Gyr, Lonza). |
| AU | ~8 | Curated notable ASX delistings (Ansett, Sable, CSR, Linc, Aurelia, Vodafone Hutchison, Opus, Dragon Mining). |
| CN | ~34 | Curated A-share delistings: early era (Jinyu 2002), LeTV/Shenwu 2020, and the full 2022 delisting wave (24 entries from two sourced lists), plus 2023–2024 notables. A-shares delisted at a high rate 2019–2025; this list is a representative subset, not exhaustive. |
| IN | ~118 | Curated dated delistings (Reliance Broadcast, Cadbury India, Essar Oil, plus Moneycontrol-sourced BSE entries) + ~110 undated symbols/names from an NSE delisted-company list mirror (marked "verify"). |
| CA | ~11 | Curated notable TSX delistings (Alcan, Great West Lifeco, Hudson's Bay, Sable, Nexen, …). |

## Ticker-recycle checks ("is the ticker recycled today?")

`ticker_recycled` was computed against **current listing snapshots**:

| Market | Current-listing reference | Snapshot date |
|---|---|---|
| US | NASDAQ/NYSE/NYSE American symbol files (GitHub auto-updated mirror of NASDAQ Trader) | 2026-08-28 |
| HK | HKEX List of Securities | 2025-06-30 |
| JP | JPX security code list | 2024-06-28 |
| DE | Deutsche Börse Prime Standard / General Standard / Scale / Basic Board sheets | 2024-10-01 |
| UK | LSE instrument list (All Equity) | 2022-11-30 |
| AU | ASX listed companies list | 2025-06-07 |

Rules:

- A delisting that occurred **on/after the snapshot date** cannot be verified → `unknown`.
- If the ticker is in the current list under a **different name** → `yes`, and the current company is given (e.g. `WRD` WorldCom (2002) → today **WeRide Inc.**; HK `00700` YAOHAN INT'L → today **TENCENT**).
- If the ticker is in the current list under the **same (or a renamed) name** → `yes` with a note that the same (or renamed) company holds it.
- Markets without a reachable current-listing reference (CA, FR, NL, CH, CN, IN, KR) → `unknown`.

## Limitations (be honest about "exhaustive")

1. **US**: the 461-record EDGAR-based set is strong but is a sample of Form 25/15 filings analyzed by its author (2008–2026); the 1990–2008 period is curated-notable, not exhaustive. A complete US delisting file since 1990 (thousands of tickers) only exists in licensed databases (CRSP, Compustat, Norgate Data, Refinitiv) or paywalled scrapes.
2. **HK**: the official list has **no delisting dates**, so "since 1990" cannot be filtered server-side; pre-1990 delistings are included with that caveat.
3. **JP**: ~400 delisting **codes** (2015–2022) lack names — no free bulk code→name reference was reachable. Codes+dates are correct (JPX annual lists).
4. **KR**: delisting year is approximated from the last fiscal year in the source dataset (±1 year).
5. **CA/UK/DE/FR/NL/CH/AU/CN/IN**: curated "notable delistings" lists. Exchange-level exhaustive delisting registers for these markets are not published as free bulk downloads; entries flagged `verify` in `notes` should be double-checked before heavy reliance.
6. **Ticker reuse** is a point-in-time statement against the snapshot dates above; tickers can be re-issued later (especially in HK).

## Rebuild

```bash
pip install pandas openpyxl
python scripts/build_dataset.py   # reads raw/ + data/curated/, writes data/*.json and data/*.xlsx
```

Raw inputs live in `raw/` (git-ignored, ~15 MB); see `SOURCES.md` for exact files and URLs to re-derive them.

*Generated 2026-08-28.*
