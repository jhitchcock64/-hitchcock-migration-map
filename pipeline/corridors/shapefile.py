"""
Minimal readers for ESRI shapefiles (polylines) and their .dbf tables, plus
the inverse of the Albers equal-area projection -- enough for the railroad
and road data used by build_network.py, with the standard library only.
"""
import math, struct, zipfile


def read_dbf(data):
    """-> list of dicts (strings stripped; numbers as float/int where possible)."""
    n = struct.unpack('<I', data[4:8])[0]
    hlen, rlen = struct.unpack('<HH', data[8:12])
    fields, pos = [], 32
    while data[pos] != 0x0D:
        name = data[pos:pos + 11].split(b'\0')[0].decode('latin-1')
        ftype, flen, fdec = chr(data[pos + 11]), data[pos + 16], data[pos + 17]
        fields.append((name, ftype, flen, fdec)); pos += 32
    rows = []
    for i in range(n):
        off = hlen + i * rlen + 1          # skip the deletion flag
        rec = {}
        for name, ftype, flen, fdec in fields:
            raw = data[off:off + flen]; off += flen
            v = raw.decode('utf-8', 'replace').strip()
            if ftype in 'NF':
                try: v = float(v) if (fdec or '.' in v) else int(v)
                except ValueError: v = None
            rec[name] = v
        rows.append(rec)
    return rows


def read_polylines(data):
    """-> list of parts lists (each part a list of (x, y)), one entry per record."""
    out, pos = [], 100
    while pos < len(data):
        _, clen = struct.unpack('>II', data[pos:pos + 8]); pos += 8
        rec = data[pos:pos + clen * 2]; pos += clen * 2
        st = struct.unpack('<i', rec[:4])[0]
        if st == 0: out.append([]); continue
        if st not in (3, 13, 23): raise ValueError(f'shape type {st} is not a polyline')
        nparts, npts = struct.unpack('<ii', rec[36:44])
        parts = list(struct.unpack(f'<{nparts}i', rec[44:44 + 4 * nparts])) + [npts]
        base = 44 + 4 * nparts
        xy = struct.unpack(f'<{2 * npts}d', rec[base:base + 16 * npts])
        pts = list(zip(xy[0::2], xy[1::2]))
        out.append([pts[parts[k]:parts[k + 1]] for k in range(nparts)])
    return out


def read_zip(path, stem):
    """(records, polylines) of <stem>.dbf / <stem>.shp inside a zip."""
    z = zipfile.ZipFile(path)
    return read_dbf(z.read(stem + '.dbf')), read_polylines(z.read(stem + '.shp'))


class AlbersInverse:
    """Ellipsoidal Albers equal-area conic, inverse (Snyder, Map Projections, 1987, eq. 14-18ff)."""
    def __init__(self, lat0, lon0, lat1, lat2, a=6378137.0, f=1 / 298.257222101, x0=0.0, y0=0.0):
        self.a, self.e = a, math.sqrt(f * (2 - f)); self.lon0, self.x0, self.y0 = lon0, x0, y0
        e = self.e
        m = lambda p: math.cos(p) / math.sqrt(1 - (e * math.sin(p)) ** 2)
        self.q = lambda p: (1 - e * e) * (math.sin(p) / (1 - (e * math.sin(p)) ** 2)
                                          - 1 / (2 * e) * math.log((1 - e * math.sin(p)) / (1 + e * math.sin(p))))
        r = math.radians
        m1, m2 = m(r(lat1)), m(r(lat2)); q0, q1, q2 = self.q(r(lat0)), self.q(r(lat1)), self.q(r(lat2))
        self.n = (m1 * m1 - m2 * m2) / (q2 - q1)
        self.C = m1 * m1 + self.n * q1
        self.rho0 = a * math.sqrt(self.C - self.n * q0) / self.n

    def __call__(self, x, y):
        a, e, n = self.a, self.e, self.n
        x, y = x - self.x0, y - self.y0
        rho = math.hypot(x, self.rho0 - y)
        theta = math.atan2(x, self.rho0 - y) if n > 0 else math.atan2(-x, -(self.rho0 - y))
        q = (self.C - (rho * n / a) ** 2) / n
        phi = math.asin(max(-1, min(1, q / 2)))
        for _ in range(15):                  # iterate for latitude
            s = math.sin(phi)
            dphi = ((1 - (e * s) ** 2) ** 2 / (2 * math.cos(phi)) *
                    (q / (1 - e * e) - s / (1 - (e * s) ** 2) + 1 / (2 * e) * math.log((1 - e * s) / (1 + e * s))))
            phi += dphi
            if abs(dphi) < 1e-12: break
        return self.lon0 + math.degrees(theta / n), math.degrees(phi)
