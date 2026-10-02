"""
Runs every question in tools/ask_questions.txt through the Ask page (index.html) in headless
Chromium and sorts the answers: ANSWERED, CHOICE (asked "which one?"), NOT FOUND (a name it
couldn't find), NOT UNDERSTOOD, ERROR.

Usage:  python tools/check_ask.py [--all]      (--all prints every answer, not just the misses)
With HM_PASSPHRASE set, it unlocks the living and asks as James; otherwise as a grandchild of
Albert Carl Hitchcock (one line only). The password is only read from the environment.
"""
import os, sys, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
QS = [l.strip() for l in open(ROOT / 'tools' / 'ask_questions.txt', encoding='utf-8') if l.strip() and not l.startswith('#')]
show_all = '--all' in sys.argv

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    errors = []; pg.on('pageerror', lambda e: errors.append(str(e)[:300]))
    pg.goto((ROOT / 'index.html').as_uri())
    pg.wait_for_function("typeof Ask !== 'undefined'")
    pg.evaluate("Ask.load()")
    pw = os.environ.get('HM_PASSPHRASE')
    if pw:
        pg.click('#lock-slot .lock-btn'); pg.fill('#lock-slot input', pw); pg.press('#lock-slot input', 'Enter')
        pg.wait_for_function("Family.shown", timeout=30000)
        pg.wait_for_timeout(1500)
        who = pg.evaluate("(async () => { await Ask.load(); const k = RELATIVES.n.indexOf('James Albert Hitchcock'); await Ask.setMe(k, 0); return RELATIVES.n[k]; })()")
    else:
        who = pg.evaluate("(async () => { await Ask.load(); const k = RELATIVES.n.findIndex(n => n.startsWith('Albert Carl Hitchcock')); await Ask.setMe(k, 2); return 'a grandchild of ' + RELATIVES.n[k]; })()")
    print('asking as', who, '\n')
    rows = []
    for q in QS:
        try:
            html = pg.evaluate("q => Ask.answer(q)", q)
            text = pg.evaluate("h => { const d = document.createElement('div'); d.innerHTML = h; return d.innerText.replace(/\\s+/g, ' ').trim(); }", html)
        except Exception as e:
            rows.append(('ERROR', q, str(e)[:200])); continue
        kind = ('NOT UNDERSTOOD' if text.startswith('I didn’t understand') else
                'NOT FOUND' if text.startswith('I couldn’t find') else
                'CHOICE' if text.startswith('Which one do you mean') else 'ANSWERED')
        rows.append((kind, q, text))
    b.close()

from collections import Counter
c = Counter(k for k, _, _ in rows)
for kind in ['ERROR', 'NOT UNDERSTOOD', 'NOT FOUND', 'CHOICE', 'ANSWERED']:
    if kind == 'ANSWERED' and not show_all: continue
    sel = [r for r in rows if r[0] == kind]
    if sel: print(f'== {kind} ({len(sel)})')
    for _, q, t in sel: print(f'  {q}\n      {t[:170]}')
print('\n' + ', '.join(f'{k}: {n}' for k, n in c.most_common()), f'of {len(rows)}')
if errors: print('page errors:', errors[:5])
