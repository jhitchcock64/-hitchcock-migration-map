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
  // stored per browser: {k: pid, g: 0 for the person themselves, or generations below them}
  let me = null;
  try { me = JSON.parse(localStorage.getItem("hm-ask-me") || "null"); } catch (e) {}
  function meIdx() { return me && at.has(me.k) ? at.get(me.k) : -1; }
  // g > 0: a descendant of k, and of k's spouse s (if one is chosen, or k had only one)
  function setMe(k, g, s) {
    if (k != null && g > 0 && s == null && spouses[k].length === 1) s = spouses[k][0];
    me = k == null ? null : Object.assign({ k: pid(k), g }, s != null && s >= 0 ? { s: pid(s) } : {});
    try { me ? localStorage.setItem("hm-ask-me", JSON.stringify(me)) : localStorage.removeItem("hm-ask-me"); } catch (e) {}
    showMe();
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
    el.innerHTML = k >= 0 ? `Asking as <b>${E(meLabel())}</b> · <a href="#" data-act="me">change</a>`
      : `<a href="#" data-act="me">Tell me who you are</a> for &ldquo;how am I related&rdquo; questions`;
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
    jenny: "jennie", abby: "abigail", sue: "susan", allie: "allison", al: "albert", bert: "albert" };
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
    const hits = find(q);
    if (!hits.length) return { none: true };
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
    const times = ["", " once removed", " twice removed", " three times removed"][rem] || ` ${rem} times removed`;
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
    } else { A = up(fromK); whose = name(fromK) + "&rsquo;s"; }
    const r = relate(A, t, whose);
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
    if (ss.length) return card(`Yes. ${who(k)} served in ${E(w ? w.label : ss.map(s => s.war.replace(/,.*$/, "")).join(" and "))}.`,
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
  function bornIn(place) {
    const S = scope(), re = new RegExp("\\b" + place.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i"), rows = [];
    for (const k of S.set) { const p = prof(k); if (p && re.test(p.b[1] || "")) rows.push(k); }
    rows.sort((a, b) => (R.b[a] || 0) - (R.b[b] || 0));
    if (!rows.length) return card(`None of ${S.whose} ancestors on the map is recorded as born in ${E(place)}.`, scopeNote(S));
    return card(`${rows.length} of ${S.whose} ancestors ${rows.length === 1 ? "was" : "were"} born in ${E(place)}.`,
      `<ul class="list">${rows.slice(0, 80).map(k => `<li>${who(k)} <span class="sub">${E(prof(k).b[1])}</span></li>`).join("")}</ul>` +
      (rows.length > 80 ? `<p class="note">The first 80, oldest first.</p>` : "") + scopeNote(S));
  }
  function ships(q) {
    const S = scope(), m = /(?:on|aboard) (?:the )?(.+)/i.exec(q), ship = m && !/^(a )?ships?$/i.test(m[1]) ? m[1].replace(/^ship /i, "") : "";
    const ev = NOTABLE.events.filter(e => e.sh && (!ship || e.sh.toLowerCase().includes(ship.toLowerCase())) && e.p.some(p => S.set.has(at.get(p))));
    if (!ev.length) return card(ship ? `None of ${S.whose} ancestors is recorded arriving on the ${E(ship)}.` : `No ships recorded.`, scopeNote(S));
    ev.sort((a, b) => a.y - b.y);
    return card(ship ? `${S.whose.replace(/^./, c => c.toUpperCase())} ancestors on the ${E(ev[0].sh)}` : `${cap(S.whose)} ancestors&rsquo; ships`,
      `<ul class="list">${ev.map(e => `<li><b>${E(e.sh)}</b>, ${E(e.d)}: ${e.p.filter(p => S.set.has(at.get(p))).map(p => who(at.get(p))).join(", ")}<div class="sub">${E(e.t)}</div></li>`).join("")}</ul>` + scopeNote(S));
  }
  function oldest() {
    const S = scope();
    const k = [...S.set].filter(x => R.b[x] > 0).sort((a, b) => R.b[a] - R.b[b])[0];
    return k == null ? null : card(`${cap(S.whose)} earliest-born ancestor in the tree is ${who(k)}.`,
      `<p>${cap(he(k))} is ${S.whose} ${E(relTo(S, k))}.</p>` + scopeNote(S), k);
  }
  function count() {
    const S = scope(), named = [...S.set].filter(k => R.n[k]);
    const gens = Math.max(...[...S.set].map(k => S.A.get(k).d));
    return card(`The tree names ${named.length.toLocaleString()} of ${S.whose} ancestors, going back ${gens} generations.`, scopeNote(S));
  }

  // ---------------------------------------------------------------- the question
  let pending = null;
  function needMe(q) {
    pending = q;
    return card("First, who are you?", `<p>Search for yourself, or for a parent or grandparent if you aren&rsquo;t in the tree yet.</p>` + pickerHTML());
  }
  function pickerHTML() {
    return `<div class="picker"><input id="me-q" type="search" placeholder="Your name, or a parent&rsquo;s" autocomplete="off"><div id="me-list"></div>` +
      (Family.shown ? "" : `<p class="note">Living family are listed only after the family password is entered (the lock at the top right). ` +
        `Otherwise, choose a parent or grandparent who has died.</p>`) +
      (me ? `<p class="note"><a href="#" data-act="forget">Forget who I am on this device</a></p>` : "") + `</div>`;
  }
  const isMe = s => /^(me|myself|i|us)$/i.test(s.trim());
  async function answer(raw) {
    await load();
    const q = raw.trim().replace(/[?.!]+$/, "").replace(/\s+/g, " "), l = q.toLowerCase();
    let m, k;
    const person = (s, f) => { const r = resolve(s); return r.none ? notFound(s) : r.many ? choose(r.many, q) : f(r.k); };

    // how am I related to X / how is X related to me / how is X related to Y
    if ((m = /^(?:how (?:am i|are we)|what(?:'s| is) my relationship) (?:related )?to (.+)$/i.exec(q)) ||
        (m = /^(?:how is|how was|how are|how were) (.+?) related to (?:me|us)$/i.exec(q)) ||
        (m = /^(?:is|was|are) (.+?) (?:related to me|my relative|my ancestor)$/i.exec(q)) ||
        (m = /^(?:who is|who was|what is|what was) (.+?) to me$/i.exec(q)))
      return upMe() ? person(m[1], t => relationAnswer(t)) : needMe(raw);
    if ((m = /^how (?:is|was|are|were) (.+?) related to (.+)$/i.exec(q))) {
      if (isMe(m[2])) return upMe() ? person(m[1], t => relationAnswer(t)) : needMe(raw);
      const a = resolve(m[1]), b = resolve(m[2]);
      if (a.none) return notFound(m[1]); if (b.none) return notFound(m[2]);
      if (a.many) return choose(a.many, q); if (b.many) return choose(b.many, q);
      return relationAnswer(a.k, b.k);
    }
    // wars
    const w = war(l);
    if ((m = /^(?:which|what|who|list)(?: of)?(?: (?:my|our|the))? ?(?:ancestors|relatives|people|family members|men|family)? ?(?:who )?(?:fought|served|were|was|fight|serve)\b(.*)$/i.exec(q)) && (w || /war|military|army|soldier|served|fought/.test(l)))
      return veterans(w, q);
    if (/^(?:list|show)?\s*(?:the )?(?:veterans|soldiers)/i.test(q)) return veterans(w, q);
    if ((m = /^(?:did|was|has|were) (.+?) (?:ever )?(?:serve|fight|served|fought|a soldier|a veteran|in the (?:army|military|militia)|in the (.+))(?:\b.*)?$/i.exec(q)))
      return person(m[1].replace(/\s+(?:in|during)$/, ""), t => served(t, w));
    // dates and places
    if ((m = /^(?:when|what year|what date) (?:was|is) (.+?) born$/i.exec(q)) || (m = /^(?:when is|when was) (.+?)'s (?:birthday|birth)$/i.exec(q)))
      return person(m[1], t => vital(t, "born"));
    if ((m = /^(?:when|what year|what date) did (.+?) die$/i.exec(q)) || (m = /^when was (.+?)'s death$/i.exec(q)))
      return person(m[1], t => vital(t, "died"));
    if ((m = /^how old was (.+?) when (?:he|she|they) died$/i.exec(q))) return person(m[1], t => vital(t, "died"));
    if ((m = /^where (?:was|is) (.+?) born$/i.exec(q))) return person(m[1], t => wherePlace(t, "born"));
    if ((m = /^where did (.+?) die$/i.exec(q)) || (m = /^where (?:is|was) (.+?) buried$/i.exec(q))) return person(m[1], t => wherePlace(t, "died"));
    if ((m = /^where did (.+?) live$/i.exec(q))) return person(m[1], t => lived(t));
    // family
    if ((m = /^who (?:were|are) (.+?)'s parents$/i.exec(q)) || (m = /^who (?:were|are) the parents of (.+)$/i.exec(q))) return person(m[1], t => family(t, "parents"));
    if ((m = /^who (?:was|is) (.+?)'s (father|mother|dad|mom)$/i.exec(q))) return person(m[1], t => family(t, /father|dad/.test(m[2]) ? "father" : "mother"));
    if ((m = /^who did (.+?) marry$/i.exec(q)) || (m = /^who (?:was|is) (.+?)'s (?:wife|husband|spouse)$/i.exec(q))) return person(m[1], t => family(t, "spouse"));
    if ((m = /^(?:who (?:were|are) )?(.+?)'s (?:children|kids)$/i.exec(q)) || (m = /^how many (?:children|kids) did (.+?) have$/i.exec(q))) return person(m[1], t => family(t, "children"));
    // groups
    if ((m = /^(?:which|what|who)(?: of)?(?: my| our| the)? ?(?:ancestors|relatives|people)? (?:were|was) (?:born|from) in (.+)$/i.exec(q)) ||
        (m = /^(?:which|what|who)(?: of)?(?: my| our| the)? ?(?:ancestors|relatives|people)? (?:came|come|were|was) from (.+)$/i.exec(q)))
      return bornIn(m[1]);
    if (/^(?:which|what|who)/i.test(q) && (/\b(ship|ships|mayflower|sailed|voyage|aboard)\b/i.test(q) || /\bcame (?:over )?on (?:the )?/i.test(q))) return ships(q);
    if (/^(?:who (?:is|was) )?(?:my|our|the) (?:oldest|earliest)(?: known)? ancestor/i.test(q)) return oldest();
    if (/^how many ancestors/i.test(q)) return count();
    if (/^who am i$/i.test(q)) { pending = null; return card("Who are you?", pickerHTML()); }
    // a person
    if ((m = /^(?:who (?:is|was)|tell me about|what about|show me|about) (.+)$/i.exec(q))) return person(m[1], t => person_(t));
    const r = resolve(q);
    if (r.k != null) return person_(r.k);
    if (r.many) return choose(r.many, q);
    if (q.split(" ").length <= 4 && !/^(who|what|when|where|which|how|did|was|is|are|were|why|list|show)\b/i.test(q)) return notFound(q);
    return card("I didn&rsquo;t understand that question.", `<p>I answer from the family tree and the map&rsquo;s research, and I understand questions like these:</p>` +
      `<div class="chips">${EXAMPLES.map(x => `<button class="chip" data-ask="${E(x)}">${E(x)}</button>`).join("")}</div>`);
  }
  const person_ = k => person(k);

  const EXAMPLES = ["How am I related to John Coe?", "When was Sudie Clay born?", "Did Jared Hitchcock serve in the Revolutionary War?",
    "Which of my ancestors fought in the Revolutionary War?", "Who were Thomas Baskett's parents?", "Which ancestors were born in Ireland?",
    "Where did William Worthington live?", "Who is my earliest ancestor?", "Which ancestors came on the Speedwell?"];

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
      if (a.dataset.act === "me") { await load(); pending = null; return show(card("Who are you?", pickerHTML())); }
      if (a.dataset.act === "forget") { setMe(null); return show(card("Forgotten on this device.")); }
      if (a.dataset.me) {                             // chose themselves (g = 0) or an ancestor (g > 0)
        const k = +a.dataset.me, g = +a.dataset.g;
        if (g > 0 && a.dataset.s == null && spouses[k].length > 1)
          return show(card(`Which of ${E(name(k))}&rsquo;s marriages?`, `<div class="chips">${spouses[k].map(s =>
            `<button class="chip" data-me="${k}" data-g="${g}" data-s="${s}">with ${E(name(s))} <span class="yrs">${E(yrs(s))}</span></button>`).join("")}` +
            `<button class="chip" data-me="${k}" data-g="${g}" data-s="-1">not sure</button></div>`));
        setMe(k, g, a.dataset.s != null ? +a.dataset.s : null);
        if (pending) { const p = pending; pending = null; return ask(p); }
        return show(card(`Got it: asking as ${E(meLabel())}.`, `<p>Now try &ldquo;How am I related to John Coe?&rdquo;</p>`));
      }
    });
    document.addEventListener("input", e => {
      if (e.target.id !== "me-q") return;
      const list = document.getElementById("me-list"), s = e.target.value.trim();
      if (s.length < 2) { list.innerHTML = ""; return; }
      const hits = find(s).slice(0, 8);
      list.innerHTML = hits.length ? hits.map(k => `<div class="me-row"><span>${E(name(k))} <span class="yrs">${E(yrs(k))}</span></span>` +
        `<span class="me-acts">${(R.d[k] ? [] : [[0, "This is me"]]).concat([[1, "My parent"], [2, "Grandparent"], [3, "Great-grandparent"]])
          .map(([g, t]) => `<button class="chip" data-me="${k}" data-g="${g}">${t}</button>`).join("")}</span></div>`).join("")
        : `<p class="note">No one by that name${Family.shown ? "" : " among those who have died; living family appear after the family password is entered"}.</p>`;
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
