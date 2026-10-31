"""The assistant: one box that understands three kinds of message.

  * a question ("why is CS101 at 8 AM?", "why was BR-14 rejected?")        -> code-written explanation
  * a timetable request ("I am away Tuesday", "move DSA lecture to Wed")  -> a draft change, never applied here
  * a room request                                                        -> the booking form (parser.py)

It reads language with plain rules. Nothing it returns changes any data: a draft change still goes
through the solver, the validator and an Admin's approval, and a booking still goes through the
booking checker. A model, when a key is set, is only ever used to read a room request (parser.py).
"""
import re
from .parser import parse_range, parse_single_time, hour_to_period, DAY_WORDS, DAYS
from .explain import Board, slot_check, slot_table, span, clock

CHANGE_WORDS = r"\b(move|shift|reschedule|re-schedule|swap|change|postpone|prepone|away|leave|unavailable|not available|can'?t|cannot|won'?t be|travelling|traveling|conference|closed|closure|nahi|nhi|cancel)\b"
ABSENT_WORDS = r"\b(away|leave|unavailable|not available|can'?t come|cannot come|won'?t be|travelling|traveling|conference|out of station|on leave|nahi aa|nhi aa)\b"
DAY_RE = r"\b(monday|mon|tuesday|tues|tue|wednesday|wed|thursday|thurs|thu|friday|fri)\b"
TOD = {"morning": (1, 5), "subah": (1, 5), "afternoon": (6, 9), "after lunch": (6, 9), "lunch ke baad": (6, 9),
       "evening": (9, 9), "before lunch": (1, 5)}


def _days(t):
    out = []
    for m in re.finditer(DAY_RE, t):
        d = DAYS[DAY_WORDS[m.group(1)]]
        if d not in out:
            out.append(d)
    return out


def _periods(t):
    """(from_period, to_period) named in the text, or None."""
    for key, rng in TOD.items():
        if key in t:
            r = rng
            break
    else:
        r = None
    m = re.search(r"\bp\s?([1-9])\b(?:\s*(?:to|-)\s*p?\s?([1-9])\b)?", t)
    if m:
        a = int(m.group(1)); b = int(m.group(2) or a)
        return a, b
    rg = parse_range(t)
    if rg:
        a24, b24, _ = rg
        a = hour_to_period(a24)
        b = hour_to_period(b24 - 1) if b24 > a24 else a
        if a and b:
            return a, min(b, 9)
    h = parse_single_time(t, "am" if "morning" in t or "subah" in t else None)
    if h:
        p = hour_to_period(h)
        if p:
            return p, p
    return r


def _find_sessions(S, user, text, restrict=True):
    """Candidate classes named in the text, narrowed to the ones this person may talk about."""
    t = text.lower()
    data = S.data
    courses = {c["id"]: c for c in data["courses"]}
    ids = {m.upper() for m in re.findall(r"\b([a-z]{2,3}\s?\d{3})\b", t)}
    ids = {i.replace(" ", "") for i in ids}
    words = set(re.findall(r"[a-z]+", t))
    scored = []
    for c in data["courses"]:
        if c["id"] in ids:
            scored.append((10, c["id"]))
            continue
        tw = [w for w in re.findall(r"[a-z]+", c["title"].lower()) if len(w) > 3 and w not in ("and", "with", "lab", "laboratory")]
        hit = sum(1 for w in tw if w in words)
        initials = "".join(w[0] for w in re.findall(r"[a-z]+", c["title"].lower()) if w not in ("and", "of", "the", "to"))
        if len(initials) >= 3 and initials in words:
            hit += 2
        if hit and hit >= max(1, len(tw) // 2):
            scored.append((hit, c["id"]))
    top = [cid for sc, cid in scored if sc == max(x for x, _ in scored)] if scored else []
    kind = next((k for k in ("lab", "tutorial", "lecture") if re.search(rf"\b{k}s?\b", t)), None)
    out = []
    for s in data["sessions"]:
        if s["id"] not in S.assign:
            continue
        if top and s["course_id"] not in top:
            continue
        if not top and not (user["role"] == "faculty"):
            continue
        if kind and s["kind"] != kind:
            continue
        if restrict:
            if user["role"] == "faculty" and s["faculty_id"] != user.get("faculty_id"):
                continue
            if user["role"] == "department_coordinator" and courses[s["course_id"]]["department"] != user["department"]:
                continue
        out.append(s)
    return out


def _label(S, s):
    a = S.assign[s["id"]]
    c = next(c for c in S.data["courses"] if c["id"] == s["course_id"])
    return f"{c['title']} ({s['course_id']}{'' if s['kind'] == 'lecture' else ' ' + s['kind']}) · {span(a[0], a[1], s['duration'])} · {a[2]}"


def _narrow(S, cands, days, per):
    out = []
    for s in cands:
        d, st, _ = S.assign[s["id"]]
        if days and d not in days:
            continue
        if per and not (st <= per[1] and st + s["duration"] - 1 >= per[0]):
            continue
        out.append(s)
    return out


def _faculty_named(S, text):
    t = text.lower()
    for f in S.data["faculty"]:
        parts = [p for p in re.findall(r"[a-z]+", f["name"].lower()) if p not in ("dr", "prof", "mr", "ms", "mrs")]
        if parts and sum(1 for p in parts if p in t) >= min(2, len(parts)) and (len(parts) == 1 or True):
            return f
    return None


def _room_named(S, text):
    for r in S.data["rooms"]:
        if re.search(rf"\b{re.escape(r['id'].lower())}\b", text.lower()):
            return r["id"]
    return None


# ----------------------------------------------------------------------------- router
def route(S, user, text):
    t = " ".join(text.lower().split())
    if re.search(r"\bbr-\d+[a-z]?\b", t) and re.search(r"\b(why|reason|explain|kyun|kyon|status|what happened)\b", t):
        return "explain"
    if re.search(r"\b(why|kyun|kyon|explain|reason)\b", t):
        return "explain"
    if user["role"] == "club":
        return "change" if re.search(r"\b(move|shift|reschedule|swap|postpone|prepone)\b", t) and re.search(r"\b[a-z]{2,3}\s?\d{3}\b|\bclass|lecture|timetable", t) else "booking"
    if re.search(r"\b(book|need a room|need room|venue|hall for|auditorium|seminar hall|lab for|room for|chahiye)\b", t) and not re.search(r"\b(move|shift|reschedule)\b", t):
        return "booking"
    if re.search(CHANGE_WORDS, t):
        return "change"
    return "booking"


# ----------------------------------------------------------------------------- explain
def do_explain(S, user, text, booking_explain, session_explain, force_sid=None):
    t = text.lower()
    m = re.search(r"\bbr-\d+[a-z]?\b", t)
    if m:
        return {"intent": "explain", "kind": "booking", "answers": [booking_explain(m.group(0).upper())]}
    if force_sid:
        return {"intent": "explain", "kind": "session", "answers": [session_explain(force_sid)]}
    cands = _find_sessions(S, user, text, restrict=False)
    days, per = _days(t), _periods(t)
    narrowed = _narrow(S, cands, days, per)
    note = None
    if cands and not narrowed and (days or per):
        note = "There is no such class at the time you said, so here is where it actually is."
    cands = narrowed or cands
    if not cands:
        return {"intent": "explain", "kind": "none", "answers": [],
                "ask": "Which class or booking do you mean? Try a course code like CS101, or a booking number like BR-14."}
    if len(cands) > 4:
        return {"intent": "explain", "kind": "choose", "answers": [],
                "ask": "That matches several classes. Which one?", "choices": [{"id": s["id"], "label": _label(S, s)} for s in cands[:12]]}
    answers = [session_explain(s["id"]) for s in cands]
    if note:
        for a in answers:
            a["lines"].insert(0, note)
    return {"intent": "explain", "kind": "session", "answers": answers}


# ----------------------------------------------------------------------------- change
def do_change(S, user, text, force_sid=None):
    t = " ".join(text.lower().split())
    if user["role"] == "club":
        return {"intent": "change", "text": text, "ask": "Clubs can ask for rooms, not for changes to classes. Describe the room you need and I will fill the form."}
    days, per = _days(t), _periods(t)
    out = {"intent": "change", "text": text}
    # room closure (admin)
    rid = _room_named(S, t)
    if rid and re.search(r"\b(closed|closure|leak|repair|maintenance|unavailable|out of order)\b", t):
        if user["role"] != "admin":
            return {**out, "ask": "Only the Dean's office can close a room. Ask them, or ask for a different room."}
        a, b = per if per else (1, 9)
        return {**out, "summary": f"Close {rid} on {', '.join(days or ['MON'])} P{a} to P{b}",
                "dis": {"id": "assistant", "changes": [{"type": "room_unavailable", "room_id": rid, "days": days or ["MON"],
                                                         "periods": list(range(a, b + 1)), "reason": text[:80]}]}}
    # absence
    if re.search(ABSENT_WORDS, t) and not re.search(r"\b(move|shift|reschedule|swap)\b", t):
        fac = None
        if user["role"] == "faculty":
            fac = next((f for f in S.data["faculty"] if f["id"] == user.get("faculty_id")), None)
        else:
            fac = _faculty_named(S, text)
            if fac and user["role"] == "department_coordinator" and fac["department"] != user["department"]:
                return {**out, "ask": f"{fac['name']} is not in {user['department']}. Only their own coordinator can report that."}
        if not fac:
            return {**out, "ask": "Which teacher is away? Use their name, for example “Dr. Pooja Das is away on Tuesday”."}
        if not days:
            return {**out, "ask": "Which day or days will you be away?", "faculty_id": fac["id"]}
        a, b = per if per else (1, 9)
        return {**out, "summary": f"{fac['name']} away {', '.join(d.title() for d in days)} P{a} to P{b}",
                "dis": {"id": "assistant", "changes": [{"type": "faculty_unavailable", "faculty_id": fac["id"], "days": days,
                                                         "periods": list(range(a, b + 1)), "reason": text[:80]}]}}
    # move / avoid a class
    cands = [x for x in S.data["sessions"] if x["id"] == force_sid] if force_sid else _find_sessions(S, user, text)
    if not cands:
        return {**out, "ask": "Which class? Use the course code or name, for example “move CS101 lecture to Wednesday afternoon”."}
    split = re.split(r"\b(?:to|towards|into|pe|par|ko|on)\b(?=\s+(?:next\s+)?(?:" + DAY_RE[2:-2].replace("(", "(?:", 1) + r"|\d|p\d|morning|afternoon|evening|after|noon|subah))", t, maxsplit=1)
    before, after = (split[0], split[1]) if len(split) == 2 else (t, "")
    tgt_days, tgt_per = (_days(after), _periods(after)) if after else ([], None)
    cur_days, cur_per = _days(before), _periods(before)
    if not after and re.search(r"\b(can'?t|cannot|not|avoid|nahi|nhi|free me|free my)\b", t):
        cur_days, cur_per = days, per
    if not force_sid:
        cands = _narrow(S, cands, cur_days, cur_per) or cands
    if len(cands) > 1:
        return {**out, "ask": "Which class do you mean?", "choices": [{"id": s["id"], "label": _label(S, s)} for s in cands[:10]]}
    s = cands[0]
    d, st, _ = S.assign[s["id"]]
    cur = span(d, st, s["duration"])
    if not after and re.search(r"\b(can'?t|cannot|not|avoid|nahi|nhi|free)\b", t):
        per_av = list(range(st, st + s["duration"]))
        if cur_per:
            per_av = list(range(cur_per[0], cur_per[1] + 1))
        av = [{"day": cur_days[0] if cur_days else d, "periods": per_av}]
        return {**out, "session": {"id": s["id"], "label": _label(S, s)}, "summary": f"Find a new time for {_label(S, s).split(' · ')[0]} (not {span(av[0]['day'], per_av[0], len(per_av))})",
                "dis": {"id": "assistant", "changes": [{"type": "move_session", "session_id": s["id"], "avoid": av}]}}
    if not tgt_days and not tgt_per:
        return {**out, "session": {"id": s["id"], "label": _label(S, s)},
                "ask": f"Where should it go? It is now {cur}. Say a day and time, for example “Wednesday 3 pm”.",
                "slots": [{"label": r["label"], "day": r["day"], "start": r["start"]} for r in slot_table(S.data, S.assign, s["id"], S._reservations()) if r["kind"] == "free"][:6]}
    rows = slot_table(S.data, S.assign, s["id"], S._reservations())
    want_d = tgt_days[0] if tgt_days else d
    start = None
    if tgt_per:
        start = tgt_per[0]
        if s["duration"] > 1 and tgt_per[1] - tgt_per[0] + 1 < s["duration"] and tgt_per[0] == tgt_per[1]:
            start = tgt_per[0]
    pick = None
    vague = bool(tgt_per) and bool(after) and re.search(r"\b(morning|afternoon|evening|after lunch|before lunch|subah)\b", after) and not re.search(r"\d", after)
    if start and not vague:
        pick = next((r for r in rows if r["day"] == want_d and r["start"] == start), None)
        if pick is None and (d, st) == (want_d, start):
            return {**out, "ask": "That is where it already is."}
    else:
        lo, hi = tgt_per if tgt_per else (1, 9)
        inside = [r for r in rows if r["day"] == want_d and lo <= r["start"] <= hi]
        pool = [r for r in inside if r["kind"] == "free"] or [r for r in inside if r["kind"] == "if_others_move"] or inside
        pick = pool[0] if pool else None
    if pick is None:
        return {**out, "ask": "I could not find that time. Try “Wednesday 3 pm”."}
    check = slot_check(Board(S.data, S.assign, S._reservations()), s["id"], pick["day"], pick["start"])
    best_room = None
    near = lambda r: (r["day"] != pick["day"], abs(r["start"] - pick["start"]), r["penalty"])
    alts = sorted([r for r in rows if r["kind"] == "free"], key=near)[:4]
    return {**out, "session": {"id": s["id"], "label": _label(S, s)},
            "summary": f"Move {_label(S, s).split(' · ')[0]}: {cur} → {pick['label']}",
            "target": {"label": pick["label"], "day": pick["day"], "start": pick["start"], "kind": pick["kind"],
                       "reasons": [b["text"] for b in check["blockers"]], "room": best_room},
            "alternatives": [{"label": r["label"], "day": r["day"], "start": r["start"]} for r in alts if (r["day"], r["start"]) != (pick["day"], pick["start"])],
            "dis": {"id": "assistant", "changes": [{"type": "move_session", "session_id": s["id"],
                                                     "to": {"day": pick["day"], "start_period": pick["start"]}}]}}
