#!/usr/bin/env python3
"""
Build the cross-market delisted equity dataset.

Sources (see README.md for full provenance):
  US  : royelee/delist-detection (SEC EDGAR Form 25/15 based, 2008-2026) + curated pre-2008
  HK  : HKEX official "List of Stock Names (Delisted companies)"
  JP  : nogamoga/jp-delisted-codes (2015-2026) + learningihara1-arch DB (2023-2026, names/reasons)
        + delisting.info year tables (1990-2022 where available) + curated
  KR  : kt3472/kospi_delisted raw_data.xlsx (Target==1 delisted sample)
  CA/UK/DE/FR/NL/CH/AU/CN/IN : curated lists (data/curated/*.json)

Outputs:
  data/delisted_equity_data.json
  data/delisted_equity_data.xlsx
"""
import json, os, re, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw')
CUR = os.path.join(ROOT, 'data', 'curated')
OUT = os.path.join(ROOT, 'data')

# ----------------------------------------------------------------------------
# 1. CURRENT-TICKER LOOKUPS (for the "is the ticker recycled today?" question)
# ----------------------------------------------------------------------------

def load_us_current():
    m = {}
    for f, exch in [('us_nyse_full.json', 'NYSE'),
                    ('us_nasdaq_full.json', 'NASDAQ'),
                    ('us_amex_full.json', 'NYSE American')]:
        p = os.path.join(RAW, 'current', f)
        if not os.path.exists(p):
            continue
        for r in json.load(open(p, encoding='utf-8')):
            sym = (r.get('symbol') or '').strip()
            name = re.sub(r'\s*Common Stock\s*$', '', (r.get('name') or '').strip())
            if sym:
                m[sym.upper()] = (name, exch)
    return m

def load_hk_current():
    p = os.path.join(RAW, 'current', 'hk_current.xlsx')
    df = pd.read_excel(p, header=2)
    m = {}
    for _, r in df.iterrows():
        cat = str(r.get('Category', ''))
        sub = str(r.get('Sub-Category', ''))
        if 'Equity' in cat and ('Main Board' in sub or 'GEM' in sub or 'Equity' in sub):
            code = str(r.get('Stock Code', '')).strip()
            if code.isdigit():
                m[code.zfill(5)] = str(r.get('Name of Securities', '')).strip()
    return m

def load_jp_current():
    p = os.path.join(RAW, 'current', 'jp_current.xlsx')
    df = pd.read_excel(p)
    m = {}
    for _, r in df.iterrows():
        code = str(r.get('Local Code', '')).strip()
        if code and code not in ('nan', '-'):
            m[code] = str(r.get('Name (English)', '')).strip()
    return m

def load_de_current():
    p = os.path.join(RAW, 'current', 'de_current.xlsx')
    m = {}
    sheets = pd.read_excel(p, sheet_name=None, header=None)
    for name, df in sheets.items():
        if name == 'Cover':
            continue
        # find header row containing 'Trading Symbol'
        hdr = None
        for i in range(min(12, len(df))):
            row = [str(x) for x in df.iloc[i].tolist() if pd.notna(x)]
            if any('Trading Symbol' in c for c in row):
                hdr = i
                break
        if hdr is None:
            continue
        cols = df.iloc[hdr].tolist()
        ci = {str(c): j for j, c in enumerate(cols) if pd.notna(c)}
        js = ci.get('Trading Symbol'); jc = ci.get('Company')
        if js is None or jc is None:
            continue
        for i in range(hdr + 1, len(df)):
            sym = df.iat[i, js]
            comp = df.iat[i, jc]
            if pd.notna(sym) and pd.notna(comp) and str(sym).strip() not in ('', '-'):
                m[str(sym).strip().upper()] = str(comp).strip()
    return m

def load_uk_current():
    p = os.path.join(RAW, 'current', 'uk_current.xlsx')
    df = pd.read_excel(p, sheet_name='1.0 All Equity', header=None)
    m = {}
    # locate header row with 'Ticker'
    hdr = None
    for i in range(min(12, len(df))):
        row = [str(x) for x in df.iloc[i].tolist() if pd.notna(x)]
        if any(x.strip().lower() == 'ticker' for x in row):
            hdr = i
            break
    if hdr is None:
        return m
    cols = [str(c).strip() if pd.notna(c) else '' for c in df.iloc[hdr].tolist()]
    it = cols.index('Ticker'); iname = cols.index('Name')
    for i in range(hdr + 1, len(df)):
        t = df.iat[i, it]; n = df.iat[i, iname]
        if pd.notna(t) and pd.notna(n) and str(t).strip():
            m[str(t).strip().upper()] = str(n).strip()
    return m

def load_au_current():
    p = os.path.join(RAW, 'current', 'asx_current.csv')
    df = pd.read_csv(p)
    m = {}
    for _, r in df.iterrows():
        code = str(r.get('ASX code', '')).strip().upper()
        if code:
            m[code] = str(r.get('Company name', '')).strip()
    return m

# ----------------------------------------------------------------------------
# 2. DELISTED RECORDS
# ----------------------------------------------------------------------------

def rec(market, exchange, ticker, name, date=None, dtype=None, notes='', source=''):
    return dict(market=market, exchange=exchange, ticker=ticker, company_name=name,
                delisting_date=date, delisting_type=dtype, notes=notes, source=source)

def parse_us():
    out = []
    cls = pd.read_csv(os.path.join(RAW, 'us', 'delist_classifications.csv'))
    dl = pd.read_csv(os.path.join(RAW, 'us', 'dlret.csv'))
    wx = pd.read_csv(os.path.join(RAW, 'us', 'web_verification.csv'))
    dl = dl.set_index('ticker'); wx = wx.set_index('ticker')
    bmap = {'merger': 'Merger / acquisition (taken private or acquired)',
            'exchange_transfer': 'Exchange transfer (delisted from one exchange, listed on another)',
            'compliance_failure': 'Delisting for non-compliance / failed listing standards',
            'liquidation': 'Bankruptcy / liquidation / voluntary deregistration',
            'expiration': 'Fund / other expiration'}
    src = 'https://github.com/royelee/delist-detection (SEC EDGAR Form 25/15 analysis)'
    for _, r in cls.iterrows():
        t = r['ticker']
        name = re.sub(r'\s*\(CIK \d+\)\s*$', '', str(r['resolved_name'])).strip()
        name = re.sub(r'\s+', ' ', name).title() if name.upper().isupper() else name
        exch = str(dl.loc[t, 'exchange']).capitalize() if t in dl.index else ''
        date = r['observed_delist_date']
        fdate = r.get('delist_filing_date')
        d = rec('US', exch if exch not in ('Other', 'nan') else 'US exchange', t, name,
                date=str(date), dtype=bmap.get(r['bucket'], str(r['bucket'])),
                notes=(f"CIK {str(r['cik']).zfill(10)}; form {r['delist_filing_form']} filed {fdate}; "
                       f"payout ${r['payout_per_share']}" if t in dl.index and pd.notna(dl.loc[t, 'payout_per_share'])
                       else f"CIK {str(r['cik']).zfill(10)}; form {r['delist_filing_form']} filed {fdate}"),
                source=src)
        if t in wx.index and pd.notna(wx.loc[t, 'former_names']):
            d['notes'] += f"; former name: {wx.loc[t, 'former_names']}"
        out.append(d)
    return out

def parse_hk():
    out = []
    src = 'https://di.hkex.com.hk/di/NSDelistedStockList.aspx?lang=EN (HKEX official delisted stock name list)'
    for line in open(os.path.join(RAW, 'hk', 'hkex_delisted.txt'), encoding='utf-8'):
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 2:
            continue
        code, name = parts[0].strip(), parts[1].strip()
        if not code:
            continue
        out.append(rec('HK', 'HKEX', code.zfill(5), name,
                       notes='Delisting date not provided by source (list covers all delisted HK stocks, some pre-1990)',
                       source=src))
    return out

def parse_jp():
    out = []
    src_n = 'https://github.com/nogamoga/jp-delisted-codes (annual delisting codes, JPX)'
    src_l = 'https://github.com/learningihara1-arch/japan-delisted-companies-database (delisting DB 2023-2026)'
    names = {}
    reasons = {}
    try:
        for j in json.load(open(os.path.join(RAW, 'jp', 'jp_delisted_rows.json'), encoding='utf-8')):
            names[str(j['code']).zfill(4)] = j['name']
            reasons[str(j['code']).zfill(4)] = j.get('reasonCategory', '')
    except Exception:
        pass
    for y in range(2015, 2027):
        p = os.path.join(RAW, 'jp', f'nogamoga_{y}.json')
        if not os.path.exists(p):
            continue
        for j in json.load(open(p, encoding='utf-8')):
            code = str(j['code']).zfill(4)
            d = j.get('date', '')
            rmap = {'他社による買収': 'Acquisition by another company (take-private)',
                    '支配株主等による買収': 'Acquisition by controlling shareholder (take-private)',
                    'ＭＢＯ': 'Management buyout (MBO)',
                    '子会社化': 'Becoming a subsidiary',
                    '他社による買収（公開買付け、株式併合）': 'Acquisition (tender offer / share exchange)',
                    'ＭＢＯ（公開買付け、株式併合）': 'MBO (tender offer / share exchange)',
                    '上場維持基準への不適合': 'Failed to meet listing maintenance standards',
                    '内部管理体制不適切': 'Internal control deficiencies',
                    '前澤ホールディングスの完全子会社化': 'Fully acquired by Maetsu Holdings'}
            out.append(rec('JP', 'TSE/JPX', code, names.get(code, ''),
                           date=d,
                           dtype=rmap.get(reasons.get(code, ''), 'Delisted (type unknown for 2015-2022 codes)'),
                           notes=('Name from delisting DB' if code in names else 'Name not resolved from available sources'),
                           source=(src_l if code in names else src_n)))
    # dedupe by (code, date)
    seen = set(); res = []
    for d in out:
        k = (d['ticker'], d['delisting_date'])
        if k in seen:
            continue
        seen.add(k); res.append(d)
    return res

def parse_kr():
    out = []
    p = os.path.join(RAW, 'kr', 'raw_data.xlsx')
    df = pd.read_excel(p)
    df = df[df['Target'] == 1]
    src = 'https://github.com/kt3472/kospi_delisted (KOSPI delisted company dataset)'
    for _, r in df.iterrows():
        sym = str(r['Symbol']).strip()
        code = sym[1:] if re.match(r'^[A-Z]\d+$', sym) else sym
        fy = r.get('회계년')
        out.append(rec('KR', 'KRX (KOSPI)', code, str(r['Name']).strip(),
                       date=(f"{int(fy)} (approx. — last fiscal year in source)" if pd.notna(fy) else None),
                       dtype='Delisted (delisting year approximated from last fiscal year in source)',
                       source=src))
    return out

def parse_curated():
    out = []
    if os.path.isdir(CUR):
        for f in sorted(os.listdir(CUR)):
            if f.endswith('.json'):
                for d in json.load(open(os.path.join(CUR, f), encoding='utf-8')):
                    d.setdefault('notes', '')
                    d.setdefault('source', 'Curated from public sources (see README.md)')
                    out.append(d)
    return out

# ----------------------------------------------------------------------------
# 3. REUSE CHECK
# ----------------------------------------------------------------------------

def current_map_for(market):
    return {'US': load_us_current(), 'HK': load_hk_current(), 'JP': load_jp_current(),
            'DE': load_de_current(), 'UK': load_uk_current(), 'AU': load_au_current()}

# dates of the current-listing snapshots used for the recycle check
LIST_DATES = {'US': '2026-08-28', 'HK': '2025-06-30', 'JP': '2024-06-28',
              'DE': '2024-10-01', 'UK': '2022-11-30', 'AU': '2025-06-07'}

def norm_name(s):
    s = re.sub(r'[^a-z0-9 ]', '', str(s).lower())
    return ' '.join(s.split())

def check_reuse(records, cmaps):
    for d in records:
        cm = cmaps.get(d['market'])
        t = str(d['ticker']).strip().upper()
        if cm is None:
            d['ticker_recycled'] = 'unknown'; d['current_company_name'] = ''
            continue
        key = t
        if d['market'] == 'HK':
            key = t.zfill(5)
        if d['market'] == 'JP':
            key = t.zfill(4)
        # temporal guard: only meaningful when delisting happened before the list snapshot
        dy = str(d.get('delisting_date') or '')[:4]
        if dy.isdigit() and int(dy) >= int(LIST_DATES[d['market']][:4]):
            d['ticker_recycled'] = 'unknown'
            d['current_company_name'] = ''
            d['notes'] = (d.get('notes') + ' | ' if d.get('notes') else '') + \
                f"delisted on/after current-list snapshot {LIST_DATES[d['market']]}; recycle status not verifiable"
            continue
        if key in cm:
            cur_name = cm[key] if isinstance(cm[key], str) else cm[key][0]
            d['current_company_name'] = cur_name
            same = norm_name(cur_name)[:20] and norm_name(cur_name) and \
                   (norm_name(cur_name) in norm_name(d.get('company_name')) or
                    norm_name(d.get('company_name')) in norm_name(cur_name))
            if same:
                d['ticker_recycled'] = 'yes'
                d['notes'] = (d.get('notes') + ' | ' if d.get('notes') else '') + \
                    f'ticker in use as of {LIST_DATES[d["market"]]} by the same (or renamed) company'
            else:
                d['ticker_recycled'] = 'yes'
        else:
            d['ticker_recycled'] = 'no'
            d['current_company_name'] = ''
    return records

# ----------------------------------------------------------------------------
# 4. MAIN
# ----------------------------------------------------------------------------

def main():
    os.makedirs(OUT, exist_ok=True)
    records = []
    records += parse_us()
    records += parse_hk()
    records += parse_jp()
    records += parse_kr()
    records += parse_curated()
    # fill JP names for code-only records from any named JP record (curated/DB)
    jp_names = {}
    for d in records:
        if d['market'] == 'JP' and d.get('company_name'):
            jp_names[str(d['ticker']).zfill(4)] = d['company_name']
    for d in records:
        if d['market'] == 'JP' and not d.get('company_name'):
            nm = jp_names.get(str(d['ticker']).zfill(4))
            if nm:
                d['company_name'] = nm
                d['notes'] = (d.get('notes') + ' | ' if d.get('notes') else '') + 'name filled from curated/DB entry with same code'
    # normalize
    for d in records:
        for k in ['market', 'exchange', 'ticker', 'company_name', 'delisting_date',
                  'delisting_type', 'notes', 'source']:
            if d.get(k) is None:
                d[k] = ''
    cmaps = {k: v for k, v in current_map_for('x').items() if v}
    check_reuse(records, cmaps)

    # dedupe exact rows
    seen = set(); uniq = []
    for d in records:
        k = (d['market'], d['ticker'], d['delisting_date'], d['company_name'])
        if k in seen:
            continue
        seen.add(k); uniq.append(d)
    uniq.sort(key=lambda d: (d['market'], d['ticker'], str(d['delisting_date'])))

    df = pd.DataFrame(uniq, columns=['market', 'exchange', 'ticker', 'company_name',
                                     'delisting_date', 'delisting_type', 'ticker_recycled',
                                     'current_company_name', 'notes', 'source'])

    # JSON
    meta = {
        'title': 'Delisted equity tickers and company names, 13 markets, since 1990 (best-effort)',
        'generated_at': '2026-08-28',
        'markets': sorted(set(df['market'])),
        'record_count': len(df),
        'columns': list(df.columns),
        'coverage_notes': {
            'US': '2008-2026: 461 tickers from SEC EDGAR Form 25/15 analysis (royelee/delist-detection) with type, date, exchange, CIK. 1990-2007: curated notable delistings. A truly exhaustive US list since 1990 requires licensed CRSP/Compustat data.',
            'HK': 'Complete official HKEX delisted stock name list (all delisted stocks ever; delisting dates not published in the source list).',
            'JP': '2015-2026: official annual delisting codes (JPX); names/reasons for 2023-2026 from delisting DB; 1990-2022 notable delistings from delisting.info year tables and curated lists. Excludes routine exchange-transfer delistings for pre-2015.',
            'KR': '374 delisted KOSPI companies (1994-2018 fiscal-year based dataset); delisting year approximated from last fiscal year in source.',
            'CA': 'Curated notable delistings since 1990.',
            'UK': 'Curated notable delistings since 1990.',
            'DE': 'Curated notable delistings since 1990.',
            'FR': 'Curated notable delistings since 1990.',
            'NL': 'Curated notable delistings since 1990.',
            'CH': 'Curated notable delistings since 1990.',
            'AU': 'Curated notable delistings since 1990.',
            'CN': 'Curated A-share delistings (emphasizing 2015-2025 wave) plus sourced 2022 lists.',
            'IN': 'Curated notable NSE/BSE delistings with dates where known, plus a sourced undated NSE delisted symbol list.',
        },
        'ticker_reuse_notes': {
            'US': 'Checked against auto-updated NASDAQ/NYSE/NYSE American symbol files (rreichel3/US-Stock-Symbols).',
            'HK': 'Checked against HKEX List of Securities (30 Jun 2025).',
            'JP': 'Checked against JPX security code list (Jun 2024).',
            'DE': 'Checked against Deutsche Boerse listed company sheets (Oct 2024).',
            'UK': 'Checked against LSE instrument list (30 Nov 2022).',
            'AU': 'Checked against ASX listed companies list (7 Jun 2025).',
            'CA/FR/NL/CH/CN/HK-old/IN/KR': 'No complete current-listing reference available in this environment; marked "unknown".',
        },
    }
    with open(os.path.join(OUT, 'delisted_equity_data.json'), 'w', encoding='utf-8') as f:
        json.dump({'metadata': meta, 'records': df.to_dict(orient='records')}, f, ensure_ascii=False, indent=1)

    # XLSX
    write_xlsx(df, meta)
    print('total records:', len(df))
    print(df.groupby('market').size().to_string())

def write_xlsx(df, meta):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = Workbook()
    thin = Border(*[Side(style='thin', color='D0D0D0')]*4)
    hdr_fill = PatternFill('solid', fgColor='1F3864')
    hdr_font = Font(color='FFFFFF', bold=True, size=11)

    def style_sheet(ws, headers, widths, n_rows):
        for j, (h, w) in enumerate(zip(headers, widths), 1):
            c = ws.cell(row=1, column=j, value=h)
            c.fill, c.font = hdr_fill, hdr_font
            c.alignment = Alignment(vertical='center', wrap_text=True)
            ws.column_dimensions[get_column_letter(j)].width = w
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{n_rows+1}"
        for i in range(2, n_rows + 2):
            for j in range(1, len(headers) + 1):
                c = ws.cell(row=i, column=j)
                c.border = thin
                if i % 2 == 0:
                    c.fill = PatternFill('solid', fgColor='F2F5FA')

    COLS = ['market', 'exchange', 'ticker', 'company_name', 'delisting_date', 'delisting_type',
            'ticker_recycled', 'current_company_name', 'notes', 'source']
    HEADERS = ['Market', 'Exchange', 'Ticker', 'Company name (at delisting)', 'Delisting date',
               'Delisting type', 'Ticker recycled today?', 'Current company using ticker', 'Notes', 'Source']
    WIDTHS = [9, 16, 14, 38, 26, 42, 15, 34, 46, 44]

    # README sheet
    ws = wb.active; ws.title = 'README'
    ws.column_dimensions['A'].width = 30; ws.column_dimensions['B'].width = 110
    ws['A1'] = 'Delisted equity tickers — 13 markets, since 1990 (best-effort)'; ws['A1'].font = Font(bold=True, size=14)
    row = 3
    ws.cell(row=row, column=1, value='Generated').font = Font(bold=True); ws.cell(row=row, column=2, value=meta['generated_at']); row += 1
    ws.cell(row=row, column=1, value='Records').font = Font(bold=True); ws.cell(row=row, column=2, value=str(meta['record_count'])); row += 2
    ws.cell(row=row, column=1, value='Coverage by market').font = Font(bold=True, size=12); row += 1
    for m, note in meta['coverage_notes'].items():
        ws.cell(row=row, column=1, value=m).font = Font(bold=True)
        c = ws.cell(row=row, column=2, value=note); c.alignment = Alignment(wrap_text=True, vertical='top')
        row += 1
    row += 1
    ws.cell(row=row, column=1, value='Ticker-recycle checks').font = Font(bold=True, size=12); row += 1
    for m, note in meta['ticker_reuse_notes'].items():
        ws.cell(row=row, column=1, value=m).font = Font(bold=True)
        c = ws.cell(row=row, column=2, value=note); c.alignment = Alignment(wrap_text=True, vertical='top')
        row += 1

    # All sheet
    ws = wb.create_sheet('All delisted')
    for j, h in enumerate(HEADERS, 1):
        ws.cell(row=1, column=j, value=h)
    for i, (_, r) in enumerate(df.iterrows(), 2):
        for j, c in enumerate(COLS, 1):
            v = r[c]
            ws.cell(row=i, column=j, value=('' if pd.isna(v) else v))
    style_sheet(ws, HEADERS, WIDTHS, len(df))

    # per-market sheets
    for m in sorted(df['market'].unique()):
        sub = df[df['market'] == m]
        ws = wb.create_sheet(f'{m} ({len(sub)})'.replace('/', '-'))
        for j, h in enumerate(HEADERS, 1):
            ws.cell(row=1, column=j, value=h)
        for i, (_, r) in enumerate(sub.iterrows(), 2):
            for j, c in enumerate(COLS, 1):
                v = r[c]
                ws.cell(row=i, column=j, value=('' if pd.isna(v) else v))
        style_sheet(ws, HEADERS, WIDTHS, len(sub))

    # recycle overview
    ws = wb.create_sheet('Recycled tickers')
    sub = df[(df['ticker_recycled'] == 'yes') & (df['current_company_name'] != '')]
    rc = ['market', 'ticker', 'company_name', 'delisting_date', 'current_company_name']
    rh = ['Market', 'Ticker', 'Former company', 'Delisting date', 'Current company']
    for j, h in enumerate(rh, 1):
        ws.cell(row=1, column=j, value=h)
    for i, (_, r) in enumerate(sub.sort_values(['market', 'ticker']).iterrows(), 2):
        for j, c in enumerate(rc, 1):
            v = r[c]
            ws.cell(row=i, column=j, value=('' if pd.isna(v) else v))
    style_sheet(ws, rh, [9, 14, 38, 26, 38], len(sub))

    wb.save(os.path.join(OUT, 'delisted_equity_data.xlsx'))

if __name__ == '__main__':
    main()
