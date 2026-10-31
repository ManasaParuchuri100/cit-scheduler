"use strict";
/* CIT Scheduler front end. One file, no build step. */
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ---------- icons (24px line icons, drawn here, no emoji) */
const IC = {
  home: ["M3 10.5 12 3l9 7.5V19a2 2 0 0 1-2 2h-4.5v-6h-5v6H5a2 2 0 0 1-2-2z"],
  calendar: ["M6 4.5h12A2.5 2.5 0 0 1 20.5 7v11.5A2.5 2.5 0 0 1 18 21H6a2.5 2.5 0 0 1-2.5-2.5V7A2.5 2.5 0 0 1 6 4.5z", "M8 2.5v4M16 2.5v4M3.5 10h17"],
  building: ["M5 21V5.5A1.5 1.5 0 0 1 6.5 4h7A1.5 1.5 0 0 1 15 5.5V21", "M15 9.5h2.5A1.5 1.5 0 0 1 19 11v10M3 21h18M8.5 8h3M8.5 12h3M8.5 16h3"],
  clipboard: ["M9 3.5h6a1 1 0 0 1 1 1V6H8V4.5a1 1 0 0 1 1-1z", "M8 5H6.5A2 2 0 0 0 4.5 7v12.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7A2 2 0 0 0 17.5 5H16", "M9 12h6M9 16h4"],
  swap: ["M7 7.5h13M16.5 3.5l4 4-4 4", "M17 16.5H4M7.5 12.5l-4 4 4 4"],
  file: ["M14 3H7.5A2 2 0 0 0 5.5 5v14a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V7.5z", "M14 3v4.5h4.5M9 13h6M9 17h4"],
  mail: ["M5 5.5h14A1.5 1.5 0 0 1 20.5 7v10a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 17V7A1.5 1.5 0 0 1 5 5.5z", "M4 7.5l8 5.5 8-5.5"],
  plus: ["M12 5v14M5 12h14"],
  search: ["M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "M20.5 20.5l-4.6-4.6"],
  bell: ["M6 9a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9", "M10.300 21a2 2 0 0 0 3.400 0"],
  sparkle: ["M11 3.5l1.700 4.800L17.500 10l-4.800 1.700L11 16.500l-1.700-4.800L4.500 10l4.800-1.700z", "M18.500 15.500l.7 1.800 1.800.7-1.800.7-.7 1.800-.7-1.800-1.800-.7 1.800-.7z"],
  check: ["M5 12.500l4.500 4.500L19 7.500"],
  alert: ["M12 8.500v4.500M12 16.500v.2", "M10.300 4.200 3 17a2 2 0 0 0 1.700 3h14.600a2 2 0 0 0 1.700-3L13.700 4.200a2 2 0 0 0-3.400 0z"],
  arrow: ["M5 12h14M13 6l6 6-6 6"],
  x: ["M6 6l12 12M18 6 6 18"],
  logout: ["M9.500 20.500H6a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2h3.500", "M15.500 16.500 20 12l-4.500-4.500M20 12H9.500"],
  shield: ["M12 3l7.500 2.800v5.700c0 4.600-3.100 8.100-7.500 9.500-4.400-1.400-7.500-4.900-7.500-9.500V5.800z", "M8.800 12l2.200 2.200 4.200-4.400"],
  users: ["M16 20.500v-1.700a3.800 3.800 0 0 0-3.800-3.800H7.300a3.800 3.800 0 0 0-3.800 3.800v1.700", "M9.800 11a3.500 3.500 0 1 0 0-7 3.500 3.500 0 0 0 0 7z", "M20.500 20.500v-1.700a3.800 3.800 0 0 0-2.800-3.700M15.500 4.200a3.500 3.500 0 0 1 0 6.600"],
  book: ["M4.500 19A2.500 2.500 0 0 1 7 16.500h12.500V3.500H7A2.500 2.500 0 0 0 4.500 6z", "M4.500 19A2.500 2.500 0 0 0 7 21.500h12.500v-5"],
  mic: ["M12 14.500a3 3 0 0 0 3-3v-5a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3z", "M18.500 11a6.500 6.500 0 0 1-13 0M12 17.500v3.500"],
  grid: ["M4 4h6.500v6.500H4zM13.500 4H20v6.500h-6.500zM4 13.500h6.500V20H4zM13.500 13.500H20V20h-6.500z"],
  doc: ["M14 3H7.500A2 2 0 0 0 5.500 5v14a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V7.500z", "M14 3v4.500h4.500"],
};
const ic = (n, s = 20, sw = 1.8) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${(IC[n] || []).map(d => `<path d="${d}"/>`).join("")}</svg>`;

/* ---------- state */
const st = { token: sessionStorage.getItem("cit_token") || "", me: null, meta: null, tab: "overview", ov: null, week: null,
  tt: { view: "group", id: "", week: null, course: "", kinds: { lecture: true, tutorial: true, lab: true, event: true } }, rooms: { day: "MON", frm: 1, to: 2, min_cap: 0, rtype: "", need: [] }, roomRes: null,
  bk: { week: null, filter: "all", showForm: false, sub: "rooms" }, sw: { scope: "day", week: 0, give: "", take: "", opts: null, note: "", q: "", day: "", only: true, dept: "mine", cells: null, rows: [] }, ol: { form: null, check: null, rows: [] }, xc: { form: null, check: null, rows: [], week: 9 }, bf: null, ch: { type: "faculty", out: null }, notesOpen: false, accounts: null, pickRole: "admin", ask: null, found: null };
const DAYS = ["MON", "TUE", "WED", "THU", "FRI"];
const DAYN = { MON: "Mon", TUE: "Tue", WED: "Wed", THU: "Thu", FRI: "Fri", SAT: "Sat" };
const DAYF = { MON: "Monday", TUE: "Tuesday", WED: "Wednesday", THU: "Thursday", FRI: "Friday", SAT: "Saturday" };
const NEEDS = { projector: "Projector", pa_system: "Mic and sound", stage: "Stage", computers: "Computers", power_benches: "Power benches", accessible: "Step-free access", ac: "Air conditioning" };
const TYPES = { classroom: "Classroom", lecture_hall: "Lecture hall", seminar_hall: "Seminar hall", auditorium: "Auditorium", outdoor: "Open air", lab_cs: "Computer lab", lab_elec: "Electronics lab", lab_phy: "Physics lab", lab_civil: "Civil lab", workshop: "Workshop" };
const CATS = { exam: "Exams", regular_session: "Regular classes", institute_event: "Institute events", guest_lecture: "Guest lectures", department_event: "Department events", club_event: "Club events" };
const CAT1 = { exam: "exam", regular_session: "regular class", institute_event: "institute event", guest_lecture: "guest lecture", department_event: "department event", club_event: "club event" };
const NAV = { overview: ["Overview", "home"], timetable: ["Timetable", "calendar"], rooms: ["Rooms", "building"], bookings: ["Bookings", "clipboard"], changes: ["Changes", "swap"], exams: ["Exams", "file"],
  requests: ["Away and requests", "mail"], swaps: ["Swap classes", "swap"], newrequest: ["New request", "plus"], myrequests: ["My requests", "clipboard"] };
const SHADE = [["#2D3A47", "#fff"], ["#3B4D5F", "#fff"], ["#6F859B", "#fff"], ["#B9C6A0", "#3F4F26"], ["#E3D3AE", "#5C4513"], ["#E6ECF1", "#3B4D5F"]];

/* ---------- helpers */
function toast(msg, bad) { const t = $("#toast"); t.textContent = msg; t.className = "toast" + (bad ? " err" : ""); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.add("hidden"), 4500); }
async function api(path, method = "GET", body) {
  const r = await fetch(path, { method, headers: { "Content-Type": "application/json", ...(st.token ? { Authorization: "Bearer " + st.token } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
  let j = null; try { j = await r.json(); } catch (e) { }
  if (r.status === 401 && st.token) { signOut(); throw new Error("Please sign in again"); }
  if (!r.ok) throw new Error((j && (j.error || j.detail)) || r.statusText);
  return j;
}
const act = async fn => { try { return await fn(); } catch (e) { toast(e.message, true); } };
const per = p => st.meta.periods.find(x => x.id === +p);
const pStart = p => per(p) ? per(p).start : "";
const pEnd = p => per(p) ? per(p).end : "";
const span = (a, b) => `${pStart(a)} to ${pEnd(b)}`;
const pOpt = (sel, end) => st.meta.periods.map(p => `<option value="${p.id}" ${+sel === p.id ? "selected" : ""}>P${p.id} · ${end ? p.end : p.start}</option>`).join("");
const dayOpt = (sel, days = DAYS) => days.map(d => `<option value="${d}" ${sel === d ? "selected" : ""}>${DAYF[d]}</option>`).join("");
const facName = id => (st.meta.faculty.find(f => f.id === id) || {}).name || id;
const courseTitle = id => (st.meta.courses[id] || {}).title || id;
const role = () => st.me.user.role;
const initials = n => n.replace(/^(Dr|Prof)\.?\s+/i, "").split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase();
const pill = (tone, text) => `<span class="pill ${tone}">${esc(text)}</span>`;
const field = (label, inner, opts = {}) => `<label class="field ${opts.hint ? "hint" : ""} ${opts.cls || ""}"><span class="l">${label}${opts.tag ? `<em>${opts.tag}</em>` : ""}</span>${inner}</label>`;
const tg = (attr, val, checked, text) => `<label class="tg"><input type="checkbox" ${attr}="${esc(val)}" ${checked ? "checked" : ""}><span>${esc(text)}</span></label>`;
function download(name) {
  act(async () => {
    const r = await fetch("/api/export/" + name, { headers: { Authorization: "Bearer " + st.token } });
    if (!r.ok) throw new Error((await r.json()).error || "Could not export");
    const b = await r.blob(), a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = name; a.click();
  });
}
function statusPills(r) {
  const out = [];
  if (r.cancelled) out.push(pill("gray", "Cancelled"));
  else if (r.status === "rejected") out.push(pill("bad", "Not possible"));
  else if (r.status === "approved") out.push(r.state === "published" ? pill("ok", "Approved") : pill("warn", "Ready, waiting for approval"));
  else out.push(r.state === "published" ? pill("warn", "Alternative approved") : pill("warn", "Alternative offered, waiting"));
  if (r.room_changed && r.status !== "rejected") out.push(pill("info", "Room changed"));
  if (r.overrides && r.overrides.length) out.push(pill("bad", "Moves a class"));
  return out.join(" ");
}
const classStatus = s => pill({ "On time": "ok", "Room changed": "warn", "Time changed": "warn", "Moved for an event": "bad" }[s] || "gray", s);

/* ---------- login */
const ROLES = [
  ["admin", "shield", "Admin", "Dean's office", "Generates the timetable, decides bookings, approves changes.", ["Overview", "Timetable", "Rooms", "Bookings", "Changes", "Exams"]],
  ["department_coordinator", "users", "Department coordinator", "Per department", "Asks for changes to the department's sessions, books rooms, approves the department's labs.", ["Overview", "Timetable", "Rooms", "Bookings", "Changes"]],
  ["faculty", "book", "Faculty", "Teachers", "Sees their own timetable, marks when they are away, asks for a room.", ["Overview", "My timetable", "Away and requests"]],
  ["club", "mic", "Club representative", "Clubs and societies", "Asks for a venue, cancels a request, sees the reason for every answer.", ["Overview", "Find a room", "New request", "My requests"]],
];
function artSVG() {
  const cols = ["#6F859B", "#B9C6A0", "#EBDADC", "#E2E9D2", "#F1E2BD"]; let s = "";
  const pat = [[0, 0, 1], [0, 3, 2], [1, 1, 2], [2, 0, 1], [2, 2, 3], [3, 1, 1], [3, 4, 2], [4, 0, 2], [4, 3, 1]];
  pat.forEach(([c, r, h], i) => { s += `<rect x="${c * 88}" y="${r * 62}" width="78" height="${h * 62 - 8}" rx="14" fill="${cols[i % 5]}" opacity="${i % 3 ? .55 : .9}"/>`; });
  return `<svg class="art" width="440" height="380" viewBox="0 0 440 380">${s}</svg>`;
}

/* ---------- landing page */
const MOCK = [
  // day, first period, periods, kind, title, room
  [0, 1, 1, "lecture", "CS201", "LH-2"], [0, 2, 3, "lab", "CS292 Lab", "ELEC-LAB-2"], [0, 6, 1, "lecture", "MA101", "LH-1"],
  [1, 2, 1, "tutorial", "MA101 tut", "CR-201"], [1, 4, 1, "lecture", "EC201", "LH-3"], [1, 7, 1, "lecture", "ME201", "LH-5"],
  [2, 1, 1, "lecture", "PH101", "CR-101"], [2, 3, 1, "lecture", "CS201", "LH-2"], [2, 6, 2, "event", "Guest lecture", "Auditorium"],
  [3, 2, 1, "lecture", "CS203", "LH-2"], [3, 4, 1, "tutorial", "PH101 tut", "CR-103"], [3, 6, 3, "lab", "CS291 Lab", "CS-LAB-1"],
  [4, 1, 1, "tutorial", "CS201 tut", "CR-203"], [4, 4, 1, "lecture", "MA101", "LH-1"], [4, 7, 1, "lecture", "EC201", "LH-3"]];
const MOCK_T = { 1: "08:00", 2: "09:00", 3: "10:00", 4: "11:00", 5: "12:00", 6: "14:00", 7: "15:00", 8: "16:00" };
function appMock() {
  const H = 46, L = 22, y = p => p <= 5 ? (p - 1) * H : 5 * H + L + (p - 6) * H, total = 8 * H + L;
  const end = p => { const e = p + 1; return MOCK_T[e] || "17:00"; };
  const cols = ["Mon", "Tue", "Wed", "Thu", "Fri"].map((d, ci) => `<div class="mk-col"><i class="mk-lunch" style="top:${5 * H}px;height:${L}px"></i>${MOCK.filter(m => m[0] === ci).map((m, k) => {
    const [, p, n, kind, t, room] = m, idx = MOCK.indexOf(m);
    return `<div class="mk-blk ${kind}" style="top:${y(p) + 2}px;height:${y(p + n - 1) + H - y(p) - 4}px;--i:${idx}"><b>${t}</b><span>${room}</span>${n > 1 ? `<em>${MOCK_T[p]} to ${end(p + n - 1)}</em>` : ""}</div>`; }).join("")}</div>`).join("");
  const hours = [1, 2, 3, 4, 5, 6, 7, 8].map(p => `<div class="mk-h" style="top:${y(p)}px">${MOCK_T[p]}</div>`).join("");
  const mini = [...Array(5)].map((_, r) => [...Array(7)].map((_, c) => { const n = r * 7 + c - 2; const ok = n >= 1 && n <= 30; const cls = !ok ? "off" : (n === 6 || n === 10) ? "on" : (n > 6 && n < 10) ? "rng" : ""; return `<i class="${cls}">${ok ? n : ""}</i>`; }).join("")).join("");
  return `<div class="mk" id="mk"><div class="mk-win">
    <div class="mk-bar"><i></i><i></i><i></i><span>CIT Scheduler</span></div>
    <div class="mk-body"><aside class="mk-side"><div class="mk-mini"><div class="mk-mh"><b>September</b></div><div class="mk-dn">${["M", "T", "W", "T", "F", "S", "S"].map(d => `<i>${d}</i>`).join("")}</div><div class="mk-dg">${mini}</div></div>
      <div class="mk-lab">Subjects</div>
      <label class="mk-ck on"><u style="--c:#6F859B"></u>Data Structures</label><label class="mk-ck on"><u style="--c:#7C9A5B"></u>Calculus</label><label class="mk-ck"><u style="--c:#D9A24A"></u>Digital Logic</label>
      <div class="mk-lab">Rooms free now</div><div class="mk-chips"><span>LH-3</span><span>SH-1</span><span>AUD</span></div></aside>
      <div class="mk-main"><div class="mk-head"><div><small>Class</small><b>Year 2 · CSE-2</b></div><div class="mk-seg"><span class="on">Class</span><span>Teacher</span><span>Room</span></div></div>
        <div class="mk-days"><i></i>${["Mon", "Tue", "Wed", "Thu", "Fri"].map(d => `<b>${d}</b>`).join("")}</div>
        <div class="mk-grid" style="height:${total}px"><div class="mk-hours">${hours}</div>${cols}<div class="mk-now"><i></i></div></div></div></div></div>
    <div class="mk-pop"><div class="mk-pt">New request</div><div class="mk-in">Hackathon kickoff</div><div class="mk-in sm"><span>Mon</span> 16:00 to 18:00</div><div class="mk-in sm"><span>Seminar hall</span> 120 people</div>
      <div class="mk-state"><span class="chk"><i class="spin"></i>Checking the rules</span><span class="ok">${ic("shield", 16, 2)}Approved, no clash</span></div><div class="mk-save">Save</div>
      <svg class="mk-cur" width="26" height="26" viewBox="0 0 24 24"><path d="M5 3l14 7-6 2-2 6z" fill="#26303B" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg></div>
    <div class="mk-float f1"><span class="d"></span><div><b>189 classes placed</b><small>0 clashes</small></div></div>
    <div class="mk-float f2"><div class="ico">${ic("building", 18)}</div><div><b>Auditorium</b><small>Wed 14:00, held for a guest lecture</small></div></div></div>`;
}
function artNumber() {
  return `<svg viewBox="0 0 300 200" aria-hidden="true"><defs><pattern id="hat" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="#fff"/><path d="M0 0v7" stroke="#3B4D5F" stroke-width="2.4"/></pattern></defs>
    <text x="150" y="176" text-anchor="middle" class="num-t" fill="url(#hat)" stroke="#3B4D5F" stroke-width="2.2">27</text></svg>`;
}
function miniGrid() {
  const cls = ["#DCE5EE", "#DFE7CF", "#F1E2BD", "#DCE5EE", "#DFE7CF", "#DCE5EE"];
  const cells = [[0, 0, 2], [0, 2, 1], [1, 1, 1], [1, 3, 2], [2, 0, 1], [2, 2, 2], [3, 1, 2], [3, 3, 1], [4, 0, 2], [4, 2, 1]];
  return `<div class="mg">${["M", "T", "W", "T", "F"].map(d => `<i class="d">${d}</i>`).join("")}${cells.map(([c, r, h], i) => `<i class="b" style="grid-column:${c + 1};grid-row:${r + 2} / span ${h};background:${cls[i % cls.length]};--i:${i}"></i>`).join("")}</div>`;
}
function showLanding() {
  st.view = "landing";
  const letters = "CHILIKA".split("").map((c, i) => `<span class="ch" style="--i:${i}">${c}</span>`).join("");
  const roles = ROLES.map((r, i) => `<article class="rl-card reveal" style="--i:${i}"><span class="ic">${ic(r[1], 24)}</span><h3>${r[2]}</h3><p>${r[4]}</p><div class="tabs">${r[5].map(t => `<span>${t}</span>`).join("")}</div></article>`).join("");
  const prio = ["Exams", "Regular classes", "Institute events", "Guest lectures", "Department events", "Club events"].map((n, i) => `<div class="pr reveal" style="--i:${i}"><span class="num" style="background:${SHADE[i][0]};color:${SHADE[i][1]}">${i + 1}</span>${n}</div>`).join("");
  $("#app").innerHTML = `<div class="land" id="land"><section class="hero" id="hero">
    <header class="l-top"><span class="l-badge">CIT</span><div class="l-name"><b>Chilika Institute of Technology</b><small>Campus timetables, rooms and events</small></div><span class="l-tag">Every class in its place, every event with a reason</span>
      <nav class="l-nav"><button class="l-link" data-act="landscroll" data-v="l-show">How it works</button><button class="l-link" data-act="landscroll" data-v="l-roles">Roles</button><button class="l-link" data-act="landscroll" data-v="l-rules">Priority</button><button class="btn sm" data-act="tologin">Sign in</button></nav></header>
    <h1 class="l-title" aria-label="Chilika Institute of Technology"><span class="l-mask"><span class="l-big" aria-hidden="true">${letters}</span></span></h1>
    <figure class="l-photo"><img src="/static/campus.jpg" alt="The CIT main building and its dome" fetchpriority="high"></figure>
    <div class="l-title fg" aria-hidden="true"><span class="l-mask"><span class="l-big">${letters}</span></span></div>
    <div class="l-ribbon" aria-hidden="true">Institute of Technology</div>
    <div class="l-intro"><p>Timetables, midsem exams, room bookings and campus events for the whole institute, in one place. Every decision comes with a reason.</p><button class="btn lg" data-act="tologin">Sign in</button></div>
    <dl class="l-meta"><div><dt>27</dt><dd>rooms and labs</dd></div><div><dt>189</dt><dd>classes a week</dd></div><div><dt>4</dt><dd>roles, one login each</dd></div></dl>
  </section>
  <section class="l-sec l-show" id="l-show"><div class="l-wrap"><div><div class="l-kick reveal">See it work</div><h2 class="l-h reveal">A request goes in, the rules decide, and you see why</h2><p class="l-lead reveal">Type what you need in plain English or Hinglish. The app checks every clash, ranks the request by priority and answers with a reason a person can read.</p></div><div class="h-art reveal">${appMock()}</div></div></section>
  <section class="l-campus"><div class="cp-card reveal" id="cp"><img src="/static/campus.jpg" alt="CIT campus lawns and colonnade" loading="lazy"><div class="cp-text"><div class="l-kick">The campus</div><h2>One campus, every room accounted for</h2>
    <div class="cp-facts"><div><b data-count="27">0</b><span>rooms</span></div><div><b data-count="7">0</b><span>labs</span></div><div><b data-count="500">0</b><span>seat auditorium</span></div><div><b data-count="800">0</b><span>seat open-air theatre</span></div></div></div></div></section>
  <section class="l-sec" id="l-roles"><div class="l-wrap"><div class="l-kick reveal">Four roles</div><h2 class="l-h reveal">Everyone sees what they need to do their job</h2><div class="rl-grid">${roles}</div></div></section>
  <section class="l-sec alt" id="l-rules"><div class="l-wrap"><div class="l-kick reveal">When two requests want the same room</div><h2 class="l-h reveal">The higher level wins, and every decision comes with a reason</h2><div class="pr-row">${prio}</div>
    <div class="l-stats reveal"><div><b data-count="189">0</b><span>classes a week</span></div><div><b data-count="27">0</b><span>rooms</span></div><div><b data-count="14">0</b><span>student groups</span></div><div><b data-count="41">0</b><span>midsem exams</span></div></div></div></section>
  <section class="l-end"><div class="l-wrap"><div class="l-cta reveal"><div><h2>Chilika Institute of Technology</h2><p>Sign in with your role to see your timetable, find a room or approve a change.</p></div><button class="btn lg" data-act="tologin">Sign in${ic("arrow", 18, 2.2)}</button></div></div></section></div>`;
  initLanding();
}
function initLanding() {
  const L = $("#land"); if (!L) return;
  requestAnimationFrame(() => requestAnimationFrame(() => L.classList.add("go")));
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const count = n => { const to = +n.dataset.count, t0 = performance.now(); const tick = t => { const k = Math.min(1, (t - t0) / 1300); n.textContent = Math.round(to * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(tick); }; if (still) n.textContent = to; else requestAnimationFrame(tick); };
  const hero = $("#hero");
  if (!still && hero) {
    hero.addEventListener("mousemove", e => { const r = hero.getBoundingClientRect(); hero.style.setProperty("--mx", ((e.clientX - r.left) / r.width - .5).toFixed(3)); hero.style.setProperty("--my", ((e.clientY - r.top) / r.height - .5).toFixed(3)); });
    hero.addEventListener("mouseleave", () => { hero.style.setProperty("--mx", 0); hero.style.setProperty("--my", 0); });
    const cp = $("#cp img"), onScroll = () => { if (!st.view || st.view !== "landing" || !cp) return; const r = cp.parentElement.getBoundingClientRect(), k = (r.top + r.height / 2 - innerHeight / 2) / innerHeight; cp.style.transform = `translateY(${(k * -40).toFixed(1)}px)`; };
    addEventListener("scroll", onScroll, { passive: true });
  }
  const mk = $("#mk"), art = L.querySelector(".h-art");
  if (!still && mk && art) { art.addEventListener("mousemove", e => { const r = art.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5; mk.style.setProperty("--rx", (-y * 5).toFixed(2) + "deg"); mk.style.setProperty("--ry", (x * 7).toFixed(2) + "deg"); });
    art.addEventListener("mouseleave", () => { mk.style.setProperty("--rx", "0deg"); mk.style.setProperty("--ry", "0deg"); }); }
  const io = new IntersectionObserver(es => es.forEach(en => {
    if (!en.isIntersecting) return; en.target.classList.add("in"); io.unobserve(en.target);
    en.target.querySelectorAll("[data-count]").forEach(count);
  }), { threshold: .25 });
  L.querySelectorAll(".reveal").forEach(n => io.observe(n));
}
async function showLogin() {
  st.accounts = st.accounts || await api("/api/demo-accounts");
  const cur = ROLES.find(r => r[0] === st.pickRole), list = st.accounts.accounts[st.pickRole];
  $("#app").innerHTML = `<div class="login"><section class="left">
    <div class="row" style="justify-content:space-between"><div class="brand"><div class="mark">${ic("calendar", 22)}</div><div><b>CIT Scheduler</b><small>Chilika Institute of Technology</small></div></div><button class="btn ghost sm" data-act="tolanding">Back to home</button></div>
    <div class="hero"><h1>Chilika Institute of Technology</h1>
      <p>Classes, rooms and events in one place. Sign in with your role: you only see what you need, and everyone can see why a request was approved or not.</p>
      <div class="rolepick">${ROLES.map(r => `<button type="button" class="rp ${st.pickRole === r[0] ? "on" : ""}" data-act="pickrole" data-v="${r[0]}"><span class="ic">${ic(r[1], 20)}</span><span><b>${r[2]}</b><small>${r[3]}</small></span></button>`).join("")}</div>
      <form id="loginform" class="stack-s">
        ${field("Account", `<select id="lg-email">${list.map(a => `<option value="${a.email}">${esc(a.name)}${a.department ? " · " + a.department : ""}</option>`).join("")}</select>`)}
        ${field("Email", `<input type="email" id="lg-email2" value="${esc(list[0].email)}" autocomplete="username">`)}
        ${field("Password", `<input type="password" id="lg-pass" value="demo" autocomplete="current-password">`)}
        <div class="row" style="margin-top:20px"><button class="btn lg" type="submit">Sign in as ${esc(cur[2])}</button><span class="muted small">Demo accounts use the password “demo”.</span></div>
      </form></div>
    <div class="muted xs">Nobody can approve their own request.</div></section>
    <section class="right"><h2>What each role sees</h2>${ROLES.map(r => `<div class="rc"><b>${r[2]}</b><p>${r[4]}</p><div class="tabs">${r[5].map(t => `<span>${t}</span>`).join("")}</div></div>`).join("")}${artSVG()}</section></div>`;
  $("#lg-email").onchange = e => $("#lg-email2").value = e.target.value;
  $("#loginform").onsubmit = e => { e.preventDefault(); act(async () => {
    const r = await api("/api/login", "POST", { email: $("#lg-email2").value, password: $("#lg-pass").value });
    st.token = r.token; sessionStorage.setItem("cit_token", r.token); await boot(); }); };
}
function signOut() { st.token = ""; sessionStorage.removeItem("cit_token"); st.me = null; st.ov = null; st.bf = null; st.ask = null; showLanding(); }

/* ---------- shell */
async function boot() {
  if (!st.token) return showLanding();
  try { st.me = await api("/api/me"); st.meta = await api("/api/meta"); } catch (e) { return showLanding(); }
  st.week = st.me.current_week; st.tt.week = st.tt.week || st.me.current_week; st.bk.week = st.bk.week || st.me.sem.fest_week;
  const u = st.me.user;
  if (u.role === "faculty") { st.tt.view = "faculty"; st.tt.id = u.faculty_id; }
  await go("overview");
}
async function go(tab) {
  st.tab = tab; st.notesOpen = false;
  try { st.me = await api("/api/me"); } catch (e) { }
  await render();
}
async function render() {
  const u = st.me.user, unread = st.me.unread, hasSearch = ["admin", "department_coordinator"].includes(u.role);
  $("#app").innerHTML = `<header class="top"><div class="brand"><div class="mark">${ic("calendar", 22)}</div><div><b>CIT Scheduler</b><small>Chilika Institute of Technology</small></div></div>
    ${hasSearch ? `<div class="search"><div class="box">${ic("search", 20)}<input id="gs" placeholder="Search rooms, faculty, classes" autocomplete="off"></div><div class="results hidden" id="gsr"></div></div>` : ""}
    <div class="row sp" style="gap:12px"><button class="btn ghost" data-act="askopen" aria-label="Ask">${ic("sparkle", 18)}<span class="ask-l">Ask</span></button>
      <button class="icon-btn" data-act="notes" aria-label="Notifications">${ic("bell", 20)}${unread ? `<span class="dot-badge">${unread}</span>` : ""}</button>
      <div class="me"><div class="avatar">${esc(initials(u.name))}</div><div><b>${esc(u.name)}</b><small>${esc(u.role_label)}${u.department ? " · " + u.department : ""}</small></div></div>
      <button class="icon-btn" data-act="signout" aria-label="Sign out" title="Sign out">${ic("logout", 20)}</button></div></header>
    <div class="shell"><nav class="side"><div class="label">Menu</div>${u.tabs.map(t => `<button class="${st.tab === t && !st.notesOpen ? "on" : ""}" data-act="tab" data-v="${t}">${ic(NAV[t][1], 20)}${role() === "faculty" && t === "timetable" ? "My timetable" : NAV[t][0]}</button>`).join("")}
      <div class="foot"><b style="font-size:12px">Priority</b><br>Exams, classes, institute events, guest lectures, department events, club events. The first one wins.</div></nav>
    <main id="main"></main></div><div id="modal"></div>`;
  if (hasSearch) bindSearch();
  renderModal();
  const m = $("#main");
  if (st.notesOpen) m.innerHTML = await notesView();
  else { m.innerHTML = '<div class="empty">Loading</div>'; await act(async () => { m.innerHTML = await VIEWS[st.tab](); if (AFTER[st.tab]) AFTER[st.tab](); window.scrollTo(0, 0); }); }
}
async function notesView() {
  const o = await api("/api/overview"); await api("/api/notifications/read", "POST"); st.me.unread = 0;
  return `${pageHead("Notifications", "Updates about your requests and timetable")}<div class="card flush">${o.notifications.length ? o.notifications.map(n => `<div class="item"><div class="body"><b>${esc(n.text)}</b><span>${esc(n.at.replace("T", " ").slice(0, 16))}</span></div></div>`).join("") : '<div class="empty">Nothing new.</div>'}</div>`;
}
function pageHead(title, sub, cta) { return `<div class="page-head"><div><h1>${title}</h1>${sub ? `<div class="sub">${sub}</div>` : ""}</div>${cta ? `<div class="sp">${cta}</div>` : ""}</div>`; }

/* search */
function bindSearch() {
  const inp = $("#gs"), box = $("#gsr");
  inp.oninput = () => {
    const q = inp.value.trim().toLowerCase(); if (q.length < 2) return box.classList.add("hidden");
    const m = st.meta, res = [];
    m.rooms.forEach(r => (r.id + " " + r.name).toLowerCase().includes(q) && res.push(["room", r.id, r.id, r.name + " · " + r.capacity + " seats"]));
    m.faculty.forEach(f => (f.name + " " + f.id).toLowerCase().includes(q) && res.push(["faculty", f.id, f.name, f.department + " · " + f.id]));
    m.groups.forEach(g => (g.id + " " + g.name).toLowerCase().includes(q) && res.push(["group", g.id, g.id, g.name]));
    box.innerHTML = res.slice(0, 7).map(r => `<button data-act="searchgo" data-v="${r[0]}|${esc(r[1])}"><span class="pill info">${r[0] === "group" ? "Class" : r[0] === "faculty" ? "Teacher" : "Room"}</span><span><b>${esc(r[2])}</b> <small>${esc(r[3])}</small></span></button>`).join("") || '<div class="empty small">No match</div>';
    box.classList.remove("hidden");
  };
  inp.onblur = () => setTimeout(() => box.classList.add("hidden"), 200);
}

/* ask modal: one box for a room request, a timetable request or a question */
const ASK_EX = { club: ["seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye", "Why was BR-14 decided that way?"],
  faculty: ["I am away on Thursday morning", "Move my Digital Logic Design lecture to Wednesday afternoon", "Why is my Data Structures class on that day?"],
  department_coordinator: ["Dr. Ananya Mishra is on leave Monday", "Why is CS101 where it is?", "Need a seminar hall for 80 people Wednesday 6 to 8 pm"],
  admin: ["LH-4 is closed on Wednesday for repairs", "Why is CS201 placed where it is?", "Why was BR-14 decided that way?"] };
function renderModal() {
  const m = $("#modal");
  if (st.cls) { m.innerHTML = clsModal(); return; }
  if (!st.ask) { m.innerHTML = ""; return; }
  const a = st.ask, ex = ASK_EX[role()] || [];
  m.innerHTML = `<div class="scrim" data-act="askclose"><div class="modal wide">
    <div class="row"><h2>Ask in plain words</h2><button class="icon-btn sp" data-act="askclose" aria-label="Close">${ic("x", 18)}</button></div>
    <p class="muted small" style="margin:8px 0 20px">English or Hinglish. Ask for a room, ask for a change to a class, or ask why something is where it is. Nothing changes until you send it and the Dean's office approves.</p>
    <textarea class="say" id="ask-text" placeholder="${esc(ex[0] || "")}">${esc(a.text || "")}</textarea>
    <div class="chips" style="margin-top:12px">${ex.map((t, i) => `<button class="chipbtn" data-act="askex" data-v="${i}">${esc(t)}</button>`).join("")}</div>
    <div class="row" style="margin-top:20px"><button class="btn" data-act="askgo" ${a.busy ? "disabled" : ""}>${a.busy ? "Working" : "Ask"}</button></div>
    <div id="askres">${askResult(a.res)}</div></div></div>`;
  setTimeout(() => { const t = $("#ask-text"); if (t && !a.res) t.focus(); }, 30);
}
const lines = ls => `<ul class="why-list">${ls.map(l => `<li>${esc(l)}</li>`).join("")}</ul>`;
function askResult(r) {
  if (!r) return "";
  if (r.intent === "explain") {
    if (r.ask) return `<div class="sess" style="margin-top:24px"><b>${esc(r.ask)}</b>${(r.choices || []).map(c => `<div style="margin-top:10px"><button class="btn ghost sm" data-act="askpick" data-v="${esc(c.id)}">${esc(c.label)}</button></div>`).join("")}</div>`;
    return r.answers.map(a => `<div class="sess" style="margin-top:24px"><b>${esc(a.title)}</b>${lines(a.lines)}${(a.alternatives || []).length ? `<div class="muted xs" style="margin-top:8px">Other open times: ${a.alternatives.map(x => esc(x.label)).join(" · ")}</div>` : ""}</div>`).join("");
  }
  if (r.intent === "change") {
    if (r.ask && !r.dis) return `<div class="sess" style="margin-top:24px"><b>${esc(r.ask)}</b>${(r.choices || []).map(c => `<div style="margin-top:10px"><button class="btn ghost sm" data-act="askpick" data-v="${esc(c.id)}">${esc(c.label)}</button></div>`).join("")}${(r.slots || []).length ? `<div class="muted xs" style="margin-top:12px">Free right now: ${r.slots.map(x => esc(x.label)).join(" · ")}</div>` : ""}</div>`;
    let h = `<div class="sess" style="margin-top:24px"><div class="muted xs" style="font-weight:700;letter-spacing:.06em">WHAT I UNDERSTOOD</div><b style="display:block;margin-top:6px;font-size:16px">${esc(r.summary)}</b>`;
    if (r.target) {
      const t = r.target, k = { free: ["ok", "Free right now"], if_others_move: ["warn", "Possible if another class moves"], ruled_out: ["bad", "Not allowed"] }[t.kind];
      h += `<div style="margin-top:10px">${pill(k[0], k[1])}</div>${t.reasons.length ? lines(t.reasons) : ""}`;
      if (t.kind === "ruled_out") h += `<div class="small" style="margin-top:6px;font-weight:600;color:var(--bad)">That time breaks a rule that cannot be moved around, so it cannot be done as asked.</div>`;
      if ((r.alternatives || []).length) h += `<div class="sect-label" style="margin-top:16px">Times that work without moving anyone else</div><div class="chips" style="margin-top:8px">${r.alternatives.map((x, i) => `<button class="chipbtn" data-act="askalt" data-v="${i}">${esc(x.label)}</button>`).join("")}</div>`;
    }
    h += `<div class="row" style="margin-top:20px;gap:10px;flex-wrap:wrap"><button class="btn" data-act="askpreview" ${r.busy ? "disabled" : ""}>${r.busy ? "Working" : "See what would change"}</button></div>`;
    if (r.preview) h += `<div style="margin-top:20px">${diffHTML(r.preview)}${r.preview.feasible ? `<div style="margin-top:16px"><button class="btn" data-act="asksend">Send to the Dean's office</button> <span class="muted xs">The checker has already confirmed this breaks no rule.</span></div>` : ""}</div>`;
    return h + "</div>";
  }
  return "";
}
async function askRun(sid) {
  const a = st.ask; a.busy = true; renderModal();
  try {
    const r = await api("/api/assistant", "POST", { text: a.text, session_id: sid || undefined });
    if (r.intent === "booking") {
      st.bf = newForm(); st.ask = null; await parseInto(a.text); st.bk.showForm = true; renderModal(); return go(roleHome());
    }
    a.res = r;
  } finally { a.busy = false; renderModal(); }
}
function dayStart(label) { return label; }

/* class panel: why it is here, and move it */
const canMove = c => { const u = st.me.user; return u.role === "admin" || (u.role === "faculty" && c.faculty_id === u.faculty_id) || (u.role === "department_coordinator" && (st.meta.courses[c.course_id] || {}).department === u.department); };
async function openClass(sid, cell) {
  st.cls = { id: sid, cell, why: null, slots: null, preview: null, dis: null, tab: "why" }; renderModal();
  try { st.cls.why = await api("/api/explain/session?id=" + encodeURIComponent(sid)); } catch (e) { st.cls.why = { title: "", lines: [e.message] }; }
  renderModal();
}
function clsModal() {
  const c = st.cls, x = c.cell, mv = canMove(x);
  const slotRow = r => `<div class="slot"><div><b>${esc(r.label)}</b><div class="muted xs">${r.kind === "free" ? "Free for the teacher, the class and a room" + (r.rooms.length ? ": " + r.rooms.slice(0, 3).join(", ") : "") : esc(r.reasons.join(". "))}</div></div>${r.kind !== "ruled_out" ? `<button class="btn ghost sm" data-act="clspick" data-v="${r.day}|${r.start}">Choose</button>` : ""}</div>`;
  let body = "";
  if (c.tab === "why") body = c.why ? `<p style="margin:0 0 4px;font-weight:600">${esc(c.why.title)}</p>${lines(c.why.lines)}` : '<div class="muted small">Working it out</div>';
  else if (!c.slots) body = '<div class="muted small">Looking at every time in the week</div>';
  else {
    const f = c.slots.slots.filter(r => r.kind === "free"), g = c.slots.slots.filter(r => r.kind === "if_others_move"), n = c.slots.slots.filter(r => r.kind === "ruled_out");
    body = `<div class="muted small" style="margin-bottom:12px">Now: ${DAYF[c.slots.now.day]} ${pStart(c.slots.now.start)} in ${esc(c.slots.now.room)}. Pick a new time. The app checks every rule and moves as few other classes as it can.</div>
      <div class="sect-label">Free without moving anyone</div>${f.length ? f.slice(0, 8).map(slotRow).join("") : '<div class="muted small" style="padding:8px 0">No time is free for this teacher, these classes and a room at once.</div>'}
      ${g.length ? `<div class="sect-label" style="margin-top:20px">Possible if another class moves</div>${g.slice(0, 6).map(slotRow).join("")}` : ""}
      <details style="margin-top:20px"><summary>Ruled out (${n.length}), and why</summary>${n.map(slotRow).join("")}</details>
      <div style="margin-top:20px"><button class="btn ghost sm" data-act="clsavoid">Just ask for a different time, any time is fine</button></div>`;
    if (c.preview) body += `<div class="sess" style="margin-top:20px"><b>${esc(c.pickLabel || "Your request")}</b><div style="margin-top:12px">${diffHTML(c.preview)}</div>${c.preview.feasible ? `<div style="margin-top:16px"><button class="btn" data-act="clssend">Send to the Dean's office</button></div>` : ""}</div>`;
  }
  return `<div class="scrim" data-act="clsclose"><div class="modal wide"><div class="row"><div><h2>${esc(x.title)}</h2><div class="muted small" style="margin-top:4px">${esc(x.course_id)} · ${esc(x.kind)} · ${DAYF[x.day]} ${pStart(x.start)} · ${esc(x.room)} · ${esc(x.faculty)}</div></div><button class="icon-btn sp" data-act="clsclose" aria-label="Close">${ic("x", 18)}</button></div>
    <div class="seg" style="margin:20px 0">${[["why", "Why it is here"], ...(mv ? [["move", "Move it"]] : [])].map(([k, n]) => `<button class="${c.tab === k ? "on" : ""}" data-act="clstab" data-v="${k}">${n}</button>`).join("")}</div>${body}</div></div>`;
}

/* ---------- shared pieces */
function prioCard(o) {
  const cap = o.your_cap, mine = o.priority.find(p => p.id === cap);
  const notes = { club: "A club can ask for club level only, even if the request says “guest lecture” or “institute event”.", faculty: "A faculty member can ask up to guest lecture level.",
    department_coordinator: "A department can ask up to department event level.", admin: "The Dean's office can ask up to institute event level." };
  return `<section class="card"><div class="card-head"><h2>Priority order</h2><span class="sub">If two things want the same room at the same time, the one on the left gets it.</span></div>
    <div class="prio">${o.priority.map((p, i) => `<div class="step ${p.id === cap ? "you" : ""}"><span class="num" style="background:${SHADE[i][0]};color:${SHADE[i][1]}">${i + 1}</span>${esc(p.label)}${p.id === cap ? '<span class="you-tag">Your highest</span>' : ""}</div>`).join("")}</div>
    <div class="prio-note">${notes[o.role] || ""} Between two requests at the same level, the earlier one wins.${o.week === o.exam_week ? " This week is exam week, so no events can be booked." : ""}</div></section>`;
}
function classTable(rows, empty) {
  if (!rows.length) return `<div class="empty">${empty || "No classes."}</div>`;
  return `<div class="tablewrap"><table class="t"><tr><th>Period</th><th>Class</th><th>Group</th><th>Room</th><th>Status</th></tr>${rows.map(c => `<tr>
    <td><b>${c.dur > 1 ? `P${c.start} to P${c.start + c.dur - 1}` : "P" + c.start}</b><small>${pStart(c.start)} to ${pEnd(c.start + c.dur - 1)}</small></td>
    <td><b>${esc(c.title)}</b><small>${esc(c.course_id)} · ${esc(c.faculty)}</small></td><td>${esc(c.groups.join(", "))}</td><td>${esc(c.room)}</td><td>${classStatus(c.status)}</td></tr>`).join("")}</table></div>`;
}
const TONE = { bad: "bad", warn: "warn", info: "info", ok: "ok", gray: "gray" };
function attentionList(items, head, sub) {
  return `<div class="list-head"><h2>${head}</h2><div class="muted small" style="margin-top:4px;font-weight:500">${sub}</div></div>` +
    (items.length ? items.map(a => `<div class="item"><span class="tag">${pill(TONE[a.tone] || "gray", a.type)}</span><div class="body"><b>${esc(a.title)}</b><span>${esc(a.text)}</span></div>${a.tab ? `<button class="go" data-act="tab" data-v="${a.tab}">${esc(a.action || "Open")}${ic("arrow", 16)}</button>` : ""}</div>`).join("") : '<div class="empty">Nothing needs attention.</div>');
}
function tilesCard(list, head) {
  return `<section class="card"><h2>${head || "Waiting for you"}</h2>${list.map(t => `<button class="tile" data-act="tab" data-v="${t.tab}"><span class="n">${t.n}</span><span class="t">${esc(t.text)}</span><span class="arr">${ic("arrow", 16)}</span></button>`).join("")}</section>`;
}
function bkRow(r) {
  const win = r.windows.map(w => `${DAYN[w.day]} ${span(w.from_period, w.to_period)}`).join("  or  ");
  const bar = r.status === "rejected" ? "var(--bad)" : r.state === "published" ? "var(--ok)" : "#D9A24A";
  const who = r.own ? "Another person must approve your request." : r.lab_departments.length ? `Waits for the ${r.lab_departments.join(" or ")} coordinator or the Dean's office.` : "Waits for the Dean's office.";
  return `<div class="bk"><div class="bar" style="background:${bar}"></div><div class="main">
    <div class="title"><b>${esc(r.id)} · ${esc(r.title)}</b>${pill("gray", CATS[r.category] || r.category)}${statusPills(r)}${r.series_id ? pill("info", `Repeats weekly · ${r.series_pos} of ${r.series_total}`) : ""}<span class="sp muted small">Week ${r.week} · ${esc(r.by)}</span></div>
    <div class="when">${r.status === "rejected" ? '<span class="muted">No room was given</span>' : `${DAYF[r.day]}, ${span(r.start, r.end)} · ${rmx(r.room)}`}</div>
    <div class="why">${esc(r.reason || "")}</div><div class="why">Asked for ${esc(win)} · ${r.attendance} people${r.requested_room ? " · wanted " + rmx(r.requested_room) : ""}</div>
    ${(r.overrides || []).map(o => `<div class="moves">Class ${esc(o.session_id)} moves to ${DAYF[o.day]} ${pStart(o.start_period)} in ${rmx(o.room_id)} to make room.</div>`).join("")}
    <div class="acts">${r.can_decide ? `<button class="btn sm" data-act="approve" data-v="${r.id}">${r.series_id ? "Approve this week" : "Approve"}</button>` : ""}
    ${r.series_waiting > 1 ? `<button class="btn sm dark" data-act="approveseries" data-v="${esc(r.series_id)}">Approve all ${r.series_waiting} weeks</button>` : ""}
    ${(r.own || r.can_decide || role() === "admin") && !r.cancelled ? `<button class="btn sm danger" data-act="cancelbk" data-v="${r.id}">${r.series_id ? "Cancel this week" : r.can_decide ? "Cancel" : "Cancel request"}</button>` : ""}
    ${r.series_live > 1 && (r.own || r.can_decide || role() === "admin") && !r.cancelled ? `<button class="btn sm danger" data-act="cancelseries" data-v="${esc(r.series_id)}" data-w="${r.week}">Cancel this and later weeks</button>` : ""}
    ${!r.can_decide && r.state !== "published" && r.status !== "rejected" ? `<span class="muted xs">${who}</span>` : ""}</div></div></div>`;
}

/* ---------- room photos on hover */
const rmx = id => id ? `<span class="rm" data-room="${esc(id)}">${esc(id)}</span>` : "";
function roomPhoto(r) {
  const t = r.type, id = r.id;
  if (t === "auditorium") return "auditorium";
  if (t === "outdoor") return "campus";
  if (t === "lab_cs") return "lab-computer";
  if (t === "lab_elec" || t === "workshop") return "lab-instruments";
  if (t.startsWith("lab")) return "lab-science";
  if (t === "lecture_hall") return ["LH-1", "LH-2", "LH-3"].includes(id) ? "hall-white" : "hall-wood";
  if (t === "seminar_hall") return "hall-wood";
  return /^CR-1/.test(id) ? "hall-white" : "hall-wood";
}
const roomPhotoUrl = r => { const k = roomPhoto(r); return k === "campus" ? "/static/campus.jpg" : `/static/rooms/${k}.jpg`; };
function venuesCard() {
  const rooms = (st.meta && st.meta.rooms) || [];
  const grp = [["Halls", r => ["auditorium", "lecture_hall", "seminar_hall", "outdoor"].includes(r.type)], ["Classrooms", r => r.type === "classroom"], ["Labs and workshops", r => r.type.startsWith("lab") || r.type === "workshop"]];
  return `<section class="card venues"><div class="v-head"><h2>Venues</h2><span class="muted small">Hover to see a room. Click to ask for it.</span></div>${grp.map(([n, f]) => {
    const l = rooms.filter(f); return l.length ? `<div class="v-row"><span class="v-lab">${n}</span><div class="v-chips">${l.map(r => `<button type="button" class="vn ${st.bf && st.bf.form && st.bf.form.requested_room === r.id && st.bk.showForm ? "on" : ""}" data-act="venuepick" data-v="${esc(r.id)}" data-room="${esc(r.id)}"><b>${esc(r.id)}</b><span>${r.capacity}</span></button>`).join("")}</div></div>` : "";
  }).join("")}</section>`;
}
function initRoomPreview() {
  if (document.getElementById("rv") || matchMedia("(hover: none)").matches) return;
  const el = document.createElement("aside"); el.id = "rv"; el.className = "rv"; el.setAttribute("aria-hidden", "true");
  el.innerHTML = `<div class="rv-in"><div class="rv-img"><img alt=""><img alt=""></div><div class="rv-body"><div class="rv-kick"></div><h3></h3><p></p><div class="rv-tags"></div></div></div>`;
  document.body.appendChild(el);
  const imgs = el.querySelectorAll(".rv-img img"), body = el.querySelector(".rv-body"); let cur = -1, hideT = 0, shown = "";
  const show = id => {
    const r = ((st.meta && st.meta.rooms) || []).find(x => x.id === id); if (!r) return;
    clearTimeout(hideT);
    if (shown !== id) {
      shown = id; const nxt = (cur + 1) % 2, im = imgs[nxt], url = roomPhotoUrl(r);
      im.onload = () => { imgs.forEach((x, i) => x.classList.toggle("on", i === nxt)); cur = nxt; };
      im.src = url; if (im.complete && im.naturalWidth) im.onload();
      body.classList.remove("in"); void body.offsetWidth;
      el.querySelector(".rv-kick").textContent = (TYPES[r.type] || r.type) + " · " + r.building;
      el.querySelector("h3").textContent = r.name + " (" + r.id + ")";
      el.querySelector("p").textContent = r.capacity + " seats" + (r.accessible ? ", step-free access" : "");
      el.querySelector(".rv-tags").innerHTML = r.features.map(f => `<span>${esc(NEEDS[f] || f)}</span>`).join("");
      body.classList.add("in");
    }
    el.classList.add("on");
  };
  const hide = () => { clearTimeout(hideT); hideT = setTimeout(() => { el.classList.remove("on"); shown = ""; }, 140); };
  document.addEventListener("mouseover", e => { const t = e.target.closest && e.target.closest("[data-room]"); if (t) show(t.dataset.room); else hide(); });
  document.addEventListener("focusin", e => { const t = e.target.closest && e.target.closest("[data-room]"); if (t) show(t.dataset.room); });
  document.addEventListener("focusout", hide);
  document.addEventListener("scroll", hide, { passive: true, capture: true });
}
const weekField = (id, val) => field("Week", `<input type="number" min="1" max="${st.me.sem.weeks}" id="${id}" value="${val}">`);

/* ---------- VIEWS */
const VIEWS = {}, AFTER = {};

VIEWS.overview = async () => {
  const o = st.ov = await api("/api/overview" + (st.ovDay ? "?day=" + st.ovDay : "")), r = role(), u = st.me.user;
  const real = new Date().toLocaleDateString("en-GB", { weekday: "long" }), day = DAYF[o.today], sub = `${o.today_is_weekend ? real + " · showing " + day + "'s classes, the next teaching day" : day} · Week ${o.week}${o.week === o.fest_week ? " · Spectra week" : ""} · ${{ admin: "Dean's office", department_coordinator: o.department + " department", faculty: u.name, club: u.name }[r]}`;
  let h = "";
  const dayBar = r === "club" ? "" : `<div class="seg" style="margin:-8px 0 24px;max-width:100%;overflow-x:auto" aria-label="Day shown">${DAYS.map(x => `<button class="${o.today === x ? "on" : ""}" data-act="ovday" data-v="${x}">${DAYF[x]}</button>`).join("")}</div>`;
  if (r === "admin") h += pageHead("Overview", sub);
  else if (r === "club") h += pageHead("Overview", sub, `<button class="btn lg" data-act="tab" data-v="newrequest">${ic("plus", 18)}New request</button>`);
  else if (r === "faculty") h += pageHead("Overview", sub, `<button class="btn lg" data-act="tab" data-v="requests">${ic("plus", 18)}I will be away</button>`);
  else h += pageHead("Overview", sub, `<button class="btn lg" data-act="tab" data-v="bookings">${ic("plus", 18)}New request</button>`);
  if (o.generated) h += dayBar;
  h += `<div class="stack">${prioCard(o)}`;
  if (r === "admin") {
    const running = st.me.job && st.me.job.state === "running";
    if (!o.generated || running) {
      h += `<section class="card dark" style="padding:40px"><h2 style="font-size:24px">Set up the semester</h2><p style="margin:12px 0 24px;max-width:560px;line-height:1.65">Build the weekly timetable, the midsem exam schedule and the Spectra week booking decisions in one go. Every rule is checked as it goes.</p>
      ${running ? `<div class="progress"><i></i></div><p id="jobmsg" style="margin-top:16px;font-size:13px">${esc(st.me.job.message)}</p>` : `<div class="row" style="gap:12px;flex-wrap:wrap"><button class="btn lg" style="background:#fff;color:var(--navy)" data-act="useseed">Use the ready-made timetable</button><button class="btn lg" style="background:transparent;color:#fff;box-shadow:inset 0 0 0 1px rgba(255,255,255,.55)" data-act="generate">Generate a new one</button></div><p class="small" style="margin-top:14px;opacity:.8">The ready-made one loads at once. A new one takes about a minute.</p>`}</section>`;
      if (running) setTimeout(pollJob, 1500);
    } else {
      const hh = o.health, ok = hh && hh.hard === 0;
      h += `<div class="cols"><div class="stack"><section class="card flush">${attentionList(o.attention, "Needs attention", "Changes, closures and events that touch classes")}
        <div class="band"><h2 style="font-size:16px">Classes on ${DAYF[o.today]}</h2><span class="muted small">${DAYF[o.today]} · ${o.classes_today_total} sessions, those with a change first</span><button class="link sp" data-act="tab" data-v="timetable">Open timetable</button></div>
        ${classTable(o.classes_today)}</section></div>
      <aside>${tilesCard(o.waiting_tiles)}
        <section class="card"><h2>Semester setup</h2><p class="muted small" style="margin:8px 0 16px;line-height:1.6;font-weight:500">${o.sessions} sessions · ${o.rooms} rooms · ${o.faculty} faculty · ${o.groups} groups · ${o.exams} exams</p>
          <div class="stack-s"><button class="btn" style="width:100%" data-act="generate">Generate all</button>
          <div class="row" style="gap:8px"><button class="btn ghost sm" style="flex:1" data-act="download" data-v="schedule.json">schedule.json</button><button class="btn ghost sm" style="flex:1" data-act="download" data-v="schedule_after.json">schedule_after.json</button></div>
          <button class="btn ghost sm" style="width:100%" data-act="loadds">Load a dataset file</button><input type="file" id="ds-file" accept=".json" hidden>
          <button class="btn danger sm" style="width:100%" data-act="reset">Reset demo</button></div>
          <div style="border-top:1px solid var(--line-soft);margin-top:20px;padding-top:16px" class="small">Hard rules broken: <b style="color:${ok ? "var(--ok)" : "var(--bad)"}">${hh ? hh.hard : "–"}</b> of 14 checks<br><span class="muted">Soft penalty: ${hh ? hh.soft : "–"} · booking score ${hh && hh.booking ? hh.booking.booking_score : "–"}</span>
          <div style="margin-top:12px"><button class="link" data-act="check">Run official check</button></div><div id="checkout" class="stack-s" style="margin-top:12px"></div></div></section>
        <section class="card"><h2>Recent activity</h2><div class="stack-s" style="margin-top:12px">${o.audit.map(a => `<div class="small"><span class="faint">${esc(a.at.replace("T", " ").slice(5, 16))}</span> <b style="font-weight:600">${esc(a.by.split("@")[0])}</b> ${esc(a.what)}</div>`).join("") || '<div class="muted small">Nothing yet.</div>'}</div></section></aside></div>`;
    }
  } else if (r === "department_coordinator") {
    h += `<div class="cols"><div class="stack">
      ${o.labs_waiting.length ? `<section class="card flush"><div class="list-head"><h2>Lab bookings for you to approve</h2><div class="muted small" style="margin-top:4px;font-weight:500">Requests for ${o.department} labs. Anything that moves a class goes to the Dean's office.</div></div>${o.labs_waiting.map(bkRow).join("")}</section>` : ""}
      <section class="card flush">${attentionList(o.attention, "Needs attention", "Changes and closures that touch your department")}
        <div class="band"><h2 style="font-size:16px">${o.department} classes on ${DAYF[o.today]}</h2><span class="muted small">${DAYF[o.today]} · ${o.classes_week} classes a week · ${o.faculty_count} faculty</span><button class="link sp" data-act="tab" data-v="timetable">Open timetable</button></div>${classTable(o.classes_today, "No classes on this day.")}</section></div>
      <aside>${tilesCard(o.waiting_tiles)}${myRequestsCard(o)}</aside></div>`;
  } else if (r === "faculty") {
    h += `<div class="cols"><div class="stack">
      <section class="card flush"><div class="list-head"><h2>Your classes on ${DAYF[o.today]}</h2><div class="muted small" style="margin-top:4px;font-weight:500">${DAYF[o.today]} · ${o.classes_week} sessions and ${o.hours_week} teaching hours a week</div></div>${classTable(o.classes_today, "No classes on this day.")}
        <div class="band"><span class="small muted">Away or need a room?</span><button class="link sp" data-act="tab" data-v="requests">Away and requests</button></div></section>
      ${o.away.length ? `<section class="card flush"><div class="list-head"><h2>When you are away</h2><div class="muted small" style="margin-top:4px;font-weight:500">No classes are placed in these times</div></div>${o.away.map(a => `<div class="item"><span class="tag">${pill("warn", DAYN[a.day])}</span><div class="body"><b>${span(Math.min(...a.periods), Math.max(...a.periods))}</b><span>${esc(a.reason || "")}</span></div></div>`).join("")}</section>` : ""}
      </div><aside>${tilesCard(o.waiting_tiles)}${o.my_changes.length ? `<section class="card"><h2>Your away requests</h2><div class="stack-s" style="margin-top:12px">${o.my_changes.map(c => `<div class="sess"><div class="row"><b>${esc(c.id)}</b>${chPill(c)}</div><div class="reason">${esc(describeDis(c.dis))}</div></div>`).join("")}</div></section>` : ""}${myRequestsCard(o)}</aside></div>`;
  } else {
    h += `<div class="cols"><section class="card flush"><div class="list-head"><h2>Where classes are, and where they are not</h2><div class="muted small" style="margin-top:4px;font-weight:500">Check this before you ask for a room</div></div>
      ${o.rules.map(x => `<div class="item"><span class="tag">${pill(TONE[x.tone], x.type)}</span><div class="body"><b>${esc(x.title)}</b><span>${esc(x.text)}</span></div></div>`).join("")}
      <div class="band"><span class="small muted">Not sure which room is free?</span><button class="link sp" data-act="tab" data-v="rooms">Find a room</button></div></section>
      <aside>${myRequestsCard(o)}</aside></div>`;
  }
  return h + "</div>" + extraOverview(o);
};
function myRequestsCard(o) {
  const b = (o.my_bookings || []).filter(Boolean);
  return `<section class="card"><h2>My requests</h2>${b.length ? b.slice(0, 4).map(r => `<div class="sess" style="margin-top:12px"><div class="row" style="gap:8px"><b style="flex:1;font-size:14px">${esc(r.id)} · ${esc(r.title)}</b></div>
    <div class="row" style="margin:8px 0">${statusPills(r)}</div>
    <div class="small">${r.status === "rejected" ? "No room was given" : `${DAYN[r.day]} ${span(r.start, r.end)} · ${esc(r.room)}`}</div><div class="reason"><b style="font-weight:700;color:var(--text)">Why:</b> ${esc(r.reason || "")}</div>
    ${(r.own && !r.cancelled) ? `<button class="link" style="color:var(--bad);margin-top:8px" data-act="cancelbk" data-v="${r.id}">Cancel request</button>` : ""}</div>`).join("") : '<div class="empty small">You have not asked for a room yet.</div>'}
    <div style="margin-top:16px"><button class="link" data-act="${role() === "club" || role() === "faculty" ? "tab" : "mybookings"}" data-v="${role() === "club" ? "myrequests" : role() === "faculty" ? "requests" : "mine"}">All my requests</button></div></section>`;
}
async function pollJob() {
  if (st.tab !== "overview") return;
  const j = await api("/api/job").catch(() => null); if (!j) return;
  if (j.state === "running") { const m = $("#jobmsg"); if (m) m.textContent = j.message; setTimeout(pollJob, 2000); }
  else { st.me.job = j; if (j.state === "error") toast(j.message, true); else toast("Everything is ready"); await go("overview"); }
}

/* --- timetable */
const KIND_C = { lecture: ["Lecture", "#6F859B"], tutorial: ["Tutorial", "#7C9A5B"], lab: ["Lab", "#D9A24A"], event: ["Event", "#B46A72"] };
VIEWS.timetable = async () => {
  const t = st.tt, u = st.me.user;
  const ch = t.ch = await api("/api/timetable/choices");
  const okId = { group: ch.groups, faculty: ch.faculty, room: ch.rooms, course: ch.courses };
  if (!t.id || !(okId[t.view] || []).some(x => x.id === t.id)) {
    if (t.view === "course") t.id = ch.courses[0].id;
    else if (t.view === "faculty") { const f = ch.faculty.find(f => f.id === u.faculty_id) || (u.role === "department_coordinator" && ch.faculty.find(f => f.department === u.department)) || ch.faculty[0]; t.id = f.id; }
    else if (t.view === "room") t.id = ch.rooms[0].id;
    else if (u.role === "department_coordinator") { const g = ch.groups.find(g => g.department === u.department) || ch.groups[0]; t.id = g.id; }
    else t.id = ch.groups[0].id;
  }
  t.data = await api(`/api/timetable?view=${t.view}&id=${encodeURIComponent(t.id)}&week=${t.week}`);
  setSubjects(t.data.cells.map(c => c.course_id));
  if (t.course && !t.data.cells.some(c => c.course_id === t.course)) t.course = "";
  return `${pageHead(u.role === "faculty" ? "My timetable" : "Timetable", `Week ${t.week}${t.data.fest_week ? " · Spectra week, events in purple" : ""}${t.data.exam_week ? " · Exam week, classes do not run" : ""}`)}
  <div class="tt-layout"><aside class="card tt-side" id="tt-side">${ttSide()}</aside><div id="tt-main">${ttMain()}</div></div>`;
};
function ttSide() {
  const t = st.tt, u = st.me.user, ch = t.ch, d = t.data, subj = {};
  d.cells.forEach(c => { const s = subj[c.course_id] ||= { id: c.course_id, title: c.title, n: 0, h: 0 }; s.n++; s.h += c.dur; });
  const list = Object.values(subj).sort((a, b) => a.title.localeCompare(b.title));
  const opts = t.view === "group" ? ch.groups.map(g => [g.id, g.id + " · " + g.name]) : t.view === "faculty" ? [...ch.faculty].sort((a, b) => a.name.localeCompare(b.name)).map(f => [f.id, f.name + " · " + f.department]) : t.view === "course" ? ch.courses.map(c => [c.id, c.id + " · " + c.title]) : ch.rooms.map(r => [r.id, `${r.id} · ${r.name} (${r.capacity})`]);
  const kinds = {}; d.cells.forEach(c => kinds[c.kind] = (kinds[c.kind] || 0) + 1); if (d.events.length) kinds.event = d.events.length;
  return `<details class="tt-fold" ${st.tt.foldOpen === false ? "" : "open"}><summary>Filters${t.course ? " · 1 subject" : ""}</summary>${u.role !== "faculty" ? `<div class="sect-label">Show</div><div class="seg wrap">${[["group", "Class"], ["faculty", "Teacher"], ["room", "Room"], ["course", "Subject"]].map(([k, n]) => `<button class="${t.view === k ? "on" : ""}" data-act="ttview" data-v="${k}">${n}</button>`).join("")}</div>
    <div style="margin-top:14px">${field({ group: "Class", faculty: "Teacher", room: "Room", course: "Subject" }[t.view], `<select id="tt-id">${opts.map(([v, n]) => `<option value="${esc(v)}" ${v === t.id ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>`)}</div>` : ""}
    <div style="margin-top:14px">${field("Week", `<input type="number" id="tt-week" min="1" max="${st.me.sem.weeks}" value="${t.week}">`)}</div>
    ${t.view !== "course" ? `<div class="sect-label" style="margin-top:24px">Subject</div>
      <div class="tt-search">${ic("search", 16)}<input id="tt-q" placeholder="Find a subject" autocomplete="off"></div>
      <div class="sj-list" id="sj-list"><button class="sj ${t.course ? "" : "on"}" data-act="ttsubj" data-v=""><span class="rd"></span><span><b>All subjects</b><small>${d.cells.length} sessions</small></span></button>
      ${list.map(s => `<button class="sj ${t.course === s.id ? "on" : ""}" data-act="ttsubj" data-v="${esc(s.id)}" data-name="${esc((s.title + " " + s.id).toLowerCase())}"><span class="rd" style="--sw:${subjCol(s.id).bar}"></span><span><b>${esc(s.title)}</b><small>${esc(s.id)} · ${s.n} session${s.n > 1 ? "s" : ""} · ${s.h} h</small></span></button>`).join("") || '<div class="muted small" style="padding:8px 0">No classes here.</div>'}</div>` : ""}
    <div class="sect-label" style="margin-top:24px">Type</div>
    ${Object.entries(KIND_C).map(([k, [n, c]]) => `<label class="ck ${kinds[k] ? "" : "dim"}"><input type="checkbox" data-ttkind="${k}" ${t.kinds[k] ? "checked" : ""}><u style="--c:${c}"></u>${n}<em>${kinds[k] || 0}</em></label>`).join("")}
    <button class="link" style="margin-top:20px" data-act="ttclear">Clear filters</button></details>`;
}
function ttFiltered() {
  const t = st.tt, d = t.data;
  const cells = d.cells.filter(c => t.kinds[c.kind] && (!t.course || c.course_id === t.course));
  return { ...d, cells, events: t.course || !t.kinds.event ? [] : d.events };
}
function ttMain() {
  const t = st.tt, u = st.me.user, d = ttFiltered(), all = t.data;
  const hrs = d.cells.reduce((a, c) => a + c.dur, 0), subj = t.course && all.cells.find(c => c.course_id === t.course);
  const bar = `<div class="tt-bar"><div><b>${t.view === "course" ? esc((all.cells[0] || {}).title || "Subject") : subj ? esc(subj.title) : "All subjects"}</b><span class="muted small"> · ${d.cells.length} session${d.cells.length === 1 ? "" : "s"}, ${hrs} hour${hrs === 1 ? "" : "s"} a week${d.events.length ? " · " + d.events.length + " event" + (d.events.length > 1 ? "s" : "") : ""}</span></div>
    <div class="legend">${[...new Map(d.cells.map(c => [c.course_id, c])).values()].slice(0, 24).map(c => { const k = subjCol(c.course_id); return `<span><i style="background:${k.bg};box-shadow:inset 3px 0 0 ${k.bar}"></i>${esc(c.course_id)}</span>`; }).join("")}${d.events.length ? `<span><i style="background:var(--event)"></i>Event</span>` : ""}<span><i style="box-shadow:inset 0 0 0 2px #D9A24A;background:#fff"></i>Moved</span>${d.cells.some(c => c.swapped_from) ? `<span><i style="border:2px dashed #2D3A47;background:#fff"></i>Teacher swapped</span>` : ""}${t.view !== "group" && t.view !== "course" ? `<span><i style="background:#F9DDE0"></i>${t.view === "faculty" ? "Away" : "Closed"}</span>` : ""}</div></div>`;
  if (all.exam_week) return `<div class="card empty">Week ${t.week} is exam week, so there are no regular classes. See the Exams tab.</div>${xcTimetable(all.extras || [])}`;
  return `${bar}<div class="card flush">${d.cells.length || d.events.length || (!t.course && (all.away || []).length) ? `<div class="tablewrap">${grid(d)}</div>` : `<div class="empty">Nothing matches these filters. <button class="link" data-act="ttclear">Clear filters</button></div>`}</div>`;
}
function ttPaint() { const m = $("#tt-main"), s = $("#tt-side"); if (m) m.innerHTML = ttMain(); if (s) { const fd = s.querySelector("details"); if (fd) st.tt.foldOpen = fd.open; const q = ($("#tt-q") || {}).value || ""; s.innerHTML = ttSide(); bindTT(); if (q) { $("#tt-q").value = q; ttSearch(q); } } }
function ttSearch(q) { q = q.trim().toLowerCase(); document.querySelectorAll("#sj-list .sj[data-name]").forEach(b => b.classList.toggle("hidden", !!q && !b.dataset.name.includes(q))); }
function bindTT() {
  const sel = $("#tt-id"); if (sel) sel.onchange = e => { st.tt.id = e.target.value; st.tt.course = ""; render(); };
  const wk = $("#tt-week"); if (wk) wk.onchange = e => { st.tt.week = +e.target.value || 1; render(); };
  const q = $("#tt-q"); if (q) q.oninput = e => ttSearch(e.target.value);
  document.querySelectorAll("[data-ttkind]").forEach(x => x.onchange = e => { st.tt.kinds[e.target.dataset.ttkind] = e.target.checked; ttPaint(); });
}
AFTER.timetable = () => { if (st.tt.foldOpen === undefined && matchMedia("(max-width:1000px)").matches) { const d = document.querySelector(".tt-fold"); if (d) { d.open = false; st.tt.foldOpen = false; } } bindTT(); };
const ROWH = 50, LUNCH = 24;
const yOf = p => p <= 5 ? (p - 1) * ROWH : 5 * ROWH + LUNCH + (p - 6) * ROWH;
function grid(d) {
  const view = d.view, items = [];
  d.cells.forEach(c => items.push({ sid: c.id, cell: { id: c.id, title: c.title, course_id: c.course_id, kind: c.kind, day: c.day, start: c.start, room: c.room, faculty: c.faculty, faculty_id: c.faculty_id }, day: c.day, a: c.start, b: c.start + c.dur - 1, col: subjCol(c.course_id), cls: c.kind + (c.moved_this_week || c.changed ? " moved" : "") + (c.swapped_from ? " swapped" : ""),
    t: c.course_id + (c.kind !== "lecture" ? " · " + c.kind : ""), l: view === "group" ? `${c.room} · ${c.faculty}` : view === "faculty" ? `${c.room} · ${c.groups.join(", ")}` : view === "course" ? `${c.groups.join(", ")} · ${c.room}` : `${c.groups.join(", ")} · ${c.faculty}`,
    tip: `${c.title}\n${c.kind}, ${c.room}\n${c.faculty}\n${c.groups.join(", ")}${c.moved_this_week ? "\nMoved this week for an event" : ""}${c.changed ? "\nChanged from the original timetable" : ""}${c.swapped_from ? "\nTeacher swapped, was " + c.swapped_from : ""}` }));
  d.events.forEach(e => items.push({ day: e.day, a: e.start, b: e.end, cls: "event", t: e.title, l: e.room + " · " + e.by, tip: `${e.title}\n${e.room}\n${e.by}\n${e.reason || ""}` }));
  const blocked = (list, label) => list.forEach(u => { const ps = [...u.periods].sort((x, y) => x - y); let s = ps[0], prev = s; for (let i = 1; i <= ps.length; i++) { if (ps[i] !== prev + 1) { items.push({ day: u.day, a: s, b: prev, cls: "away", t: label, l: u.reason || "", tip: u.reason || label }); s = ps[i]; } prev = ps[i]; } });
  if (view === "faculty") blocked(d.away, "Away"); if (view === "room") blocked(d.closed, "Closed");
  const total = 13 * ROWH + LUNCH; let cols = "";
  DAYS.forEach(day => {
    const list = items.filter(i => i.day === day).sort((x, y) => x.a - y.a || y.b - x.b), lanes = [];
    list.forEach(it => { let l = lanes.findIndex(e => e < it.a); if (l < 0) { l = lanes.length; lanes.push(0); } lanes[l] = it.b; it.lane = l; });
    list.forEach(it => { it.n = Math.max(...list.filter(o => o.a <= it.b && o.b >= it.a).map(o => o.lane)) + 1; });
    cols += `<div class="col" style="height:${total}px">${bgRows()}${list.map(it => `<div class="blk ${it.cls}" ${it.sid ? `role="button" tabindex="0" data-act="clsopen" data-v="${esc(it.sid)}" data-cell='${esc(JSON.stringify(it.cell))}'` : ""} title="${esc(it.tip)}" style="${it.col ? `background:${it.col.bg};color:${it.col.ink};--bc:${it.col.bar};` : ""}top:${yOf(it.a) + 3}px;height:${yOf(it.b) + ROWH - yOf(it.a) - 6}px;left:calc(${it.lane} * 100% / ${it.n} + 4px);width:calc(100% / ${it.n} - 8px)"><b>${esc(it.t)}</b><span>${esc(it.l)}</span></div>`).join("")}</div>`;
  });
  const tm = st.meta.periods.map(p => (p.id === 6 ? `<div style="height:${LUNCH}px;font-size:10px;color:var(--faint);padding:4px 20px;font-weight:700;letter-spacing:.06em">LUNCH</div>` : "") + `<div class="tm"><b>P${p.id}</b>${p.start}</div>`).join("");
  return `<div class="tt"><div class="hd"></div>${DAYS.map(x => `<div class="hd">${DAYF[x]}</div>`).join("")}<div>${tm}</div>${cols}</div>`;
}
function bgRows() { let s = ""; for (let p = 1; p <= 13; p++) s += (p === 6 ? '<div class="bg lunch"></div>' : "") + `<div class="bg ${p > 9 ? "night" : ""}"></div>`; return s; }

/* --- rooms */
VIEWS.rooms = async () => {
  const q = st.rooms, types = [...new Set(st.meta.rooms.filter(r => r.allowed_uses.includes("event")).map(r => r.type))];
  return `${pageHead(role() === "club" ? "Find a room" : "Rooms", "See what is free before you ask. Rooms that fit come first.")}<div class="stack"><section class="card stack-s">
    <div class="fields">${weekField("rm-week", st.week)}${field("Day", `<select id="rm-day">${dayOpt(q.day)}</select>`)}${field("From", `<select id="rm-from">${pOpt(q.frm)}</select>`)}${field("Until", `<select id="rm-to">${pOpt(q.to, true)}</select>`)}
    ${field("Seats at least", `<input type="number" id="rm-cap" min="0" value="${q.min_cap || ""}" placeholder="Any">`)}${field("Type", `<select id="rm-type"><option value="">Any</option>${types.map(t => `<option value="${t}" ${q.rtype === t ? "selected" : ""}>${TYPES[t] || t}</option>`).join("")}</select>`)}</div>
    <div class="chips" style="margin-top:16px">${Object.entries(NEEDS).map(([k, n]) => tg("data-need", k, q.need.includes(k), n)).join("")}</div>
    <div style="margin-top:20px"><button class="btn" data-act="findrooms">Show rooms</button></div></section><div id="roomres">${st.roomRes ? roomTable(st.roomRes) : ""}</div></div>`;
};
function roomTable(res) {
  const q = st.rooms, can = ["admin", "department_coordinator", "club"].includes(role());
  return `<section class="card flush"><div class="list-head"><h2>${DAYF[q.day]}, ${span(q.frm, q.to)}</h2><div class="muted small" style="margin-top:4px;font-weight:500">Week ${res.week}. ${res.rooms.filter(r => r.status === "free" && r.fits).length} rooms are free and fit.</div></div><div class="tablewrap"><table class="t"><tr><th>Room</th><th>Type</th><th>Seats</th><th>Features</th><th>That time</th><th></th></tr>
  ${res.rooms.map(r => `<tr data-room="${esc(r.id)}" class="${r.status !== "free" ? "rm-busy" : r.fits ? "rm-free" : "rm-nofit"}"><td><b>${esc(r.id)}</b><small>${esc(r.name)} · ${esc(r.building)}</small></td><td>${TYPES[r.type] || r.type}</td><td>${r.capacity}</td>
  <td class="small" style="max-width:260px">${r.features.map(f => NEEDS[f] || f).join(", ")}${r.accessible ? ", step-free" : ""}</td>
  <td>${r.status === "free" ? (r.fits ? '<span class="pill free">Free</span>' : `${pill("gray", "Free")}<small>Does not match your filters</small>`) : r.status === "closed" ? pill("bad", "Closed") : `${pill("warn", r.status === "class" ? "Class" : "Event")}<small>${esc(r.what)}</small>`}</td>
  <td style="text-align:right">${can && r.status === "free" && r.fits ? `<button class="btn sm" data-act="reqroom" data-v="${esc(r.id)}">Ask for this</button>` : ""}</td></tr>`).join("")}</table></div></section>`;
}

/* --- booking form (assistant, editable form, live check) */
function newForm(pre = {}) {
  return { text: pre.text || "", form: { title: "", requested_category: pre.cat || defaultCat(), week: st.me.sem.fest_week, attendance: "", duration_periods: pre.dur || "", room_types: [], needs: [], requested_room: pre.room || null, mandatory_for_groups: [], series: false, repeat_until: "",
    windows: [pre.day ? { day: pre.day, from_period: pre.frm, to_period: pre.to } : { day: "MON", from_period: 6, to_period: 8 }] }, assumptions: [], follow_up: null, source: "", check: null, result: null, filled: [] };
}
function allowedCats() { const order = st.meta.priority.map(p => p.id), cap = st.meta.role_cap[role()] || "club_event"; return order.slice(order.indexOf(cap)); }
function defaultCat() { const a = allowedCats(); return a[a.length - 1]; }
const EXAMPLES = ["Open mic Wednesday 7 to 9 pm, 90 people, mic needed", "AUD Friday 11 am to 1 pm, stage and PA", "Computer lab Thu or Fri, 6 straight hours after 2 pm, 70 people"];
function formHTML() {
  const b = st.bf, f = b.form, fl = k => b.filled.includes(k), types = [...new Set(st.meta.rooms.filter(r => r.allowed_uses.includes("event")).map(r => r.type))], cats = allowedCats();
  const T = k => fl(k) ? "from your message" : "";
  return `<div class="stack">
  <section class="card"><h2>1 · Describe what you need</h2><div class="muted small" style="margin:6px 0 16px;font-weight:500">Type it the way you would say it. Check the form. Submit.</div>
    <textarea class="say" id="bf-text" placeholder="e.g. seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye">${esc(b.text)}</textarea>
    <div class="row" style="margin-top:16px"><button class="btn" data-act="parse">Fill the form</button><span class="muted xs">Try:</span>${EXAMPLES.map((e, i) => `<button class="try" data-act="try" data-v="${i}">${esc(e)}</button>`).join("")}</div>
    ${b.source ? `<div class="muted xs" style="margin-top:12px">${b.source === "claude" ? "Read by the AI assistant." : "Read by the built-in reader."} You can change every field below.</div>` : ""}
    ${b.follow_up ? `<div class="assumed" style="margin-top:16px"><b>${esc(b.follow_up)}</b></div>` : ""}</section>
  <div class="cols"><section class="card stack-s"><h2>2 · Check and edit</h2>
    <div class="fields" style="margin-top:12px">
      ${field("Title", `<input type="text" data-bf="title" value="${esc(f.title)}" placeholder="What is it?">`, { cls: "wide", hint: !f.title, tag: !f.title ? "add a title" : "" })}
      ${field("Kind of event", `<select data-bf="requested_category">${cats.map(c => `<option value="${c}" ${f.requested_category === c ? "selected" : ""}>${CATS[c]}</option>`).join("")}</select>`)}
      ${field("Week", `<input type="number" min="1" max="${st.me.sem.weeks}" data-bf="week" value="${f.week}">`)}
      ${field("People", `<input type="number" min="1" data-bf="attendance" value="${esc(f.attendance)}" placeholder="How many">`, { hint: fl("attendance") || !f.attendance, tag: T("attendance") || (!f.attendance ? "add" : "") })}
      ${field("Hours", `<input type="number" min="1" max="13" data-bf="duration_periods" value="${esc(f.duration_periods)}" placeholder="How long">`, { hint: fl("duration_periods") || !f.duration_periods, tag: T("duration_periods") || (!f.duration_periods ? "add" : "") })}
      ${field("Specific room", `<select data-bf="requested_room"><option value="">No preference</option>${st.meta.rooms.filter(r => r.allowed_uses.includes("event")).map(r => `<option value="${r.id}" ${f.requested_room === r.id ? "selected" : ""}>${r.id} · ${r.name} (${r.capacity})</option>`).join("")}</select>`, { hint: fl("requested_room") })}
    </div>
    <div style="margin-top:20px"><div class="sect-label">When can it happen?</div>${f.windows.map((w, i) => `<div class="winrow">
      ${field("Day", `<select data-bfwin="${i}" data-k="day">${dayOpt(w.day)}</select>`, { hint: fl("windows") })}${field("Earliest start", `<select data-bfwin="${i}" data-k="from_period">${pOpt(w.from_period)}</select>`, { hint: fl("windows") })}${field("Must end by", `<select data-bfwin="${i}" data-k="to_period">${pOpt(w.to_period, true)}</select>`, { hint: fl("windows") })}
      ${f.windows.length > 1 ? `<button class="icon-btn" data-act="delwin" data-v="${i}" aria-label="Remove">${ic("x", 16)}</button>` : "<span></span>"}</div>`).join("")}
      <div class="row" style="margin-top:12px"><button class="link" data-act="addwin">+ Another day or time</button>
      ${f.windows.length > 1 ? `<label class="small" style="font-weight:600"><input type="checkbox" data-bf="series" ${f.series ? "checked" : ""}> I need <b>every</b> one of these days, not just one</label>` : ""}</div></div>
    <div style="margin-top:20px"><div class="sect-label">Does it repeat? <span style="text-transform:none;letter-spacing:0;font-weight:500">(for example a weekly rehearsal. One approval covers every week)</span></div>
      <div class="fields">${field("Repeat every week until week", `<input type="number" min="${f.week}" max="${st.me.sem.weeks}" data-bf="repeat_until" value="${esc(f.repeat_until)}" placeholder="Does not repeat">`)}</div>
      <div id="bf-repeat" class="small" style="margin-top:10px">${repeatNote(f)}</div></div>
    <div style="margin-top:20px"><div class="sect-label">Kind of room <span style="text-transform:none;letter-spacing:0;font-weight:500">(leave empty for any hall or classroom)</span></div><div class="chips">${types.map(t => tg("data-bftype", t, f.room_types.includes(t), TYPES[t] || t)).join("")}</div></div>
    <div style="margin-top:20px"><div class="sect-label">It needs</div><div class="chips">${Object.entries(NEEDS).map(([k, n]) => tg("data-bfneed", k, f.needs.includes(k), n)).join("")}</div></div>
    <details style="margin-top:20px"><summary>Compulsory for a class? Pick the groups</summary><div class="chips" style="margin-top:12px">${st.meta.groups.map(g => tg("data-bfgrp", g.id, f.mandatory_for_groups.includes(g.id), g.id)).join("")}</div></details>
    ${b.assumptions.length ? `<div class="assumed" style="margin-top:20px"><b>Assumed, please confirm</b>${b.assumptions.map(a => `<div>· ${esc(a)}</div>`).join("")}</div>` : ""}
  </section>
  <aside><section class="card"><h2>Live check</h2><div style="margin-top:16px" id="bf-check">${checkHTML()}</div></section></aside></div>
  <section class="card submit-bar"><p class="small" style="line-height:1.6;font-weight:500">${st.bf.check && st.bf.check.effective_category ? `Your request ranks as <b>${esc(CAT1[st.bf.check.effective_category])}</b>. ` : ""}The rules decide it at once, with the reason, and then a person who did not ask for it approves it.</p>
    <button class="btn lg" data-act="sendbk">Submit request</button></section>
  ${b.result ? `<section class="card"><h2>Answer</h2><div style="margin-top:12px">${b.result.map(r => `<div class="sess"><div class="row"><b>${esc(r.id)}</b>${r.week && b.result.length > 1 ? `<span class="muted small">Week ${r.week}</span>` : ""}${r.status === "approved" ? pill("ok", "Room found") : r.status === "alternative_offered" ? pill("warn", "Alternative offered") : pill("bad", "Not possible")}</div><div style="margin-top:6px">${esc(r.reason)}</div><div class="reason">It now waits for approval. Track it under ${role() === "club" ? "My requests" : role() === "faculty" ? "Away and requests" : "Bookings"}.</div></div>`).join("")}</div></section>` : ""}</div>`;
}
function checkHTML() {
  const c = st.bf.check; if (!c) return '<span class="muted small">The app checks rooms here as you fill in the form.</span>';
  if (!c.ok) return c.problems.map(p => `<div class="chk"><span class="m w">${ic("alert", 13, 2.4)}</span><span>${esc(p)}</span></div>`).join("");
  return c.checks.map(x => `<div class="chk"><span class="m ${x.ok ? "" : "w"}">${ic(x.ok ? "check" : "alert", 13, 2.6)}</span><span>${esc(x.text)}</span></div>`).join("") +
    (c.options.length ? `<div style="margin-top:16px">${c.options.slice(0, 6).map(o => `<span class="opt-chip">${esc(o.room)} · ${DAYN[o.day]} ${pStart(o.start)}</span>`).join("")}</div>` : "");
}
let checkTimer;
function recheck() { clearTimeout(checkTimer); checkTimer = setTimeout(() => act(async () => { st.bf.check = await api("/api/bookings/check", "POST", cleanForm()); const el = $("#bf-check"); if (el) el.innerHTML = checkHTML(); }), 350); }
function repeatWeeks(f) {
  const sem = st.me.sem, cur = st.me.current_week || 3, from = +f.week, to = +f.repeat_until || 0;
  if (!to || to <= from) return null;
  const weeks = [from], skipped = [];
  for (let w = from + 1; w <= Math.min(to, sem.weeks); w++) (w === sem.exam_week || w < cur ? skipped : weeks).push(w);
  return { weeks, skipped, n: weeks.length * (f.series ? f.windows.length : 1) };
}
function repeatNote(f) {
  if (+f.repeat_until && +f.repeat_until < +f.week) return '<span style="color:var(--bad)">The last week cannot come before week ' + f.week + '.</span>';
  const r = repeatWeeks(f); if (!r) return '<span class="muted">Leave empty for a single booking.</span>';
  const ex = r.skipped.map(w => w === st.me.sem.exam_week ? `Week ${w} is exam week, so it is skipped.` : `Week ${w} has already passed, so it is skipped.`).join(" ");
  return `<b>${r.n} booking${r.n > 1 ? "s" : ""}</b> in weeks ${r.weeks.join(", ")}. ${ex} Each week is checked for a room on its own, the Dean's office approves them all in one go.` + (r.n > 26 ? ' <span style="color:var(--bad)">That is more than 26. Shorten it.</span>' : "");
}
function cleanForm() { const f = { ...st.bf.form }; f.repeat_until = +f.repeat_until > +f.week ? +f.repeat_until : null; f.attendance = +f.attendance || 0; f.duration_periods = +f.duration_periods || 0; f.requested_room = f.requested_room || null; f.raw_text = st.bf.text; return f; }
const toggle = (arr, v, on) => { const i = arr.indexOf(v); if (on && i < 0) arr.push(v); if (!on && i >= 0) arr.splice(i, 1); };
function bindForm() {
  const root = $("#main");
  root.oninput = root.onchange = e => {
    const t = e.target, f = st.bf && st.bf.form; if (!f) return;
    if (t.id === "bf-text") { st.bf.text = t.value; return; }
    if (t.dataset.bf) { const k = t.dataset.bf; f[k] = t.type === "checkbox" ? t.checked : (k === "week" ? +t.value : t.value); }
    else if (t.dataset.bftype) toggle(f.room_types, t.dataset.bftype, t.checked);
    else if (t.dataset.bfneed) toggle(f.needs, t.dataset.bfneed, t.checked);
    else if (t.dataset.bfgrp) toggle(f.mandatory_for_groups, t.dataset.bfgrp, t.checked);
    else if (t.dataset.bfwin !== undefined) { const w = f.windows[+t.dataset.bfwin]; w[t.dataset.k] = t.dataset.k === "day" ? t.value : +t.value; }
    else return;
    if (t.dataset.bf === "week" || t.dataset.bf === "repeat_until" || t.dataset.bf === "series") { const el = $("#bf-repeat"); if (el) el.innerHTML = repeatNote(f); }
    recheck();
  };
}
function bookingFormView(pre) { if (!st.bf || pre) st.bf = newForm(pre || {}); return formHTML(); }
async function parseInto(text) {
  if (!text.trim()) throw new Error("Write a few words about what you need");
  if (!st.bf) st.bf = newForm();
  st.bf.text = text;
  const r = await api("/api/bookings/parse", "POST", { text, week: st.bf.form.week });
  const f = st.bf.form, filled = [];
  if (r.week) f.week = r.week;
  const set = (k, v, has) => { f[k] = v; if (has) filled.push(k); };
  set("title", /^(need|want|require|book|please|we |i |can |hum|chahiye|looking)/i.test(r.title || "") ? "" : (r.title || ""), false);
  f.requested_category = allowedCats().includes(r.requested_category) ? r.requested_category : defaultCat();
  set("attendance", r.attendance || "", !!r.attendance); set("duration_periods", r.duration_periods || "", !!r.duration_periods);
  set("room_types", r.room_types || [], (r.room_types || []).length > 0); set("needs", r.needs || [], (r.needs || []).length > 0);
  set("requested_room", r.requested_room || null, !!r.requested_room); f.mandatory_for_groups = r.mandatory_for_groups || []; f.series = !!r.series; f.repeat_until = r.repeat_until || "";
  const th = r.time_hint || { from_period: 6, to_period: 8 };
  set("windows", r.windows.length ? r.windows : [{ day: "MON", from_period: th.from_period, to_period: th.to_period }], r.windows.length > 0);
  Object.assign(st.bf, { assumptions: r.assumptions || [], follow_up: r.follow_up, source: r.source || "rules", result: null, filled });
}
const roleHome = () => ({ club: "newrequest", faculty: "requests" }[role()] || "bookings");

VIEWS.newrequest = async () => `${pageHead("New request", "Say what you need, check the form, and send it.")}${bookingFormView(st._pre)}`;
AFTER.newrequest = () => { st._pre = null; bindForm(); recheck(); };

/* --- bookings */
async function loadBookings(mine) { return api(`/api/bookings?week=${st.bk.week}${mine ? "&mine=1" : ""}`); }
VIEWS.bookings = async () => {
  if (st.bk.sub === "online") return bookingsOnline();
  if (st.bk.sub === "mine") return bookingsMine();
  const d = await loadBookings(false), f = st.bk.filter;
  const rows = d.rows.filter(r => f === "all" || (f === "wait" && r.state !== "published" && r.status !== "rejected") || (f === "ok" && r.state === "published" && r.status !== "rejected") || (f === "no" && r.status === "rejected"));
  const canAll = d.rows.filter(r => r.can_decide).length;
  return `${pageHead("Bookings", `Week ${st.bk.week}${st.bk.week === st.me.sem.fest_week ? " · Spectra week" : ""} · highest priority first. Nobody approves their own request.`, `<button class="btn lg" data-act="toggleform">${st.bk.showForm ? ic("x", 18) + "Close form" : ic("plus", 18) + "New request"}</button>`)}
    ${bkTabs()}<div class="stack">${st.bk.showForm ? bookingFormView() : ""}${venuesCard()}
    <section class="card flush"><div class="list-head"><div class="toolbar"><div style="width:120px">${weekField("bk-week", st.bk.week)}</div>
      <div class="seg">${[["all", "All"], ["wait", "Waiting"], ["ok", "Approved"], ["no", "Not possible"]].map(([k, n]) => `<button class="${f === k ? "on" : ""}" data-act="bkfilter" data-v="${k}">${n}</button>`).join("")}</div>
      ${canAll ? `<button class="btn sp" data-act="approveall">Approve all I can (${canAll})</button>` : ""}</div>
      ${d.exam_week ? '<p class="muted small" style="margin-top:12px">This is exam week. Exams come first, so events cannot be booked.</p>' : ""}</div>
      ${rows.length ? rows.map(bkRow).join("") : '<div class="empty">No bookings here.</div>'}</section></div>`;
};
AFTER.bookings = () => { if (st.bk.sub === "online" || st.bk.sub === "mine") return; $("#bk-week") && ($("#bk-week").onchange = e => { st.bk.week = +e.target.value || 1; render(); }); if (st.bk.showForm) { bindForm(); recheck(); } };
VIEWS.myrequests = async () => {
  const d = await api("/api/bookings?mine=1&all=1"), wk = [...new Set(d.rows.map(r => r.week))].sort((x, y) => x - y);
  return `${pageHead("My requests", "Every request, its answer and the reason. Events that have already happened are removed automatically.", `<button class="btn lg" data-act="tab" data-v="newrequest">${ic("plus", 18)}New request</button>`)}
  <section class="card flush"><div class="list-head"><h2>All my requests</h2><div class="muted small" style="margin-top:4px;font-weight:500">${d.rows.length ? d.rows.length + " in week" + (wk.length > 1 ? "s " : " ") + wk.join(", ") : "Nothing yet"}</div></div>${d.rows.length ? d.rows.map(bkRow).join("") : '<div class="empty">You have no requests yet. Use New request to ask for a room.</div>'}</section>`;
};
AFTER.myrequests = () => { };

/* --- changes */
function describeDis(dis) {
  return dis.changes.map(c => {
    if (c.type === "faculty_unavailable") return `${facName(c.faculty_id)} away ${c.days.map(d => DAYN[d]).join(", ")} ${span(Math.min(...c.periods), Math.max(...c.periods))}${c.reason ? " (" + c.reason + ")" : ""}`;
    if (c.type === "room_unavailable") return `${c.room_id} closed ${c.days.map(d => DAYN[d]).join(", ")} ${span(Math.min(...c.periods), Math.max(...c.periods))}${c.reason ? " (" + c.reason + ")" : ""}`;
    if (c.type === "add_session") return `Add ${c.session.id} (${courseTitle(c.session.course_id)})`;
    if (c.type === "remove_session") return `Remove ${c.session_id}`;
    if (c.type === "move_session") return c.to ? `Move ${c.session_id} to ${DAYF[c.to.day]} ${pStart(c.to.start_period)}` : `Find a new time for ${c.session_id}`;
    if (c.type === "add_faculty") return `Add teacher ${c.faculty.name}`;
    return c.type;
  }).join("; ");
}
const chPill = c => c.status === "pending" ? pill("warn", "Waiting for approval") : c.status === "approved" ? pill("ok", "Approved") : c.status === "undone" ? pill("gray", "Undone") : pill("bad", "Rejected");
/* Undo: two steps, so a stray click cannot roll the timetable back */
function undoBox(kind, x, noun) {
  if (x.status === "undone" && x.undone) {
    const u = x.undone, c = u.check || {};
    return `<div class="why undo-note">Undone by ${esc(u.by_name)} on ${esc(u.at.replace("T", " ").slice(0, 16))}. ${c.hard === null || c.hard === undefined ? "Only one week was affected, so the weekly timetable was never changed." : `The official checker was run again: ${c.hard} rule problems.`}${u.reason ? ` Reason: ${esc(u.reason)}` : ""}</div>`;
  }
  if (x.can_undo) {
    return st.undoAsk === x.id
      ? `<div class="undo-ask"><div class="small"><b>Roll the timetable back to how it was before ${esc(x.id)}?</b> The official checker runs again straight after, and if it finds a clash nothing is changed.</div>
          <div class="acts"><div style="flex:1;min-width:200px"><label class="field"><span class="l">Reason (optional)</span><input type="text" id="undo-${esc(x.id)}" maxlength="200"></label></div>
          <button class="btn danger" data-act="undo${kind}" data-v="${esc(x.id)}">Yes, undo it</button><button class="btn ghost" data-act="undoask" data-v="">Keep it</button></div></div>`
      : `<div class="acts"><button class="btn sm ghost" data-act="undoask" data-v="${esc(x.id)}">Undo this ${noun}</button></div>`;
  }
  if (x.undo_blocked) return `<div class="why muted">Only the most recent change can be undone, because later ones build on it.</div>`;
  return "";
}
function diffHTML(c) {
  if (!c.feasible) return `<div class="sess" style="background:var(--bad-bg)"><b style="color:var(--bad)">This cannot be done as asked.</b>${(c.why_not || []).map(w => `<div class="small" style="margin-top:4px">${esc(w)}</div>`).join("")}</div>`;
  if (!c.diff.length) return '<div class="muted small">Nothing needs to move.</div>';
  const nm = id => { const s = st.meta.sessions.find(x => x.id === id); return s ? `${courseTitle(s.course_id)} (${id})` : id; };
  const w = a => a ? `${DAYN[a[0]]} ${pStart(a[1])} · ${a[2]}` : "none";
  return `<div class="small muted" style="margin-bottom:8px;font-weight:500">${c.moved} change time · ${c.room_only} change room only · ${c.added} added · ${c.removed} removed. Everyone else stays put.</div>
  <div class="tablewrap"><table class="t diff"><tr><th>Session</th><th>Before</th><th>After</th><th>Why</th></tr>${c.diff.map(d => `<tr><td>${esc(nm(d.session_id))}</td><td>${w(d.before)}</td><td><b>${w(d.after)}</b></td><td class="small">${esc(d.why)}</td></tr>`).join("")}</table></div>`;
}
VIEWS.changes = async () => {
  const d = await api("/api/changes"), u = st.me.user, ch = st.ch;
  const types = [["faculty", "Teacher away"], ...(u.role === "admin" ? [["room", "Room closed"]] : []), ["add", "Add a class"], ["remove", "Remove a class"]];
  if (!types.some(t => t[0] === ch.type)) ch.type = "faculty";
  const pending = d.rows.filter(r => r.status === "pending"), done = d.rows.filter(r => r.status !== "pending");
  const xd = await api("/api/extras"); st.xc.rows = xd.rows; st.xc.week = xd.week;
  return `${pageHead("Changes", "The app moves as few classes as it can, shows exactly what moves, and waits for another admin to approve.")}<div class="stack">${xcHeadCard()}
  <section class="card"><h2>Ask for a change</h2><div class="seg" style="margin:16px 0 20px;max-width:100%;overflow-x:auto">${types.map(([k, n]) => `<button class="${ch.type === k ? "on" : ""}" data-act="chtype" data-v="${k}">${n}</button>`).join("")}</div>${changeForm(ch.type)}
    <div id="chout">${ch.out ? `<div class="sess" style="margin-top:24px;background:var(--field)"><div class="row"><h3>${esc(ch.out.id)}</h3>${chPill(ch.out)}</div><div style="margin-top:12px">${diffHTML(ch.out)}</div></div>` : ""}</div></section>
  <section class="card flush"><div class="list-head"><h2>Waiting for approval</h2></div>${pending.length ? pending.map(changeCard).join("") : '<div class="empty">Nothing waiting.</div>'}</section>
  <section class="card flush"><div class="list-head"><h2>Earlier</h2></div>${done.length ? done.map(changeCard).join("") : '<div class="empty">No earlier changes.</div>'}</section></div>`;
};
function changeCard(c) {
  return `<div class="bk"><div class="bar" style="background:${c.status === "approved" ? "var(--ok)" : c.status === "rejected" ? "var(--bad)" : "#D9A24A"}"></div><div class="main">
  <div class="title"><b>${esc(c.id)}</b>${chPill(c)}<span class="sp muted small">${esc(c.by_name)} · ${esc(c.at.replace("T", " ").slice(0, 16))}</span></div>
  <div class="when">${esc(describeDis(c.dis))}</div>${c.note ? `<div class="why">${esc(c.note)}</div>` : ""}
  <details style="margin-top:12px" ${c.status === "pending" ? "open" : ""}><summary>${c.feasible ? "What moves" : "Why it cannot be done"}</summary><div style="margin-top:12px">${diffHTML(c)}</div></details>
  ${c.can_decide ? `<div class="acts"><div style="flex:1;min-width:200px"><label class="field"><span class="l">Reason (optional)</span><input type="text" id="note-${c.id}"></label></div><button class="btn" ${c.feasible ? "" : "disabled"} data-act="chapprove" data-v="${c.id}">Approve</button><button class="btn danger" data-act="chreject" data-v="${c.id}">Reject</button></div>` :
    c.status === "pending" && c.own ? '<div class="why">Another admin must approve your request.</div>' : ""}
  ${c.after_check ? `<div class="why">After approval: ${c.after_check.hard} rule problems.</div>` : ""}${undoBox("change", c, "change")}${c.status === "rejected" && c.reason ? `<div class="why">Reason: ${esc(c.reason)}</div>` : ""}</div></div>`;
}
function facOptions() { const u = st.me.user; return st.meta.faculty.filter(f => f.department !== "ADMIN" && (u.role !== "department_coordinator" || f.department === u.department)).map(f => `<option value="${f.id}">${esc(f.name)} · ${f.department}</option>`).join(""); }
function changeForm(t) {
  const days = `<div class="chips">${DAYS.map(d => tg("data-chday", d, false, DAYN[d])).join("")}</div>`;
  const per2 = `${field("From", `<select id="ch-from">${pOpt(1)}</select>`)}${field("Until", `<select id="ch-to">${pOpt(9, true)}</select>`)}`;
  const go = k => `<div style="margin-top:20px"><button class="btn" data-act="chsend" data-v="${k}">Check and send</button></div>`;
  if (t === "faculty") return `<div class="fields">${field("Teacher", `<select id="ch-fac">${facOptions()}</select>`)}${per2}${field("Reason", `<input type="text" id="ch-reason" placeholder="e.g. Conference">`)}</div><div style="margin-top:16px"><div class="sect-label">Which days</div>${days}</div>${go("faculty")}`;
  if (t === "room") return `<div class="fields">${field("Room", `<select id="ch-room">${st.meta.rooms.map(r => `<option value="${r.id}">${r.id} · ${r.name}</option>`).join("")}</select>`)}${per2}${field("Reason", `<input type="text" id="ch-reason" placeholder="e.g. Ceiling repair">`)}</div><div style="margin-top:16px"><div class="sect-label">Which days</div>${days}</div>${go("room")}`;
  if (t === "remove") { const u = st.me.user, list = st.meta.sessions.filter(s => u.role !== "department_coordinator" || (st.meta.courses[s.course_id] || {}).department === u.department);
    return `<div class="fields">${field("Class to remove", `<select id="ch-sess">${list.map(s => `<option value="${s.id}">${esc(courseTitle(s.course_id))} · ${s.id} · ${esc(facName(s.faculty_id))}</option>`).join("")}</select>`, { cls: "wide" })}</div>${go("remove")}`; }
  if (t === "add") { const u = st.me.user, cs = Object.entries(st.meta.courses).filter(([id, c]) => u.role !== "department_coordinator" || c.department === u.department);
    return `<div class="fields">${field("Course", `<select id="ch-course">${cs.map(([id, c]) => `<option value="${id}">${esc(c.title)} · ${id}</option>`).join("")}</select>`)}${field("Kind", `<select id="ch-kind"><option>lecture</option><option>tutorial</option><option>lab</option></select>`)}${field("Teacher", `<select id="ch-fac">${facOptions()}</select>`)}${field("Hours", `<input type="number" id="ch-dur" min="1" max="4" value="1">`)}</div>
    <div style="margin-top:16px"><div class="sect-label">For which classes</div><div class="chips">${st.meta.groups.map(g => tg("data-chgrp", g.id, false, g.id)).join("")}</div></div>${go("add")}`; }
  return `<div class="stack-s"><div class="muted small" style="font-weight:500">Paste the change file exactly as the Dean's office gives it, or choose the JSON file.</div><input type="file" id="ch-file" accept=".json"><textarea class="say" style="border-color:var(--line)" id="ch-json" rows="6" placeholder='{"changes":[{"type":"faculty_unavailable", ...}]}'></textarea></div>${go("file")}`;
}
AFTER.changes = () => { const f = $("#ch-file"); if (f) f.onchange = async e => { $("#ch-json").value = await e.target.files[0].text(); }; };
function buildDis(kind) {
  const val = id => $(id) && $(id).value, days = [...document.querySelectorAll("[data-chday]:checked")].map(x => x.dataset.chday);
  const periods = []; if ($("#ch-from")) for (let p = +val("#ch-from"); p <= +val("#ch-to"); p++) periods.push(p);
  if (kind === "faculty") { if (!days.length) throw new Error("Choose at least one day"); return { changes: [{ type: "faculty_unavailable", faculty_id: val("#ch-fac"), days, periods, reason: val("#ch-reason") }] }; }
  if (kind === "room") { if (!days.length) throw new Error("Choose at least one day"); return { changes: [{ type: "room_unavailable", room_id: val("#ch-room"), days, periods, reason: val("#ch-reason") }] }; }
  if (kind === "remove") return { changes: [{ type: "remove_session", session_id: val("#ch-sess") }] };
  if (kind === "add") {
    const groups = [...document.querySelectorAll("[data-chgrp]:checked")].map(x => x.dataset.chgrp); if (!groups.length) throw new Error("Choose at least one class");
    const kindv = val("#ch-kind"), size = groups.reduce((a, g) => a + st.meta.groups.find(x => x.id === g).size, 0);
    const lab = st.meta.sessions.find(s => s.kind === "lab" && s.course_id === val("#ch-course")), n = st.meta.sessions.filter(s => s.course_id === val("#ch-course")).length + 1;
    return { changes: [{ type: "add_session", session: { id: `${val("#ch-course")}-X${n}`, course_id: val("#ch-course"), kind: kindv, groups, faculty_id: val("#ch-fac"), size, duration: +val("#ch-dur") || 1,
      room_types: kindv === "lab" ? (lab ? lab.room_types : ["lab_cs"]) : ["classroom", "lecture_hall", "auditorium"], needs_accessible: groups.some(g => st.meta.groups.find(x => x.id === g).needs_accessible), basket_slot: null, fixed_slot: null } }] };
  }
  const t = val("#ch-json"); if (!t.trim()) throw new Error("Paste or choose the change file"); return JSON.parse(t);
}

/* --- faculty requests */
VIEWS.requests = async () => {
  const d = await api("/api/changes"), u = st.me.user, mine = await loadBookings(true), xd = await api("/api/extras"); st.xc.rows = xd.rows; st.xc.week = xd.week; if (!st.xc.form) st.xc.form = xcBlank();
  return `${pageHead("Away and requests", "Tell the Dean's office when you are away, or ask for a room for a talk.")}<div class="stack">${xcFormCard()}
  <section class="card"><h2>I will be away</h2><div class="muted small" style="margin:6px 0 20px;font-weight:500">Your classes in that time are moved to other slots. The Dean's office approves it.</div>
    <div class="fields">${field("From", `<select id="ch-from">${pOpt(1)}</select>`)}${field("Until", `<select id="ch-to">${pOpt(9, true)}</select>`)}${field("Reason", `<input type="text" id="ch-reason" placeholder="e.g. Conference">`)}</div>
    <div style="margin-top:16px"><div class="sect-label">Which days</div><div class="chips">${DAYS.map(x => tg("data-chday", x, false, DAYN[x])).join("")}</div></div>
    <input type="hidden" id="ch-fac" value="${u.faculty_id}"><div style="margin-top:20px"><button class="btn" data-act="chsend" data-v="faculty">Check and send</button></div>
    <div id="chout">${st.ch.out ? `<div class="sess" style="margin-top:24px"><div class="row"><h3>${esc(st.ch.out.id)}</h3>${chPill(st.ch.out)}</div><div style="margin-top:12px">${diffHTML(st.ch.out)}</div></div>` : ""}</div></section>
  <section class="card flush"><div class="list-head"><h2>Your away requests</h2></div>${d.rows.length ? d.rows.map(c => `<div class="item"><span class="tag">${chPill(c)}</span><div class="body"><b>${esc(c.id)} · ${esc(describeDis(c.dis))}</b>${c.reason ? `<span>${esc(c.reason)}</span>` : ""}</div></div>`).join("") : '<div class="empty">None yet.</div>'}</section>
  <section class="card flush"><div class="list-head row"><div><h2>Room for a guest lecture or talk</h2><div class="muted small" style="margin-top:4px;font-weight:500">Faculty requests rank as guest lectures at most.</div></div><button class="btn sp" data-act="toggleform">${st.bk.showForm ? "Close form" : "New request"}</button></div>
  ${st.bk.showForm ? `<div style="padding:0 28px 28px">${bookingFormView()}</div>` : ""}${mine.rows.map(bkRow).join("")}</section></div>`;
};
AFTER.requests = () => { if (st.bk.showForm) { bindForm(); recheck(); } xcLive(true); };

/* --- exams */
VIEWS.exams = async () => {
  const d = await api("/api/exams"), ex = d.rows, sessions = d.sessions, by = {};
  ex.forEach(e => (by[e.day] ||= {})[e.session] = (by[e.day][e.session] || []).concat(e));
  return `${pageHead("Exams", `Midsem · week ${d.week} · each room seats half its capacity`, role() === "admin" ? '<button class="btn ghost" data-act="rexam">Plan again</button>' : "")}
  <div class="grid g2">${d.days.map(day => `<section class="card"><h2>${DAYF[day]}</h2>${sessions.map(s => `<div class="sect-label" style="margin-top:20px">${s.id} · ${s.start} to ${s.end}</div>${(by[day] && by[day][s.id] || []).map(e => `<div class="sess"><b>${e.courses.map(c => esc(courseTitle(c))).join(" + ")}</b> <span class="faint xs">${e.exam_id}</span><div class="small muted" style="font-weight:500;margin-top:2px">${e.size} students · ${e.groups.join(", ")}</div><div class="small" style="margin-top:6px">${e.rooms.map(r => pill("info", r)).join(" ")}</div></div>`).join("") || '<div class="muted small">No exam</div>'}`).join("")}</section>`).join("")}</div>`;
};

/* ---------- actions */
/* ---------- subject colours: every subject keeps one colour everywhere */
function setSubjects(ids) {
  const u = [...new Set(ids)].sort(), n = Math.max(u.length, 1), gcd = (x, y) => y ? gcd(y, x % y) : x;
  let stride = 1, best = 1e9; for (let s = 1; s < n || s === 1; s++) { if (gcd(s, n) === 1 && Math.abs(s - n * 0.382) < best) { best = Math.abs(s - n * 0.382); stride = s; } if (n === 1) break; }
  st._sj = {};
  u.forEach((id, k) => { const h = Math.round(((k * stride) % n * 360 / n + 14) % 360), alt = k % 2;
    st._sj[id] = { bg: `hsl(${h} ${alt ? 38 : 46}% ${alt ? 90 : 86}%)`, bar: `hsl(${h} 44% ${alt ? 50 : 42}%)`, ink: `hsl(${h} 55% 19%)` }; });
}
function subjCol(cid) {
  if (st._sj && st._sj[cid]) return st._sj[cid];
  const h = [...cid].reduce((a, c) => a * 31 + c.charCodeAt(0), 7) % 360;
  return { bg: `hsl(${h} 42% 88%)`, bar: `hsl(${h} 42% 46%)`, ink: `hsl(${h} 55% 19%)` };
}

/* ---------- class swaps between teachers */
const swSlot = c => c ? `${esc(c.course_id)}${c.kind !== "lecture" ? " " + esc(c.kind) : ""} · ${DAYF[c.day]}${c.date_label ? " " + c.date_label : ""} · ${c.from} to ${c.to} · ${esc(c.room)}` : "Class removed";
const SW_STATUS = { waiting_teacher: ["warn", "Waiting for the teacher"], waiting_head: ["info", "Waiting for the department head"], approved: ["ok", "In the timetable"], undone: ["gray", "Undone"],
  declined: ["bad", "Teacher said no"], rejected: ["bad", "Turned down by the head"], cancelled: ["gray", "Withdrawn"], failed: ["bad", "Could not be applied"] };
function swCard(w) {
  const [tone, label] = SW_STATUS[w.status] || ["gray", w.status], t = w.teacher;
  const heads = w.heads.map(h => `${esc(h.head)}${h.status === "approved" ? " (approved)" : ""}`).join(" and ");
  const s1 = t ? (t.approve ? "done" : "bad") : w.status === "waiting_teacher" ? "now" : "";
  const s2 = w.status === "approved" ? "done" : w.status === "rejected" ? "bad" : w.status === "waiting_head" ? "now" : "";
  const s3 = w.status === "approved" ? "done" : w.status === "failed" ? "bad" : "";
  const step = (c, title, sub) => `<li class="${c}"><i></i><div><b>${title}</b><small>${sub}</small></div></li>`;
  const open = w.status === "waiting_teacher" || w.status === "waiting_head";
  return `<article class="swcard"><div class="sw-top"><b>${esc(w.id)}</b>${pill(tone, label)}${pill("gray", w.scope === "day" ? `Week ${w.week} only` : "Every week")}<span class="muted xs sp">${esc(w.at.replace("T", " ").slice(0, 16))}</span></div>
    <div class="sw-pair"><div><span class="sw-l">${esc(w.a_name)} gives</span><div class="sw-c">${swSlot(w.give_slot)}</div></div><span class="sw-x">${ic("swap", 20)}</span><div><span class="sw-l">${esc(w.b_name)} gives</span><div class="sw-c">${swSlot(w.take_slot)}</div></div></div>
    ${w.note ? `<p class="small" style="margin:12px 0 0"><span class="muted">Note: </span>${esc(w.note)}</p>` : ""}
    <ol class="sw-steps">${step(s1, `${esc(w.b_name)} agrees`, t ? (t.approve ? "Agreed" : "Said no" + (t.reason ? ": " + esc(t.reason) : "")) : "Asked first")}
      ${step(s2, "Department head approves", heads + (w.status === "rejected" && w.reason ? ". " + esc(w.reason) : ""))}${step(s3, "Timetable updated", w.status === "approved" ? (w.scope === "day" ? `Both teachers see it in week ${w.week}. Other weeks stay as they were` : "Both teachers see the change now") : w.status === "failed" ? esc(w.reason) : "Only after both approvals")}</ol>
    ${w.can_respond || w.can_decide ? `<div class="sw-act"><input type="text" id="swr-${esc(w.id)}" placeholder="Reason (optional)" maxlength="200"><div class="row" style="gap:8px">
      <button class="btn sm" data-act="${w.can_respond ? "swrespond" : "swdecide"}" data-v="${esc(w.id)}" data-a="1">${w.can_respond ? "Agree to swap" : "Approve"}</button>
      <button class="btn sm danger" data-act="${w.can_respond ? "swrespond" : "swdecide"}" data-v="${esc(w.id)}" data-a="0">${w.can_respond ? "Decline" : "Turn down"}</button></div></div>` : ""}
    ${undoBox("swap", w, "swap")}
    ${w.can_cancel ? `<div style="margin-top:12px"><button class="btn sm ghost" data-act="swcancel" data-v="${esc(w.id)}">Withdraw request</button></div>` : ""}
    ${open || w.history.length ? `<details class="sw-hist"><summary>History</summary>${w.history.map(h => `<div class="xs"><span class="muted">${esc(h.at.replace("T", " ").slice(0, 16))}</span> ${esc(h.text)}</div>`).join("")}</details>` : ""}</article>`;
}
VIEWS.swaps = async () => {
  const d = await api("/api/swaps"), rows = st.sw.rows = d.rows, r = role();
  if (r === "faculty") {
    await swLoadCells();
    const inbox = rows.filter(w => w.can_respond), mine = rows.filter(w => w.mine), other = rows.filter(w => !w.mine && !w.can_respond && w.for_me);
    return `${pageHead("Swap classes", "Offer one of your classes and ask a colleague to take it, while you take one of theirs. They answer first, then the department head.")}<div class="stack">
      ${inbox.length ? `<section class="card"><h2>Waiting for your answer</h2><div class="sw-list" style="margin-top:16px">${inbox.map(swCard).join("")}</div></section>` : ""}
      <section class="card" id="swx">${swBuilder()}</section>
      <section class="card"><h2>My requests</h2><div class="sw-list" style="margin-top:16px">${mine.length ? mine.map(swCard).join("") : '<div class="muted small">You have not asked for any swaps yet.</div>'}</div></section>
      ${other.length ? `<section class="card"><h2>Asked of you before</h2><div class="sw-list" style="margin-top:16px">${other.map(swCard).join("")}</div></section>` : ""}</div>`;
  }
  const todo = rows.filter(w => w.can_decide), early = rows.filter(w => w.status === "waiting_teacher"), done = rows.filter(w => !w.can_decide && w.status !== "waiting_teacher");
  const sec = (h, l, empty) => `<section class="card"><h2>${h}</h2><div class="sw-list" style="margin-top:16px">${l.length ? l.map(swCard).join("") : `<div class="muted small">${empty}</div>`}</div></section>`;
  return `${pageHead("Class swaps", r === "admin" ? "Teachers asking to exchange classes. The Dean's office can approve for any department." : `Teachers asking to exchange classes, for ${st.me.user.department} and its colleagues. You decide once both teachers agree.`)}<div class="stack">
    ${sec("Waiting for you", todo, "Nothing to approve right now.")}${early.length ? sec("Waiting for the other teacher first", early, "") : ""}${sec("Decided", done, "No decided swaps yet.")}</div>`;
};
async function swLoadCells() {
  const q = st.sw; if (!q.week) q.week = st.me.current_week || 3;
  const tt = await api("/api/timetable?week=" + (q.scope === "day" ? q.week : 1));
  q.cells = tt.cells.sort((a, b) => DAYS.indexOf(a.day) - DAYS.indexOf(b.day) || a.start - b.start); q.examWeek = !!tt.exam_week && q.scope === "day";
}
function wkRange(w) {
  const m = new Date((st.me.week_monday || "") + "T12:00:00"); if (isNaN(m)) return "";
  const a = new Date(m); a.setDate(m.getDate() + 7 * (w - (st.me.current_week || 3))); const b = new Date(a); b.setDate(a.getDate() + 4);
  const f = d => d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  return `${f(a)} to ${f(b)}`;
}
function swWhen() {
  const q = st.sw, one = q.scope === "day";
  return `<div class="sw-when"><div class="sw-step"><span class="n">1</span><div><h2>When</h2><div class="muted small">${one ? "Only the day you need. Every other week keeps its usual teacher." : "The two classes change teacher in every week of the semester."}</div></div></div>
    <div class="row" style="gap:16px;flex-wrap:wrap;margin-top:12px"><div class="seg" style="max-width:100%"><button type="button" class="${one ? "on" : ""}" data-act="swscope" data-v="day">Just one day</button><button type="button" class="${one ? "" : "on"}" data-act="swscope" data-v="always">Every week</button></div>
    ${one ? `<label class="field" style="width:140px"><span class="l">Week</span><input type="number" id="sw-week" min="1" max="${st.me.sem.weeks}" value="${q.week}"></label><span class="muted small" style="align-self:end;padding-bottom:14px">Monday to Friday: <b>${wkRange(q.week)}</b></span>` : ""}</div></div>`;
}
function swBuilder() {
  const s = st.sw, cells = s.cells || []; setSubjects([...cells.map(c => c.course_id), ...((s.opts && s.opts.options) || []).map(o => o.course_id)]);
  const g = cells.find(c => c.id === s.give);
  const byDay = DAYS.map(d => [d, cells.filter(c => c.day === d)]).filter(([, l]) => l.length);
  const when = swWhen();
  if (s.examWeek) return when + '<div class="empty" style="margin-top:20px">Week ' + s.week + ' is exam week. Classes do not run, so there is nothing to swap. Pick another week.</div>';
  const my = when + `<div class="sw-step" style="margin-top:28px"><span class="n">2</span><div><h2>Pick the class you want to give</h2><div class="muted small">${s.scope === "day" ? "Your classes in week " + s.week + "." : "From your own timetable."}</div></div></div>
    <div class="sw-days">${byDay.map(([d, l]) => `<div class="sw-day"><span class="sw-dl">${DAYN[d]}${l[0].date_label && s.scope === "day" ? " · " + esc(l[0].date_label) : ""}</span>${l.map(c => { const k = subjCol(c.course_id); return `<button type="button" class="swc ${s.give === c.id ? "on" : ""}" data-act="swgive" data-v="${esc(c.id)}" style="--bc:${k.bar};--bg2:${k.bg}"><b>${esc(c.course_id)}${c.kind !== "lecture" ? " · " + esc(c.kind) : ""}</b><span>${pStart(c.start)} to ${pEnd(c.start + c.dur - 1)} · ${esc(c.room)}</span><small>${esc(c.groups.join(", "))}</small></button>`; }).join("")}</div>`).join("")}</div>`;
  if (!g) return my;
  return my + `<div class="sw-step" style="margin-top:32px"><span class="n">3</span><div><h2>Pick the class you would like to take</h2><div class="muted small">Classes of other teachers. The teacher who takes it now is shown, and they are asked first.</div></div></div>
    <div class="sw-filter"><div class="tt-search" style="flex:1;min-width:200px">${ic("search", 16)}<input id="sw-q" placeholder="Search a subject or teacher" value="${esc(s.q)}" autocomplete="off"></div>
      <select id="sw-dept"><option value="mine" ${s.dept === "mine" ? "selected" : ""}>My department (${esc(st.me.user.department)})</option><option value="all" ${s.dept === "all" ? "selected" : ""}>All departments</option></select><select id="sw-day"><option value="">Any day</option>${dayOpt(s.day)}</select><label class="ck"><input type="checkbox" id="sw-only" ${s.only ? "checked" : ""}>Only swaps that work</label></div>
    <div id="sw-opts">${swOpts()}</div>
    <div id="sw-sum">${swSummary()}</div>`;
}
function swOpts() {
  const s = st.sw; if (!s.opts) return '<div class="muted small" style="padding:16px 0">Looking at every class</div>';
  const q = s.q.trim().toLowerCase();
  let l = s.opts.options.filter(o => (!s.only || o.ok) && (s.dept === "all" || o.department === st.me.user.department || o.course_department === st.me.user.department) && (!s.day || o.day === s.day) && (!q || (o.course_id + " " + o.title + " " + o.teacher + " " + o.department).toLowerCase().includes(q)));
  const total = l.length; l = l.slice(0, 40);
  if (!l.length) return '<div class="empty" style="margin-top:12px">No class matches. Try clearing the filters.</div>';
  return `<div class="sw-opts">${l.map(o => { const k = subjCol(o.course_id); return `<button type="button" class="swo ${o.ok ? "" : "off"} ${s.take === o.id ? "on" : ""}" data-act="swtake" data-v="${esc(o.id)}" ${o.ok ? "" : 'aria-disabled="true"'} style="--bc:${k.bar};--bg2:${k.bg}">
    <div class="swo-h"><b>${esc(o.course_id)}${o.kind !== "lecture" ? " · " + esc(o.kind) : ""}</b><span>${esc(o.title)}</span>${o.same_course ? pill("ok", "Same subject") : ""}</div>
    <div class="small">${DAYF[o.day]}${o.date_label ? " " + o.date_label : ""} · ${o.from} to ${o.to} · ${esc(o.room)} · ${esc(o.groups.join(", "))}</div>
    <div class="swo-t">Taught now by <b>${esc(o.teacher)}</b> · ${esc(o.department)}</div>
    ${o.ok ? (o.notes.length ? `<div class="xs muted" style="margin-top:6px">${o.notes.map(esc).join(". ")}</div>` : "") : `<div class="swo-why">${o.problems.map(esc).join(". ")}</div>`}</button>`; }).join("")}</div>${total > 40 ? `<div class="muted xs" style="margin-top:12px">Showing 40 of ${total}. Search to narrow it down.</div>` : ""}`;
}
function swSummary() {
  const s = st.sw, g = (s.cells || []).find(c => c.id === s.give), o = s.opts && s.opts.options.find(x => x.id === s.take);
  if (!g || !o) return "";
  const gc = s.opts.give;
  return `<div class="sw-sum"><div class="sw-step"><span class="n">4</span><div><h2>Check and send</h2></div></div>
    <div class="sw-pair"><div><span class="sw-l">You give</span><div class="sw-c">${swSlot(gc)}</div></div><span class="sw-x">${ic("swap", 20)}</span><div><span class="sw-l">You take, from ${esc(o.teacher)}</span><div class="sw-c">${swSlot(o)}</div></div></div>
    <p class="small" style="margin:16px 0 0"><b>${s.scope === "day" ? "Only for week " + s.week + "." : "For every week."}</b> <b>${esc(o.teacher)}</b> conducts this class now and will be asked first. If they agree, it goes to ${o.department === st.me.user.department ? "the " + esc(o.department) + " coordinator" : "the department heads of " + esc(st.me.user.department) + " and " + esc(o.department)} for approval. ${s.scope === "day" ? `The two classes change hands on ${DAYN[gc.day]} ${gc.date_label} and ${DAYN[o.day]} ${o.date_label}, and nothing else moves.` : "The timetable only changes after that."}</p>
    ${o.notes.length ? `<div class="sw-note">${o.notes.map(esc).join(". ")}</div>` : ""}
    <label class="field" style="margin-top:16px"><span class="l">Note for ${esc(o.teacher)} (optional)</span><input type="text" id="sw-note" maxlength="300" value="${esc(s.note)}" placeholder="e.g. I have a conference that day"></label>
    <div style="margin-top:16px"><button class="btn" data-act="swsend">Send request to ${esc(o.teacher)}</button></div></div>`;
}
function swPaint() { const x = $("#swx"); if (x) x.innerHTML = swBuilder(); }
async function swPickGive(id) {
  st.sw.give = id; st.sw.take = ""; st.sw.opts = null; st.sw.note = ""; swPaint();
  st.sw.opts = await api("/api/swaps/options?give=" + encodeURIComponent(id) + (st.sw.scope === "day" ? "&week=" + st.sw.week : "")); if (st.sw.give === id) swPaint();
}

/* ---------- online guest lectures (inside Bookings) */
function bkTabs() {
  return `<div class="seg bk-tabs" style="margin:0 0 24px" role="tablist"><button class="${st.bk.sub === "rooms" ? "on" : ""}" data-act="bksub" data-v="rooms" role="tab">Room bookings</button><button class="${st.bk.sub === "online" ? "on" : ""}" data-act="bksub" data-v="online" role="tab">Online guest lectures</button><button class="${st.bk.sub === "mine" ? "on" : ""}" data-act="bksub" data-v="mine" role="tab">My bookings</button></div>`;
}
function olBlank() { return { title: "", speaker: "", org: "", week: Math.min(st.me.sem.weeks, (st.me.current_week || 3) + 1), day: "WED", start: "18:00", end: "19:00", link: "", groups: [], notes: "" }; }
async function bookingsMine() {
  const d = await api("/api/bookings?mine=1&all=1"), u = st.me.user, rows = d.rows;
  const wk = [...new Set(rows.map(r => r.week))].sort((a, b) => a - b);
  return `${pageHead("Bookings", `Every request ${esc(u.name)} has made, with its answer. Events that have already happened are removed automatically.`, `<button class="btn lg" data-act="newbk">${ic("plus", 18)}New request</button>`)}${bkTabs()}
    <div class="stack"><section class="card flush"><div class="list-head"><h2>My bookings</h2><div class="muted small" style="margin-top:4px;font-weight:500">${rows.length ? rows.length + " request" + (rows.length > 1 ? "s" : "") + " in week" + (wk.length > 1 ? "s " : " ") + wk.join(", ") : "Nothing yet"}</div></div>
    ${rows.length ? rows.map(bkRow).join("") : '<div class="empty">You have no booking requests. Use New request to ask for a room.</div>'}</section></div>`;
}
async function bookingsOnline() {
  const d = await api("/api/online"); st.ol.rows = d.rows; if (!st.ol.form) st.ol.form = olBlank();
  return `${pageHead("Bookings", "Online guest lectures need no room. The only rule is that the students have no class or exam at that time.")}${bkTabs()}
    <div class="stack"><section class="card" id="ol-form">${olForm()}</section><section class="card flush"><div class="list-head"><h2>Scheduled online lectures</h2><div class="muted small" style="margin-top:4px;font-weight:500">${role() === "admin" ? "Everything, including lectures waiting for you." : "Scheduled lectures, and your own requests."}</div></div>${olList()}</section></div>`;
}
function olForm() {
  const f = st.ol.form, groups = st.meta.groups, all = f.groups.length === groups.length;
  return `<h2>Schedule an online lecture</h2><div class="muted small" style="margin:6px 0 20px;font-weight:500">${role() === "admin" ? "It is scheduled straight away." : "The Dean's office approves it after the check below."}</div>
    <div class="fields">${field("Title", `<input type="text" id="ol-title" maxlength="120" value="${esc(f.title)}" placeholder="e.g. Careers in embedded systems">`, { cls: "wide" })}
    ${field("Speaker", `<input type="text" id="ol-speaker" maxlength="80" value="${esc(f.speaker)}" placeholder="Name of the guest">`)}${field("Organisation", `<input type="text" id="ol-org" maxlength="80" value="${esc(f.org)}" placeholder="Optional">`)}</div>
    <div class="fields" style="margin-top:16px">${weekField("ol-week", f.week)}${field("Day", `<select id="ol-day">${dayOpt(f.day, [...DAYS, "SAT"])}</select>`)}${field("Starts", `<input type="time" id="ol-start" value="${esc(f.start)}" min="07:00" max="22:00" step="900">`)}${field("Ends", `<input type="time" id="ol-end" value="${esc(f.end)}" min="07:00" max="22:00" step="900">`)}</div>
    <div class="fields" style="margin-top:16px">${field("Meeting link", `<input type="url" id="ol-link" maxlength="400" value="${esc(f.link)}" placeholder="https://meet.google.com/... or a Zoom or Teams link">`, { cls: "wide" })}</div>
    <div class="sect-label" style="margin-top:24px">Who should attend <button type="button" class="link" data-act="olall" style="margin-left:12px;text-transform:none;letter-spacing:0">${all ? "Clear all" : "Select all groups"}</button></div>
    <div class="chips">${groups.map(g => tg("data-olg", g.id, f.groups.includes(g.id), g.id)).join("")}</div>
    <div style="margin-top:16px">${field("Notes for students", `<textarea id="ol-notes" rows="2" maxlength="400" placeholder="Optional. Passcode, topic, what to prepare">${esc(f.notes)}</textarea>`)}</div>
    <div id="ol-check" class="ol-check">${olCheckHTML()}</div>
    <div style="margin-top:16px"><button class="btn" data-act="olsave">${role() === "admin" ? "Schedule lecture" : "Send for approval"}</button></div>`;
}
function olCheckHTML() {
  const c = st.ol.check; if (!c) return '<span class="muted small">The check runs as you fill the form.</span>';
  if (c.errors.length) return `<div class="chk warn">${ic("alert", 18)}<div>${c.errors.map(esc).join("<br>")}</div></div>`;
  if (c.clashes.length) return `<div class="chk bad">${ic("alert", 18)}<div><b>Students have something else then</b><br>${c.clashes.map(esc).join("<br>")}</div></div>`;
  return `<div class="chk ok">${ic("check", 18)}<div><b>No clash.</b> Nobody in the chosen groups has a class or exam then.${c.platform ? " Link looks like " + esc(c.platform) + "." : ""}</div></div>`;
}
function olReadForm() {
  const f = st.ol.form, v = id => ($("#" + id) || {}).value;
  if (!$("#ol-title")) return f;
  Object.assign(f, { title: v("ol-title"), speaker: v("ol-speaker"), org: v("ol-org"), week: +v("ol-week") || 1, day: v("ol-day"), start: v("ol-start"), end: v("ol-end"), link: v("ol-link"), notes: v("ol-notes"),
    groups: [...document.querySelectorAll("[data-olg]:checked")].map(x => x.dataset.olg) });
  return f;
}
let olTimer = 0;
function olLive() { clearTimeout(olTimer); olTimer = setTimeout(async () => { try { st.ol.check = await api("/api/online/check", "POST", olReadForm()); const c = $("#ol-check"); if (c) c.innerHTML = olCheckHTML(); } catch (e) { } }, 350); }
const OL_STATUS = { scheduled: ["ok", "Scheduled"], waiting: ["warn", "Waiting for the Dean's office"], rejected: ["bad", "Turned down"], cancelled: ["gray", "Cancelled"] };
function olList() {
  const rows = st.ol.rows || []; if (!rows.length) return '<div class="empty">No online lectures yet.</div>';
  return rows.map(o => { const [tone, lab] = OL_STATUS[o.status] || ["gray", o.status], live = o.status === "scheduled";
    return `<div class="olc ${o.status === "cancelled" || o.status === "rejected" ? "dim" : ""}"><div class="ol-when"><b>Week ${o.week}</b><span>${DAYN[o.day]}</span><em>${esc(o.start)} to ${esc(o.end)}</em></div>
      <div class="ol-main"><div class="row" style="gap:10px"><h3 class="ol-t">${esc(o.title)}</h3>${pill(tone, lab)}${pill("gray", o.platform)}</div>
        <div class="small">${esc(o.speaker)}${o.org ? ", " + esc(o.org) : ""}</div>
        <div class="xs muted" style="margin-top:4px">For ${esc(o.groups.join(", "))} · ${esc(o.id)} · by ${esc(o.by_name)}</div>${o.notes ? `<div class="xs" style="margin-top:6px">${esc(o.notes)}</div>` : ""}
        ${o.reason ? `<div class="xs" style="margin-top:6px;color:var(--bad)">${esc(o.reason)}</div>` : ""}
        <div class="ol-acts">${live || o.status === "waiting" ? `<a class="btn sm ${live ? "" : "ghost"}" href="${esc(o.link)}" target="_blank" rel="noopener noreferrer">${live ? "Open the meeting" : "Preview link"}</a><button class="btn sm ghost" data-act="olcopy" data-v="${esc(o.link)}">Copy link</button>` : ""}
          ${o.can_decide ? `<button class="btn sm dark" data-act="oldecide" data-v="${esc(o.id)}" data-a="1">Approve</button><button class="btn sm danger" data-act="oldecide" data-v="${esc(o.id)}" data-a="0">Turn down</button>` : ""}
          ${o.can_cancel ? `<button class="btn sm danger" data-act="olcancel" data-v="${esc(o.id)}">Cancel</button>` : ""}</div></div></div>`; }).join("");
}

/* --- extra classes in exam week: only exams are hard, the rest is a score */
const XC_STATUS = { waiting: ["warn", "Waiting for approval"], approved: ["ok", "Approved"], declined: ["bad", "Turned down"], cancelled: ["gray", "Cancelled"] };
const XC_LEVEL = { none: ["ok", "No issues"], minor: ["ok", "Small issues"], some: ["warn", "Some issues"], many: ["bad", "Many issues"] };
const XC_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"];
function xcMine() { const u = st.me.user; return st.meta.sessions.filter(s => s.faculty_id === u.faculty_id); }
function xcBlank() { const s0 = xcMine()[0] || {}; return { session_id: s0.id || "", day: "MON", start: "18:30", end: "20:00", room: "", size: s0.size || 60, topic: "" }; }
function xcRead() {
  const f = st.xc.form, v = id => ($("#" + id) || {}).value;
  if (!$("#xc-class")) return f;
  Object.assign(f, { session_id: v("xc-class"), day: v("xc-day"), start: v("xc-start"), end: v("xc-end"), room: v("xc-room") || "", size: +v("xc-size") || 0, topic: v("xc-topic") });
  return f;
}
function xcFormCard() {
  const f = st.xc.form, mine = xcMine();
  return `<section class="card" id="xc-form"><h2>Extra class in exam week</h2>
    <div class="muted small" style="margin:6px 0 20px;font-weight:500">Week ${st.xc.week} only. You can ask for any time from 07:00 to 22:00. Exams come first: your students' exams and the rooms exams use cannot be booked. Everything else only adds to a score that your head sees.</div>
    <div class="fields">${field("Class", `<select id="xc-class">${mine.map(s => `<option value="${s.id}" ${s.id === f.session_id ? "selected" : ""}>${esc(courseTitle(s.course_id))} · ${s.kind} · ${esc(s.groups.join(", "))}</option>`).join("")}</select>`, { cls: "wide" })}
    ${field("Day", `<select id="xc-day">${XC_DAYS.map(d => `<option value="${d}" ${d === f.day ? "selected" : ""}>${DAYF[d]}</option>`).join("")}</select>`)}
    ${field("Starts", `<input type="time" id="xc-start" value="${esc(f.start)}" min="07:00" max="22:00" step="900">`)}${field("Ends", `<input type="time" id="xc-end" value="${esc(f.end)}" min="07:00" max="22:00" step="900">`)}
    ${field("Students", `<input type="number" id="xc-size" min="1" max="1000" value="${f.size}">`)}
    ${field("Room", `<select id="xc-room">${xcRoomOpts()}</select>`)}
    ${field("What is it for", `<input type="text" id="xc-topic" maxlength="200" value="${esc(f.topic)}" placeholder="e.g. Revision of units 3 and 4">`, { cls: "wide" })}</div>
    <div id="xc-check" style="margin-top:20px">${xcCheckHTML()}</div>
    <div style="margin-top:16px"><button class="btn" data-act="xcsend">Send for approval</button></div>
    ${xcList(st.xc.rows.filter(x => x.own), false)}</section>`;
}
function xcRoomOpts() {
  const c = st.xc.check, f = st.xc.form, rooms = (c && c.rooms) || [];
  let o = `<option value="">Pick the best room for me</option>`;
  if (f.room && !rooms.some(r => r.id === f.room)) o += `<option value="${esc(f.room)}" selected>${esc(f.room)}</option>`;
  return o + rooms.map(r => `<option value="${r.id}" ${r.id === f.room ? "selected" : ""}>${esc(r.id)} · seats ${r.capacity} · ${r.penalty ? r.penalty + " point" + (r.penalty > 1 ? "s" : "") : "no issues"}</option>`).join("");
}
function xcSoftHTML(list) { return `<ul class="xc-soft">${list.map(w => `<li><span>${esc(w.text)}</span><em>+${w.pts}</em></li>`).join("")}</ul>`; }
function xcCheckHTML() {
  const c = st.xc.check; if (!c) return '<span class="muted small">The check runs as you fill the form.</span>';
  if (c.errors && c.errors.length && !c.hard.length && !c.soft.length) return `<div class="chk warn">${ic("alert", 18)}<div>${c.errors.map(esc).join("<br>")}</div></div>`;
  let h = "";
  if (c.hard.length) h += `<div class="chk bad">${ic("alert", 18)}<div><b>Not possible, exams come first</b><br>${c.hard.map(esc).join("<br>")}</div></div>`;
  else {
    const [tone, lab] = XC_LEVEL[c.level] || XC_LEVEL.none;
    h += `<div class="chk ${tone === "gray" ? "ok" : tone}">${ic(c.level === "none" ? "check" : "alert", 18)}<div><b>${lab}${c.penalty ? ` · ${c.penalty} point${c.penalty > 1 ? "s" : ""}` : ""}</b><br>${c.level === "none" ? "Nothing in the way. This can be sent." : "You can still send this. Your head will see these points."}${c.soft.length ? xcSoftHTML(c.soft) : ""}</div></div>`;
    if (c.errors && c.errors.length) h += `<div class="chk warn" style="margin-top:10px">${ic("alert", 18)}<div>${c.errors.map(esc).join("<br>")}</div></div>`;
  }
  if (c.exams && c.exams.length) h += `<div class="xs muted" style="margin-top:10px">Exams for these students that day: ${c.exams.map(esc).join(" · ")}</div>`;
  return h;
}
let xcTimer = 0;
function xcLive(now) {
  clearTimeout(xcTimer);
  const run = async () => { if (!$("#xc-class")) return; try { st.xc.check = await api("/api/extras/check", "POST", xcRead()); const c = $("#xc-check"); if (c) c.innerHTML = xcCheckHTML(); const r = $("#xc-room"); if (r) r.innerHTML = xcRoomOpts(); } catch (e) { } };
  if (now) run(); else xcTimer = setTimeout(run, 350);
}
function xcList(rows, head) {
  if (!rows.length) return head ? '<div class="empty">No extra class requests.</div>' : "";
  return `<div class="xc-rows" ${head ? "" : 'style="margin-top:28px"'}>${head ? "" : '<div class="sect-label">Your extra class requests</div>'}${rows.map(x => { const [tone, lab] = XC_STATUS[x.status] || ["gray", x.status], [lt, ll] = XC_LEVEL[x.level] || XC_LEVEL.none;
    return `<div class="xcr ${x.status === "cancelled" || x.status === "declined" ? "dim" : ""}"><div class="ol-when"><b>${DAYN[x.day]}</b><span>Week ${x.week}</span><em>${esc(x.start)} to ${esc(x.end)}</em></div>
    <div class="ol-main"><div class="row" style="gap:10px;flex-wrap:wrap"><h3 class="ol-t">${esc(x.course_id)} · ${esc(x.title)}</h3>${pill(tone, lab)}${pill(lt === "ok" && !x.penalty ? "gray" : lt, ll + (x.penalty ? " · " + x.penalty + (x.penalty === 1 ? " point" : " points") : ""))}</div>
      <div class="small">${esc(x.topic)}</div>
      <div class="xs muted" style="margin-top:4px">${esc(x.groups.join(", "))} · ${x.size} students · ${esc(x.room)} · ${esc(x.id)}${head || !x.own ? " · by " + esc(x.by_name) : ""}</div>
      ${x.warnings && x.warnings.length ? xcSoftHTML(x.warnings) : ""}
      ${x.reason ? `<div class="xs" style="margin-top:6px;color:var(--bad)">${esc(x.reason)}</div>` : ""}
      <div class="ol-acts">${x.can_decide ? `<button class="btn sm dark" data-act="xcdecide" data-v="${esc(x.id)}" data-a="1">Approve</button><button class="btn sm danger" data-act="xcdecide" data-v="${esc(x.id)}" data-a="0">Turn down</button>` : ""}
        ${x.can_cancel ? `<button class="btn sm ghost" data-act="xccancel" data-v="${esc(x.id)}">Cancel</button>` : ""}</div></div></div>`; }).join("")}</div>`;
}
function xcHeadCard() {
  const rows = st.xc.rows; if (!rows.length) return "";
  const wait = rows.filter(x => x.status === "waiting"), rest = rows.filter(x => x.status !== "waiting");
  return `<section class="card flush"><div class="list-head"><h2>Extra classes in exam week</h2><div class="muted small" style="margin-top:4px;font-weight:500">${wait.length ? wait.length + " waiting. " : ""}Points show how many soft rules a request bends. Nothing here clashes with an exam.</div></div>${xcList(wait.concat(rest), true)}</section>`;
}
function xcTimetable(xs) {
  if (!xs.length) return "";
  const order = Object.fromEntries(XC_DAYS.map((d, i) => [d, i]));
  xs = [...xs].sort((a, b) => order[a.day] - order[b.day] || a.start.localeCompare(b.start));
  return `<section class="card flush" style="margin-top:20px"><div class="list-head"><h2>Extra classes this week</h2><div class="muted small" style="margin-top:4px;font-weight:500">Approved by the head. These are not part of the regular timetable.</div></div>${xs.map(x => `<div class="olc"><div class="ol-when"><b>${DAYN[x.day]}</b><em>${esc(x.start)} to ${esc(x.end)}</em></div><div class="ol-main"><h3 class="ol-t">${esc(x.course_id)} · ${esc(x.title)}</h3><div class="small">${esc(x.topic)}</div><div class="xs muted" style="margin-top:4px">${esc(x.groups.join(", "))} · ${esc(x.room)} · ${esc(x.by_name)}</div></div></div>`).join("")}</section>`;
}
function extraOverview(o) {
  let h = "";
  if (o.extras_waiting) h += `<section class="card"><div class="row"><div><h2>Extra class requests waiting</h2><div class="muted small" style="margin-top:4px">${o.extras_waiting} request${o.extras_waiting > 1 ? "s" : ""} for exam week</div></div><button class="btn sp" data-act="tab" data-v="changes">Open</button></div></section>`;
  if (o.swaps_waiting) h += `<section class="card"><div class="row"><div><h2>Swap requests waiting for you</h2><div class="muted small" style="margin-top:4px">${o.swaps_waiting} request${o.swaps_waiting > 1 ? "s" : ""} to answer</div></div><button class="btn sp" data-act="tab" data-v="swaps">Open</button></div></section>`;
  if ((o.online_upcoming || []).length) h += `<section class="card"><h2>Coming up online</h2><div style="margin-top:12px">${o.online_upcoming.map(x => `<div class="ol-mini"><b>${esc(x.title)}</b><span>Week ${x.week} · ${DAYN[x.day]} ${esc(x.start)} to ${esc(x.end)} · ${esc(x.platform)}</span><a href="${esc(x.link)}" target="_blank" rel="noopener noreferrer">Join</a></div>`).join("")}</div></section>`;
  return h ? `<div class="stack" style="margin-top:24px">${h}</div>` : "";
}
document.addEventListener("input", e => {
  const t = e.target;
  if (t.id === "sw-q") { st.sw.q = t.value; const o = $("#sw-opts"); if (o) o.innerHTML = swOpts(); }
  else if (t.id === "sw-note") st.sw.note = t.value;
  else if (t.closest && t.closest("#ol-form") && ["INPUT", "TEXTAREA"].includes(t.tagName)) { olReadForm(); olLive(); }
  else if (t.closest && t.closest("#xc-form") && ["INPUT", "TEXTAREA"].includes(t.tagName)) { xcRead(); xcLive(); }
});
document.addEventListener("change", e => {
  const t = e.target;
  if (t.id === "sw-week") { const w = Math.max(1, Math.min(st.me.sem.weeks, +t.value || 1)); Object.assign(st.sw, { week: w, give: "", take: "", opts: null, note: "" }); swLoadCells().then(swPaint).catch(err => toast(err.message, true)); }
  else if (t.id === "sw-dept") { st.sw.dept = t.value; const o = $("#sw-opts"); if (o) o.innerHTML = swOpts(); }
  else if (t.id === "sw-day") { st.sw.day = t.value; const o = $("#sw-opts"); if (o) o.innerHTML = swOpts(); }
  else if (t.id === "sw-only") { st.sw.only = t.checked; const o = $("#sw-opts"); if (o) o.innerHTML = swOpts(); }
  else if (t.closest && t.closest("#ol-form") && ["INPUT", "SELECT"].includes(t.tagName)) { olReadForm(); olLive(); }
  else if (t.closest && t.closest("#xc-form") && ["INPUT", "SELECT"].includes(t.tagName)) {
    if (t.id === "xc-class") { const x = st.meta.sessions.find(q => q.id === t.value); if (x && $("#xc-size")) $("#xc-size").value = x.size; st.xc.form.room = ""; }
    if (t.id === "xc-day" || t.id === "xc-start" || t.id === "xc-end") st.xc.form.room = "";
    xcRead(); xcLive();
  }
});

document.addEventListener("click", e => {
  const el = e.target.closest("[data-act]"); if (!el) return; const a = el.dataset.act, v = el.dataset.v;
  if (a === "askclose" && el.classList.contains("scrim") && e.target !== el) return;
  if (a === "clsclose" && el.classList.contains("scrim") && e.target !== el) return;
  act(async () => {
    switch (a) {
      case "pickrole": st.pickRole = v; return showLogin();
      case "signout": return signOut();
      case "tab": return go(v);
      case "notes": st.notesOpen = !st.notesOpen; return render();
      case "searchgo": { const [k, id] = v.split("|"); st.tt.view = k; st.tt.id = id; return go("timetable"); }
      case "askopen": st.ask = { text: "" }; return renderModal();
      case "askclose": st.ask = null; return renderModal();
      case "askex": { st.ask.text = (ASK_EX[role()] || [])[+v] || ""; st.ask.res = null; return renderModal(); }
      case "askgo": { st.ask.text = $("#ask-text").value; if (!st.ask.text.trim()) throw new Error("Write a few words first"); st.ask.res = null; return askRun(); }
      case "askpick": { st.ask.text = $("#ask-text").value; return askRun(v); }
      case "askalt": { const r = st.ask.res, x = r.alternatives[+v]; r.dis.changes[0] = { type: "move_session", session_id: r.dis.changes[0].session_id, to: { day: x.day, start_period: x.start } };
        r.summary = r.summary.replace(/→ .*$/, "→ " + x.label); r.target = { ...r.target, label: x.label, kind: "free", reasons: [], room: null }; r.preview = null; return renderModal(); }
      case "askpreview": { const r = st.ask.res; r.busy = true; renderModal(); try { r.preview = await api("/api/changes/preview", "POST", { dis: r.dis }); } finally { r.busy = false; } return renderModal(); }
      case "asksend": { const r = st.ask.res, c = await api("/api/changes", "POST", { dis: r.dis, note: r.summary }); st.ask = null; renderModal(); toast(c.id + " sent for approval"); return go(st.tab); }
      case "tologin": return showLogin();
      case "tolanding": return showLanding();
      case "landscroll": return document.getElementById(v).scrollIntoView({ behavior: "smooth" });
      case "ovday": st.ovDay = v; return render();
      case "loadds": return $("#ds-file").click();
      case "clsclose": if (el.classList.contains("scrim") && e.target !== el) return; st.cls = null; return renderModal();
      case "clstab": { st.cls.tab = v; renderModal(); if (v === "move" && !st.cls.slots) { st.cls.slots = await api("/api/sessions/slots?id=" + encodeURIComponent(st.cls.id)); renderModal(); } return; }
      case "clspick": { const [d, p] = v.split("|"); const r = st.cls.slots.slots.find(x => x.day === d && x.start === +p); st.cls.pickLabel = "Move to " + r.label;
        st.cls.dis = { id: "move", changes: [{ type: "move_session", session_id: st.cls.id, to: { day: d, start_period: +p } }] };
        st.cls.preview = await api("/api/changes/preview", "POST", { dis: st.cls.dis }); return renderModal(); }
      case "clsavoid": { const n = st.cls.slots.now; st.cls.pickLabel = "Find a different time";
        st.cls.dis = { id: "move", changes: [{ type: "move_session", session_id: st.cls.id, avoid: [{ day: n.day, periods: Array.from({ length: st.cls.slots.dur }, (_, i) => n.start + i) }] }] };
        st.cls.preview = await api("/api/changes/preview", "POST", { dis: st.cls.dis }); return renderModal(); }
      case "clssend": { const c = await api("/api/changes", "POST", { dis: st.cls.dis, note: st.cls.pickLabel || "" }); st.cls = null; renderModal(); toast(c.id + " sent for approval"); return go(st.tab); }
      case "clsopen": { const c = JSON.parse(el.dataset.cell); return openClass(v, c); }
      case "venuepick": {
        if (!(st.bk.showForm && st.bf && st.bf.form)) { st.bk.showForm = true; st.bf = newForm({ room: v }); return render(); }
        const f = st.bf.form; f.requested_room = f.requested_room === v ? null : v;
        const sel = document.querySelector('[data-bf="requested_room"]'); if (sel) sel.value = f.requested_room || "";
        document.querySelectorAll(".vn").forEach(b => b.classList.toggle("on", b.dataset.room === f.requested_room));
        recheck(); toast(f.requested_room ? v + " chosen for the request" : "Room choice cleared"); return;
      }
      case "newbk": st.bk.sub = "rooms"; st.bk.showForm = true; st.bf = newForm(); return render();
      case "mybookings": st.bk.sub = "mine"; return go("bookings");
      case "useseed": { await api("/api/seed", "POST"); toast("Timetable loaded"); return go("overview"); }
      case "generate": { if (st.me.job && st.me.job.state === "running") return; st.me.job = await api("/api/generate", "POST"); return go("overview"); }
      case "reset": if (!confirm("Erase everything and start from the original data?")) return; await api("/api/reset", "POST"); toast("App reset"); st.ov = null; return boot();
      case "download": return download(v);
      case "check": { const out = {}; for (const n of ["schedule.json", "schedule_after.json"]) out[n] = await api("/api/export-check/" + n);
        $("#checkout").innerHTML = Object.entries(out).map(([n, r]) => `<div class="sess"><b>${n}</b><div class="row" style="margin-top:8px;gap:6px">${pill(r.hard ? "bad" : "ok", r.hard + " hard violations")}${pill("gray", "soft " + r.soft)}${pill("gray", "score " + (r.bookings ? r.bookings.booking_score + "/" + r.bookings.booking_score_max_if_all_approved : "–"))}</div>${r.violations.map(x => `<div class="small" style="margin-top:6px">${esc(x.rule)}: ${esc(x.detail)}</div>`).join("")}</div>`).join(""); return; }
      case "ttview": st.tt.view = v; st.tt.id = ""; st.tt.course = ""; return render();
      case "ttsubj": st.tt.course = v; return ttPaint();
      case "ttclear": st.tt.course = ""; st.tt.kinds = { lecture: true, tutorial: true, lab: true, event: true }; return ttPaint();
      case "findrooms": { const q = st.rooms; st.week = +$("#rm-week").value || st.week; q.day = $("#rm-day").value; q.frm = +$("#rm-from").value; q.to = +$("#rm-to").value; q.min_cap = +$("#rm-cap").value || 0; q.rtype = $("#rm-type").value; q.need = [...document.querySelectorAll("[data-need]:checked")].map(x => x.dataset.need);
        if (q.to < q.frm) throw new Error("The end time is before the start");
        st.roomRes = await api(`/api/rooms/find?day=${q.day}&frm=${q.frm}&to=${q.to}&week=${st.week}&min_cap=${q.min_cap}&rtype=${q.rtype}&need=${q.need.join(",")}`); $("#roomres").innerHTML = roomTable(st.roomRes); return; }
      case "reqroom": { const q = st.rooms; st._pre = { room: v, day: q.day, frm: q.frm, to: q.to, dur: q.to - q.frm + 1 }; st.bf = null;
        if (role() === "club") return go("newrequest"); st.bk.showForm = true; st.bf = newForm(st._pre); st._pre = null; return go(role() === "faculty" ? "requests" : "bookings"); }
      case "try": { st.bf.text = EXAMPLES[+v]; $("#bf-text").value = st.bf.text; return; }
      case "parse": { await parseInto($("#bf-text").value); return render(); }
      case "addwin": { const w = st.bf.form.windows; w.push({ ...w[w.length - 1] }); return render(); }
      case "delwin": st.bf.form.windows.splice(+v, 1); return render();
      case "sendbk": { const r = await api("/api/bookings", "POST", cleanForm()); st.bf = newForm(); st.bf.result = r.created; toast("Request sent"); return go(st.tab); }
      case "toggleform": st.bk.showForm = !st.bk.showForm; if (st.bk.showForm) st.bf = newForm(); return render();
      case "bksub": st.bk.sub = v; return render();
      case "swscope": { if (st.sw.scope === v) return; Object.assign(st.sw, { scope: v, give: "", take: "", opts: null, note: "" }); await swLoadCells(); return swPaint(); }
      case "swgive": return swPickGive(v);
      case "swtake": { const o = st.sw.opts && st.sw.opts.options.find(x => x.id === v); if (!o || !o.ok) return; st.sw.take = v; const b = $("#sw-opts"); if (b) b.innerHTML = swOpts(); const s = $("#sw-sum"); if (s) { s.innerHTML = swSummary(); s.scrollIntoView({ behavior: "smooth", block: "nearest" }); } return; }
      case "swsend": { const r = await api("/api/swaps", "POST", { give: st.sw.give, take: st.sw.take, note: ($("#sw-note") || {}).value || "", scope: st.sw.scope, week: st.sw.scope === "day" ? st.sw.week : null }); toast(`Request ${r.id} sent to ${r.b_name}`); Object.assign(st.sw, { give: "", take: "", opts: null, note: "", q: "" }); return render(); }
      case "swrespond": { await api(`/api/swaps/${v}/respond`, "POST", { approve: el.dataset.a === "1", reason: ($(`#swr-${v}`) || {}).value || "" }); toast(el.dataset.a === "1" ? "Agreed. It now goes to the department head" : "Declined"); return render(); }
      case "swdecide": { const r = await api(`/api/swaps/${v}/decide`, "POST", { approve: el.dataset.a === "1", reason: ($(`#swr-${v}`) || {}).value || "" }); toast(r.status === "approved" ? "Approved and applied to the timetable" : r.status === "waiting_head" ? "Approved. Waiting for the other head" : r.status === "failed" ? "Could not be applied: " + r.reason : "Turned down", r.status === "failed"); return render(); }
      case "undoask": st.undoAsk = v || null; return render();
      case "undochange": case "undoswap": {
        const reason = ($("#undo-" + v) || {}).value || "", isCh = a === "undochange";
        const r = await api(isCh ? `/api/changes/${v}/undo` : `/api/swaps/${v}/undo`, "POST", { reason }); st.undoAsk = null;
        const ck = r.undone && r.undone.check; toast(`${v} undone. ` + (ck && ck.hard !== null && ck.hard !== undefined ? `Official checker: ${ck.hard} rule problems` : "Timetable unchanged for other weeks")); return render();
      }
      case "swcancel": await api(`/api/swaps/${v}/cancel`, "POST"); toast("Request withdrawn"); return render();
      case "olall": { olReadForm(); const f = st.ol.form; f.groups = f.groups.length === st.meta.groups.length ? [] : st.meta.groups.map(g => g.id); const x = $("#ol-form"); if (x) x.innerHTML = olForm(); olLive(); return; }
      case "olsave": { const f = olReadForm(); const r = await api("/api/online", "POST", f); toast(r.status === "scheduled" ? "Online lecture scheduled" : "Sent to the Dean's office for approval"); st.ol.form = olBlank(); st.ol.check = null; return render(); }
      case "xcsend": { const f = xcRead(); const r = await api("/api/extras", "POST", f); toast(`${r.id} sent${r.penalty ? " with " + r.penalty + " point" + (r.penalty > 1 ? "s" : "") : ""}`); st.xc.form = xcBlank(); st.xc.check = null; return render(); }
      case "xcdecide": { const reason = el.dataset.a === "0" ? (prompt("Reason for turning it down (optional)") || "") : ""; await api(`/api/extras/${v}/decide`, "POST", { approve: el.dataset.a === "1", reason }); toast(el.dataset.a === "1" ? "Approved" : "Turned down"); return render(); }
      case "xccancel": if (!confirm("Cancel this extra class?")) return; await api(`/api/extras/${v}/cancel`, "POST"); toast("Cancelled"); return render();
      case "olcopy": try { await navigator.clipboard.writeText(v); toast("Link copied"); } catch (e) { toast("Could not copy. Select the link and copy it", true); } return;
      case "oldecide": { const reason = el.dataset.a === "0" ? (prompt("Reason for turning it down (optional)") || "") : ""; await api(`/api/online/${v}/decide`, "POST", { approve: el.dataset.a === "1", reason }); toast(el.dataset.a === "1" ? "Approved" : "Turned down"); return render(); }
      case "olcancel": if (!confirm("Cancel this online lecture?")) return; await api(`/api/online/${v}/cancel`, "POST"); toast("Cancelled"); return render();
      case "bkfilter": st.bk.filter = v; return render();
      case "approve": { const r = await api("/api/bookings/publish", "POST", { ids: [v] }); toast(r.published.length ? v + " approved" : r.message, !r.published.length); return render(); }
      case "approveall": { const d = await loadBookings(false); const ids = d.rows.filter(r => r.can_decide).map(r => r.id); const r = await api("/api/bookings/publish", "POST", { ids }); toast(r.published.length + " approved"); return render(); }
      case "approveseries": { const r = await api(`/api/bookings/series/${v}/publish`, "POST"); toast(r.published.length ? `${r.published.length} weeks approved in one go` + (r.refused.length ? `, ${r.refused.length} left for someone else` : "") : "Nothing for you to approve", !r.published.length); return render(); }
      case "cancelseries": { if (!confirm("Cancel this week and every later week of this repeating booking? The rooms are released.")) return; const r = await api(`/api/bookings/series/${v}/cancel`, "POST", { from_week: +el.dataset.w }); toast(r.cancelled + " bookings cancelled"); return render(); }
      case "cancelbk": if (!confirm("Cancel this request? Its room is released.")) return; await api(`/api/bookings/${v}/cancel`, "POST"); toast("Cancelled"); return render();
      case "chtype": st.ch.type = v; st.ch.out = null; return render();
      case "chsend": { const dis = buildDis(v); const c = await api("/api/changes", "POST", { dis, note: "" }); st.ch.out = c; toast(c.feasible ? "Sent for approval" : "That cannot be done as asked", !c.feasible); return render(); }
      case "chapprove": case "chreject": { const note = ($("#note-" + v) || {}).value || ""; await api(`/api/changes/${v}/decide`, "POST", { approve: a === "chapprove", reason: note }); toast(a === "chapprove" ? v + " approved and applied" : v + " rejected"); return render(); }
      case "rexam": await api("/api/exams/reschedule", "POST"); toast("Exams planned again"); return render();
    }
  });
});
document.addEventListener("change", e => {
  if (e.target.id !== "ds-file" || !e.target.files[0]) return;
  act(async () => {
    const blob = JSON.parse(await e.target.files[0].text());
    if (!confirm("Load this dataset? Everything built so far is cleared and the timetable has to be generated again.")) return;
    const r = await api("/api/dataset", "POST", blob);
    toast(`Loaded ${r.sessions} sessions, ${r.rooms} rooms, ${r.faculty} teachers`); st.ov = null; return boot();
  });
});
boot();

initRoomPreview();
