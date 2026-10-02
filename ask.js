// The Ask page (index.html): answers questions about the family from the site's own data.
// No AI model: each question is matched against a set of patterns and answered from
// GRAPH, PROFILES, MILITARY, NOTABLE (data.js, profiles.js) and RELATIVES (relatives.js,
// everyone in the GEDCOM, loaded on first use). Living people's names come back only
// after the family password is entered (site.js).
const Ask = (() => {
  const E = Family.esc;
  let R = null, at = new Map(), kids = [], spouses = [], toks = [], loading = null;

  // ---------------------------------------------------------------- data
  function load() {
    if (loading) return loading;
    loading = (async () => {
      if (typeof RELATIVES === "undefined") await Family.script("relatives.js");
      if (typeof PROFILES === "undefined") await Family.script("profiles.js");
      await Family.ready;
      R = RELATIVES;
      R.id.forEach((id, k) => at.set("@" + id + "@", k));
      kids = R.id.map(() => []); spouses = R.id.map(() => []);
      R.id.forEach((_, k) => { for (const p of [R.f[k], R.m[k]]) if (p >= 0) kids[p].push(k); });
      for (let i = 0; i < R.sp.length; i += 2) { spouses[R.sp[i]].push(R.sp[i + 1]); spouses[R.sp[i + 1]].push(R.sp[i]); }
      await unlockNames();
      Family.onChange(() => unlockNames());
    })();
    return loading;
  }
  async function unlockNames() {
    const d = Family.shown ? await Family.openBlob(R.lv) : null;
    if (d) for (const [k, [n, b, dd]] of Object.entries(d)) { R.n[k] = n; R.b[k] = b; R.d[k] = dd; }
    toks = R.n.map(n => new Set(words(n)));
  }
  const words = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[“”"‘’'.,()]/g, " ").split(/\s+/).filter(Boolean);

  const pid = k => "@" + R.id[k] + "@";
  const onMap = k => !!GRAPH.people[pid(k)];
  const living = k => !R.n[k];
  const name = k => R.n[k] || "Private";
  const sexOf = k => R.s[k];
  const yrs = k => { const b = R.b[k], d = R.d[k]; return b || d > 0 ? `${b || "?"}–${d > 0 ? d : ""}` : ""; };
  const prof = k => typeof PROFILES !== "undefined" && PROFILES.people[pid(k)];
  const he = k => sexOf(k) === "F" ? "she" : sexOf(k) === "M" ? "he" : "they";
  const his = k => sexOf(k) === "F" ? "her" : sexOf(k) === "M" ? "his" : "their";
  const cap = s => s.charAt(0).toUpperCase() + s.slice(1);

  // ---------------------------------------------------------------- who's asking
  // the site-wide "Viewing as" person (viewer.js; chosen from the button in the header):
  // {k: pid, g: 0 for the person themselves, or generations below them, s?: the spouse counted with k}
  let me = Viewer.get();
  function meIdx() { return me && at.has(me.k) ? at.get(me.k) : -1; }
  // set it from here (tools/check_ask.py does): g > 0 = a descendant of k, and of k's spouse s (if chosen, or k had only one)
  function setMe(k, g, s) {
    if (k == null) return Viewer.set(null);
    if (g > 0 && s == null && spouses[k].length === 1) s = spouses[k][0];
    // the closest person on the map at or above the viewer, for the pages that only know the map's people
    const M = up(k, g); if (g > 0 && s != null && s >= 0) for (const [x, v] of up(s, g)) if (!M.has(x)) M.set(x, v);
    const near = [...M].filter(([x]) => onMap(x)).sort((a, b) => a[1].d - b[1].d)[0];
    Viewer.set(Object.assign({ k: pid(k), g, n: R.n[k], m: near ? pid(near[0]) : null, o: near ? near[1].d : 0 }, s != null && s >= 0 ? { s: pid(s) } : {}));
  }
  function meLabel() {
    const k = meIdx();
    if (k < 0) return "";
    const s = me.s && at.has(me.s) ? " and " + name(at.get(me.s)) : "";
    return me.g === 0 ? name(k) : `a ${["", "child", "grandchild", "great-grandchild"][me.g] || "descendant"} of ${name(k)}${s}`;
  }
  function showMe() {
    const el = document.getElementById("asking-as");
    if (!el) return;
    const k = me && R ? meIdx() : -1;
    el.innerHTML = k >= 0 ? `Answering for <b>${E(meLabel())}</b> · <a href="#" data-act="me">change</a>`
      : `Family, or think you might be? <a href="#" data-act="me">Say who you are</a> (&ldquo;Viewing as&rdquo;, top right) to ask how you&rsquo;re related`;
  }

  // ---------------------------------------------------------------- finding people by name
  const STOP = new Set(["the", "my", "mr", "mrs", "miss", "dr", "rev", "capt", "col", "gen", "lt", "sgt", "of", "a"]);
  // common nicknames, so "Nick Hitchcock" finds Nicholas
  const NICK = { nick: "nicholas", tom: "thomas", tommy: "thomas", bill: "william", will: "william", billy: "william",
    jim: "james", jimmy: "james", bob: "robert", bobby: "robert", rob: "robert", dick: "richard", rick: "richard",
    jack: "john", johnny: "john", joe: "joseph", sam: "samuel", ben: "benjamin", dan: "daniel", dave: "david",
    ed: "edward", ned: "edward", ted: "edward", harry: "henry", hank: "henry", fred: "frederick", fritz: "frederick",
    chuck: "charles", charlie: "charles", andy: "andrew", tony: "anthony", mike: "michael", steve: "stephen",
    liz: "elizabeth", beth: "elizabeth", betsy: "elizabeth", betty: "elizabeth", kate: "katherine", katie: "katherine",
    peggy: "margaret", maggie: "margaret", polly: "mary", molly: "mary", patsy: "martha", sally: "sarah", nancy: "ann",
    jenny: "jennie", abby: "abigail", sue: "susan", allie: "allison", al: "albert", bert: "albert", jon: "john", hal: "henry" };
  function find(q) {
    const qt = words(q).filter(w => !STOP.has(w));
    if (!qt.length) return [];
    const myAnc = me ? ancestorsOfMe() : null, out = [];
    for (let k = 0; k < R.n.length; k++) {
      if (!R.n[k]) continue;
      let score = 0, ok = true;
      for (const w of qt) {
        if (toks[k].has(w)) { score += 3; continue; }
        if (NICK[w] && toks[k].has(NICK[w])) { score += 2; continue; }
        let hit = false;
        if (w.length >= 3) for (const t of toks[k]) if (t.startsWith(w)) { hit = true; break; }
        if (!hit && w.length === 1) for (const t of toks[k]) if (t[0] === w) { hit = true; break; }            // an initial: "Albert D."
        if (!hit && w.length >= 4 && w.endsWith("s") && toks[k].has(w.slice(0, -1))) hit = true;              // "hitchcocks father"
        if (!hit) { ok = false; break; }
        score += 1;
      }
      if (!ok) continue;
      if (onMap(k)) score += 4;
      if (myAnc && myAnc.has(k)) score += 3;
      score -= toks[k].size * 0.1;           // fewer extra names = closer match
      out.push([k, score]);
    }
    return out.sort((a, b) => b[1] - a[1]).map(x => x[0]);
  }
  // one person, or a list to choose from
  function resolve(q) {
    let hits = find(q);
    if (!hits.length) return { none: true };
    if (hits.length === 1) return { k: hits[0] };
    // people whose names hold every word as written ("Tommy Baskett" is Tommy, not a Thomas)
    const qw = words(q).filter(w => !STOP.has(w)), whole = hits.filter(k => qw.every(w => toks[k].has(w)));
    if (whole.length) hits = whole;
    if (hits.length === 1) return { k: hits[0] };
    const exact = words(q).filter(w => !STOP.has(w)).length < 2 ? [] : hits.filter(k => words(name(k)).filter(w => !STOP.has(w)).join(" ") === words(q).filter(w => !STOP.has(w)).join(" "));
    const pool = exact.length ? exact : hits;
    const mapped = pool.filter(onMap);
    if (mapped.length === 1) return { k: mapped[0] };
    if (pool.length === 1) return { k: pool[0] };
    return { many: pool.slice(0, 10) };
  }

  // ---------------------------------------------------------------- relationships
  // every ancestor of k: index -> {d: generations up, c: the child it was reached from}
  function up(k, shift = 0, from = -1) {
    const m = new Map([[k, { d: shift, c: from }]]); let fr = [k];
    for (let d = shift + 1; fr.length; d++) {
      const nx = [];
      for (const x of fr) for (const p of [R.f[x], R.m[x]]) if (p >= 0 && !m.has(p)) { m.set(p, { d, c: x }); nx.push(p); }
      fr = nx;
    }
    return m;
  }
  const ME = -2;                     // "you", when you're a descendant of someone in the tree
  function upMe() {
    const k = meIdx();
    if (k < 0) return null;
    if (me.g === 0) return up(k);
    const m = up(k, me.g, ME);
    if (me.s && at.has(me.s)) for (const [x, v] of up(at.get(me.s), me.g, ME)) if (!m.has(x)) m.set(x, v);
    m.set(ME, { d: 0, c: -1 }); return m;
  }
  // when "you" are known only through one ancestor (or couple), other lines are missing
  function partial() {
    const k = meIdx();
    if (k < 0 || me.g === 0 || (me.g === 1 && me.s)) return "";
    return `<p class="note">Counting only through ${E(name(k))}${me.s && at.has(me.s) ? " and " + E(name(at.get(me.s))) : ""}: ` +
      `you may also be related through your other ${me.g === 1 ? "parent" : "grandparents"}. <a href="#" data-act="me">Choose someone closer</a>, ` +
      `or enter the family password to find yourself.</p>`;
  }
  function ancestorsOfMe() { const m = R && upMe(); return m ? new Set([...m.keys()].filter(x => x !== ME && m.get(x).d > 0)) : null; }

  const ord = n => n + (n % 100 >= 11 && n % 100 <= 13 ? "th" : ["th", "st", "nd", "rd"][n % 10] || "th");
  const sx = (k, m, f, n) => sexOf(k) === "M" ? m : sexOf(k) === "F" ? f : n;
  function greats(n, base) { return n <= 0 ? base : n === 1 ? "great-" + base : ord(n) + " great-" + base; }
  // what the person at b generations below the common ancestor is to the one a generations below it
  function term(a, b, k, half) {
    const h = half ? "half-" : "";
    if (b === 0 && a === 0) return "the same person";
    if (b === 0) return a === 1 ? sx(k, "father", "mother", "parent") : greats(a - 2, sx(k, "grandfather", "grandmother", "grandparent"));
    if (a === 0) return b === 1 ? sx(k, "son", "daughter", "child") : greats(b - 2, sx(k, "grandson", "granddaughter", "grandchild"));
    if (a === 1 && b === 1) return h + sx(k, "brother", "sister", "sibling");
    if (a === 1) return h + greats(b - 3, b === 2 ? sx(k, "nephew", "niece", "nephew or niece") : sx(k, "grandnephew", "grandniece", "grandnephew or niece"));
    if (b === 1) return h + (a === 2 ? sx(k, "uncle", "aunt", "uncle or aunt") : a === 3 ? sx(k, "great-uncle", "great-aunt", "great-uncle or aunt")
      : ord(a - 2) + " " + sx(k, "great-uncle", "great-aunt", "great-uncle or aunt"));
    const deg = Math.min(a, b) - 1, rem = Math.abs(a - b);
    const times = rem === 0 ? "" : [, " once removed", " twice removed", " three times removed"][rem] || ` ${rem} times removed`;
    return `${h}${ord(deg)} cousin${times}`;
  }
  // blood relationship between two ancestor maps; null if none
  function blood(A, B) {
    let best = null;
    for (const [c, x] of A) { if (c === ME) continue; const y = B.get(c); if (!y) continue;
      const s = x.d + y.d;
      if (!best || s < best.s || (s === best.s && Math.max(x.d, y.d) < Math.max(best.a, best.b))) best = { c, a: x.d, b: y.d, s };
    }
    if (!best) return null;
    // half: the two lines leave the common ancestor through children whose other parents differ
    const ca = A.get(best.c).c, cb = B.get(best.c).c;
    if (best.a > 0 && best.b > 0 && ca >= 0 && cb >= 0) {
      const other = x => [R.f[x], R.m[x]].find(p => p >= 0 && p !== best.c);
      const oa = other(ca), ob = other(cb);
      best.half = oa != null && ob != null && oa !== ob;
    }
    best.also = [...A.keys()].filter(c => c !== best.c && c !== ME && B.has(c) && A.get(c).d === best.a && B.get(c).d === best.b);
    return best;
  }
  // the line from the common ancestor down to where the map started
  function line(M, c) { const out = []; for (let x = c; x !== -1 && x !== undefined; x = M.get(x).c) { out.push(x); if (x === ME) break; } return out; }

  // how t is related to the person the map A was built from (subject: "your", or "Margaret's")
  function relate(A, t, whose) {
    const T = up(t), bl = blood(A, T);
    if (bl) return { kind: "blood", text: term(bl.a, bl.b, t, bl.half), bl, A, T };
    // by marriage: t married a blood relative; or t is a blood relative of someone who married in
    for (const s of spouses[t]) {
      const b2 = blood(A, up(s));
      if (b2) return { kind: "spouse", text: `the ${sx(t, "husband", "wife", "spouse")} of ${whose} ${term(b2.a, b2.b, s, b2.half)}, ${name(s)}`, via: s };
    }
    const k = A.has(ME) ? -1 : [...A.keys()].find(x => A.get(x).d === 0);
    if (k >= 0) for (const s of spouses[k]) {
      const b3 = blood(up(s), T);
      if (b3) return { kind: "inlaw", text: `${whose} ${sx(s, "husband", "wife", "spouse")}'s ${term(b3.a, b3.b, t, b3.half)}`, via: s };
    }
    return chain(A, t, whose);
  }
  // anything else: the shortest path through parents, children and marriages
  function chain(A, t, whose) {
    const start = [...A.keys()].find(x => A.get(x).d === 0), seen = new Map([[start, null]]);
    let fr = [start];
    for (let step = 0; fr.length && step < 14 && !seen.has(t); step++) {
      const nx = [];
      for (const x of fr) {
        const nb = x === ME ? [me.k, me.s].filter(p => p && at.has(p)).map(p => [at.get(p), "parent"]) : [
          ...[R.f[x], R.m[x]].filter(p => p >= 0).map(p => [p, "parent"]),
          ...kids[x].map(c => [c, "child"]), ...spouses[x].map(s => [s, "spouse"])];
        for (const [y, how] of nb) if (y >= 0 && !seen.has(y)) { seen.set(y, [x, how]); nx.push(y); }
      }
      fr = nx;
    }
    if (!seen.has(t)) return null;
    const steps = []; for (let y = t; seen.get(y); y = seen.get(y)[0]) steps.unshift([y, seen.get(y)[1]]);
    const word = (y, how) => how === "parent" ? sx(y, "father", "mother", "parent") : how === "child" ? sx(y, "son", "daughter", "child") : sx(y, "husband", "wife", "spouse");
    return { kind: "chain", text: "connected by marriage", start, steps: steps.map(([y, how]) => [y, word(y, how)]) };
  }

  // ---------------------------------------------------------------- answers
  const link = k => onMap(k) ? `<a href="map.html#p=${encodeURIComponent(pid(k))}">${E(name(k))}</a>` : E(name(k));
  const who = k => `${link(k)}${yrs(k) ? ` <span class="yrs">(${E(yrs(k))})</span>` : ""}`;
  function actions(k) {
    if (!onMap(k)) return "";
    const p = encodeURIComponent(pid(k));
    return `<div class="acts"><a class="btn solid" href="map.html#p=${p}">Profile</a><a class="btn" href="map.html?life=${p}">Life journey</a>` +
      `<a class="btn" href="map.html?target=${p}">Family journey</a><a class="btn" href="tree.html#root=${p}">Tree</a></div>`;
  }
  const card = (head, body = "", k = null) => `<div class="answer"><h2>${head}</h2>${body}${k != null ? actions(k) : ""}</div>`;
  function choose(list, again) {
    return card("Which one do you mean?", `<div class="chips">${list.map(k =>
      `<button class="chip" data-pick="${k}" data-again="${E(again)}">${E(name(k))}${yrs(k) ? ` <span class="yrs">${E(yrs(k))}</span>` : ""}${onMap(k) ? "" : ' <span class="off">not on the map</span>'}</button>`).join("")}</div>`);
  }
  function notFound(q) {
    return card(`I couldn&rsquo;t find &ldquo;${E(q)}&rdquo; in the tree.`,
      `<p>Check the spelling, or try a first name and surname.${Family.shown ? "" : " Living family appear only after the family password is entered."}</p>`);
  }

  function lineHTML(M, c, top) {
    const L = line(M, c).filter(x => x !== ME);
    const gap = M.has(ME) && me.g > 1 ? Array.from({ length: me.g - 1 }, (_, i) => me.g - 1 - i)
      .map(i => `<li class="gap">your ${i === 1 ? "parent" : i === 2 ? "grandparent" : "great-grandparent"}</li>`).join("") : "";
    return `<ol class="line">${L.map(x => `<li>${who(x)}</li>`).join("")}${gap}${M.has(ME) ? `<li>you</li>` : ""}</ol>`;
  }
  function relationAnswer(t, fromK) {
    let A, whose, subj;
    if (fromK == null) {
      A = upMe(); whose = "your";
      if (!A) return null;
      if (me.g === 0 && at.get(me.k) === t) return card(`That&rsquo;s you.`);
    } else { A = up(fromK); whose = E(name(fromK)) + "&rsquo;s"; }
    const r = relate(A, t, fromK == null ? "your" : name(fromK) + "’s");
    if (!r) return card(`${who(t)} isn&rsquo;t connected to ${fromK == null ? "you" : E(name(fromK))} in this tree.`,
      `<p>No chain of parents, children and marriages links them.</p>` + (fromK == null ? partial() : ""));
    if (r.kind === "blood") {
      const { bl } = r, c = bl.c;
      const common = [c, ...bl.also.filter(x => spouses[c].includes(x))];
      let body = "";
      if (bl.b === 0) body = `<p class="lead">The line from ${sx(t, "him", "her", "them")} down to ${fromK == null ? "you" : E(name(fromK))}:</p>${lineHTML(A, c)}`;
      else if (bl.a === 0) body = `<p class="lead">The line down from ${fromK == null ? "you" : E(name(fromK))}:</p>${lineHTML(r.T, c)}`;
      else body = `<p class="lead">Your common ancestor${common.length > 1 ? "s" : ""}: ${common.map(who).join(" and ")}, ` +
        `${fromK == null ? "your" : E(name(fromK)) + "&rsquo;s"} ${term(bl.a, 0, c).replace(/father|mother/, "parent").replace(/grandfather|grandmother/, "grandparent")}${common.length > 1 ? "s" : ""}.</p>` +
        `<div class="two"><div><div class="eyebrow">${fromK == null ? "Your" : E(name(fromK)) + "&rsquo;s"} line</div>${lineHTML(A, c)}</div>` +
        `<div><div class="eyebrow">${E(name(t))}&rsquo;s line</div>${lineHTML(r.T, c)}</div></div>`;
      return card(`${who(t)} is ${whose} ${E(r.text)}.`, body + (fromK == null ? partial() : ""), t);
    }
    if (r.kind === "chain") {
      const other = fromK == null ? "you" : E(name(fromK)), M = up(at.get(GRAPH.james_id));
      let lead = "";
      if (fromK != null && M.has(t) && M.has(fromK) && M.get(t).d && M.get(fromK).d)
        lead = `<p>Both are Margaret&rsquo;s ancestors, on different sides of her family: ${E(name(t))} is her ${E(term(M.get(t).d, 0, t))}, ` +
          `${E(name(fromK))} her ${E(term(M.get(fromK).d, 0, fromK))}.</p>`;
      const steps = `<ol class="line"><li>${r.start === ME ? "you" : who(r.start)}</li>` + r.steps.map(([y, w], i) =>
        `<li>${/husband|wife|spouse/.test(w) ? "married " : i === 0 && r.start === ME && me.g > 1 ? (me.g === 2 ? "grandchild of " : "descendant of ")
          : `${w === "father" || w === "mother" || w === "parent" ? "child of" : "parent of"} `}${who(y)}</li>`).join("") + `</ol>`;
      return card(`${who(t)} and ${other} aren&rsquo;t related by blood${fromK == null && partial() ? " through that line" : ""}.`,
        lead + `<p class="lead">The shortest connection, through marriages:</p>` + steps + (fromK == null ? partial() : ""), t);
    }
    return card(`${who(t)} is ${E(r.text)}.`, `<p>By marriage, not by blood.</p>`, t);
  }

  const WARS = [
    [/revolution|revolutionary|independence|1776/, /Revolution/, "the Revolution"],
    [/civil war|confedera|union army|1861/, /Civil War/, "the Civil War"],
    [/1812|creek war/, /1812/, "the War of 1812"],
    [/french (and|&) indian|seven years/, /French and Indian/, "the French and Indian War"],
    [/world war (i|1|one)\b|wwi\b|ww1|great war/, /World War I\b/, "World War I"],
    [/king philip/, /King Philip/, "King Philip's War"],
    [/pequot/, /Pequot/, "the Pequot War"],
    [/jenkins/, /Jenkins/, "the War of Jenkins' Ear"],
    [/bacon/, /Bacon/, "Bacon's Rebellion"],
  ];
  function war(q) { for (const [re, match, label] of WARS) if (re.test(q)) return { match, label }; return null; }
  function services(k, w) { return (MILITARY[pid(k)] || []).filter(s => !w || w.match.test(s.war)); }
  function milRecords(k) { const p = prof(k); return p ? p.t.filter(e => e[2] === "military") : []; }

  // the set "my ancestors" means: yours if we know who you are, else Margaret's
  function scope() {
    const A = upMe();
    if (A) return { set: new Set([...A.keys()].filter(x => x !== ME && A.get(x).d > 0)), A, whose: "your", who: "you" };
    const root = at.get(GRAPH.james_id), M = up(root);
    return { set: new Set([...M.keys()].filter(x => M.get(x).d > 0)), A: M, whose: "Margaret&rsquo;s", who: "Margaret", note: true };
  }
  const relTo = (S, k) => { const d = S.A.get(k); return d ? term(d.d, 0, k) : ""; };
  const scopeNote = S => S.note ? `<p class="note">Counting from Margaret. <a href="#" data-act="me">Tell me who you are</a> to count from you.</p>` : partial();

  function veterans(w, q) {
    const S = scope(), rows = [];
    for (const [p, list] of Object.entries(MILITARY)) {
      const k = at.get(p);
      if (k == null || !S.set.has(k)) continue;
      const ss = list.filter(s => !w || w.match.test(s.war));
      if (ss.length) rows.push([k, ss]);
    }
    rows.sort((a, b) => S.A.get(a[0]).d - S.A.get(b[0]).d || (R.b[a[0]] || 0) - (R.b[b[0]] || 0));
    const label = w ? w.label : "any war";
    if (!rows.length) return card(`None of ${S.whose} ancestors on the map is recorded as serving in ${E(label)}.`, scopeNote(S));
    return card(`${rows.length} of ${S.whose} ancestors served in ${E(label)}.`,
      `<ul class="list">${rows.map(([k, ss]) => `<li>${who(k)}, ${S.whose} ${E(relTo(S, k))}` +
        `<div class="sub">${ss.map(s => E(s.war + (s.unit ? ": " + s.unit : ""))).join("<br>")}</div></li>`).join("")}</ul>` + scopeNote(S) +
      `<div class="acts"><a class="btn" href="map.html?military=1">See their service on the map</a></div>`);
  }
  function served(k, w) {
    const ss = services(k, w), recs = milRecords(k);
    const warName = s => { const x = s.war.replace(/[,;].*$/, ""); return /^(Revolution|Civil War|War of|French and Indian|Pequot|Creek)/.test(x) ? "the " + x : x; };
    if (ss.length) return card(`Yes. ${who(k)} served in ${E(w ? w.label : [...new Set(ss.map(warName))].join(" and "))}.`,
      ss.map(s => `<div class="svc"><div class="eyebrow">${E(s.war)}</div><p><b>${E(s.unit || "")}</b></p><p>${E(s.summary || "")}</p>` +
        (s.sources && s.sources.length ? `<p class="src">Sources: ${E(s.sources.join("; "))}</p>` : "") + `</div>`).join(""), k);
    if (recs.length) return card(`The tree has military records for ${who(k)}, but no documented service${w ? " in " + E(w.label) : ""}.`,
      `<ul class="list">${recs.map(e => `<li>${E(e[1] || "")} ${E(e[3] || "")}${e[4] ? " — " + E(e[4]) : ""}</li>`).join("")}</ul>`, k);
    const any = w && services(k, null);
    if (any && any.length) return card(`No record of ${who(k)} in ${E(w.label)}.`, `<p>${cap(he(k))} served in ${E(any.map(s => s.war).join("; "))}.</p>`, k);
    return card(`Nothing here shows ${who(k)} serving${w ? " in " + E(w.label) : ""}.`,
      onMap(k) ? `<p>Neither the tree nor the research behind the map records military service for ${his(k) === "their" ? "them" : sx(k, "him", "her", "them")}.</p>` : `<p>${cap(he(k))} isn&rsquo;t on the map, and the map&rsquo;s military research covers only direct ancestors.</p>`, k);
  }
  function vital(k, what) {
    const p = prof(k), born = what === "born", f = born ? "b" : "d";
    const date = p && p[f][0], place = p && p[f][1], y = born ? R.b[k] : R.d[k];
    if (born ? !date && !y : !date && !(y > 0)) {
      if (!born && !R.d[k] && living(k) === false && R.b[k] >= 1926) return card(`The tree has no death record for ${who(k)}.`);
      return card(`The tree doesn&rsquo;t record when ${who(k)} ${born ? "was born" : "died"}.`, place ? `<p>Place: ${E(place)}.</p>` : "", k);
    }
    let age = "";
    if (!born && R.b[k] && y > 0) age = ` ${cap(he(k))} was about ${y - R.b[k]}.`;
    return card(`${who(k)} ${born ? "was born" : "died"} ${date ? (/^\d{4}$/.test(date) ? "in " : /^(abt|about|bef|aft|before|after|cal|est)/i.test(date) ? "" : "on ") + E(date) : "in " + y}${place ? " in " + E(place) : ""}.`,
      age ? `<p>${age.trim()}</p>` : "", k);
  }
  function wherePlace(k, what) {
    const p = prof(k), x = p && p[what === "born" ? "b" : "d"];
    if (!x || !x[1]) return card(`The tree doesn&rsquo;t record where ${who(k)} ${what === "born" ? "was born" : "died"}.`, "", k);
    return card(`${who(k)} ${what === "born" ? "was born" : "died"} in ${E(x[1])}${x[0] ? ", " + E(x[0]) : ""}.`, "", k);
  }
  function lived(k) {
    const p = prof(k);
    if (!p) return card(`${who(k)} isn&rsquo;t on the map, so I only know ${his(k)} name and dates.`);
    const res = p.t.filter(e => ["born", "lived", "died"].includes(e[2]) && e[3]);
    const seen = new Set(), rows = res.filter(e => !seen.has(e[3]) && seen.add(e[3]));
    return card(`Where ${who(k)} lived`, `<ul class="list">${rows.map(e => `<li><b>${E(e[3])}</b> <span class="yrs">${E(e[1] || e[0] || "")}</span></li>`).join("")}</ul>`, k);
  }
  function family(k, what) {
    const f = R.f[k], m = R.m[k];
    if (what === "parents") {
      const ps = [f, m].filter(x => x >= 0);
      if (!ps.length) return card(`The tree doesn&rsquo;t name ${who(k)}&rsquo;s parents.`, "", k);
      const rel = R.r[k] ? ` (${E(R.r[k])} parents; the tree also has others)` : "";
      return card(`${who(k)}&rsquo;s parents: ${ps.map(who).join(" and ")}${rel}.`, "", k);
    }
    if (what === "father" || what === "mother") {
      const x = what === "father" ? f : m;
      return x >= 0 ? card(`${who(k)}&rsquo;s ${what} was ${who(x)}.`, "", k) : card(`The tree doesn&rsquo;t name ${who(k)}&rsquo;s ${what}.`, "", k);
    }
    if (what === "spouse") {
      const s = spouses[k];
      return s.length ? card(`${who(k)} married ${s.map(who).join(", then ")}.`, "", k) : card(`The tree doesn&rsquo;t record a marriage for ${who(k)}.`, "", k);
    }
    const c = kids[k].slice().sort((a, b) => (R.b[a] || 9999) - (R.b[b] || 9999));
    return c.length ? card(`${who(k)} had ${c.length} ${c.length === 1 ? "child" : "children"} in the tree.`, `<ul class="list">${c.map(x => `<li>${who(x)}</li>`).join("")}</ul>`, k)
      : card(`The tree records no children for ${who(k)}.`, "", k);
  }
  function person(k) {
    const p = prof(k), bits = [];
    const A = upMe();
    if (A) { const r = relate(A, k, "your"); if (r) bits.push(`${cap(he(k))} is ${r.kind === "blood" ? "your " : ""}${E(r.text)}.`); }
    if (p) {
      if (p.b[0] || p.b[1]) bits.push(`Born ${E([p.b[0], p.b[1]].filter(Boolean).join(", "))}.`);
      if (p.d[0] || p.d[1]) bits.push(`Died ${E([p.d[0], p.d[1]].filter(Boolean).join(", "))}.`);
      if (MILITARY[pid(k)]) bits.push(`Served in ${E(MILITARY[pid(k)].map(s => s.war).join("; "))}.`);
    } else if (!onMap(k)) bits.push(`${cap(he(k))} isn&rsquo;t one of Margaret&rsquo;s direct ancestors, so the map doesn&rsquo;t follow ${his(k) === "their" ? "them" : sx(k, "him", "her", "them")}.`);
    const story = p && p.st ? `<p class="story"><i>${E(p.st.title || "")}</i> — ${E((p.st.text || [])[0] || "").slice(0, 400)}${((p.st.text || [])[0] || "").length > 400 ? "…" : ""}</p>` : "";
    return card(who(k), `<p>${bits.join(" ")}</p>${story}`, k);
  }
  // ---------------------------------------------------------------- places and regions
  const US_STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia"];
  const AMERICA = new RegExp("\\b(" + US_STATES.join("|") + "|USA|United States|America|New England|Bermuda|Canada|Quebec|Ontario|Nova Scotia|Panama|Cuba|Jamaica|Barbados|Mexico)\\b", "i");
  // a region: towns or counties (t) that must sit in one of the states (s); or just the states
  const rx = a => new RegExp("\\b(" + a.join("|") + ")\\b", "i");
  const REGIONS = [
    [/hudson valley|hudson river valley|the hudson\b/, "the Hudson Valley", { s: /New York/, t: rx(["Albany", "Columbia", "Dutchess", "Greene", "Orange", "Putnam", "Rensselaer", "Rockland",
      "Saratoga", "Ulster", "Westchester", "Kingston", "Poughkeepsie", "Newburgh", "Hudson", "Fishkill", "Catskill", "Rhinebeck", "Peekskill", "Tarrytown",
      "Yonkers", "Troy", "Saugerties", "New Paltz", "Beacon", "Coxsackie", "Claverack", "Kinderhook", "Red Hook", "Hyde Park", "Goshen", "Cornwall",
      "Nyack", "Haverstraw", "Ossining", "White Plains", "Bedford", "Rye", "Mamaroneck", "New Rochelle", "Pound Ridge", "North Salem", "Somers",
      "Cortlandt", "Esopus", "Marbletown", "Hurley", "Wawarsing", "Shawangunk", "Walden", "Warwick", "New Windsor", "Stillwater", "Schaghticoke",
      "Waterford", "Lansingburgh", "Greenbush", "Schodack", "Philipsburg", "Livingston", "Durham", "Cairo", "Windham", "Greenville", "New Baltimore", "Athens"]),
      note: "Counted: Albany, Columbia, Dutchess, Greene, Orange, Putnam, Rensselaer, Rockland, Saratoga, Ulster and Westchester counties, and their towns." }],
    [/tri-?state|evansville area|evansville region/, "the Evansville tri-state area", { by: [
      [/Indiana/, rx(["Vanderburgh", "Warrick", "Posey", "Gibson", "Spencer", "Evansville", "Newburgh", "Mount Vernon", "Boonville", "Princeton", "Rockport", "New Harmony"])],
      [/Kentucky/, rx(["Henderson", "Daviess", "Union", "Webster", "McLean", "Mclean", "Hopkins", "Muhlenberg", "Owensboro", "Morganfield", "Uniontown", "Sturgis", "Sebree",
        "Calhoun", "Livermore", "Spottsville", "Hebbardsville", "Bremen", "South Carrollton", "Greenville", "Madisonville", "Tillottsons"])],
      [/Illinois/, rx(["White", "Wabash", "Gallatin", "Edwards", "Carmi", "Mount Carmel", "Shawneetown"])]],
      note: "Counted: Vanderburgh, Warrick, Posey, Gibson and Spencer counties in Indiana; Henderson, Daviess, Union, Webster, McLean, Hopkins and Muhlenberg in Kentucky; White, Wabash, Gallatin and Edwards in Illinois." }],
    [/long island/, "Long Island", { s: /New York/, t: rx(["Suffolk", "Nassau", "Queens", "Kings", "Brooklyn", "Southold", "Southampton", "East Hampton",
      "Huntington", "Hempstead", "Oyster Bay", "Jamaica", "Flushing", "Newtown", "Maspeth", "Rockville Centre", "Babylon", "Islip", "Brookhaven", "Smithtown"]) }],
    [/shenandoah/, "the Shenandoah Valley", { s: /Virginia/, t: rx(["Augusta", "Rockingham", "Shenandoah", "Frederick", "Page", "Warren", "Clarke",
      "Rockbridge", "Botetourt", "Berkeley", "Staunton", "Harrisonburg", "Winchester", "Woodstock", "Luray", "Front Royal", "Elkton"]) }],
    [/tidewater/, "Tidewater Virginia", { s: /Virginia/, t: rx(["James City", "Jamestown", "Williamsburg", "York", "Gloucester", "Isle of Wight",
      "Surry", "Norfolk", "Princess Anne", "Nansemond", "Warwick", "Elizabeth City", "Charles City", "Henrico", "Middlesex", "Lancaster",
      "Northumberland", "Westmoreland", "Essex", "King and Queen", "King William", "New Kent", "Mathews", "Accomack", "Northampton", "Portsmouth", "Hampton"]) }],
    [/bluegrass/, "the Bluegrass", { s: /Kentucky/, t: rx(["Fayette", "Bourbon", "Scott", "Woodford", "Jessamine", "Clark", "Madison", "Mercer", "Boyle",
      "Franklin", "Harrison", "Nicholas", "Lexington", "Paris", "Georgetown", "Versailles", "Danville", "Frankfort"]) }],
    [/catskill/, "the Catskills", { s: /New York/, t: rx(["Delaware", "Greene", "Ulster", "Sullivan", "Schoharie", "Delhi", "Walton", "Franklin", "Catskill"]) }],
    [/ohio valley|ohio river/, "the Ohio Valley", { t: rx(["Cincinnati", "Louisville", "Evansville", "Owensboro", "Henderson", "Paducah", "Maysville",
      "Pittsburgh", "Wheeling", "Marietta", "Ripley", "Madison", "Newburgh", "Mason", "Brown", "Clermont", "Jefferson", "Oldham", "Covington", "Kenton"]) }],
    [/black forest|schwarzwald/, "the Black Forest", { t: rx(["Baiersbronn", "Freudenstadt", "Schwarzwald", "Black Forest"]) }],
    [/\bulster\b(?!.*new york)/, "Ulster", { s: /Ireland/, t: rx(["Antrim", "Armagh", "Down", "Fermanagh", "Londonderry", "Derry", "Tyrone", "Donegal", "Cavan", "Monaghan", "Ulster"]) }],
    [/new england/, "New England", { s: /Connecticut|Massachusetts|Rhode Island|New Hampshire|Vermont|Maine|New England/ }],
    [/deep south/, "the Deep South", { s: /Georgia|Alabama|Mississippi|Louisiana|South Carolina/ }],
    [/\bthe south\b|southern states|\bdixie\b/, "the South", { s: /Virginia|Carolina|Georgia|Alabama|Mississippi|Louisiana|Tennessee|Kentucky|Florida|Arkansas|Texas/ }],
    [/midwest|middle west/, "the Midwest", { s: /Ohio|Indiana|Illinois|Michigan|Wisconsin|Minnesota|Iowa|Missouri|Kansas|Nebraska|Dakota/ }],
    [/mid-?atlantic/, "the Mid-Atlantic", { s: /New York|New Jersey|Pennsylvania|Delaware|Maryland/ }],
    [/\bthe west\b|west coast|pacific/, "the West", { s: /California|Oregon|Washington|Nevada|Arizona|Colorado|Utah|Idaho|Montana|Wyoming|New Mexico/ }],
    [/british isles|great britain|\bthe uk\b|united kingdom|\bbritain\b/, "Britain and Ireland", { s: /England|Scotland|Wales|Ireland|Britain/ }],
    [/\beurope\b|the old country|old world/, "Europe", { s: /England|Scotland|Wales|Ireland|Germany|Switzerland|Sweden|France|Netherlands|Holland|Norway|Denmark|Prussia|Hanover|Bavaria|Europe/ }],
    [/\bamerica\b|the us\b|the u\.s|united states|the colonies/, "America", { s: AMERICA }],
  ];
  const ADJ = { irish: "Ireland", german: "Germany", english: "England", scottish: "Scotland", scotch: "Scotland", "scots-irish": "Ireland", welsh: "Wales",
    swiss: "Switzerland", swedish: "Sweden", dutch: "Netherlands", french: "France", british: "England", norwegian: "Norway", danish: "Denmark",
    prussian: "Prussia", italian: "Italy", canadian: "Canada", huguenot: "France" };
  // countries, with the regions the tree's places name without the country ("Siselen, Bern")
  const COUNTRY = {
    Switzerland: /\b(Switzerland|Schweiz|Bern|Berne|Zürich|Zurich|Basel|Aargau|Seeland|Siselen|Lucerne|Luzern|Solothurn|Thurgau|Glarus|Graubünden|Vaud|Neuchâtel|Fribourg|Emmental)\b/i,
    Germany: /\b(Germany|Deutschland|Baden|Württemberg|Wurttemberg|Baiersbronn|Hanover|Hannover|Bavaria|Bayern|Prussia|Hesse|Hessen|Pfalz|Palatinate|Niedersachsen|Saxony|Westphalia|Rhineland|Bremen, Germany|Elberfeld|Osterholz|Worpswede)\b/i,
    Ireland: /\b(Ireland|Cavan|Tyrone|Monaghan|Antrim|Armagh|Donegal|Londonderry|Derry|Fermanagh|Roscommon|Dublin|Cork|Ulster)\b/i,
    Sweden: /\b(Sweden|Sverige|Götaland|Gotaland|Småland|Smaland|Jönköping|Jonkoping|Västra|Vastra)\b/i,
    Scotland: /\bScotland\b/i, Wales: /\b(Wales|Glamorgan\w*)\b/i, England: /\b(England|Kent|Essex|Suffolk|Norfolk, England|Yorkshire|Devon|London)\b/i,
    France: /\b(France|Le Havre|Alsace|Lorraine)\b/i, Netherlands: /\b(Netherlands|Holland)\b/i,
  };
  // a test for a place phrase: a region, a country adjective, a state, or any place text
  function placeTest(s) {
    s = s.trim().replace(/^the /i, "").replace(/[?.!]+$/, "");
    for (const [re, label, def] of REGIONS) if (re.test(s.toLowerCase()))
      return { label, note: def.note, test: pl => !!pl && (def.by ? def.by.some(([st, t]) => st.test(pl) && t.test(pl)) : (!def.s || def.s.test(pl)) && (!def.t || def.t.test(pl))) };
    const a = ADJ[s.toLowerCase()] || Object.keys(COUNTRY).find(c => c.toLowerCase() === s.toLowerCase());
    if (a) { const re = COUNTRY[a] || new RegExp("\\b" + a + "\\b", "i"); return { label: a, test: pl => !!pl && re.test(pl) }; }
    if (!s || s.length < 3) return null;
    const esc = s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/,?\s+(county|co\.?)$/i, "");
    const re = new RegExp("\\b" + esc + "\\b", "i");
    const known = US_STATES.some(st => st.toLowerCase() === s.toLowerCase());          // a state is a place even if no one lived there
    return { label: s.replace(/\b\w/g, c => c.toUpperCase()), test: pl => !!pl && re.test(pl), literal: !known };
  }
  // the places recorded for someone: [year, place, kind]
  function placesOf(k, kinds = null) {
    const p = prof(k), out = [];
    if (!p) return out;
    for (const e of p.t) if (e[3] && (!kinds || kinds.includes(e[2]))) out.push([e[0], e[3], e[2]]);
    if (p.b[1] && (!kinds || kinds.includes("born"))) out.push([R.b[k] || null, p.b[1], "born"]);
    if (p.d[1] && (!kinds || kinds.includes("died"))) out.push([R.d[k] > 0 ? R.d[k] : null, p.d[1], "died"]);
    if (p.bu && (!kinds || kinds.includes("buried"))) out.push([R.d[k] > 0 ? R.d[k] : null, p.bu, "buried"]);
    return out;
  }
  const LIVED = ["born", "lived", "died", "married", "buried", "Arrival"];

  // ---------------------------------------------------------------- the text of someone's records, for topic searches
  const blobs = new Map();
  function blob(k) {
    if (blobs.has(k)) return blobs.get(k);
    const p = prof(k), parts = [];
    if (p) {
      // James's context lines ("James Monroe was President ...", "Born in reign of Queen Victoria ...") aren't about the person
      for (const n of p.nt || []) parts.push(["note", n.replace(/[^.]*\b(was|were) (the )?(Royal |Lieutenant |Colonial )?(President|Governor|Mayor|Prime Minister|King|Queen)\b[^.]*\.?/g, "")
        .replace(/Born in (the )?reign of [^.]*\.?/gi, "").trim()]);
      if (p.st) parts.push(["story", (p.st.title || "") + ". " + (p.st.text || []).join(" ")]);
      for (const e of p.t) if (!["born", "lived", "died", "buried"].includes(e[2]) || e[4]) parts.push(["record", [e[1], e[2], e[3], e[4]].filter(Boolean).join(", ")]);
      for (const i of p.r || []) parts.push(["source", PROFILES.sources[i]]);
    }
    for (const s of MILITARY[pid(k)] || []) parts.push(["service", `${s.war}: ${s.unit || ""}. ${s.summary || ""}`]);
    for (const e of NOTABLE.events) if (e.p.includes(pid(k))) parts.push(["event", `${e.d}, ${e.l}: ${e.t}`]);
    blobs.set(k, parts);
    return parts;
  }
  function snippet(text, re) {
    const m = re.exec(text); if (!m) return "";
    const a = Math.max(0, m.index - 90), b = Math.min(text.length, m.index + m[0].length + 110);
    return (a ? "…" : "") + E(text.slice(a, m.index)) + "<mark>" + E(m[0]) + "</mark>" + E(text.slice(m.index + m[0].length, b)) + (b < text.length ? "…" : "");
  }
  function mentions(k, re, where = null) {
    for (const [kind, t] of blob(k)) { if (where && !where.includes(kind)) continue; re.lastIndex = 0; if (re.test(t)) { re.lastIndex = 0; return { kind, html: snippet(t, re) }; } }
    return null;
  }
  // topics: words people ask about -> what to look for in the records
  const TOPICS = [
    [/royal|royalty|king|queen|prince|princess|monarch|crown|plantagenet|magna carta/, "royalty", /\b([Rr]oyal (descent|line|lineage|blood|family|ancestry|house|court|household|post|bastard)|[Rr]oyalty|King (Edward|Henry|John|William the Conqueror|Charles|James|Richard|Stephen|Robert the Bruce|David|Malcolm|Alfred|Louis)\b|King's (Posts|household|council|court)|Queen (Elizabeth|Mary|Anne|Eleanor|Isabella|Catherine)\b|Plantagenet|Magna Carta|[Mm]onarch|Tudor|Charlemagne|Henry VIII|Edward (I|III)\b)/],
    [/knight/, "knighthood", /\b([Kk]nighted|[Kk]nighthood|a knight|Knight of|Sir [A-Z][a-z]+)\b/],
    [/noble|nobility|aristocra|title|titled|gentry|\bsir\b|lord|baron|earl|duke|coat of arms/, "a title or the gentry", /\b([Kk]nighted|a knight|Knight of|Sir [A-Z][a-z]+|[Bb]aronet|Baron [A-Z]|Earl of|Duke of|Lord [A-Z][a-z]+|Lady [A-Z][a-z]+|[Gg]entry|[Gg]entleman|Esquire|[Cc]oat of arms|[Aa]rmiger\w*|[Nn]obility)\b/],
    [/witch/, "witchcraft", /\b(witch\w*)\b/i],
    [/slave|enslav/, "slavery", /\b(slaves?|enslaved|slave ?holders?|slavery|negro(es)?)\b/i],
    [/indian|native american|natives|cherokee|creek|powhatan|pequot|shawnee|iroquois|wampanoag|narragansett|tribe/, "Native Americans", /\b(Indians?|Native Americans?|Cherokee|Creek|Powhatan|Pequot|Shawnee|Iroquois|Seneca|Wampanoag|Narragansett|Mohegan|tribe|massacre|captivity)\b/i],
    [/farmer|farming|farm\b|planter|plantation|agricultur|yeoman|husbandman/, "farming", /\b([Ff]arm(er|ers|ing|ed)?(?! Museum)|[Ff]arm [Hh]and|[Pp]lanter|[Pp]lantation|[Yy]eoman|[Hh]usbandman|[Aa]gricultur(e|ist|al laborer))\b/],
    [/minister|reverend|pastor|preacher|clergy|deacon|ordain/, "the ministry", /\b((?<!Prime )[Mm]inister(?! of)|[Rr]everend|Rev\. [A-Z]|[Pp]astor|[Pp]reacher|[Cc]lergy(man)?|[Oo]rdained|[Dd]eacon)\b/],
    [/church|religio|faith|baptist|methodist|presbyterian|lutheran|catholic|episcopal|congregational/, "church or religion", /\b(church|congregation|parish|Baptist|Methodist|Presbyterian|Congregational|Anglican|Episcopal|Lutheran|Catholic|Reformed|baptized|christened)\b/i],
    [/quaker|friends meeting/, "the Quakers", /\b(Quakers?|Society of Friends|Friends Meeting|monthly meeting)\b/i],
    [/harvard/, "Harvard", /\bHarvard\b/i], [/yale/, "Yale", /\bYale\b/i],
    [/college|university|educat|graduat|school/, "school or college", /\b(college|university|Harvard|Yale|graduated|degree|school(master|teacher)?|academy|seminary)\b/i],
    [/doctor|physician|surgeon|medic/, "medicine", /\b(physician|doctor|surgeon|Dr\.|medical|medicine|apothecary)\b/i],
    [/governor/, "a governorship", /\bgovernor\b/i],
    [/legislat|burgess|assembly|congress|senat|representative|general court|politic|office/, "public office", /\b(burgess(es)?|House of Burgesses|assembly|legislat\w+|general court|deputy|congress\w*|senat\w+|representative|selectm[ae]n|justice of the peace|magistrate|sheriff|mayor|Speaker)\b/i],
    [/found|settler|first settler|proprietor/, "founding a town", /\b(found(ed|er|ers|ing)|first settlers?|original proprietors?|proprietors?|laid out|patent)\b/i],
    [/ran a newspaper|newspaper (man|owner|editor|publisher)|editor|publisher|printer|journalis/, "running a newspaper", /\b([Ee]ditor|[Pp]ublisher|[Pp]rinter|[Jj]ournalist|founded (by )?["“]?The|The (Franklin Register|Walton Chronicle|Oneonta Spy)|newspaper (owner|editor|publisher))\b/],
    [/lawyer|attorney/, "the law", /\b(lawyer|attorney|counsel(l)?or at law|admitted to the bar)\b/i],
    [/judge|justice|magistrate/, "the courts", /\b([Jj]udge|[Jj]ustice of the [Pp]eace|[Mm]agistrate|[Cc]hief [Jj]ustice)\b/],
    [/sheriff|constable|police/, "law enforcement", /\b(sheriff|constable|police\w*|marshal)\b/i],
    [/teacher|schoolmaster|taught/, "teaching", /\b(teacher|schoolmaster|taught|school ?teacher|professor)\b/i],
    [/merchant|trader|store|shop|business/, "trade", /\b(merchant|trader|store(keeper)?|shop(keeper)?|business|mill(er)?|tavern|innkeeper)\b/i],
    [/carpenter|blacksmith|\bsmith\b|\bmason\b|cooper|tanner|weaver|shoemaker|\bcrafts?(man|men)?\b|tradesm/, "a craft", /\b(carpenter|blacksmith|joiner|mason|cooper|tanner|weaver|shoemaker|cordwainer|wheelwright|saddler|tailor|potter)\b/i],
    [/sailor|mariner|sea captain|ship ?captain|navy|seaman/, "the sea", /\b(mariner|sailor|seaman|sea captain|navy|naval|ship master|whal\w+)\b/i],
    [/prisoner|captur|captive|pow\b/, "captivity", /\b(prisoner|captured|captive|captivity|imprison\w*|parole[d]?)\b/i],
    [/pension/, "a pension", /\bpension\w*\b/i],
    [/officer|captain|lieutenant|colonel|major|general|ensign|rank/, "an officer's rank", /\b(captain|capt\.|lieutenant|lt\.|colonel|col\.|major|general|ensign|commissioned)\b/i],
    [/\bwills?\b|probate|estate|inherit/, "a will or probate", /\b(Wills?( and| &) Probate|[Pp]robate|last will|his will|her will|[Tt]estament|[Ee]xecut(or|rix)|[Ii]nventory of|bequeath\w*)\b/],
    [/obituar/, "an obituary", /\bobituar\w*\b/i],
    [/newspaper|in the news|article/, "the newspaper", /\b(newspaper|article|Newspapers\.com|Courier|Gazette|Journal|Times|Star)\b/i],
    [/scout/, "the Boy Scouts", /\bscouts?\b/i],
    [/ellis island/, "Ellis Island", /\bEllis Island\b/i],
    [/mayflower/, "the Mayflower", /\bMayflower\b/i],
    [/jamestown/, "Jamestown", /\bJamestown\b/i],
    [/salem/, "Salem", /\bSalem\b/i],
    [/shipwreck|wreck/, "a shipwreck", /\b(wreck(ed)?|shipwreck)\b/i],
    [/famous|notable|historic|important|well known/, "something notable", null],
    [/twin/, "twins", /\btwins?\b/i],
    [/murder|killed|drown|accident|disease|epidemic|cholera|smallpox|fever|flu\b|influenza/, "how they died", /\b(murder\w*|killed|drown\w*|accident\w*|cholera|smallpox|fever|influenza|consumption|tuberculosis|epidemic|shot|wounded)\b/i],
  ];
  function topicOf(s) {
    const l = s.toLowerCase();
    for (const [re, label, look] of TOPICS) if (re.test(l)) return { label, look };
    return null;
  }

  // ---------------------------------------------------------------- lists of people
  function listCard(head, rows, S, extra = "") {
    const MAX = 60;
    return card(head, `<ul class="list">${rows.slice(0, MAX).map(([k, sub]) => `<li>${who(k)}${S && S.A.get(k) ? `, ${S.whose} ${E(relTo(S, k))}` : ""}` +
      (sub ? `<div class="sub">${sub}</div>` : "") + `</li>`).join("")}</ul>` +
      (rows.length > MAX ? `<p class="note">Showing ${MAX} of ${rows.length}.</p>` : "") + extra + (S ? scopeNote(S) : ""));
  }
  const byGen = S => (a, b) => (S.A.get(a[0]) ? S.A.get(a[0]).d : 99) - (S.A.get(b[0]) ? S.A.get(b[0]).d : 99) || (R.b[a[0]] || 0) - (R.b[b[0]] || 0);
  const byYear = (a, b) => (R.b[a[0]] || 9999) - (R.b[b[0]] || 9999);
  // who, of the ancestors in scope, meets a test; rows are [k, html about why]
  function group(S, test, head, sort = byYear, many = false, count = false) {
    const rows = [];
    for (const k of S.set) { if (!R.n[k]) continue; const why = test(k); if (why) rows.push([k, why === true ? "" : why]); }
    rows.sort(sort);
    return rows;
  }
  function groupAnswer(S, rows, what, count, none, extra = "") {
    if (!rows.length) return card(none || `I found none of ${S.whose} ancestors who ${what}.`, `<p class="note">Only the ${GRAPH ? Object.keys(GRAPH.people).length.toLocaleString() : ""} people on the map have full records to search.</p>` + scopeNote(S));
    const n = rows.length, w1 = n === 1 ? what.replace(/^were /, "was ").replace(/^have /, "has ").replace(/^are /, "is ") : what;
    return listCard(`${n === 1 ? "One of" : n + " of"} ${S.whose} ancestors ${w1}.`, rows, S, extra);
  }
  const years = k => [R.b[k], R.d[k] > 0 ? R.d[k] : 0];
  const age = k => { const [b, d] = years(k); return b && d ? d - b : null; };
  function aliveIn(k, y0, y1 = y0) {
    const [b, d] = years(k);
    if (!b && !d) return false;
    const from = b || d - 60, to = d || (b + 70);
    return from <= y1 && to >= y0;
  }
  const PERIODS = [
    [/revolution|revolutionary war/, [1775, 1783], "the Revolution"], [/civil war/, [1861, 1865], "the Civil War"],
    [/war of 1812/, [1812, 1815], "the War of 1812"], [/great depression|depression/, [1929, 1939], "the Great Depression"],
    [/world war (ii|2|two)|wwii|ww2/, [1939, 1945], "World War II"], [/world war (i|1|one)\b|wwi\b|ww1|great war/, [1914, 1918], "World War I"],
    [/columbus/, [1492, 1492], "Columbus's voyage"], [/mayflower|plymouth/, [1620, 1620], "the Mayflower's voyage"],
    [/jamestown/, [1607, 1607], "the founding of Jamestown"], [/gold rush/, [1848, 1855], "the Gold Rush"],
    [/french (and|&) indian/, [1754, 1763], "the French and Indian War"], [/king philip/, [1675, 1676], "King Philip's War"],
    [/salem witch|witch trials/, [1692, 1693], "the Salem witch trials"], [/declaration|independence/, [1776, 1776], "1776"],
  ];
  function period(s) {
    const l = s.toLowerCase();
    for (const [re, r, label] of PERIODS) if (re.test(l)) return { r, label };
    let m;
    if ((m = /\b(1[0-9])00s\b/.exec(l)) || (m = /\b(1[0-9]|2[01])(?:st|nd|rd|th) century\b/.exec(l)))
      { const c = /century/.test(m[0]) ? +m[1] - 1 : +m[1]; return { r: [c * 100, c * 100 + 99], label: `the ${c * 100}s` }; }
    if ((m = /\b(1[5-9]\d|20[0-2])0s\b/.exec(l))) return { r: [+m[1] * 10, +m[1] * 10 + 9], label: `the ${m[1]}0s` };
    if ((m = /\bbetween (1[5-9]\d\d|20[0-2]\d) and (1[5-9]\d\d|20[0-2]\d)\b/.exec(l))) return { r: [+m[1], +m[2]], label: `${m[1]}–${m[2]}` };
    if ((m = /\bbefore (1[5-9]\d\d|20[0-2]\d)\b/.exec(l))) return { r: [0, +m[1] - 1], label: `before ${m[1]}` };
    if ((m = /\bafter (1[5-9]\d\d|20[0-2]\d)\b/.exec(l))) return { r: [+m[1] + 1, 3000], label: `after ${m[1]}` };
    if ((m = /\b(1[5-9]\d\d|20[0-2]\d)\b/.exec(l))) return { r: [+m[1], +m[1]], label: m[1] };
    return null;
  }
  // where George Washington was in person, and when (for "who may have met Washington"): a stop counts
  // only if its place and its first year match (Long Island in 1776, not the British lines there in 1777-79)
  const WASHINGTON = [[/Fort Necessity|Great Meadows/i, [1754]], [/Monongahela|Braddock/i, [1755]], [/Cambridge|Boston|Dorchester/i, [1775, 1776]],
    [/Long Island|Brooklyn Heights|Harlem Heights/i, [1776]], [/White Plains/i, [1776, 1778]], [/Trenton/i, [1776, 1777]], [/Princeton/i, [1777]],
    [/Brandywine/i, [1777]], [/Germantown/i, [1777]], [/Valley Forge/i, [1777, 1778]], [/Monmouth/i, [1778]], [/Morristown|Jockey Hollow/i, [1777, 1779, 1780]],
    [/Yorktown/i, [1781]], [/Newburgh|New Windsor/i, [1782, 1783]]];
  function metWashington(S) {
    const rows = [];
    for (const k of S.set) {
      const why = [];
      for (const s of MILITARY[pid(k)] || []) for (const st of s.stops || []) {
        const place = (st.b || "") + " " + (st.l || ""), y = /\d{4}/.exec(st.d || ""), yy = y ? +y[0] : 0;
        if (WASHINGTON.some(([re, ys]) => re.test(place) && ys.includes(yy))) why.push(`${E(st.b || st.l)}, ${E(st.d || "")}`);
      }
      // his name alone isn't enough (a brother named George Washington Howell): the general, his army, serving under him
      const t = mentions(k, /\b(General Washington|Gen\.? Washington|President Washington|(under|with|by) (General |Gen\. |Col\. |Colonel )?(George )?Washington\b(?! (Co|County|Township))|Washington's (army|headquarters|guard|life ?guard|staff|command))/i, ["note", "story", "service", "event"]);
      if (t) why.push(t.html);
      if (why.length) rows.push([k, [...new Set(why)].slice(0, 4).join("<br>")]);
    }
    rows.sort(byYear);
    if (!rows.length) return card(`None of ${S.whose} ancestors is recorded anywhere George Washington was.`, scopeNote(S));
    return listCard(`${rows.length} of ${S.whose} ancestors were where George Washington was, or their records mention him.`, rows, S,
      `<p class="note">Being in the same army, battle or winter camp as Washington doesn&rsquo;t mean they met him. These are the ancestors whose service put them where he commanded in person ` +
      `(Fort Necessity, Braddock&rsquo;s march, the siege of Boston, Long Island, White Plains, Trenton, Princeton, Brandywine, Germantown, Valley Forge, Monmouth, Morristown, Yorktown), or whose records name him.</p>`);
  }

  // ---------------------------------------------------------------- the question
  let pending = null;
  function needMe(q) {
    pending = q;
    return card("First, who are you?", pickerHTML());
  }
  function pickerHTML() {
    // the picker itself is the "Viewing as" button in the header (viewer.js), shared by every page
    return `<p>Choose yourself with the <b>Viewing as</b> button at the top right: it&rsquo;s remembered on this device and used by the map, the tree and the People page too.</p>` +
      `<p><button class="chip" data-act="me">Choose who I am</button></p>` +
      (Family.shown ? "" : `<p class="note">Living family are listed only after the family password is entered (the lock at the top right). ` +
        `Otherwise, choose a parent or grandparent who has died.</p>`);
  }
  const isMe = s => /^(me|myself|i|us|we)$/i.test(s.trim());
  const EXAMPLES = ["How am I related to John Coe?", "When was Sudie Clay born?", "Did Jared Hitchcock serve in the Revolutionary War?",
    "Which of my ancestors fought in the Revolutionary War?", "Which of my ancestors may have met George Washington?", "Which of my ancestors were farmers?",
    "How many of my ancestors lived in the Hudson Valley?", "Who were Thomas Baskett's parents?", "Which ancestors were born in Ireland?",
    "Where did William Worthington live?", "Who is my earliest ancestor?", "Which ancestors came on the Speedwell?", "Who had a connection to royalty?",
    "Who was alive in 1776?", "Tell me about the Basketts", "Who lived the longest?", "Who are my great-grandparents?", "Tell me a family story"];

  function help() {
    const groups = [["You and your family", ["How am I related to John Coe?", "Who are my great-grandparents?", "What is my paternal line?", "How far back does my tree go?"]],
      ["People", ["When was Sudie Clay born?", "Where did William Worthington live?", "Who were Thomas Baskett's parents?", "Tell me about Mehitable Leete", "Do we have a photo of Sudie Clay?"]],
      ["Service and history", ["Which of my ancestors fought in the Revolutionary War?", "Who fought at Monmouth?", "Which of my ancestors may have met George Washington?", "Who came on the Speedwell?"]],
      ["Places and eras", ["How many of my ancestors lived in the Hudson Valley?", "Which ancestors were born in Ireland?", "Who was alive in 1776?", "What was happening in my family in 1850?"]],
      ["Topics", ["Which of my ancestors were farmers?", "Who had a connection to royalty?", "Which ancestors were ministers?", "Tell me about the Basketts", "Tell me a family story"]]];
    return card("Here&rsquo;s what you can ask", groups.map(([h, qs]) => `<div class="eyebrow">${h}</div><div class="chips" style="margin:6px 0 14px">${qs.map(x => `<button class="chip" data-ask="${E(x)}">${E(x)}</button>`).join("")}</div>`).join("") +
      `<p class="note">Answers come only from the family tree and the research behind the map. I understand many ways of asking, but not everything; if a question doesn&rsquo;t work, try one of these shapes.</p>`);
  }
  function about() {
    return card("About these answers", `<p>This page answers from James Hitchcock&rsquo;s family tree on Ancestry (${R.n.length.toLocaleString()} people) and the research behind the map: ` +
      `military service from pension files and service records, notable events from published histories, and each person&rsquo;s records and notes. It doesn&rsquo;t use an AI model and doesn&rsquo;t look anything up online.</p>` +
      `<p>The tree is a work in progress. Dates and places are only as good as the records behind them; each profile on the map lists the records attached to that person.</p>` +
      `<div class="acts"><a class="btn" href="about.html">About the site</a><a class="btn" href="people.html">Everyone on the map</a></div>`);
  }

  // one person's photos, occupation, cause of death, records, siblings, grandparents, descendants
  function photo(k) {
    const p = prof(k);
    if (!p || !p.ph) return card(`There&rsquo;s no portrait of ${who(k)} on the site.`, living(k) ? "" : `<p class="note">Portraits come from James&rsquo;s photos and Ancestry profile pictures.</p>`, k);
    return card(who(k), `<div class="photos">${p.ph.map(src => `<img src="${E(src)}" alt="${E(name(k))}">`).join("")}</div>`, k);
  }
  function occupation(k) {
    const re = /\b(occupation|farm(er|ing)?|planter|merchant|minister|reverend|pastor|physician|doctor|lawyer|attorney|editor|printer|publisher|teacher|carpenter|blacksmith|miller|mariner|sailor|clerk|laborer|labourer|salesman|engineer|mechanic|manager|owner|worked|employed|business|store|founded|newspaper)\b/i;
    const hits = blob(k).filter(([kind, t]) => kind !== "source" && re.test(t)).slice(0, 6);
    if (!hits.length) return card(`The tree doesn&rsquo;t record what ${who(k)} did for a living.`, `<p class="note">Census records often say; they may be attached in Ancestry without an occupation entered.</p>`, k);
    return card(`What the records say about ${who(k)}&rsquo;s work`, `<ul class="list">${hits.map(([kind, t]) => `<li>${snippet(t, re)}</li>`).join("")}</ul>`, k);
  }
  function howDied(k) {
    const re = /\b(died of|death from|cause of death|killed|drown\w*|murder\w*|accident\w*|cholera|smallpox|fever|influenza|consumption|tuberculosis|pneumonia|cancer|heart|wounds?|shot|executed|lost at sea)\b/i;
    const hits = blob(k).filter(([kind, t]) => kind !== "source" && re.test(t)).slice(0, 4);
    const base = vitalText(k, "died");
    if (!hits.length) return card(`The tree doesn&rsquo;t say how ${who(k)} died.`, base ? `<p>${base}</p>` : "", k);
    return card(`How ${who(k)} died`, (base ? `<p>${base}</p>` : "") + `<ul class="list">${hits.map(([, t]) => `<li>${snippet(t, re)}</li>`).join("")}</ul>`, k);
  }
  function vitalText(k, what) {
    const p = prof(k), f = what === "born" ? "b" : "d";
    const x = p ? p[f] : ["", ""], y = what === "born" ? R.b[k] : R.d[k];
    const when = x[0] || (y > 0 ? String(y) : ""), where = x[1];
    if (!when && !where) return "";
    return `${cap(he(k))} ${what === "born" ? "was born" : "died"}${when ? " " + (/^\d{4}$/.test(when) ? "in " : /^(abt|about|bef|aft|before|after|cal|est)/i.test(when) ? "" : "on ") + E(when) : ""}${where ? " in " + E(where) : ""}.`;
  }
  function buried(k) {
    const p = prof(k);
    if (!p || !p.bu) return card(`The tree doesn&rsquo;t record where ${who(k)} is buried.`, vitalText(k, "died") ? `<p>${vitalText(k, "died")}</p>` : "", k);
    return card(`${who(k)} is buried in ${E(p.bu)}.`, vitalText(k, "died") ? `<p>${vitalText(k, "died")}</p>` : "", k);
  }
  function lifespan(k) {
    const a = age(k);
    if (a == null) return vital(k, R.b[k] ? "died" : "born");
    return card(`${who(k)} lived about ${a} years.`, [vitalText(k, "born"), vitalText(k, "died")].filter(Boolean).map(x => `<p>${x}</p>`).join(""), k);
  }
  function records(k) {
    const p = prof(k);
    if (!p || !(p.r || []).length) return card(`No records are attached to ${who(k)} in the tree.`, "", k);
    const src = p.r.map(i => PROFILES.sources[i]);
    return card(`${src.length} record${src.length === 1 ? "" : "s"} attached to ${who(k)}`, `<ul class="list">${src.slice(0, 40).map(s => `<li>${E(s)}</li>`).join("")}</ul>` +
      (src.length > 40 ? `<p class="note">The first 40.</p>` : ""), k);
  }
  function siblings(k) {
    const f = R.f[k], m = R.m[k];
    const full = [], half = [];
    for (const p of [f, m]) if (p >= 0) for (const c of kids[p]) if (c !== k && !full.includes(c) && !half.includes(c)) {
      const same = (f < 0 || R.f[c] === f) && (m < 0 || R.m[c] === m);
      (same ? full : half).push(c);
    }
    const all = full.concat(half).sort((a, b) => (R.b[a] || 9999) - (R.b[b] || 9999));
    if (!all.length) return card(`The tree records no brothers or sisters for ${who(k)}.`, "", k);
    return card(`${who(k)} had ${all.length} ${all.length === 1 ? "sibling" : "siblings"} in the tree.`,
      `<ul class="list">${all.map(c => `<li>${who(c)}${half.includes(c) ? ' <span class="sub">half-sibling</span>' : ""}</li>`).join("")}</ul>`, k);
  }
  function generation(k, n, whose) {
    const M = up(k), rows = [...M].filter(([x, v]) => v.d === n && x !== ME).map(([x]) => x).sort((a, b) => (R.b[a] || 0) - (R.b[b] || 0));
    const label = term(n, 0, -1).replace(/father|mother/, "parent").replace(/grandfather|grandmother/, "grandparent") + "s";
    if (!rows.length) return card(`The tree names none of ${whose} ${label}.`);
    return card(`${cap(whose)} ${label}${rows.length < 2 ** n ? ` (${rows.length} of ${2 ** n} named)` : ""}`,
      `<ul class="list">${rows.map(x => `<li>${who(x)}</li>`).join("")}</ul>` + faces(rows));
  }
  function faces(rows) {
    const ph = rows.map(k => [k, prof(k)]).filter(([, p]) => p && p.ph);
    return ph.length ? `<div class="photos small">${ph.slice(0, 16).map(([k, p]) => `<a href="map.html#p=${encodeURIComponent(pid(k))}" title="${E(name(k))}"><img src="${E(p.ph[0])}" alt="${E(name(k))}"></a>`).join("")}</div>` : "";
  }
  function descendants(k) {
    const out = []; let fr = [k], seen = new Set([k]);
    for (let d = 1; fr.length && d < 30; d++) { const nx = []; for (const x of fr) for (const c of kids[x]) if (!seen.has(c)) { seen.add(c); nx.push(c); out.push([c, d]); } fr = nx; }
    const named = out.filter(([c]) => R.n[c]);
    return card(`The tree has ${out.length.toLocaleString()} descendants of ${who(k)}.`,
      `<p>${[1, 2, 3].map(d => `${out.filter(x => x[1] === d).length} ${["", "children", "grandchildren", "great-grandchildren"][d]}`).join(", ")}; ` +
      `${Math.max(0, ...out.map(x => x[1]))} generations in all.</p>` + (named.length && named.length <= 40 ? `<ul class="list">${named.map(([c, d]) => `<li>${who(c)} <span class="sub">${E(term(0, d, c))}</span></li>`).join("")}</ul>` : ""), k);
  }
  const journey = k => card(`${who(k)}&rsquo;s journey`, (PERSON_LEGS[pid(k)] || []).length
    ? `<ol class="line">${PERSON_LEGS[pid(k)].map(l => `<li>${E(l.from)} &rarr; ${E(l.to)} <span class="yrs">${l.year}</span></li>`).join("")}</ol>`
    : `<p>The tree records no moves for ${sx(k, "him", "her", "them")}.</p>`, k);

  // ---------------------------------------------------------------- surnames
  function surnameOf(s) {
    const w = s.toLowerCase().replace(/^the /, "").replace(/ family$/, "").replace(/'s$/, "").trim();
    if (!w || / /.test(w)) return null;
    const cands = [w, w.replace(/es$/, ""), w.replace(/s$/, "")];
    for (const c of cands) for (const p of Object.values(GRAPH.people)) if (p.surname && p.surname.toLowerCase() === c) return p.surname;
    return null;
  }
  const withSurname = (S, sn) => [...S.set].filter(k => GRAPH.people[pid(k)] && GRAPH.people[pid(k)].surname === sn);
  function surnameAbout(sn, what) {
    let S = scope(), rows = withSurname(S, sn);
    const inTree = R.n.filter(n => n && new RegExp("\\b" + sn + "$", "i").test(n)).length;
    let other = "";
    if (!rows.length && !S.note) {          // not your line; perhaps Margaret's (the Askews, for James)
      const root = at.get(GRAPH.james_id), M = up(root);
      const S2 = { set: new Set([...M.keys()].filter(x => M.get(x).d > 0)), A: M, whose: "Margaret&rsquo;s", who: "Margaret", note: true };
      if (withSurname(S2, sn).length) { other = `<p class="note">None of your ancestors are ${E(sn)}s; these are Margaret&rsquo;s.</p>`; S = S2; rows = withSurname(S2, sn); }
    }
    rows.sort((a, b) => (R.b[a] || 9999) - (R.b[b] || 9999));
    if (!rows.length) return card(`None of ${S.whose} ancestors on the map are ${E(sn)}s.`, `<p>The whole tree has ${inTree} people named ${E(sn)}.</p>` + scopeNote(S));
    const first = rows.find(k => R.b[k]) ?? rows[0], p = prof(first);
    const firstUS = rows.find(k => { const pp = prof(k); return pp && AMERICA.test(pp.b[1] || ""); });
    const arr = NOTABLE.events.filter(e => e.k === "arrival" && e.p.some(x => rows.includes(at.get(x)))).sort((a, b) => a.y - b.y)[0];
    const states = new Map();
    for (const k of rows) for (const [, pl] of placesOf(k, LIVED)) { const st = pl.split(", ").pop(); states.set(st, (states.get(st) || 0) + 1); }
    const where = [...states].sort((a, b) => b[1] - a[1]).slice(0, 8).map(x => x[0]);
    const vets = rows.filter(k => MILITARY[pid(k)]);
    if (what === "first") return card(`The earliest ${E(sn)} in ${S.whose} line is ${who(first)}.`, p && p.b[1] ? `<p>Born ${E(p.b[0] || "")} in ${E(p.b[1])}.</p>` + scopeNote(S) : scopeNote(S), first);
    if (what === "count") return card(`${rows.length} of ${S.whose} ancestors are ${E(sn)}s.`, `<p>The whole tree has ${inTree} people with the surname.</p>` + scopeNote(S));
    const bits = [`${rows.length} of ${S.whose} ancestors on the map are ${E(sn)}s (the whole tree has ${inTree}).`,
      `The earliest is ${who(first)}${p && p.b[1] ? `, born in ${E(p.b[1])}` : ""}.`];
    if (arr) bits.push(`The first to arrive in America: ${arr.p.filter(x => rows.includes(at.get(x))).map(x => who(at.get(x))).join(", ")}, ${E(arr.d)}${arr.sh ? " on the " + E(arr.sh) : ""}.`);
    else if (firstUS != null) bits.push(`The first born in America: ${who(firstUS)}, in ${E(prof(firstUS).b[1])}.`);
    if (where.length) bits.push(`They lived in ${E(where.join(", "))}.`);
    if (vets.length) bits.push(`${vets.length} served in the military: ${vets.map(who).join(", ")}.`);
    return card(`The ${E(sn)}s`, other + `<p>${bits.join(" ")}</p><ul class="list">${rows.slice(0, 40).map(k => `<li>${who(k)}, ${S.whose} ${E(relTo(S, k))}</li>`).join("")}</ul>` + (other ? "" : scopeNote(S)));
  }
  function surnames() {
    const S = scope(), c = new Map();
    for (const k of S.set) { const g = GRAPH.people[pid(k)]; if (g && g.surname) c.set(g.surname, (c.get(g.surname) || 0) + 1); }
    const top = [...c].sort((a, b) => b[1] - a[1]);
    return card(`${top.length} surnames among ${S.whose} ancestors`, `<p>${top.slice(0, 80).map(([s, n]) => `<button class="chip" data-ask="Tell me about the ${E(s)}s">${E(s)} <span class="yrs">${n}</span></button>`).join(" ")}</p>` + scopeNote(S));
  }

  // ---------------------------------------------------------------- your own lines
  function myLine(path, whoseLabel) {
    // path: array of "f"/"m" steps up from you
    const A = upMe(); if (!A) return null;
    let k = me.g === 0 ? at.get(me.k) : null;
    if (k == null) return card("I need to know your parents for that.", `<p>You chose ${E(meLabel())}; <a href="#" data-act="me">choose yourself</a> (after entering the family password) to follow your own lines.</p>`);
    const chain = [];
    for (const s of path) { k = s === "f" ? R.f[k] : R.m[k]; if (k < 0) break; chain.push(k); }
    if (!chain.length || k < 0 && chain.length < path.length) return card(`The tree doesn&rsquo;t go that far on that line.`, chain.length ? `<ol class="line">${chain.map(x => `<li>${who(x)}</li>`).join("")}</ol>` : "");
    const last = chain[chain.length - 1];
    return card(`${cap(whoseLabel)} is ${who(last)}.`, `<ol class="line"><li>you</li>${chain.map(x => `<li>${who(x)}</li>`).join("")}</ol>`, last);
  }
  function directLine(side) {                  // "f": father's father's ...; "m": mother's mother's ...
    const A = upMe(); if (!A) return null;
    let k = me.g === 0 ? at.get(me.k) : null;
    if (k == null) return card("I need to know your parents for that.", `<p><a href="#" data-act="me">Choose yourself</a> (after entering the family password) to follow your own lines.</p>`);
    const chain = [];
    for (;;) { k = side === "f" ? R.f[k] : R.m[k]; if (k < 0) break; chain.push(k); }
    if (!chain.length) return card("The tree doesn&rsquo;t name that parent.");
    const top = chain[chain.length - 1], p = prof(top);
    return card(side === "f" ? `Your direct paternal line goes back ${chain.length} generations, to ${who(top)}.` : `Your direct maternal line goes back ${chain.length} generations, to ${who(top)}.`,
      `<p class="lead">${side === "f" ? "Father to father" : "Mother to mother"}, from you:</p><ol class="line"><li>you</li>${chain.map(x => `<li>${who(x)}${prof(x) && prof(x).b[1] ? ` <span class="sub">${E(prof(x).b[1])}</span>` : ""}</li>`).join("")}</ol>`, top);
  }
  function surnameLine(sn) {
    const A = upMe(); if (!A) return null;
    const cand = [...A.keys()].filter(x => x !== ME && GRAPH.people[pid(x)] && GRAPH.people[pid(x)].surname === sn);
    if (!cand.length) return card(`No ${E(sn)} among your ancestors.`);
    const top = cand.sort((a, b) => A.get(b).d - A.get(a).d)[0];
    return card(`Your ${E(sn)} line goes back to ${who(top)}, your ${E(term(A.get(top).d, 0, top))}.`, `<ol class="line">${line(A, top).filter(x => x !== ME).map(x => `<li>${who(x)}</li>`).join("")}<li>you</li></ol>` + partial(), top);
  }
  function generationsIn(pt) {
    const S = scope(), rows = [];
    for (const k of S.set) {
      const hits = placesOf(k, LIVED).filter(([, pl]) => pt.test(pl));
      if (hits.length) rows.push([k, hits]);
    }
    if (!rows.length) return card(`None of ${S.whose} ancestors on the map is recorded in ${E(pt.label)}.`, scopeNote(S));
    const deepest = rows.sort((a, b) => S.A.get(b[0]).d - S.A.get(a[0]).d)[0], d = S.A.get(deepest[0]).d;
    const firstYear = Math.min(...rows.flatMap(([, h]) => h.map(x => x[0]).filter(Boolean)));
    const firstBy = rows.find(([, h]) => h.some(x => x[0] === firstYear));
    return card(`${cap(S.whose)} family has been in ${E(pt.label)} for ${d} generation${d === 1 ? "" : "s"}.`,
      `<p>The earliest there on the deepest line is ${who(deepest[0])}, ${S.whose} ${E(relTo(S, deepest[0]))} (${E(deepest[1].map(x => x[1]).filter((v, i, a) => a.indexOf(v) === i).slice(0, 3).join("; "))}).` +
      (firstBy ? ` The earliest record there is ${firstYear}: ${who(firstBy[0])}.` : "") + `</p>` +
      (pt.note ? `<p class="note">${E(pt.note)}</p>` : "") + `<p class="lead">${rows.length} of ${S.whose} ancestors lived there:</p><ul class="list">${rows.sort(byGen(S)).slice(0, 50).map(([k, h]) => `<li>${who(k)}, ${S.whose} ${E(relTo(S, k))}<div class="sub">${E([...new Set(h.map(x => x[1]))].slice(0, 3).join("; "))}</div></li>`).join("")}</ul>` + scopeNote(S));
  }

  // ---------------------------------------------------------------- group questions
  // "which of my ancestors ...", "who was a ...", "how many ...", or a bare "irish ancestors"
  function groupQuestion(q, l, count) {
    const S = scope();
    let r = l.replace(/^(which|whose|who|what|how many|list|show( me)?|name|find|give me|tell me|are there|were there|is there|was there|did|do|does|have|has|any)\b( of)?( (all|any))?( (my|our|the|your))?( (ancestors?|relatives?|people|family( members)?|forebears|forefathers|men|women|kin|folks|ones))?( of mine)?( (who|that))?\s*/, "")
             .replace(/^(were|was|are|is|have|had|did|do|ever|any|of them|anyone|anybody|someone|somebody)\s+/g, "").replace(/^(were|was|are|is|have|had|ever)\s+/, "")
             .replace(/^(do|did) (i|we) have\s*/, "").replace(/^(of )?(my|our) (ancestors|relatives|family)\s*/, "").replace(/\s+(do we have|do i have|are there|in (my|our|the) (family|tree))$/, "").trim();
    let m;
    if (/^(went|moved|migrated|headed|relocated|removed) (to|into) /.test(r) && !topicOf(r.replace(/^\w+ (to|into) /, ""))) r = r.replace(/^\w+ (to|into) /, "lived in ");
    if (/^went to /.test(r)) r = r.replace(/^went to /, "");                                       // "went to college" -> college
    if (/\b(fought|fight|fighting|battled|war(red|s)? (with|against))\b.*\b(indians?|natives?|native americans?|tribes?)\b/.test(r)) {
      const re = /\b(Pequot|King Philip|French and Indian|Creek War|Indians?|Shawnee|Cherokee|Powhatan|Narragansett)\b/i;
      return groupAnswer(S, group(S, k => { const ss = (MILITARY[pid(k)] || []).filter(s => re.test(s.war + " " + s.summary)); return ss.length && E(ss.map(s => s.war + ": " + (s.unit || "")).join("; ")); }, "", byYear),
        "fought in wars against Native Americans", count, null, `<p class="note">The Pequot War, King Philip&rsquo;s War, the French and Indian War, the Creek War, and service whose record mentions fighting Indians.</p>`);
    }
    if (/^(moved|went|migrated|headed) west(ward)?$/.test(r)) {
      const rows = group(S, k => { const L = (PERSON_LEGS[pid(k)] || []).filter(x => !x.ocean && x.x1 - x.x2 > 4); return L.length && E(L.map(x => `${x.from} → ${x.to}, ${x.year}`).slice(0, 3).join("; ")); }, "", byYear);
      return groupAnswer(S, rows, "moved west (more than about 4° of longitude in one move)", count);
    }
    // met / knew someone
    if ((m = /^(?:may have |might have |could have |ever )?(?:met|meet|known|knew|know|see|saw|seen|served (?:under|with)|fought (?:under|with|alongside))\s+(.+)$/.exec(r))) {
      if (/washington/.test(m[1])) return metWashington(S);
      const nm = m[1].replace(/^(general|gen\.?|president|king|queen|sir|col\.?|colonel|captain) /, "");
      const re = new RegExp("\\b" + nm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i");
      const rows = group(S, k => { const h = mentions(k, re); return h && h.html; });
      return groupAnswer(S, rows, `have records that mention ${E(m[1].replace(/\b\w/g, c => c.toUpperCase()))}`, count, `None of ${S.whose} ancestors&rsquo; records mention ${E(m[1])}.`);
    }
    const w = war(r);
    // came over with / arrived at
    if ((m = /^(?:came|sailed|arrived|crossed|traveled|travelled)(?: over| to america)? with (.+)$/.exec(r))) {
      const re = new RegExp("\\b" + m[1].replace(/^the /, "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
      return groupAnswer(S, group(S, k => { const t = mentions(k, re); return t && t.html; }, "", byYear), `have records that mention ${E(m[1])}`, count);
    }
    if ((m = /^(?:arrived|landed|came ashore|first arrived) (?:at|in) (.+)$/.exec(r))) {
      const pe = period(m[1]);
      if (pe && /^(the )?\d|century/.test(m[1])) return immigrants(S, count, false, null, pe);
      const pt = placeTest(m[1]);
      if (pt) return immigrants(S, count, false, pt);
    }
    if ((m = /^founded (.+)$/.exec(r)) && !/^(a |the )?(town|city|church|village|settlement)s?$/.test(m[1])) {
      const x = m[1].replace(/^the /, "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), re = new RegExp(`found\\w*[^.]{0,120}${x}|${x}[^.]{0,120}found\\w*|first settlers? of ${x}`, "i");
      return groupAnswer(S, group(S, k => { const t = mentions(k, re); return t && t.html; }, "", byYear), `have records that mention founding ${E(m[1].replace(/\b\w/g, c => c.toUpperCase()))}`, count,
        `None of ${S.whose} ancestors&rsquo; records say they founded ${E(m[1])}.`);
    }
    // a war named outright ("who was in Bacon's Rebellion"), battles, captivity, pensions
    if (w && !count && !/^(born|died|alive|lived through|living)/.test(r) && !/confedera|union|\brebels?\b|federal|yankee|\bsouth\b|\bnorth\b/.test(r)) return veterans(w, q);
    if (/battles?\b/.test(r) && !/\bat\b|battle of/.test(r)) return battles(S);
    const tp0 = topicOf(r);
    if (tp0 && /captivity|a pension/.test(tp0.label))
      return groupAnswer(S, group(S, k => { const t = mentions(k, tp0.look); return t && t.html; }, "", byGen(S)), `have records that mention ${E(tp0.label)}`, count, null,
        `<p class="note">These are mentions in the records and notes, not proof: read each one.</p>`);
    // born / died / lived / from / came (before the military: "born during the Civil War")
    const early = bornDiedLived();
    if (early) return early;
    // military
    if (/\b(fought|fight|served|serve|soldiers?|veterans?|military|militia|army|troops|enlisted|war|confederates?|rebels?|union soldiers?)\b/.test(r) && !/\bat\b/.test(r)) {
      if (/confedera|south\b|rebel/.test(r)) return groupAnswer(S, group(S, k => { const ss = (MILITARY[pid(k)] || []).filter(s => /Civil/.test(s.war) && /Confedera|C\.S\.|Georgia|Alabama|Virginia Cavalry|Mississippi|Tennessee|Kentucky Cavalry|Orphan|Morgan|Shelby|Hood/i.test(s.unit + " " + s.summary)); return ss.length && E(ss.map(s => s.unit).join("; ")); }, "", byGen(S)), "served the Confederacy", count);
      if (/union\b|north\b|federal|yankee/.test(r)) return groupAnswer(S, group(S, k => { const ss = (MILITARY[pid(k)] || []).filter(s => /Civil/.test(s.war) && !/Confedera|C\.S\.|Virginia Cavalry|Orphan|Morgan|Hood/i.test(s.unit + " " + s.summary)); return ss.length && E(ss.map(s => s.unit).join("; ")); }, "", byGen(S)), "served the Union", count);
      if (count) { const rows = group(S, k => services(k, w).length > 0); return card(`${rows.length} of ${S.whose} ancestors served in ${E(w ? w.label : "the military")}.`, `<p><button class="chip" data-ask="Which of my ancestors served in ${E(w ? w.label.replace(/^the /, "the ") : "the military")}">List them</button></p>` + scopeNote(S)); }
      return veterans(w, q);
    }
    if ((m = /^(?:fought |were |was |at |in the battle of |fought in the battle of )*(?:at|battle of) (.+)$/.exec(r)) || (m = /^(?:fought|were|was) at (.+)$/.exec(r))) {
      const b = battle(m[1]); if (b) return b;
    }
    // occupations, topics, ranks
    if (/^(officers?|captains?|lieutenants?|colonels?|majors?|generals?|a captain|a colonel|an officer)$/.test(r)) {
      const re = /\b(captain|capt\.|lieutenant|lt\.|colonel|col\.|major|general|ensign|commissioned)\b/i;
      return groupAnswer(S, group(S, k => { const t = mentions(k, re, ["service"]); return t && t.html; }, "", byGen(S)), "were officers, or are recorded with an officer&rsquo;s rank", count);
    }
    if (/married (more than once|twice|again|three times|multiple)|remarried/.test(r)) return groupAnswer(S, group(S, k => spouses[k].length > 1 && spouses[k].map(s => E(name(s))).join(", "), "", byGen(S)), "married more than once", count);
    if (/marr(y|ied) (their |a )?(first |second |third )?cousins?|cousins? marr(y|ied)/.test(r) || /marr(y|ied) cousins/.test(l)) return cousinMarriages(S);
    if (/married (the )?youngest|youngest (to marry|bride|groom)/.test(r)) return superlative("marriedyoung");
    if (/adopted|step-?(parents?|children|father|mother)|foster|guardian/.test(r)) return groupAnswer(S, group(S, k => { const g = GRAPH.people[pid(k)]; const ps = g && g.psets; return (R.r[k] ? E(R.r[k]) + " parents shown" : "") || (ps && ps.length > 1 && E(ps.map(x => x.r).join(", "))); }), "had more than one set of parents in the records (adopted, step-parents or guardians)", count);
    if (/twins?/.test(r)) return twins(S);
    if (/(have|had|with) (a )?(photos?|pictures?|portraits?)/.test(r) || /^photos?$/.test(r)) { const rows = group(S, k => prof(k) && prof(k).ph && true, "", byGen(S)); return card(`${rows.length} of ${S.whose} ancestors have portraits on the site.`, faces(rows.map(x => x[0])) + scopeNote(S)); }
    if (/most children|biggest famil|largest famil|most kids/.test(r)) return superlative("children");
    if (/moved (the )?most|most moves/.test(r)) return superlative("moves");
    if (/traveled|travelled|farthest|furthest/.test(r)) return superlative("distance");
    const tp = topicOf(r);
    if (tp) {
      if (!tp.look) return notableGroup(S);
      // a source's title is evidence for some topics (Magna Carta Ancestry, Quaker meeting records, probate files); for the rest it's a book about someone else
      const where = /royalty|title|Quakers|will or probate|obituary|newspaper|slavery|Ellis|school/.test(tp.label) ? null : ["note", "story", "record", "event", "service"];
      return groupAnswer(S, group(S, k => { const t = mentions(k, new RegExp(tp.look.source, tp.look.flags), where); return t && t.html; }, "", byGen(S)),
        `have records that mention ${E(tp.label)}`, count, `None of ${S.whose} ancestors&rsquo; records mention ${E(tp.label)}.`,
        `<p class="note">These are mentions in the records and notes, not proof: read each one.` +
        (/farming|a craft|trade|medicine|the law|teaching|the sea|the ministry/.test(tp.label) ? ` The tree records few occupations (census pages list them, but they&rsquo;re rarely entered), so this list is far from complete.` : "") + `</p>`);
    }
    // anything else short: search the records for its longest word ("sheltered the regicides" -> regicide)
    const ws = r.split(" ").filter(x => x.length >= 5 && !/^(which|their|there|where|about|people|family|ancestors?|relatives?|would|could|should|anyone|someone|become|became|during|after|before)$/.test(x));
    if (ws.length && r.split(" ").length <= 6) {
      const stem = ws.sort((a, b) => b.length - a.length)[0].replace(/(ies)$/, "y").replace(/(es|s|ed|ing)$/, "");
      const re = new RegExp("\\b" + stem.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\w*", "i");
      const rows = group(S, k => { const t = mentions(k, re); return t && t.html; }, "", byGen(S));
      if (rows.length) return groupAnswer(S, rows, `have records that mention &ldquo;${E(stem)}&rdquo;`, count, null, `<p class="note">A plain search of the records and notes: read each one.</p>`);
    }
    return null;

    function bornDiedLived() {
    if ((m = /^(?:alive|living|lived) (?:in|during|through|when|at the time of) (.+)$/.exec(r)) || (m = /^(?:lived through|were alive for|were around (?:for|during|in)) (.+)$/.exec(r))) {
      const pe = period(m[1]); if (pe) return aliveGroup(S, pe, count);
    }
    if (/^(?:were |was )?killed by (indians|natives|native americans)/.test(r))
      return groupAnswer(S, group(S, k => { const t = mentions(k, /\b((was |were )?(killed|slain|murdered) by (the )?(Indians|Native Americans|natives)|scalped)\b/i, ["note", "story", "service", "event", "record"]); return t && t.html; }),
        "have records that mention being killed by Indians", count, `None of ${S.whose} ancestors&rsquo; records say they were killed by Indians.`, `<p class="note">Read each one: a record can mention an attack without the person dying in it.</p>`);
    if ((m = /^(?:were |was )?born (?:in|at|on|during|around|near)? ?(.+)$/.exec(r))) {
      if (/\bsea\b|ship|aboard|voyage/.test(m[1])) return groupAnswer(S, group(S, k => { const t = mentions(k, /\bborn (at sea|aboard|on board)\b/i, ["note", "story", "record", "event", "service"]); return t && t.html; }), "were born at sea", count);
      if (/christmas/.test(m[1])) return groupAnswer(S, group(S, k => { const p = prof(k); return p && /^25 Dec/i.test(p.b[0] || "") && E(p.b[0]); }), "were born on Christmas Day", count);
      if (/america|the colonies|the us\b|the united states/.test(m[1]) && /first/.test(l)) return firstBornAmerica(S, null);
      const pe = period(m[1]); if (pe && !/[a-z]{4,}/.test(m[1].replace(/\b(the|in|before|after|between|and|century|s)\b/g, "").replace(/\d/g, "")))
        return groupAnswer(S, group(S, k => R.b[k] >= pe.r[0] && R.b[k] <= pe.r[1] && String(R.b[k])), `were born ${/^(before|after)/.test(pe.label) ? "" : "in "}${E(pe.label)}`, count);
      const pt = placeTest(m[1]); if (pt) return groupAnswer(S, group(S, k => { const p = prof(k); return p && pt.test(p.b[1]) && E(p.b[1]); }), `were born in ${E(pt.label)}`, count);
    }
    if ((m = /^(?:died|passed away|were killed|was killed) ?(?:in|at|during)? ?(.+)$/.exec(r))) {
      if (/young/.test(m[1])) return superlative("youngest");
      const wr = war(m[1]);
      if (wr) {
        const inService = group(S, k => { const ss = services(k, wr); return ss.length && R.d[k] > 0 && ss.some(s => { const ys = (s.war.match(/\d{4}/g) || []).map(Number); return ys.length ? R.d[k] >= Math.min(...ys) && R.d[k] <= Math.max(...ys) + 1 : false; }) && `died ${R.d[k]}`; });
        if (inService.length) return groupAnswer(S, inService, `died during their service in ${E(wr.label)}`, count);
        const pe = period(m[1]);
        if (pe) return groupAnswer(S, group(S, k => R.d[k] >= pe.r[0] && R.d[k] <= pe.r[1] && `died ${R.d[k]}${services(k, null).length ? "" : "; no service recorded"}`), `died during the years of ${E(wr.label)} (${pe.r[0]}–${pe.r[1]}); none is recorded dying in service`, count);
      }
      const pe = period(m[1]); if (pe && /^\s*(the )?\d/.test(m[1])) return groupAnswer(S, group(S, k => R.d[k] >= pe.r[0] && R.d[k] <= pe.r[1] && String(R.d[k])), `died in ${E(pe.label)}`, count);
      if (/indian|native/.test(m[1])) { const tp2 = TOPICS.find(t => t[1] === "Native Americans"); return groupAnswer(S, group(S, k => { const t = mentions(k, /\b(killed by|slain by|massacre)\b/i); return t && t.html; }), "were killed in attacks, by their records", count); }
      const pt = placeTest(m[1]); if (pt) return groupAnswer(S, group(S, k => { const p = prof(k); return p && (pt.test(p.d[1]) || pt.test(p.bu)) && E(p.d[1] || p.bu); }), `died in ${E(pt.label)}`, count);
    }
    if (/^(lived (the )?longest|lived to (be )?\d+|had long lives)/.test(r)) { const n = +((/\d+/.exec(r) || [0])[0]); return n ? groupAnswer(S, group(S, k => age(k) >= n && `${age(k)} years`, "", (a, b) => age(b[0]) - age(a[0])), `lived to ${n} or older`, count) : superlative("longest"); }
    if ((m = /^(?:lived|live|resided|settled|stayed|were|was|are|grew up|made (?:their|a) home|had (?:a )?homes?)\s+(?:in|at|near|around)\s+(.+)$/.exec(r)) || (m = /^in (.+)$/.exec(r))) {
      const pe = period(m[1]); if (pe && /^\s*(the )?\d/.test(m[1])) return aliveGroup(S, pe, count);
      const b = battle(m[1]); if (b && /^(were|was) /.test(l.replace(/^(which|who)( of)?( my)?( ancestors)? /, ""))) return b;
      const pt = placeTest(m[1]);
      if (pt) {
        const rows = group(S, k => { const h = placesOf(k, LIVED).filter(([, pl]) => pt.test(pl)); return h.length && E([...new Set(h.map(x => x[1]))].slice(0, 3).join("; ") + (h[0][0] ? ` (${Math.min(...h.map(x => x[0] || 9999))})` : "")); }, "", byGen(S));
        if (rows.length || !pt.literal) return groupAnswer(S, rows, `lived in ${E(pt.label)}`, count, null, pt.note ? `<p class="note">${E(pt.note)}</p>` : "");   // an unknown phrase ("the House of Burgesses") goes on to the topics
      }
    }
    if ((m = /^(?:came|come|were|was|are|is|emigrated|immigrated) from (.+)$/.exec(r))) {
      const pt = placeTest(m[1]);
      if (pt) return groupAnswer(S, group(S, k => { const h = placesOf(k, ["born", "lived"]).filter(([, pl]) => pt.test(pl)); return h.length && E([...new Set(h.map(x => x[1]))].slice(0, 2).join("; ")); }, "", byYear), `came from ${E(pt.label)}`, count);
    }
    if (/\b(ship|ships|mayflower|speedwell|sea venture|sailed|voyage|aboard|came over on|came on)\b/.test(r)) return ships(q);
    if (/\b(immigra\w*|emigra\w*|(came|got|made it|went|moved|sailed) (over )?to (america|the us|the united states|the colonies)|reached america|arrived|came over|crossed the (ocean|atlantic)|ellis island)/.test(r) || /^immigrants?$/.test(r))
      return immigrants(S, count, /ellis/.test(r), null, period(r.replace(/\b(america|the us|the united states)\b/g, "")));
    if ((m = /^(?:alive|living|lived) (?:in|during|through|when|at the time of) (.+)$/.exec(r)) || (m = /^(?:lived through|were alive for|were around (?:for|during|in)) (.+)$/.exec(r))) {
      const pe = period(m[1]); if (pe) return aliveGroup(S, pe, count);
    }
    return null;
    }
  }
  function ships(q) {
    const S = scope(), known = [...new Set(NOTABLE.events.filter(e => e.sh).map(e => e.sh))].concat(["Sea Venture", "Mayflower", "Speedwell", "Godspeed", "Susan Constant", "Discovery", "Arbella", "Deliverance", "Patience"]);
    const named = known.find(s => q.toLowerCase().includes(s.toLowerCase()));
    const m = /(?:on|aboard) (?:the )?(.+)/i.exec(q), ship = named || (m && !/^(a )?ships?$/i.test(m[1]) ? m[1].replace(/^ship /i, "") : "");
    const ev = NOTABLE.events.filter(e => e.sh && (!ship || e.sh.toLowerCase().includes(ship.toLowerCase())) && e.p.some(p => S.set.has(at.get(p))));
    if (!ev.length && ship) {          // not an arrival: look through the records and events for the ship's name
      const re = new RegExp("\\b" + ship.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\b", "i");
      const rows = group(S, k => { const t = mentions(k, re); return t && t.html; }, "", byYear);
      return rows.length ? listCard(`${rows.length} of ${S.whose} ancestors ${rows.length === 1 ? "has" : "have"} records that mention the ${E(ship)}.`, rows, S)
        : card(`None of ${S.whose} ancestors is recorded on the ${E(ship)}.`, scopeNote(S));
    }
    if (!ev.length) return card(`No ships recorded.`, scopeNote(S));
    ev.sort((a, b) => a.y - b.y);
    return card(ship ? `${cap(S.whose)} ancestors on the ${E(ev[0].sh)}` : `The ships ${S.whose} ancestors came on`,
      `<ul class="list">${ev.map(e => `<li><b>${E(e.sh)}</b>, ${E(e.d)}: ${e.p.filter(p => S.set.has(at.get(p))).map(p => who(at.get(p))).join(", ")}<div class="sub">${E(e.t)}</div></li>`).join("")}</ul>` + scopeNote(S));
  }
  function oldest() {
    const S = scope();
    const k = [...S.set].filter(x => R.b[x] > 0).sort((a, b) => R.b[a] - R.b[b])[0];
    return k == null ? null : card(`${cap(S.whose)} earliest-born ancestor in the tree is ${who(k)}.`,
      `<p>${cap(he(k))} is ${S.whose} ${E(relTo(S, k))}. ${vitalText(k, "born")}</p>` + scopeNote(S), k);
  }
  function count() {
    const S = scope(), named = [...S.set].filter(k => R.n[k]);
    const gens = Math.max(...[...S.set].map(k => S.A.get(k).d));
    return card(`The tree names ${named.length.toLocaleString()} of ${S.whose} ancestors, going back ${gens} generations.`, scopeNote(S));
  }
  function aliveGroup(S, pe, count) {
    const rows = group(S, k => aliveIn(k, pe.r[0], pe.r[1]) && E(yrs(k)), "", byGen(S));
    return groupAnswer(S, rows, `were alive ${pe.r[0] === pe.r[1] ? "in" : "during"} ${E(pe.label)}`, count, null, `<p class="note">From birth and death years; where one is missing, assuming a life of about 70 years.</p>`);
  }
  function battle(s) {
    const re = new RegExp(s.replace(/^the /, "").replace(/^battle of /, "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"), rows = [];
    for (const [p, list] of Object.entries(MILITARY)) for (const sv of list) for (const st of sv.stops || [])
      if (re.test(st.b || "") || re.test(st.l || "")) { const k = at.get(p); if (k != null) rows.push([k, `${E(st.b || st.l)}, ${E(st.d || "")} — ${E(sv.unit || sv.war)}`]); }
    if (!rows.length) return null;
    const S = scope(), seen = new Set(), uniq = rows.filter(([k]) => !seen.has(k) && seen.add(k));
    return listCard(`${uniq.length} of the family ${uniq.length === 1 ? "was" : "were"} at ${E(s.replace(/^the /, "").replace(/\b\w/g, c => c.toUpperCase()))}.`, uniq, S);
  }
  function battles(S) {
    const c = new Map();
    for (const k of S.set) for (const sv of MILITARY[pid(k)] || []) for (const st of sv.stops || []) if (st.b) { if (!c.has(st.b)) c.set(st.b, [st.bd || st.d, new Set()]); c.get(st.b)[1].add(k); }
    const rows = [...c].sort((a, b) => ((/\d{4}/.exec(a[1][0]) || [0])[0]) - ((/\d{4}/.exec(b[1][0]) || [0])[0]));
    return card(`${S.whose === "your" ? "Your" : "Margaret&rsquo;s"} ancestors fought in ${rows.length} battles.`, `<ul class="list">${rows.map(([b, [d, ks]]) => `<li><b>${E(b)}</b> <span class="yrs">${E(d || "")}</span><div class="sub">${[...ks].map(who).join(", ")}</div></li>`).join("")}</ul>` +
      scopeNote(S) + `<div class="acts"><a class="btn" href="map.html?military=1">See the battles on the map</a></div>`);
  }
  function immigrants(S, count, ellis, pt = null, pe = null) {
    const ev = NOTABLE.events.filter(e => e.k === "arrival" && e.p.some(x => S.set.has(at.get(x))) && (!ellis || /ellis/i.test(e.t + e.l)) && (!pt || pt.test(e.l) || pt.test(e.t))
      && (!pe || (e.y >= pe.r[0] && e.y <= pe.r[1])));
    if (pt && !ev.length) return card(`None of ${S.whose} ancestors is recorded arriving at ${E(pt.label)}.`, scopeNote(S));
    if (pe && !ev.length) return card(`None of ${S.whose} ancestors is recorded arriving in America in ${E(pe.label)}.`, scopeNote(S));
    // automatic arrivals (build_notable.py) are dated by the first record of the person in America: the crossing may be earlier
    const auto = e => e.s === "the migration records in the tree";
    const rows = []; let nAuto = 0;
    for (const e of ev.sort((a, b) => a.y - b.y)) for (const x of e.p) { const k = at.get(x); if (S.set.has(k) && !rows.some(r => r[0] === k)) {
      if (auto(e)) nAuto++;
      rows.push([k, `${E(e.d)}, ${E(e.l)}${e.sh ? ", the " + E(e.sh) : ""}${auto(e) ? " <i>(first record in America; the crossing may be earlier)</i>" : ""}`]); } }
    if (!rows.length) return card(ellis ? `None of ${S.whose} ancestors is recorded passing through Ellis Island.` : `No arrivals recorded.`, scopeNote(S));
    const nDoc = rows.length - nAuto;
    const split = nAuto ? `<p class="note">${nDoc === 0 ? "None of these crossings is documented" : nDoc === 1 ? "One of these crossings is documented" : nDoc + " of these crossings are documented"} (a ship, a passenger list, a history). ` +
      `For ${nDoc === 0 ? (nAuto === 1 ? "it" : "all " + nAuto) : "the other " + nAuto}, the year is the first time the tree places the person in America, so the crossing may have been earlier${pe ? ", in an earlier period" : ""}.</p>` : "";
    return listCard(`${rows.length} of ${S.whose} ancestors crossed the ocean to America${ellis ? " through Ellis Island" : pt ? ", arriving at " + E(pt.label) : ""}${pe ? " in " + E(pe.label) : ""}, earliest first.`, rows, S, split);
  }
  function firstBornAmerica(S, sn) {
    const rows = [...S.set].filter(k => (!sn || (GRAPH.people[pid(k)] || {}).surname === sn) && prof(k) && AMERICA.test(prof(k).b[1] || "") && R.b[k]).sort((a, b) => R.b[a] - R.b[b]);
    if (!rows.length) return card(`I can&rsquo;t tell who was first born in America${sn ? " among the " + E(sn) + "s" : ""}.`, scopeNote(S));
    const k = rows[0];
    return card(`The earliest-born ${sn ? E(sn) + " " : ""}ancestor born in America is ${who(k)}.`, `<p>${vitalText(k, "born")} ${cap(he(k))} is ${S.whose} ${E(relTo(S, k))}.</p>` + scopeNote(S), k);
  }
  function cousinMarriages(S) {
    const rows = [], seen = new Set();
    for (const k of S.set) for (const s of spouses[k]) {
      if (!S.set.has(s) || seen.has(Math.min(k, s) + "," + Math.max(k, s))) continue;
      seen.add(Math.min(k, s) + "," + Math.max(k, s));
      const b = blood(up(k), up(s));
      if (b && b.a > 0 && b.b > 0) rows.push([k, `married ${who(s)}, ${sx(k, "his", "her", "their")} ${E(term(b.a, b.b, s, b.half))} (common ancestor ${who(b.c)})`]);
    }
    if (!rows.length) return card(`No cousin marriages among ${S.whose} ancestors that the tree shows.`, scopeNote(S));
    return listCard(`${rows.length} of ${S.whose} ancestors married a relative.`, rows, S);
  }
  function twins(S) {
    const rows = [], seen = new Set();
    for (const k of S.set) for (const p of [R.f[k], R.m[k]]) if (p >= 0) for (const c of kids[p]) if (c !== k && R.b[c] && R.b[c] === R.b[k] && R.f[c] === R.f[k] && R.m[c] === R.m[k] && !seen.has(k)) {
      const a = prof(k), bd = a && a.b[0];
      seen.add(k); rows.push([k, `${E(name(c))}, also born ${R.b[k]}${bd ? " (" + E(bd) + ")" : ""}`]);
    }
    if (!rows.length) return card(`The tree shows no twins among ${S.whose} ancestors.`, scopeNote(S));
    return listCard(`${rows.length} of ${S.whose} ancestors may have been twins: a sibling was born the same year.`, rows, S);
  }
  function notableGroup(S) {
    const ev = NOTABLE.events.filter(e => e.k !== "arrival" && e.p.some(x => S.set.has(at.get(x)))).sort((a, b) => a.y - b.y);
    return card(`${ev.length} moments in history involve ${S.whose} ancestors.`, `<ul class="list">${ev.map(e => `<li><b>${E(e.d)}</b>, ${E(e.l)}: ${E(e.t)}<div class="sub">${e.p.filter(x => at.has(x)).map(x => who(at.get(x))).join(", ")}</div></li>`).join("")}</ul>` + scopeNote(S));
  }
  function superlative(kind) {
    const S = scope(); let rows, head;
    if (kind === "longest") { rows = [...S.set].filter(k => age(k) != null && age(k) < 115).sort((a, b) => age(b) - age(a)).slice(0, 12).map(k => [k, `${age(k)} years`]); head = `${S.whose === "your" ? "Your" : "Margaret&rsquo;s"} longest-lived ancestor was ${who(rows[0][0])}, at about ${age(rows[0][0])}.`; }
    if (kind === "youngest") { rows = [...S.set].filter(k => age(k) != null && age(k) >= 10).sort((a, b) => age(a) - age(b)).slice(0, 12).map(k => [k, `${age(k)} years`]); head = `The youngest to die among ${S.whose} ancestors was ${who(rows[0][0])}, at about ${age(rows[0][0])}.`; }
    if (kind === "children") { rows = [...S.set].filter(k => kids[k].length).sort((a, b) => kids[b].length - kids[a].length).slice(0, 12).map(k => [k, `${kids[k].length} children in the tree`]); head = `${who(rows[0][0])} had the most children in the tree: ${kids[rows[0][0]].length}.`; }
    if (kind === "moves") { rows = [...S.set].filter(k => (PERSON_LEGS[pid(k)] || []).length).sort((a, b) => PERSON_LEGS[pid(b)].length - PERSON_LEGS[pid(a)].length).slice(0, 12).map(k => [k, `${PERSON_LEGS[pid(k)].length} moves`]); head = `${who(rows[0][0])} moved the most: ${PERSON_LEGS[pid(rows[0][0])].length} moves.`; }
    if (kind === "distance") {
      const km = k => (PERSON_LEGS[pid(k)] || []).reduce((s, l) => { const R_ = 6371, la1 = (65 - l.y1) * Math.PI / 180, la2 = (65 - l.y2) * Math.PI / 180, dl = (l.x2 - l.x1) * Math.PI / 180;
        return s + R_ * 2 * Math.asin(Math.sqrt(Math.sin((la2 - la1) / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dl / 2) ** 2)); }, 0);
      rows = [...S.set].map(k => [k, km(k)]).filter(x => x[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([k, d]) => [k, `about ${Math.round(d).toLocaleString()} km in straight lines between the places recorded`]);
      head = `${who(rows[0][0])} traveled the farthest.`;
    }
    if (kind === "marriedyoung") {
      const at1 = k => { const p = prof(k); if (!p || !R.b[k]) return null; const ms = p.t.filter(e => e[2] === "married" && e[0]).map(e => e[0] - R.b[k]).filter(a => a >= 10); return ms.length ? Math.min(...ms) : null; };
      rows = [...S.set].map(k => [k, at1(k)]).filter(x => x[1] != null).sort((a, b) => a[1] - b[1]).slice(0, 12).map(([k, a]) => [k, `married at about ${a}`]);
      if (rows.length) head = `The youngest to marry among ${S.whose} ancestors was ${who(rows[0][0])}, at about ${at1(rows[0][0])}.`;
    }
    if (kind === "recentdeath") { rows = [...S.set].filter(k => R.d[k] > 0).sort((a, b) => R.d[b] - R.d[a]).slice(0, 8).map(k => [k, `died ${R.d[k]}`]); head = `The most recent of ${S.whose} ancestors to die was ${who(rows[0][0])}, in ${R.d[rows[0][0]]}.`; }
    if (kind === "recentimm") { const ev = NOTABLE.events.filter(e => e.k === "arrival" && e.p.some(x => S.set.has(at.get(x)))).sort((a, b) => b.y - a.y); rows = ev.slice(0, 6).map(e => [at.get(e.p.find(x => S.set.has(at.get(x)))), `${E(e.d)}, ${E(e.l)}`]); head = `${cap(S.whose)} most recent immigrant ancestor${ev[0] && ev[0].p.length > 1 ? "s" : ""}: ${ev[0].p.filter(x => S.set.has(at.get(x))).map(x => who(at.get(x))).join(", ")}, ${E(ev[0].d)}.`; }
    if (kind === "firstimm") { const ev = NOTABLE.events.filter(e => e.k === "arrival" && e.p.some(x => S.set.has(at.get(x)))).sort((a, b) => a.y - b.y); rows = ev.slice(0, 8).map(e => [at.get(e.p.find(x => S.set.has(at.get(x)))), `${E(e.d)}, ${E(e.l)}${e.sh ? ", the " + E(e.sh) : ""}`]); head = `The first of ${S.whose} ancestors to reach America: ${ev[0].p.filter(x => S.set.has(at.get(x))).map(x => who(at.get(x))).join(", ")}, ${E(ev[0].d)}${ev[0].sh ? " on the " + E(ev[0].sh) : ""}.`; }
    if (!rows || !rows.length) return null;
    return card(head, `<ul class="list">${rows.map(([k, s]) => `<li>${who(k)}, ${S.whose} ${E(relTo(S, k))}<div class="sub">${s}</div></li>`).join("")}</ul>` + scopeNote(S));
  }
  function inYear(y0, y1, label) {
    const S = scope(), ev = [];
    for (const k of S.set) { const p = prof(k); if (!p) continue;
      for (const e of p.t) if (e[0] >= y0 && e[0] <= y1 && e[2] !== "lived") ev.push([e[0], k, `${E(e[2])}${e[3] ? ", " + E(e[3]) : ""}${e[4] ? " — " + E(e[4]) : ""}`]); }
    for (const e of NOTABLE.events) if (e.y >= y0 && e.y <= y1 && e.p.some(x => S.set.has(at.get(x)))) ev.push([e.y, at.get(e.p.find(x => S.set.has(at.get(x)))), `<b>${E(e.t)}</b>`]);
    const alive = [...S.set].filter(k => aliveIn(k, y0, y1));
    const homes = new Map();
    for (const k of alive) { const h = placesOf(k, LIVED).filter(x => x[0] && x[0] <= y1).sort((a, b) => b[0] - a[0])[0]; if (h) { const st = h[1]; homes.set(st, (homes.get(st) || 0) + 1); } }
    ev.sort((a, b) => a[0] - b[0]);
    return card(`${cap(S.whose)} family in ${E(label)}`, `<p>${alive.length} of ${S.whose} ancestors were alive then. They lived in ${E([...homes].sort((a, b) => b[1] - a[1]).slice(0, 10).map(x => x[0]).join("; ") || "places the tree doesn't record")}.</p>` +
      (ev.length ? `<ul class="list">${ev.slice(0, 50).map(([y, k, t]) => `<li><span class="yrs">${y}</span> ${who(k)}: ${t}</li>`).join("")}</ul>` : `<p>No dated events in those years.</p>`) + scopeNote(S));
  }
  function story() {
    const S = scope(), pool = [];
    for (const e of NOTABLE.events) if (e.k !== "arrival" && e.p.some(x => S.set.has(at.get(x)))) pool.push(() => card(`${E(e.d)} &middot; ${E(e.l)}`, `<p>${E(e.t)}</p><p class="sub">${e.p.filter(x => at.has(x)).map(x => who(at.get(x))).join(", ")}${e.s ? " &middot; Source: " + E(e.s) : ""}</p>`, at.get(e.p[0])));
    for (const [p, list] of Object.entries(MILITARY)) { const k = at.get(p); if (k != null && S.set.has(k)) for (const s of list) if (s.summary && s.summary.length > 120) pool.push(() => card(`${who(k)} in ${E(s.war)}`, `<p><b>${E(s.unit || "")}</b></p><p>${E(s.summary)}</p>`, k)); }
    return pool.length ? pool[Math.floor(Math.random() * pool.length)]() + `<p class="note" style="text-align:center"><button class="chip" data-ask="Tell me another family story">Another one</button></p>` : null;
  }

  // ---------------------------------------------------------------- person questions in any word order
  const INTENTS = [
    ["photo", /\b(photos?|pictures?|portraits?|images?|look like|looked like|face)\b/],
    ["records", /\b(sources?|records?|documents?|citations?|evidence)\b/],
    ["occupation", /\b(occupation|job|profession|trade|for a living|do for work|what did .+ do\b|work(ed)? as)\b/],
    ["howdied", /\bhow did .+ die\b|\bcause of death\b|\bwhat killed\b/],
    ["buried", /\b(buried|burial|grave|cemetery|interred)\b/],
    ["lifespan", /\b(how long did .+ live|lifespan|life span|how old was .+ when|age at death|how old did)\b/],
    ["battles", /\bbattles?\b/],
    ["served", /\b(serve[d]?|fight|fought|soldier|veteran|military|army|militia|war|regiment|unit|enlist(ed)?|revolutionary|civil war|1812)\b/],
    ["wherebirth", /\bwher?e? .*\bborn\b|\bbirth ?place\b|\bwhere .*\bfrom\b/],
    ["wheredeath", /\bwhere .*\b(die|died|death)\b|\bdeath ?place\b/],
    ["birth", /\b(born|birth|birthday|birthdate|birth date|dob)\b/],
    ["death", /\b(die|died|death|dead|pass(ed)? away|deceased)\b/],
    ["siblings", /\b(siblings?|brothers?|sisters?)\b/],
    ["grandparents", /\bgrandparents?\b|\bgrandfathers?\b|\bgrandmothers?\b/],
    ["descendants", /\b(descendants?|grandchildren|grandkids|posterity)\b/],
    ["parents", /\b(parents?|father|mother|dad|mom|mum|raised|reared|brought up)\b/],
    ["spouse", /\b(wife|wives|husbands?|spouses?|married|marry|marriage)\b/],
    ["children", /\b(children|child|kids|sons?|daughters?|offspring)\b/],
    ["lived", /\b(live[ds]?|home|homes|residence|resided|moved|settled|places?)\b/],
    ["journey", /\b(journey|map|moves|travels?|route)\b/],
    ["tree", /\btree\b/],
    ["about", /\b(who (is|was)|tell me (about|more)|about|story|life story|biography|bio|what do we know|info|information)\b/],
  ];
  const NOISE = /\b(what|when|where|wher|wen|who|whom|whose|which|how|did|does|do|was|were|is|are|am|the|a|an|of|in|on|at|to|for|from|with|by|me|tell|show|about|more|please|can|could|you|i|know|we|us|our|my|have|has|had|there|any|ever|name|names|year|date|day|place|many|much|than|once|twice|or|and|raised|reared|brought|up|named|called|times|number|born|birth|birthday|die|died|death|dead|buried|burial|grave|parents?|father|mother|dad|mom|wife|husband|spouse|married|marry|children|child|kids|sons?|daughters?|siblings?|brothers?|sisters?|grandparents?|grandchildren|descendants?|live|lived|lives|home|photos?|pictures?|portraits?|look|like|looked|serve|served|fight|fought|soldier|war|revolutionary|revolution|civil|military|army|battles?|unit|regiment|occupation|job|living|work|sources?|records?|documents?|journey|map|tree|story|life|long|old|age|lifespan|span|cause|killed|how|get|got|go|went|come|came|s|his|her|their|he|she|they|in|1812|world|french|indian|any|mention)\b/gi;
  function personIntent(q, l, minWords = 1) {
    let intent = null;
    for (const [id, re] of INTENTS) if (re.test(l)) { intent = id; break; }
    const rest = q.replace(/[’']s\b/g, "").replace(/[?.!,]/g, " ").replace(NOISE, " ").replace(/\s+/g, " ").trim();
    if (!rest || rest.split(" ").length < minWords) return null;
    const r = resolve(rest);
    if (r.none) return intent && intent !== "about" ? { miss: rest } : null;
    if (r.many) return { html: choose(r.many, q) };
    const k = r.k, w = war(l);
    const f = {
      photo, records, occupation, howdied: howDied, buried, lifespan, battles: k2 => { const bs = (MILITARY[pid(k2)] || []).flatMap(s => (s.stops || []).filter(st => st.b).map(st => [st.b, st.bd || st.d, s.unit])); return bs.length ? card(`${who(k2)} was at ${bs.length} battle${bs.length === 1 ? "" : "s"}.`, `<ul class="list">${bs.map(b => `<li><b>${E(b[0])}</b> <span class="yrs">${E(b[1] || "")}</span><div class="sub">${E(b[2] || "")}</div></li>`).join("")}</ul>`, k2) : served(k2, w); },
      served: k2 => served(k2, w), wherebirth: k2 => wherePlace(k2, "born"), wheredeath: k2 => wherePlace(k2, "died"),
      birth: k2 => vital(k2, "born"), death: k2 => vital(k2, "died"), siblings, grandparents: k2 => generation(k2, 2, name(k2) + "&rsquo;s"),
      descendants, parents: k2 => family(k2, /\b(father|dad)\b/.test(l) ? "father" : /\b(mother|mom|mum)\b/.test(l) ? "mother" : "parents"),
      spouse: k2 => family(k2, "spouse"), children: k2 => family(k2, "children"), lived, journey, tree: k2 => card(who(k2), "", k2), about: person,
    }[intent || "about"];
    return { html: f(k) };
  }

  async function answer(raw) {
    await load();
    const q = raw.trim().replace(/[?.!]+$/, "").replace(/\s+/g, " ").replace(/^(please|so|ok|okay|hey|hi|and|also)[, ]+/i, "")
      .replace(/^(can|could|would) you (please )?(tell me|show me|find|list)\s*/i, "").replace(/^(i want to know|i'd like to know|do you know|tell me)\s+(?=(who|what|when|where|which|how|if|whether))/i, "")
      .replace(/^(if|whether)\s+/i, "");
    const l = q.toLowerCase().replace(/[’]/g, "'");
    let m;
    const person = (s, f) => { const r = resolve(s); return r.none ? notFound(s) : r.many ? choose(r.many, q) : f(r.k); };

    // help and the site itself
    if (/^(help|\?|what can i ask|what (questions|kinds? of questions|sorts? of things) can i ask|how does this work|examples?|what do you know)/.test(l)) return help();
    if (/^(who made|who built|who created|what is this|how accurate|where does (this|the) (information|data)|is this (accurate|true|reliable)|what are your sources|how do you know)/.test(l)) return about();
    if (/^how many (people|persons|names) (are )?(in|on) the (tree|site|family tree)/.test(l)) return card(`The tree has ${R.n.length.toLocaleString()} people.`, `<p>${Object.keys(GRAPH.people).length.toLocaleString()} of them are Margaret&rsquo;s direct ancestors (and her close family), on the map with full profiles.</p>`);
    if (/^how many (people|persons) (are )?on the map/.test(l)) return card(`${Object.keys(GRAPH.people).length.toLocaleString()} people are on the map.`, `<p>Margaret&rsquo;s direct ancestors and her close family; the whole tree has ${R.n.length.toLocaleString()}.</p>`);
    if (/^who am i$/.test(l)) { pending = null; return card("Who are you?", pickerHTML()); }
    if (/(tell me|share)( me)? (a|another|an interesting|something interesting|a random)\b(?! about)|surprise me|something interesting|interesting (story|thing|fact)|random (ancestor|story|fact)|who should i know about|family story/.test(l)) return story() || help();
    if (/what does .+ mean|meaning of (the )?(name|surname)|origin of the (name|surname)/.test(l)) return card("I can only answer from the family tree.", `<p>The tree doesn&rsquo;t record the meanings of names. <button class="chip" data-ask="Where did the ${E((/(?:does|of) (?:the )?(?:name |surname )?(\w+)/.exec(l) || [, "Hitchcock"])[1].replace(/^\w/, c => c.toUpperCase()))}s come from">Where did they come from?</button></p>`);

    // relationships
    if ((m = /^(?:how (?:am i|are we)|what(?:'s| is) my relationship|what(?:'s| is) our relationship) (?:related )?to (.+)$/.exec(l)) ||
        (m = /^(?:how (?:is|was|are|were)) (.+?) related to (?:me|us)$/.exec(l)) ||
        (m = /^(?:is|was|are|were) (.+?) (?:related to me|my relative|my ancestor|an ancestor of mine|in my (?:family|line|tree))$/.exec(l)) ||
        (m = /^(?:who|what) (?:is|was|are|were) (.+?) to me$/.exec(l)) || (m = /^what relation (?:is|was) (.+?) to me$/.exec(l)) ||
        (m = /^am i (?:related to|descended from|a descendant of|kin to) (.+)$/.exec(l)) || (m = /^how many generations (?:back is|separate me from|between me and|ago was|is it (?:back )?to) (.+)$/.exec(l))) {
      const tgt = m[1].replace(/^(the )/, "");
      if (/^(royalty|a king|kings|a queen|royal|nobility|a knight)/.test(tgt)) return groupQuestion(q, "which ancestors had a connection to royalty", false);
      if (/^(anyone|anybody|someone) (famous|notable|important)|^(famous|notable) people/.test(tgt)) return notableGroup(scope());
      if (!upMe()) return needMe(raw);
      const sn = surnameOf(tgt); if (sn && /s$/.test(tgt)) return surnameLine(sn);
      return person(tgt.replace(/^(general|president|sir|captain|col\.?|colonel|rev\.?|reverend|dr\.?) /, ""), t => relationAnswer(t));
    }
    if ((m = /^(?:how (?:is|was|are|were)) (.+?) related to (.+)$/.exec(l)) || (m = /^(?:are|were|is|was) (.+?) and (.+?) related$/.exec(l)) ||
        (m = /^what(?:'s| is| was) the relationship between (.+?) and (.+)$/.exec(l)) || (m = /^(?:who|what) (?:is|was) the (?:common|shared) ancestors? (?:of|between|for) (.+?) and (.+)$/.exec(l)) ||
        (m = /^(?:were|was|are|is) (.+?) and (.+?) (?:cousins|siblings|brothers|sisters|kin)$/.exec(l))) {
      if (isMe(m[2])) return upMe() ? person(m[1], t => relationAnswer(t)) : needMe(raw);
      const a = resolve(m[1]), b = resolve(m[2]);
      if (a.none) return notFound(m[1]); if (b.none) return notFound(m[2]);
      if (a.many) return choose(a.many, q); if (b.many) return choose(b.many, q);
      return relationAnswer(a.k, b.k);
    }
    if ((m = /^who was (?:born|older) first,? (.+?) or (.+)$/.exec(l)) || (m = /^(?:was|is) (.+?) older than (.+)$/.exec(l))) {
      const a = resolve(m[1]), b = resolve(m[2]);
      if (a.none) return notFound(m[1]); if (b.none) return notFound(m[2]); if (a.many) return choose(a.many, q); if (b.many) return choose(b.many, q);
      const [x, y] = (R.b[a.k] || 9999) <= (R.b[b.k] || 9999) ? [a.k, b.k] : [b.k, a.k];
      return card(`${who(x)} was born first.`, `<p>${E(name(x))}: ${R.b[x] || "unknown"}; ${E(name(y))}: ${R.b[y] || "unknown"}.</p>`);
    }

    // your own family
    if ((m = /^(?:who (?:are|were) )?(?:my|our) (parents|grandparents|great-?grandparents|great-great-grandparents|(\d+)(?:st|nd|rd|th) great-?grandparents)$/.exec(l)) ||
        (m = /^(?:show me|list|name) (?:pictures of |photos of )?(?:my|our) (parents|grandparents|great-?grandparents|great-great-grandparents|(\d+)(?:st|nd|rd|th) great-?grandparents)$/.exec(l)) ||
        (m = /^(?:pictures|photos) of my (parents|grandparents|great-?grandparents|great-great-grandparents|(\d+)(?:st|nd|rd|th) great-?grandparents)$/.exec(l))) {
      if (!upMe()) return needMe(raw);
      const n = m[1] === "parents" ? 1 : m[1] === "grandparents" ? 2 : /^great-?grandparents/.test(m[1]) ? 3 : /great-great/.test(m[1]) ? 4 : +m[2] + 2;
      const A = upMe(), rows = [...A].filter(([x, v]) => x !== ME && v.d === n).map(([x]) => x);
      const label = n === 1 ? "parents" : n === 2 ? "grandparents" : n === 3 ? "great-grandparents" : `${ord(n - 2)} great-grandparents`;
      return card(`Your ${label}${rows.length < 2 ** n ? ` (${rows.length} of ${2 ** n} in the tree)` : ""}`, `<ul class="list">${rows.sort((a, b) => (R.b[a] || 0) - (R.b[b] || 0)).map(x => `<li>${who(x)}</li>`).join("")}</ul>` + faces(rows) + partial());
    }
    if ((m = /^(?:who (?:is|was) )?(?:my|our) ((?:(?:father|mother|dad|mom)'s )*(?:father|mother|dad|mom|grandfather|grandmother|parents))$/.exec(l))) {
      if (!upMe()) return needMe(raw);
      const steps = m[1].split("'s ").flatMap(s => /grand/.test(s) ? null : [/father|dad/.test(s) ? "f" : "m"]).filter(Boolean);
      if (/grandfather|grandmother/.test(m[1]) && steps.length === m[1].split("'s ").length - 1) return generationFor(m[1]);
      if (/parents$/.test(m[1])) return card("Try &ldquo;Who are my parents?&rdquo;");
      return myLine(steps, "your " + m[1]);
    }
    if (/(my )?(maiden name|grandmother's maiden)/.test(l) && /grandmother|mother/.test(l)) { if (!upMe()) return needMe(raw); return generationFor(/great/.test(l) ? "great-grandmother" : /grand/.test(l) ? "grandmother" : "mother"); }
    if (/\b(paternal line|direct male line|father'?s line|patrilineal|male line|surname line|father to father)\b/.test(l)) return upMe() ? directLine("f") : needMe(raw);
    if (/\b(maternal line|direct female line|mother'?s line|matrilineal|female line|mother to mother)\b/.test(l)) return upMe() ? directLine("m") : needMe(raw);
    if ((m = /^trace (?:my|our|the) (\w+) (?:line|family|ancestry|roots)$/.exec(l)) || (m = /^(?:show me )?(?:my|our) (\w+) (?:line|ancestry|roots)$/.exec(l))) {
      const sn = surnameOf(m[1]); if (sn) return upMe() ? surnameLine(sn) : surnameAbout(sn);
    }
    if (/how far back (does|can|do)|how many generations (does|do|can|back)|oldest generation|how deep/.test(l) && !/been in/.test(l)) {
      const sn = (/trace (?:the |my )?(\w+?)s?\b(?! back)/.exec(l) || [])[1], s2 = sn && surnameOf(sn);
      if (s2) return upMe() ? surnameLine(s2) : surnameAbout(s2, "first");
      return count();
    }
    if (/^how many (of )?(my |our )?ancestors( do i have| are (there|named|in the tree)| in the tree| are named( in the tree)?| have we found)?$/.test(l) || /^how many generations (are|does|do) (in )?(the|my|our) (family )?tree/.test(l)) return count();
    if ((m = /^(?:show me |find )?(?:the )?(\w+?)s? on the map$/.exec(l))) { const sn = surnameOf(m[1]); if (sn) return surnameAbout(sn) + `<p class="note" style="text-align:center">On the <a href="map.html">map</a>, choose <b>Surname</b> and type ${E(sn)} to see their moves.</p>`; }
    if ((m = /(?:for )?how (?:many generations|long) (?:has|have) (?:my|our|the) family (?:been|lived) (?:in|around|near) (.+)$/.exec(l)) || (m = /^how long (?:has|have) (?:my|our) (?:family|ancestors) been in (.+)$/.exec(l))) {
      const pt = placeTest(m[1]); if (pt) return generationsIn(pt);
    }

    // superlatives and eras
    if (/(earliest|oldest|first)(-| )?(known |born |recorded )?(ancestor|person|relative)|born earliest|oldest person in the tree|earliest date|who was born first$/.test(l) && !/america|arrive|came|immigra/.test(l)) return oldest();
    if (/lived (the )?longest|longest[- ]lived|oldest when (he|she|they) died|lived to be the oldest/.test(l)) return superlative("longest");
    if (/died (the )?youngest|youngest to die|died young(est)?\b/.test(l) && !/which|who were/.test(l) || /died the youngest/.test(l)) return superlative("youngest");
    if (/most children|biggest family|largest family|most kids/.test(l)) return superlative("children");
    if (/moved (the )?most|most moves|moved around the most/.test(l)) return superlative("moves");
    if (/(traveled|travelled|went|moved) (the )?(farthest|furthest)|longest journey/.test(l)) return superlative("distance");
    if (/most recent(ly)? (ancestor )?to die|last (ancestor )?to die/.test(l)) return superlative("recentdeath");
    if (/most recent(ly)? (immigrant|to (arrive|immigrate|come))|came to america most recently|latest immigrant|last to (arrive|immigrate|come over)/.test(l)) return superlative("recentimm");
    if (/(first|earliest)( known| recorded| documented)? (of my ancestors |ancestors? |one |person |immigrant )?(to (arrive|come|reach|land|immigrate|get|set foot)|to america|in america|to the (colonies|new world))|came to america first|earliest (immigrant|arrival)|first (immigrant|arrival)|when did (my|our) family (first )?come to america/.test(l)) return superlative("firstimm");
    if ((m = /first (\w+ )?(?:of my ancestors |ancestor |one |person )?(?:to be )?born in (?:america|the colonies|the united states|the us)/.exec(l))) { const sn = m[1] && surnameOf(m[1].trim()); return firstBornAmerica(scope(), sn); }
    if ((m = /^when did the (\w+?)s? (?:first )?(?:come|arrive|get) (?:to|in) america$/.exec(l))) { const sn = surnameOf(m[1]); if (sn) return surnameAbout(sn); }
    if ((m = /(?:what (?:was )?happen(?:ed|ing)|what was going on|what were .+ doing) (?:to |in |with )?(?:my |our |the )?family(?: doing)? (?:in|during|around) (.+)$/.exec(l)) || (m = /^(?:what was )?(?:my|our) family (?:doing )?(?:in|during) (.+)$/.exec(l)) || (m = /^where was (?:my|our) family (?:in|during) (.+)$/.exec(l))) {
      const pe = period(m[1]); if (pe) return inYear(pe.r[0], Math.min(pe.r[1], pe.r[0] + 10), pe.label);
    }

    // names
    if (/named after (their|his|her) (father|dad)/.test(l)) {
      const S = scope(), rows = group(S, k => R.f[k] >= 0 && words(name(k))[0] && words(name(k))[0] === words(name(R.f[k]))[0] && `son of ${who(R.f[k])}`, "", byGen(S));
      return groupAnswer(S, rows, "shared their father&rsquo;s first name", false);
    }
    if (/names repeat|common (first|given) names|most common (first )?names$|popular names|(first|given) names/.test(l)) {
      const S = scope(), c = new Map();
      for (const k of S.set) { const f = words(name(k))[0]; if (f && f.length > 1) c.set(f, (c.get(f) || 0) + 1); }
      return card(`The most common first names among ${S.whose} ancestors`, `<p>${[...c].sort((a, b) => b[1] - a[1]).slice(0, 25).map(([n, x]) => `${E(n.replace(/^\w/, s => s.toUpperCase()))} (${x})`).join(", ")}.</p>` + scopeNote(S));
    }
    if ((m = /(?:sur)?names (?:come|came|are) from (.+)$/.exec(l)) || (m = /^(?:which|what) (\w+) (?:sur)?names/.exec(l))) {
      const pt = placeTest(ADJ[m[1]] || m[1]);
      if (pt) {
        const S = scope(), c = new Map();
        for (const k of S.set) { const g = GRAPH.people[pid(k)], p = prof(k); if (g && g.surname && p && pt.test(p.b[1])) c.set(g.surname, (c.get(g.surname) || 0) + 1); }
        const top = [...c].sort((a, b) => b[1] - a[1]);
        if (top.length) return card(`${top.length} surnames among ${S.whose} ancestors born in ${E(pt.label)}`, `<p>${top.map(([s, n]) => `<button class="chip" data-ask="Tell me about the ${E(s)}s">${E(s)} <span class="yrs">${n}</span></button>`).join(" ")}</p>` + scopeNote(S));
      }
    }
    // surnames
    if (/^(what|which) surnames|most common surnames|surnames in (my|the) (family )?tree|list (the )?surnames|^(what|which) (last )?names are in/.test(l)) return surnames();
    if ((m = /^(?:where did|where do) the (\w+?)s? (?:come from|originate)/.exec(l)) || (m = /^(?:tell me about|what about|who were|show me)? ?the (\w+?)s?(?: family)?$/.exec(l)) || (m = /^(\w+?)s? family$/.exec(l)) || (m = /^(\w+s)$/.exec(l))) {
      const sn = surnameOf(m[1]) || surnameOf(m[1] + "s"); if (sn) return surnameAbout(sn);
    }
    if ((m = /^(?:who (?:was|is) the )?(?:first|earliest|oldest) (\w+?)s?$/.exec(l))) { const sn = surnameOf(m[1]); if (sn) return surnameAbout(sn, "first"); }
    if ((m = /^how many (\w+?)s? (?:are|were) (?:there|in the tree|in my tree|in my family)/.exec(l))) { const sn = surnameOf(m[1]); if (sn) return surnameAbout(sn, "count"); }
    if ((m = /^(?:is there|was there|are there|who (?:has|had|is|was)) (?:anyone|anybody|someone|people) (?:named|called) (.+)$/.exec(l)) || (m = /^who (?:has|had) the (?:nick)?name (.+)$/.exec(l)) || (m = /^who was (?:called|known as|nicknamed) (?:the )?(.+)$/.exec(l))) {
      const t = m[1].replace(/^the /, ""), hits = find(t).filter(k => R.n[k]).slice(0, 30);
      return hits.length ? card(`${hits.length === 30 ? "30 or more" : hits.length} ${hits.length === 1 ? "person matches" : "people match"} &ldquo;${E(m[1])}&rdquo;`, `<ul class="list">${hits.map(k => `<li>${who(k)}</li>`).join("")}</ul>`) : notFound(m[1]);
    }
    if (/(which|what) states|which countries|what countries|where did my (ancestors|family) (live|come from)$/.test(l)) {
      const S = scope(), c = new Map(), byCountry = /countr|come from/.test(l);
      const countryOf = pl => { for (const [cn, re] of Object.entries(COUNTRY)) if (re.test(pl)) return cn; return AMERICA.test(pl) ? "United States" : pl.split(", ").pop(); };
      for (const k of S.set) for (const [, pl] of placesOf(k, byCountry ? ["born", "lived"] : LIVED)) {
        const st = byCountry ? countryOf(pl) : pl.split(", ").pop(); if (st && st.length > 2) c.set(st, (c.get(st) || new Set()).add(k)); }
      const rows = [...c].sort((a, b) => b[1].size - a[1].size);
      return card(`Where ${S.whose} ancestors lived`, `<p>${rows.slice(0, 40).map(([s, ks]) => `<button class="chip" data-ask="Which of my ancestors lived in ${E(s)}">${E(s)} <span class="yrs">${ks.size}</span></button>`).join(" ")}</p>` + scopeNote(S));
    }
    if (/where is (.+)/.test(l) && !/buried|born/.test(l)) { const pl = /where is (.+)/.exec(l)[1]; const pt = placeTest(pl); if (pt) { const S = scope(); const rows = group(S, k => placesOf(k, LIVED).some(([, x]) => pt.test(x)) && true); return card(`${E(pt.label)}`, `<p>${rows.length} of ${S.whose} ancestors are recorded there. I can&rsquo;t show maps here, but the <a href="map.html">map</a> can.</p>` + (rows.length ? `<ul class="list">${rows.slice(0, 20).map(([k]) => `<li>${who(k)}</li>`).join("")}</ul>` : "")); } }

    // "what year was X born", "what unit was X in": a named person comes first
    if (/^what\b/.test(l) && !/\b(ancestors|relatives|forebears|family|my|our)\b/.test(l)) { const pi = personIntent(q, l); if (pi && pi.html) return pi.html; }
    // casual noun phrases: "irish ancestors", "civil war ancestors", "ancestors in kentucky"
    {
      const cas = l.replace(/^(show me |list |find )?(all )?(my |our |the )?/, "");
      let x;
      if ((x = /^(.+?) (ancestors|relatives|forebears)$/.exec(cas))) {
        const a = x[1];
        if (war(a)) return veterans(war(a), q);
        if (/^immigrants?$|^immigrant$/.test(a)) return immigrants(scope(), false);
        if (ADJ[a] || COUNTRY[a.replace(/^\w/, c => c.toUpperCase())]) return groupQuestion(q, "which ancestors came from " + (ADJ[a] || a), false);
        if (topicOf(a)) return groupQuestion(q, "which ancestors " + a, false);
      }
      if ((x = /^(?:ancestors|relatives) (?:in|from) (.+)$/.exec(cas))) return groupQuestion(q, "which ancestors lived in " + x[1], false);
    }
    // groups: which / who / how many / list
    const isCount = /^how many\b/.test(l);
    const isGroup = /^(which|whose|what|how many|list|name|are there|were there|did any|were any|was any|do i have|have any|has any|any of|show me (all|the|my)|(was|were|is|did|has) (anyone|anybody|someone|any of))\b/.test(l) ||
      /^who (were|are|was|is|had|have|has|fought|served|came|lived|died|went|got|left|married|may|might|knew|met|ran|owned|founded|sheltered|survived|arrived|moved|traveled|travelled|immigrated|emigrated)\b/.test(l) ||
      /\b(ancestors|relatives|forebears|veterans|soldiers|immigrants)\b/.test(l);
    if (isGroup) {
      // a question about one named person ("who were Thomas Baskett's parents", "how many children did Sudie Clay have")
      if (!/\b(ancestors|relatives|forebears|family|my|our|anyone|anybody|any|people|everyone|all|someone)\b/.test(l)) {
        const pi = personIntent(q, l, 2);
        if (pi && pi.html) return pi.html;
      }
      // "who was X" is about a person when X is a name; "who was a captain" is a group
      const whoX = /^who (?:was|is) (?!an? |the first|born|killed|captured|adopted|knighted|at |in )(.+)$/.exec(l);
      const asPerson = whoX && !topicOf(whoX[1]) && !/ancestors|relatives/.test(l) && resolve(whoX[1]);
      if (asPerson && asPerson.many) return choose(asPerson.many, q);
      if (!(asPerson && asPerson.k != null)) {
        const cas = l.replace(/^(my|our|the|all)\s+/, "").replace(/^(show me |list )?(my |our |the )?/, "");
        let g = groupQuestion(q, l, isCount);
        if (!g && (m = /^(?:my |our |the )?(.+?) (ancestors|relatives|forebears)$/.exec(cas))) {       // "irish ancestors", "civil war ancestors"
          const x = m[1];
          g = war(x) ? veterans(war(x), q) : /immigrant/.test(x) ? immigrants(scope(), false) : ADJ[x] ? groupQuestion(q, "which ancestors came from " + ADJ[x], false) : topicOf(x) ? groupQuestion(q, "which ancestors " + x, false) : null;
        }
        if (!g && (m = /^(?:my |our )?ancestors (?:in|from) (.+)$/.exec(cas))) g = groupQuestion(q, "which ancestors lived in " + m[1], false);
        if (g) return g;
      }
    }
    if (/^(revolutionary war|civil war|war of 1812|french and indian war|world war i) (ancestors|soldiers|veterans)$/.test(l)) return veterans(war(l), q);

    // one person
    const pi = personIntent(q, l);
    if (pi && pi.html) return pi.html;
    if ((m = /^(?:who (?:is|was)|tell me about|what about|show me|about) (.+)$/.exec(l))) return person(m[1], t => personCard(t));
    const r = resolve(q);
    if (r.k != null) return personCard(r.k);
    if (r.many) return choose(r.many, q);
    if (pi && pi.miss) return notFound(pi.miss);
    if (q.split(" ").length <= 4 && !/^(who|what|when|where|which|how|did|was|is|are|were|why|list|show)\b/i.test(q)) return notFound(q);
    return card("I didn&rsquo;t understand that question.", `<p>I answer from the family tree and the map&rsquo;s research, and I understand questions like these:</p>` +
      `<div class="chips">${EXAMPLES.slice(0, 10).map(x => `<button class="chip" data-ask="${E(x)}">${E(x)}</button>`).join("")}</div>` +
      `<p class="note"><a href="#" data-ask="help">More kinds of questions</a></p>`);
  }
  function generationFor(label) {
    const n = label === "mother" || label === "father" ? 1 : /great/.test(label) ? 3 : 2;
    const A = upMe(), rows = [...A].filter(([x, v]) => x !== ME && v.d === n && (!/mother|father/.test(label) || sexOf(x) === (/mother/.test(label) ? "F" : "M"))).map(([x]) => x);
    return card(`Your ${E(label)}${rows.length === 1 ? "" : "s"}`, `<ul class="list">${rows.map(x => `<li>${who(x)}${/mother/.test(label) ? ` <span class="sub">born ${E(name(x).split(" ").pop())}</span>` : ""}</li>`).join("")}</ul>` + faces(rows) + partial());
  }
  const personCard = k => person(k);

  // ---------------------------------------------------------------- page wiring
  function mount() {
    const form = document.getElementById("ask"), input = document.getElementById("q"), out = document.getElementById("answer");
    const show = async (html) => { out.innerHTML = await html; out.hidden = false; document.body.classList.add("answered"); };
    const ask = async (text) => {
      if (!text.trim()) return;
      input.value = text;
      out.hidden = false; out.innerHTML = `<div class="answer thinking">Looking through the tree…</div>`;
      document.body.classList.add("answered");
      try { await show(answer(text)); } catch (e) { console.error(e); await show(card("Something went wrong answering that.", `<p>${E(e.message)}</p>`)); }
      try { history.replaceState(null, "", "?q=" + encodeURIComponent(text)); } catch (e) {}
    };
    form.onsubmit = e => { e.preventDefault(); ask(input.value); };
    input.addEventListener("focus", load, { once: true });
    document.getElementById("examples").innerHTML = EXAMPLES.slice(0, 4).map(x => `<button class="chip" data-ask="${E(x)}">${E(x)}</button>`).join("");
    // rotating example in the empty box
    let n = 0; const ph = document.getElementById("q-hint");
    const tick = () => { if (input.value || document.activeElement === input) { ph.style.opacity = 0; return; }
      ph.style.opacity = 0; setTimeout(() => { ph.textContent = `Try “${EXAMPLES[n++ % EXAMPLES.length]}”`; ph.style.opacity = 1; }, 250); };
    tick(); setInterval(tick, 3800);
    input.addEventListener("input", () => { ph.style.opacity = 0; });
    input.addEventListener("blur", () => { if (!input.value) ph.style.opacity = 1; });

    document.addEventListener("click", async e => {
      const a = e.target.closest("[data-ask],[data-pick],[data-act],[data-me]");
      if (!a) return;
      e.preventDefault();
      if (a.dataset.ask) return ask(a.dataset.ask);
      if (a.dataset.pick) {                           // a choice between namesakes: ask again about that one
        const k = +a.dataset.pick, again = a.dataset.again;
        return show(answerFor(again, k));
      }
      if (a.dataset.act === "me") { e.stopPropagation(); window.scrollTo({ top: 0, behavior: "smooth" }); return Viewer.open(); }
    });
    // "Viewing as" changed (from the header button, on this page or another): answer the waiting question, or the one showing, again
    Viewer.onChange(v => {
      me = v; showMe();
      const again = pending || (document.body.classList.contains("answered") && input.value);
      pending = null;
      if (again) ask(again);
    });
    Family.onChange(() => { if (R) unlockNames().then(showMe); });
    load().then(showMe);
    showMe();
    const q0 = new URLSearchParams(location.search).get("q");
    if (q0) ask(q0);
  }
  // re-run a question with a namesake chosen: substitute the choice for the name that was ambiguous
  async function answerFor(q, k) {
    const saved = resolve;
    const hits = new Set(find(name(k)));
    let used = false;
    resolve = s => { const r = saved(s); if (!used && r.many && r.many.includes(k)) { used = true; return { k }; } return r; };
    try { return await answer(q); } finally { resolve = saved; }
  }

  return { mount, answer, load, setMe };
})();
