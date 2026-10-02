// Site-wide "Viewing as" (James, 2026-10-02): who the visitor is, chosen once from a button in every
// page's header, remembered per browser ("hm-viewer") and used by every page: the map opens on their
// family journey, the tree is rooted at them, People counts relationships from them, Ask answers
// "my ancestors" from them. Only this button changes it; looking someone up on a page doesn't.
//
//   {k: pid chosen, g: 0 = that person is the viewer, n = the viewer is n generations below them,
//    s?: the spouse counted with k when g > 0, n: k's name, lv?: 1 if k is living,
//    m: the person on the map (GRAPH) the pages start from, o: generations from the viewer up to m,
//    ext?: 1 when m is a cousin or one of a cousin's other lines: the pages then load data_ext.js}
//
// Needs data.js (GRAPH). relatives.js (everyone in the tree) loads when the picker first opens.
const Viewer = (() => {
  const KEY = "hm-viewer";
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  let v = null;
  const listeners = [];
  try { v = JSON.parse(localStorage.getItem(KEY) || localStorage.getItem("hm-ask-me") || "null"); } catch (e) {}
  if (v && !v.m && GRAPH.people[v.k]) { v.m = v.k; v.o = v.g || 0; }        // a choice saved by the Ask page before 2026-10-02

  const unlocked = () => { try { return !!localStorage.getItem("hm-family-key"); } catch (e) { return false; } };
  const get = () => v;
  const mapId = () => (v && v.m && GRAPH.people[v.m] ? v.m : GRAPH.james_id);      // v.m is in GRAPH once the right data file is loaded
  const offset = () => (v && v.m && GRAPH.people[v.m] ? v.o || 0 : 0);
  const isSet = () => !!(v && v.m && GRAPH.people[v.m]);
  function set(nv) {
    const was = !!(v && v.ext);
    v = nv;
    try { v ? localStorage.setItem(KEY, JSON.stringify(v)) : localStorage.removeItem(KEY); localStorage.removeItem("hm-ask-me"); } catch (e) {}
    // the extended data is a different file: load the page again with it (or without it)
    if (!!(v && v.ext) !== was || !!(v && v.ext) !== !!window.HM_EXT) { location.reload(); return; }
    render();
    listeners.forEach(f => f(v));
  }
  // the site's root person is living: named only once the family password has put her name back
  const rootLabel = () => { const r = GRAPH.people[GRAPH.james_id]; return r && r.name && r.name !== "Private" ? r.name.split(" ")[0] : "the whole family"; };
  const DOWN = ["", "child", "grandchild", "great-grandchild"];
  function label() {
    if (!v) { const r = GRAPH.people[GRAPH.james_id]; return r && r.name !== "Private" ? r.name.split(" ")[0] : "the family"; }
    const nm = v.lv && !unlocked() ? "you" : v.n || "you";
    return v.g ? `a ${DOWN[v.g] || "descendant"} of ${nm}` : nm;
  }

  // ---------------------------------------------------------------- everyone in the tree, for the picker
  let R = null, toks = null, at = null, spouses = null, loading = null;
  const words = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[“”"‘’'.,()]/g, " ").split(/\s+/).filter(Boolean);
  const NICK = { nick: "nicholas", tom: "thomas", tommy: "thomas", bill: "william", will: "william", jim: "james", bob: "robert", jack: "john",
    joe: "joseph", sam: "samuel", ben: "benjamin", dan: "daniel", dave: "david", ed: "edward", fred: "frederick", charlie: "charles",
    liz: "elizabeth", betty: "elizabeth", kate: "katherine", peggy: "margaret", maggie: "margaret", polly: "mary", sally: "sarah", jenny: "jennie" };
  const b64d = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  async function openBlob(blob) {            // as pipeline/project/privacy.py writes it; the key is the one the lock remembered
    let saved = null; try { saved = localStorage.getItem("hm-family-key"); } catch (e) {}
    if (!saved || !blob) return null;
    try {
      const key = b64d(saved);
      const ek = await crypto.subtle.importKey("raw", key.slice(0, 32), "AES-CTR", false, ["decrypt"]);
      const mk = await crypto.subtle.importKey("raw", key.slice(32), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
      const iv = b64d(blob.iv), ct = b64d(blob.ct), signed = new Uint8Array(iv.length + ct.length);
      signed.set(iv); signed.set(ct, iv.length);
      if (!await crypto.subtle.verify("HMAC", mk, b64d(blob.mac), signed)) return null;
      return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({ name: "AES-CTR", counter: iv, length: 64 }, ek, ct)));
    } catch (e) { return null; }
  }
  function load() {
    if (loading) return loading;
    loading = (async () => {
      if (typeof RELATIVES === "undefined") await new Promise((ok, fail) => { const s = document.createElement("script"); s.src = "relatives.js"; s.onload = ok; s.onerror = fail; document.head.appendChild(s); });
      R = RELATIVES;
      const d = await openBlob(R.lv), living = new Set();
      R._lv = living;
      if (d) for (const [k, [n, b, dd]] of Object.entries(d)) { if (!R.n[k]) { R.n[k] = n; R.b[k] = b; R.d[k] = dd; } living.add(+k); }
      at = new Map(R.id.map((id, k) => ["@" + id + "@", k]));
      spouses = R.id.map(() => []);
      for (let i = 0; i < R.sp.length; i += 2) { spouses[R.sp[i]].push(R.sp[i + 1]); spouses[R.sp[i + 1]].push(R.sp[i]); }
      toks = R.n.map(n => new Set(words(n)));
      R._x = new Set(R.x || []);
    })();
    return loading;
  }
  const pid = k => "@" + R.id[k] + "@";
  const yrs = k => { const b = R.b[k], d = R.d[k]; return b || d > 0 ? `${b || "?"}–${d > 0 ? d : ""}` : ""; };
  function find(q) {
    const qt = words(q); if (!qt.length) return [];
    const out = [];
    for (let k = 0; k < R.n.length; k++) {
      if (!R.n[k]) continue;
      let score = 0, ok = true;
      for (const w of qt) {
        if (toks[k].has(w)) { score += 3; continue; }
        if (NICK[w] && toks[k].has(NICK[w])) { score += 2; continue; }
        let hit = false;
        if (w.length >= 3) for (const t of toks[k]) if (t.startsWith(w)) { hit = true; break; }
        if (!hit) { ok = false; break; }
        score += 1;
      }
      if (ok) out.push([k, score + (GRAPH.people[pid(k)] ? 2 : 0) + (R._lv.has(k) ? 3 : 0) - toks[k].size * 0.1]);
    }
    return out.sort((a, b) => b[1] - a[1]).slice(0, 8).map(x => x[0]);
  }
  // cousins (people only in the extended data) matching q, for the map's search on the core data:
  // [{id, name, birt, ext: true}]; the living only once the family password is entered
  async function cousins(q) {
    await load();
    const qt = words(q), out = [];
    if (!qt.length) return out;
    for (const k of R._x) {
      if (!R.n[k] || GRAPH.people[pid(k)]) continue;
      if (qt.every(w => { for (const t of toks[k]) if (t.startsWith(w) || (NICK[w] && t === NICK[w])) return true; return false; }))
        out.push({ id: pid(k), name: R.n[k], birt: R.b[k] || null, ext: true });
    }
    return out.sort((a, b) => a.name.localeCompare(b.name)).slice(0, 15);
  }
  // the nearest people on the map at or above k: [pid, generations up]
  function onMapFrom(starts, depth) {
    let fr = starts.filter(x => x >= 0), seen = new Set(fr);
    for (let d = depth; fr.length && d < 40; d++) {
      const hit = fr.find(x => GRAPH.people[pid(x)] || R._x.has(x));      // on the core map, or in the extended data
      if (hit != null) return [pid(hit), d, R._x.has(hit)];
      const nx = [];
      for (const x of fr) for (const p of [R.f[x], R.m[x]]) if (p >= 0 && !seen.has(p)) { seen.add(p); nx.push(p); }
      fr = nx;
    }
    return [null, 0, false];
  }
  function choose(k, g, s) {
    if (g > 0 && s == null && spouses[k].length === 1) s = spouses[k][0];
    let [m, o, ext] = onMapFrom(g > 0 ? [k, s != null && s >= 0 ? s : -1] : [k], g);
    // "a child of X and Y": any child of that couple in the data has exactly the viewer's ancestors, so start from one
    if (g === 1 && s != null && s >= 0) {
      const inData = x => GRAPH.people[pid(x)] || R._x.has(x);
      const child = R.id.findIndex((_, c) => ((R.f[c] === k && R.m[c] === s) || (R.f[c] === s && R.m[c] === k)) && inData(c));
      if (child >= 0) { m = pid(child); o = 0; ext = R._x.has(child); }
    }
    set(Object.assign({ k: pid(k), g, n: R.n[k], m, o }, s != null && s >= 0 ? { s: pid(s) } : {}, R._lv.has(k) ? { lv: 1 } : {}, ext ? { ext: 1 } : {}));
  }

  // ---------------------------------------------------------------- the header button
  let slot = null;
  function css() {
    if (document.getElementById("viewer-css")) return;
    const st = document.createElement("style"); st.id = "viewer-css";
    st.textContent = `
.viewer { position: relative; margin-right: 8px; }
.viewer-btn { font-family: 'SF Mono', Consolas, Menlo, monospace; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: #6b5d43;
  background: none; border: 1px solid rgba(156,122,46,0.45); border-radius: 4px; padding: 3px 8px; cursor: pointer; max-width: 260px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.viewer-btn b { color: #2c2417; font-weight: 600; }
.viewer-pop { display: none; position: absolute; right: 0; top: calc(100% + 6px); z-index: 60; width: 330px; max-width: 92vw; background: #f5eeda;
  border: 1px solid rgba(156,122,46,0.5); border-radius: 6px; padding: 12px; box-shadow: 0 4px 14px rgba(0,0,0,.15);
  font: 13px -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; color: #2c2417; text-align: left; }
.viewer-pop.show { display: block; }
.viewer-pop p { margin: 0 0 8px; line-height: 1.4; color: #6b5d43; font-size: 12px; }
.viewer-pop input { width: 100%; box-sizing: border-box; font: inherit; padding: 6px 8px; border: 1px solid rgba(156,122,46,0.5); border-radius: 4px; }
.viewer-row { padding: 7px 0; border-bottom: 1px solid rgba(156,122,46,0.25); }
.viewer-row .yrs { color: #6b5d43; font-size: 11.5px; }
.viewer-acts { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.viewer-acts button, .viewer-pop .vlink { font: inherit; font-size: 11.5px; padding: 3px 8px; border-radius: 999px; border: 1px solid rgba(156,122,46,0.5);
  background: rgba(255,255,255,0.6); cursor: pointer; color: #2c2417; }
.viewer-acts button:hover { background: #fff; border-color: #9c3c2e; }
.viewer-pop .vfoot { margin-top: 10px; font-size: 11.5px; }
.viewer-pop a { color: #9c3c2e; }`;
    document.head.appendChild(st);
  }
  function render() {
    if (!slot) return;
    const btn = slot.querySelector(".viewer-btn");
    btn.innerHTML = `Viewing as <b>${esc(label())}</b> &#9662;`;
    btn.title = "Who you are on this site: sets whose ancestors, tree and relationships every page shows";
  }
  function body(html) { slot.querySelector(".viewer-body").innerHTML = html; }
  function start() {
    const who = v ? `<p>You&rsquo;re viewing as <b>${esc(label())}</b>.${v.o && v.m && GRAPH.people[v.m] && GRAPH.people[v.m].name !== "Private" && (v.g === 0 || v.m !== v.k)
      ? ` The map, tree and People page start from ${esc(GRAPH.people[v.m].name)}, the closest of your ancestors on the map.` : ""}</p>` : "";
    body(who + `<p>Search for yourself${unlocked() ? "" : " (living family appear once the family password is entered)"}, or for a parent or grandparent who has died.</p>` +
      `<input class="viewer-q" type="search" placeholder="A name&hellip;" autocomplete="off" aria-label="Search for a person"><div class="viewer-list"></div>` +
      `<div class="vfoot">${v ? `<a href="#" class="viewer-reset">Back to the default (${esc(rootLabel())})</a>` : `Until you choose, every page shows ${rootLabel() === "the whole family" ? "the whole family" : "the family from " + esc(rootLabel())}.`}</div>`);
    const q = slot.querySelector(".viewer-q"), list = slot.querySelector(".viewer-list");
    q.focus();
    q.oninput = async () => {
      const s = q.value.trim();
      if (s.length < 2) { list.innerHTML = ""; return; }
      await load();
      const hits = find(s);
      list.innerHTML = hits.length ? hits.map(k => `<div class="viewer-row">${esc(R.n[k])} <span class="yrs">${esc(yrs(k))}</span><div class="viewer-acts">` +
        (R.d[k] ? [] : [[0, "This is me"]]).concat([[1, "My parent"], [2, "Grandparent"], [3, "Great-grandparent"]])
          .map(([g, t]) => `<button data-k="${k}" data-g="${g}">${t}</button>`).join("") + `</div></div>`).join("")
        : `<p style="margin-top:8px">No one by that name${unlocked() ? "" : " among those who have died"}.</p>`;
    };
    const reset = slot.querySelector(".viewer-reset");
    if (reset) reset.onclick = e => { e.preventDefault(); set(null); close(); };
  }
  function close() { if (slot) { slot.querySelector(".viewer-pop").classList.remove("show"); slot.querySelector(".viewer-btn").setAttribute("aria-expanded", "false"); } }
  function open() {
    if (!slot) return;
    slot.querySelector(".viewer-pop").classList.add("show"); slot.querySelector(".viewer-btn").setAttribute("aria-expanded", "true");
    start(); load();
  }
  function mount(el) {
    slot = typeof el === "string" ? document.getElementById(el) : el;
    if (!slot) return;
    css();
    slot.className = "viewer";
    slot.innerHTML = `<button class="viewer-btn" type="button" aria-expanded="false"></button><div class="viewer-pop" role="dialog" aria-label="Viewing as"><div class="viewer-body"></div></div>`;
    slot.querySelector(".viewer-btn").onclick = () => (slot.querySelector(".viewer-pop").classList.contains("show") ? close() : open());
    slot.addEventListener("click", e => {
      const b = e.target.closest("button[data-k]");
      if (!b) return;
      const k = +b.dataset.k, g = +b.dataset.g;
      if (g > 0 && b.dataset.s == null && spouses[k].length > 1) {
        body(`<p>Which of ${esc(R.n[k])}&rsquo;s marriages are you descended from?</p><div class="viewer-acts">` + spouses[k].map(s =>
          `<button data-k="${k}" data-g="${g}" data-s="${s}">with ${esc(R.n[s] || "a living spouse")} ${esc(yrs(s))}</button>`).join("") +
          `<button data-k="${k}" data-g="${g}" data-s="-1">not sure</button></div>`);
        return;
      }
      choose(k, g, b.dataset.s != null ? +b.dataset.s : null);
      close();
    });
    document.addEventListener("click", e => { if (slot && !slot.contains(e.target)) close(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
    render();
  }
  return { get, set, mapId, offset, isSet, label, mount, open, load, choose, cousins, refresh: render, onChange: f => listeners.push(f) };
})();
