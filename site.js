// Shared by the site's pages other than the map (tree.html, people.html, about.html):
// the family-password lock, the living family's details and portraits, and small helpers.
// The map (index.html) has its own copy of the lock; both use the key remembered in this
// browser ("hm-family-key"), so unlocking on any page unlocks all of them.
// Needs data.js (GRAPH, SEARCH_INDEX, NOTABLE, MILITARY, PRIVATE) and profiles.js (PROFILES).
const Family = (() => {
  const PRIV = typeof PRIVATE !== "undefined" ? PRIVATE : null;
  const b64d = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const b64e = a => btoa(String.fromCharCode(...a));
  let km = null, shown = false, shots = null;
  const listeners = [];

  async function keyMaterial(pw) {
    const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveBits"]);
    return new Uint8Array(await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: b64d(PRIV.salt), iterations: PRIV.iter }, base, 512));
  }
  async function open(key, blob) {         // AES-CTR + HMAC, as pipeline/project/privacy.py writes it
    const ek = await crypto.subtle.importKey("raw", key.slice(0, 32), "AES-CTR", false, ["decrypt"]);
    const mk = await crypto.subtle.importKey("raw", key.slice(32), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
    const iv = b64d(blob.iv), ct = b64d(blob.ct), signed = new Uint8Array(iv.length + ct.length);
    signed.set(iv); signed.set(ct, iv.length);
    if (!await crypto.subtle.verify("HMAC", mk, b64d(blob.mac), signed)) return null;
    return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({ name: "AES-CTR", counter: iv, length: 64 }, ek, ct)));
  }
  function apply(d) {                      // put the living back into the page's data
    for (const [pid, p] of Object.entries(d.graph)) GRAPH.people[pid] = p;
    for (const [i, s] of d.search) SEARCH_INDEX.splice(i, 0, s);
    if (typeof PROFILES !== "undefined") {
      Object.assign(PROFILES.people, d.profiles || {});
      for (const [pid, f] of Object.entries(d.pfam || {})) if (PROFILES.people[pid]) PROFILES.people[pid].f = f;
      for (const [pid, s] of Object.entries(d.psib || {})) if (PROFILES.people[pid]) PROFILES.people[pid].sb = s;
    }
    shown = true;
    listeners.forEach(f => f());
  }
  function script(src) {
    return new Promise((ok, fail) => { const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = fail; document.head.appendChild(s); });
  }
  // a living person's portrait, once unlocked
  async function photo(pid) {
    const pr = typeof PROFILES !== "undefined" && PROFILES.people[pid];
    if (pr && pr.ph) return pr.ph[0];
    if (!km) return null;
    if (!shots) shots = script("private_photos.js").then(() => open(km, PRIVATE_PHOTOS)).then(d => d || {}).catch(() => ({}));
    const s = await shots;
    return s[pid] ? "data:image/jpeg;base64," + s[pid] : null;
  }

  // the lock button, rendered into an element (id) in the page's header
  function mountLock(id) {
    const slot = document.getElementById(id);
    if (!slot || !PRIV) return;
    slot.className = "lock";
    slot.innerHTML = `<button class="lock-btn" type="button" aria-expanded="false"></button>
      <div class="lock-pop" role="dialog" aria-label="Show living family"><p class="lock-text"></p>
      <form><input type="password" autocomplete="current-password" aria-label="Family password"><button type="submit">Show</button></form>
      <div class="lock-msg"></div></div>`;
    const btn = slot.querySelector(".lock-btn"), pop = slot.querySelector(".lock-pop"), form = slot.querySelector("form"),
          input = slot.querySelector("input"), msg = slot.querySelector(".lock-msg"), text = slot.querySelector(".lock-text");
    const ui = () => {
      btn.innerHTML = shown ? "&#x1F513; Living family shown" : "&#x1F512; Living family hidden";
      btn.classList.toggle("open", shown);
      text.innerHTML = shown ? "Living family members are shown on this device."
        : "Living family members appear as &ldquo;Private&rdquo;. Enter the family password to show them on this device.";
      form.style.display = shown ? "none" : "flex";
      msg.innerHTML = shown ? '<a href="#" class="forget">Hide them again on this device</a>' : "";
      const f = msg.querySelector(".forget");
      if (f) f.onclick = e => { e.preventDefault(); try { localStorage.removeItem("hm-family-key"); } catch (x) {} location.reload(); };
    };
    btn.onclick = () => { const on = !pop.classList.contains("show"); pop.classList.toggle("show", on); btn.setAttribute("aria-expanded", on); if (on && !shown) input.focus(); };
    form.onsubmit = async e => {
      e.preventDefault();
      if (!input.value) return;
      msg.textContent = "Checking…";
      const k = await keyMaterial(input.value), d = await open(k, PRIV);
      if (!d) { msg.textContent = "That isn't the family password."; return; }
      km = k;
      try { localStorage.setItem("hm-family-key", b64e(k)); } catch (x) {}
      input.value = ""; pop.classList.remove("show");
      apply(d); ui();
    };
    listeners.push(ui);
    ui();
  }
  // unlock silently with the key remembered in this browser
  const ready = (async () => {
    if (!PRIV) return;
    let saved = null;
    try { saved = localStorage.getItem("hm-family-key"); } catch (e) {}
    if (!saved) return;
    try { const k = b64d(saved), d = await open(k, PRIV); if (d) { km = k; apply(d); } } catch (e) {}
  })();

  // ---- helpers shared by the pages ----
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const sex = pid => (typeof NOTABLE !== "undefined" && NOTABLE.sex[pid]) || "";
  const yearOf = s => { const m = /\d{4}/.exec(s || ""); return m ? m[0] : ""; };
  function years(pid) {
    const pr = typeof PROFILES !== "undefined" && PROFILES.people[pid], g = GRAPH.people[pid] || {};
    const b = pr ? yearOf(pr.b[0]) : (g.by || ""), d = pr ? yearOf(pr.d[0]) : "";
    return b || d ? `${b || "?"}–${d}` : "";
  }
  // generations from a root up to each ancestor
  function generations(root) {
    const gen = new Map([[root, 0]]); let frontier = [root];
    for (let g = 1; frontier.length; g++) {
      const next = [];
      for (const id of frontier) for (const q of ((GRAPH.people[id] || {}).parents || [])) if (!gen.has(q)) { gen.set(q, g); next.push(q); }
      frontier = next;
    }
    return gen;
  }
  const ordinal = n => n + (n % 100 >= 11 && n % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th");
  function relation(g, pid) {
    if (g == null || g === 0) return "";
    const s = sex(pid), base = s === "M" ? ["father", "grandfather"] : s === "F" ? ["mother", "grandmother"] : ["parent", "grandparent"];
    return g === 1 ? base[0] : g === 2 ? base[1] : g === 3 ? "great-" + base[1] : ordinal(g - 2) + " great-" + base[1];
  }
  const firstName = pid => { const n = (GRAPH.people[pid] || {}).name || ""; const m = /"([^"]+)"/.exec(n); return m ? m[1] : n.split(" ")[0]; };

  return { ready, mountLock, onChange: f => listeners.push(f), get shown() { return shown; }, photo,
           esc, years, generations, relation, firstName, sex, yearOf };
})();
