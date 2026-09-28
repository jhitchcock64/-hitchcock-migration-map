"""
Living people: hidden in the public data, readable with the family password.

The site is public (GitHub Pages). Everyone living -- born within the last
100 years with no death record in the tree, or, with no birth year, within
four generations of the root -- is published as "Private": no name, surname,
birth year or place text in GRAPH, no entry in SEARCH_INDEX, and "Private"
in the name lists on ROUTES. Their moves still draw (James, 2026-09-27:
"show lines, no names"). Their real details go into PRIVATE, encrypted with
the family password; the page's Unlock control decrypts it in the browser
and puts them back.

Encryption (all standard library; the browser uses WebCrypto):
  key material = PBKDF2-HMAC-SHA256(password, SALT, 600,000 iterations, 64 bytes)
  first 32 bytes: AES-256 key (CTR mode, 64-bit counter); last 32: HMAC-SHA256 key
  iv = HMAC(mac key, plaintext)[:8] + 8 zero bytes (deterministic, so the same
       data gives the same data.js; a different plaintext gets a different iv)
  PRIVATE = {v: 1, iter, salt, iv, ct, mac} (base64); mac = HMAC(mac key, iv + ct)

The password comes from the HM_PASSPHRASE environment variable and is never
written to any file. Without it write_data_js.py refuses to write data.js.
"""
import base64, hashlib, hmac, json, os, re
from collections import deque

SALT = hashlib.sha256(b'hitchcock-map private data v1').digest()[:16]
ITER = 600_000
LIVING_BORN_FROM = 1926          # 100 years before the root's birth


def _year(s):
    m = re.search(r'(1[5-9]\d\d|20[0-2]\d)', s or '')
    return int(m.group(1)) if m else None


def living_ids(graph, indi):
    """Ids in GRAPH treated as living."""
    P = graph['people']
    gen = {graph['james_id']: 0}
    q = deque([graph['james_id']])
    while q:
        x = q.popleft()
        for p in P[x]['parents']:
            if p in P and p not in gen: gen[p] = gen[x] + 1; q.append(p)
    out = set()
    for pid in P:
        i = indi.get(pid, {})
        if i.get('deat_date') or i.get('deat_plac'): continue
        by = _year(i.get('birt_date')) or P[pid].get('by')
        if (by and by >= LIVING_BORN_FROM) or (by is None and gen.get(pid, 0) <= 4):
            out.add(pid)
    return out


def redact(arrays, living):
    """Blank the living in the arrays, in place. Returns what was taken out."""
    P = arrays['GRAPH']['people']
    names = {P[pid]['name'] for pid in living}
    private = {'graph': {}, 'search': [], 'routes': {}}
    for pid in living:
        private['graph'][pid] = dict(P[pid])
        P[pid] = dict(P[pid], name='Private', surname='', by=None, bplace=None)
        P[pid].pop('fplace', None)
    keep = []
    for i, s in enumerate(arrays['SEARCH_INDEX']):
        (private['search'].append([i, s]) if s['id'] in living else keep.append(s))
    arrays['SEARCH_INDEX'][:] = keep
    for i, r in enumerate(arrays['ROUTES']):
        took = {}
        for k in ('people', 'family_group'):
            if r.get(k) and any(n in names for n in r[k]):
                took[k] = r[k]
                r[k] = ['Private' if n in names else n for n in r[k]]
        if took: private['routes'][str(i)] = took
    return private


def redact_profiles(profiles, living, private):
    """Profiles (build_profiles.py): the living's go into private['profiles'];
    a living child or spouse named in someone else's profile (on the map or
    not, marked lv by build_profiles) is published as {lv: 1} (and i, if
    on the map), with the full family list in private['pfam']."""
    people = profiles['people']
    private['profiles'] = {pid: people.pop(pid) for pid in sorted(living) if pid in people}
    private['pfam'] = {}
    private['psib'] = {}
    for pid, pr in people.items():
        if any(c.get('lv') or c.get('i') in living for c in pr.get('sb', [])):
            private['psib'][pid] = pr['sb']
            pr['sb'] = [_blank(c, living) for c in pr['sb']]
        hit = False
        for f in pr['f']:
            for c in f['k'] + ([f['sp']] if 'sp' in f else []):
                if c.get('lv') or c.get('i') in living: hit = True
        if hit:
            private['pfam'][pid] = pr['f']
            pr['f'] = [dict(f, **({'sp': _blank(f['sp'], living)} if 'sp' in f else {}),
                            k=[_blank(c, living) for c in f['k']]) for f in pr['f']]
    return private


def _blank(c, living):
    if not (c.get('lv') or c.get('i') in living): return c
    return {'lv': 1, **({'i': c['i']} if c.get('i') else {})}


# ---------------------------------------------------------------- AES-256 (encryption only; CTR needs no decrypt)
_SBOX = [0] * 256
def _init_sbox():
    p = q = 1
    while True:                  # generate the S-box from the multiplicative inverse (FIPS-197 5.1.1)
        p = p ^ ((p << 1) & 0xff) ^ (0x1b if p & 0x80 else 0)
        q ^= q << 1; q ^= q << 2; q ^= q << 4; q &= 0xff
        if q & 0x80: q ^= 0x09
        x = q ^ ((q << 1) | (q >> 7)) & 0xff ^ ((q << 2) | (q >> 6)) & 0xff ^ ((q << 3) | (q >> 5)) & 0xff ^ ((q << 4) | (q >> 4)) & 0xff
        _SBOX[p] = (x ^ 0x63) & 0xff
        if p == 1: break
    _SBOX[0] = 0x63
_init_sbox()


def _xt(a): return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else a << 1


def _expand(key):
    nk, nr = len(key) // 4, len(key) // 4 + 6
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    rcon = 1
    for i in range(nk, 4 * (nr + 1)):
        t = list(w[i - 1])
        if i % nk == 0:
            t = [_SBOX[b] for b in t[1:] + t[:1]]; t[0] ^= rcon; rcon = _xt(rcon)
        elif nk > 6 and i % nk == 4:
            t = [_SBOX[b] for b in t]
        w.append([a ^ b for a, b in zip(w[i - nk], t)])
    return [sum(w[4 * r:4 * r + 4], []) for r in range(nr + 1)]


def _encrypt_block(rk, block):
    s = [b ^ k for b, k in zip(block, rk[0])]
    for r in range(1, len(rk)):
        s = [_SBOX[b] for b in s]
        s = [s[(i + 4 * (i % 4)) % 16] for i in range(16)]          # ShiftRows (column-major state)
        if r != len(rk) - 1:
            m = []
            for c in range(4):
                a = s[4 * c:4 * c + 4]; t = a[0] ^ a[1] ^ a[2] ^ a[3]
                m += [a[j] ^ t ^ _xt(a[j] ^ a[(j + 1) % 4]) for j in range(4)]
            s = m
        s = [b ^ k for b, k in zip(s, rk[r])]
    return bytes(s)


def _ctr(key, iv, data):
    rk = _expand(key)
    hi, lo = iv[:8], int.from_bytes(iv[8:], 'big')
    out = bytearray()
    for n in range(0, len(data), 16):
        ks = _encrypt_block(rk, hi + ((lo + n // 16) % 2 ** 64).to_bytes(8, 'big'))
        out += bytes(a ^ b for a, b in zip(data[n:n + 16], ks))
    return bytes(out)


def _selftest():
    # FIPS-197 appendix C.3 (AES-256)
    k = bytes(range(32)); pt = bytes.fromhex('00112233445566778899aabbccddeeff')
    assert _encrypt_block(_expand(k), pt).hex() == '8ea2b7ca516745bfeafc49904b496089', 'AES self-test failed'


def encrypt(obj, password):
    _selftest()
    km = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), SALT, ITER, 64)
    ek, mk = km[:32], km[32:]
    pt = json.dumps(obj, separators=(',', ':'), ensure_ascii=False, sort_keys=True).encode('utf-8')
    iv = hmac.new(mk, pt, 'sha256').digest()[:8] + bytes(8)
    ct = _ctr(ek, iv, pt)
    mac = hmac.new(mk, iv + ct, 'sha256').digest()
    b = lambda x: base64.b64encode(x).decode()
    return {'v': 1, 'iter': ITER, 'salt': b(SALT), 'iv': b(iv), 'ct': b(ct), 'mac': b(mac)}


def decrypt(blob, password):
    """For tests: the inverse of encrypt()."""
    d = lambda k: base64.b64decode(blob[k])
    km = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), d('salt'), blob['iter'], 64)
    if not hmac.compare_digest(hmac.new(km[32:], d('iv') + d('ct'), 'sha256').digest(), d('mac')):
        raise ValueError('wrong password')
    return json.loads(_ctr(km[:32], d('iv'), d('ct')))


def password():
    pw = os.environ.get('HM_PASSPHRASE')
    if not pw:
        raise SystemExit('HM_PASSPHRASE is not set: the family password encrypts living people\'s details '
                         '(see pipeline/project/privacy.py). Set it for this session and run again.')
    return pw
