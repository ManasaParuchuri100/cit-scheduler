"""Plain English / Hinglish -> editable booking form.

Two paths, same output shape:
  * Claude (if ANTHROPIC_API_KEY is set) reads the text and returns JSON;
  * a deterministic rule parser works with no key and no network.
Either way the result is normalised against the real dataset (valid days, periods, room types, groups),
anything assumed is listed, and missing essentials become a follow-up question. The model never
validates or decides anything: the form goes to the same checker as a hand-filled one.
"""
import datetime as dt
import json
import os
import re

DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
DAY_WORDS = {"monday": 0, "mon": 0, "tuesday": 1, "tues": 1, "tue": 1, "wednesday": 2, "wed": 2,
             "thursday": 3, "thurs": 3, "thu": 3, "friday": 4, "fri": 4, "saturday": 5, "sat": 5,
             "sunday": 6, "sun": 6}
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "che": 6,
             "saat": 7, "aath": 8}
NEED_WORDS = [
    ("pa_system", r"\b(mic|mics|microphone|sound|pa system|pa|loudspeakers?|acoustics)\b"),
    ("projector", r"\b(projector|big screen|screen|slides)\b"),
    ("stage", r"\bstage\b"),
    ("computers", r"\b(computers?|laptops?|coding|hackathon)\b"),
    ("power_benches", r"\b(power points?|power benches|power sockets?)\b"),
    ("accessible", r"\b(wheelchair|accessible|ramp|step[- ]free|lift access)\b"),
    ("ac", r"\b(a/?c|air[- ]?conditioned)\b"),
]
NEED_LABEL = {"projector": "A projector", "pa_system": "Mic and sound", "stage": "A stage"}
DEPT_WORDS = {"cse": "CSE", "computer": "CSE", "ece": "ECE", "electronics": "ECE", "ee": "EE", "electrical": "EE",
              "me": "ME", "mechanical": "ME", "ce": "CE", "civil": "CE"}


# ----------------------------------------------------------------------------- helpers
def hour_to_period(h):
    """Clock hour (24h) at which something starts -> period number."""
    if h < 8:
        return None
    if h <= 12:
        return h - 7
    if h == 13:
        return 6                    # lunch hour: next period is P6
    return h - 8


def end_to_period(h):
    """Clock hour at which something ends -> last period it occupies."""
    if h == 14:
        return 5
    return hour_to_period(h - 1)


def _num(tok):
    tok = tok.lower()
    if tok.isdigit():
        return int(tok)
    return NUM_WORDS.get(tok)


def _meridiem_hour(h, mer):
    if mer == "pm" and h < 12:
        return h + 12
    if mer == "am" and h == 12:
        return 0
    return h


TIME_RE = r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?"
RANGE_RE = re.compile(r"(?:between|from)?\s*" + TIME_RE + r"\s*(?:to|-|–|till|until|and)\s*(?:(midnight)|" + TIME_RE + r")", re.I)
SINGLE_RE = re.compile(r"(?:\bat\b|\baround\b|\bafter\b)?\s*" + TIME_RE + r"(?=\s*(?:baje|o'clock|sharp|\b))", re.I)


def _norm_mer(m):
    return m.lower().replace(".", "") if m else None


def parse_range(text):
    """Find 'X to Y' clock times. Returns (start_hour, end_hour, via_between) or None."""
    for m in RANGE_RE.finditer(text):
        h1, m1, mer1, midnight, h2, m2, mer2 = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6), m.group(7)
        if h1 is None:
            continue
        a = int(h1)
        mer1, mer2 = _norm_mer(mer1), _norm_mer(mer2)
        if midnight:
            b = 24
            mer1 = mer1 or "pm"
        else:
            if h2 is None:
                continue
            b = int(h2)
            if mer1 is None and mer2 is not None:
                mer1 = mer2
                # "11 to 1 pm" -> 11 am
                if mer2 == "pm" and a > b and a <= 12:
                    mer1 = "am"
            if mer1 is None and mer2 is None:
                mer1 = mer2 = "pm" if a < 8 else "am"
                if a <= 12 and b <= 12 and a < 8:
                    mer1 = mer2 = "pm"
            if mer2 is None:
                mer2 = mer1
        a24 = _meridiem_hour(a, mer1)
        b24 = 24 if midnight else _meridiem_hour(b, mer2)
        if b24 <= a24 and not midnight:
            b24 += 12
        word = text[max(0, m.start() - 12):m.start() + 8].lower()
        return a24, b24, ("between" in word)
    return None


def parse_single_time(text, tod):
    """A lone clock time like '5 pm', '6 baje'. Hinglish day-part words fix am/pm."""
    for m in re.finditer(TIME_RE + r"\s*(baje|o'clock)?", text, re.I):
        h, mm, mer, baje = int(m.group(1)), m.group(2), _norm_mer(m.group(3)), m.group(4)
        if not (mer or baje):
            continue
        if h > 12 or h == 0:
            continue
        if mer is None:
            mer = "am" if tod == "am" else "pm"
            if h in (8, 9, 10, 11) and tod != "pm":
                mer = "am"
        return _meridiem_hour(h, mer)
    return None


def resolve_days(text, today):
    """List of weekday codes mentioned, plus whether they are a series (all needed) or alternatives."""
    t = text.lower()
    found = []
    for m in re.finditer(r"\b(monday|mon|tuesday|tues|tue|wednesday|wed|thursday|thurs|thu|friday|fri|saturday|sat|sunday|sun)\b", t):
        i = DAY_WORDS[m.group(1)]
        if i < 5 and DAYS[i] not in found:
            found.append(DAYS[i])
    notes = []
    if re.search(r"\b(kal|tomorrow)\b", t):
        d = (today + dt.timedelta(days=1)).weekday()
        if d < 5 and DAYS[d] not in found:
            found.append(DAYS[d])
        notes.append(f"“kal” means tomorrow, {(today + dt.timedelta(days=1)).strftime('%A')}")
    if re.search(r"\b(aaj|today)\b", t):
        d = today.weekday()
        if d < 5 and DAYS[d] not in found:
            found.append(DAYS[d])
        notes.append(f"“today” is {today.strftime('%A')}")
    if re.search(r"\bparso\b", t):
        d = (today + dt.timedelta(days=2)).weekday()
        if d < 5 and DAYS[d] not in found:
            found.append(DAYS[d])
    if re.search(r"\b(all of fest week|fest week|daily|every day|everyday|all week|each day)\b", t) and not found:
        found = list(DAYS)
    series = bool(re.search(r"\b(every|each|daily|all of|both days|both)\b", t)) and len(found) > 1
    if re.search(r"\bor\b", t) and len(found) > 1 and not re.search(r"\b(every|daily|both)\b", t):
        series = False
    if re.search(r"\b(and)\b", t) and len(found) > 1 and re.search(r"\b(every|both|each|daily|meets)\b", t):
        series = True
    return found, series, notes


def groups_in(text, groups):
    ids = [g["id"] for g in groups]
    out = []
    for g in ids:
        if re.search(r"\b" + re.escape(g) + r"\b", text, re.I):
            out.append(g)
    t = text.lower()
    yr = None
    if re.search(r"\b(third|3rd|final)[- ]?years?\b", t):
        yr = 3
    elif re.search(r"\b(second|2nd)[- ]?years?\b", t):
        yr = 2
    if yr:
        depts = [DEPT_WORDS[w] for w in re.findall(r"\b(cse|computer|ece|electronics|ee|electrical|me|mechanical|ce|civil)\b", t)]
        for d in dict.fromkeys(depts):
            gid = f"{d}-{yr}"
            if gid in ids and gid not in out:
                out.append(gid)
    return out


def parse_rules(text, data, role="club", today=None, week=None):
    today = today or dt.date.today()
    t = text.strip()
    low = t.lower()
    assumptions, missing = [], []
    rooms = {r["id"]: r for r in data["rooms"]}
    groups = data["student_groups"]

    # --- attendance
    att = None
    m = re.search(r"(\d[\d,]*)\s*(?:\+\s*)?(people|persons?|log|participants?|students?|attendees?|dancers?|visitors?|spectators?|audience|members?|pax|guests?)", low)
    if m:
        att = int(m.group(1).replace(",", ""))
    else:
        m = re.search(r"(?:audience|expecting|around|about|maybe|approx\w*)\s*(?:of\s*)?(\d[\d,]*)\b(?!\s*(?:am|pm|baje|hours?|hrs?|ghant))", low)
        if m and int(m.group(1)) >= 10:
            att = int(m.group(1).replace(",", ""))
    # --- duration words
    dur_h = None
    m = re.search(r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|ek|do|teen|char|chaar|paanch|chhe)\s*(?:-|\s)?(?:straight\s+|continuous\s+)?(?:hours?|hrs?|ghante|ghanta|ghanti)\b", low)
    if m:
        v = m.group(1)
        dur_h = float(v) if re.match(r"\d", v) else _num(v)
    if dur_h is None and re.search(r"\b(an hour|1 hour)\b", low):
        dur_h = 1

    # --- time of day words
    tod = None
    if re.search(r"\b(shaam|evening|raat|night)\b", low):
        tod = "pm"
    elif re.search(r"\b(subah|morning)\b", low):
        tod = "am"
    elif re.search(r"\b(afternoon|dopahar)\b", low):
        tod = "pm"

    days, series, day_notes = resolve_days(t, today)
    assumptions += day_notes

    # --- time window
    flex = None
    start_h = end_h = None
    rng = parse_range(low)
    if rng:
        start_h, end_h, between = rng
        if dur_h is not None and (end_h - start_h) > dur_h:
            flex = (start_h, end_h)               # "N hours any time between X and Y"
        elif between and dur_h is None:
            flex = (start_h, end_h)
            missing.append("duration")
    else:
        h = parse_single_time(low, tod)
        if h is not None:
            start_h = h
            if dur_h is None and not re.search(r"\b(all day|whole day)\b", low):
                dur_h = 1
                assumptions.append("No length given, so 1 hour is assumed")
    if re.search(r"\b(all day|whole day)\b", low) and start_h is None:
        start_h, end_h = 8, 18
    if start_h is None and flex is None:
        if re.search(r"after lunch", low):
            flex = (14, 18)
            assumptions.append("“after lunch” means 14:00–18:00 (P6–P9); change it if you meant later")
        elif re.search(r"\bafternoon\b|\bdopahar\b", low):
            flex = (14, 18)
            assumptions.append("“afternoon” means 14:00–18:00 (P6–P9)")
        elif re.search(r"\bevening\b|\bshaam\b", low):
            flex = (18, 22)
            assumptions.append("“evening” means 18:00–22:00 (P10–P13)")
        elif re.search(r"\bnight\b|\braat\b", low):
            flex = (18, 22)
            assumptions.append("“night” means 18:00–22:00 (P10–P13)")
        elif re.search(r"\bmorning\b|\bsubah\b", low):
            flex = (8, 12)
            assumptions.append("“morning” means 08:00–12:00 (P1–P4)")
        else:
            missing.append("time")

    # --- periods
    windows = []
    duration = None
    if start_h is not None and flex is None:
        p1 = hour_to_period(start_h)
        if end_h is not None:
            p2 = end_to_period(end_h)
            duration = (p2 - p1 + 1) if p1 and p2 else None
        else:
            dur_p = int(round(dur_h or 1))
            p2 = p1 + dur_p - 1 if p1 else None
            duration = dur_p
        for d in days or [None]:
            windows.append({"day": d, "from_period": p1, "to_period": p2})
    elif flex is not None:
        p1 = hour_to_period(flex[0])
        p2 = end_to_period(flex[1])
        duration = int(round(dur_h)) if dur_h else None
        for d in days or [None]:
            windows.append({"day": d, "from_period": p1, "to_period": p2})
    if duration is None and dur_h:
        duration = int(round(dur_h))
    if not days:
        missing.append("day")
        windows = [{"day": None, "from_period": w["from_period"], "to_period": w["to_period"]} for w in windows] or []
    if duration is None:
        missing.append("duration")

    # --- room type / room
    needs = []
    for key, rx in NEED_WORDS:
        if re.search(rx, low):
            needs.append(key)
    if "computers" in needs and not re.search(r"\b(computers?|laptops?)\b", low):
        needs.remove("computers")          # only "coding"/"hackathon" in text: implied by lab type instead
    # what the kind of event usually needs, when the person did not say (listed as an assumption they can untick)
    implied = []
    if re.search(r"\b(concert|jam night|pro-?night|music|band|dance|performance|fashion show|ceremony|inauguration|open mic|cultural)\b", low):
        implied += ["stage", "pa_system"]
        if re.search(r"\b(ceremony|inauguration)\b", low):
            implied.append("projector")
    elif re.search(r"\b(talk|speaker|lecture|seminar|workshop|presentation|founder|alumni|session|screening|quiz|panel|webinar)\b", low) and \
            not re.search(r"\b(lab|hackathon|coding|contest)\b", low):
        implied.append("projector")
        if (att or 0) >= 150:
            implied.append("pa_system")
    if (att or 0) >= 500 or (re.search(r"\b(spectators?|audience|crowd)\b", low) and (att or 0) >= 300):
        implied.append("pa_system")
    for k in implied:
        if k not in needs:
            needs.append(k)
            assumptions.append(f"{NEED_LABEL.get(k, k)} added, because that kind of event usually needs it. Untick it if not")
    requested_room = None
    for rid in rooms:
        if re.search(r"(?<![\w-])" + re.escape(rid.lower()) + r"(?![\w-])", low):
            requested_room = rid
            break
    if requested_room is None:
        m = re.search(r"\b([A-Z]{2,}-?[A-Z]?-?\d{1,3})\b", t)
        if m and m.group(1) not in rooms:
            requested_room = m.group(1)
            assumptions.append(f"“{requested_room}” is not a room I know; the form keeps it as a wish and picks a real room")
    room_types = []
    if re.search(r"\bseminar hall\b|\bsh-?\d\b", low):
        room_types.append("seminar_hall")
    if re.search(r"\bauditorium\b|\baud\b", low):
        room_types.append("auditorium")
    if re.search(r"\blecture hall\b|\blh-?\d\b", low):
        room_types.append("lecture_hall")
    if re.search(r"\bclass ?room\b", low):
        room_types.append("classroom")
    if re.search(r"\b(oat|open[- ]air|outdoor|ground|green)\b", low):
        room_types.append("outdoor")
    if re.search(r"\b(elec(tronics)? lab)\b", low):
        room_types.append("lab_elec")
    if re.search(r"\b(computer|computing|cs|coding) lab\b|\blab with computers\b|\bcomputer lab\b", low):
        room_types.append("lab_cs")
    elif re.search(r"\bphysics lab\b", low):
        room_types.append("lab_phy")
    elif re.search(r"\bcivil lab\b", low):
        room_types.append("lab_civil")
    elif re.search(r"\b(lab)\b", low) and not room_types:
        room_types.append("lab_cs" if "computers" in needs or re.search(r"cod|hackathon|program", low) else "lab_cs")
        assumptions.append("“lab” taken as a computing lab; change the room type if you meant another lab")
    if requested_room in rooms and not room_types:
        room_types = [rooms[requested_room]["type"]]
    if not room_types and re.search(r"\b(bridge|survey(ing)?|concrete|geotech|structural|civil)\b", low):
        room_types = ["lab_civil", "workshop"]
        assumptions.append("Looks like a civil engineering activity, so a civil lab or the workshop was chosen")
    if not room_types:
        order = ["classroom", "lecture_hall", "seminar_hall", "auditorium", "outdoor"]
        need = att or 0
        fits = [ty for ty in order if any(r["type"] == ty and r["capacity"] >= need and "event" in r["allowed_uses"]
                                         for r in data["rooms"])]
        room_types = [ty for ty in fits if ty in order[:3]] if need <= 120 else (fits or ["auditorium", "outdoor"])
        if not room_types:
            room_types = ["auditorium", "outdoor"]
        assumptions.append("No room type given, so any " + ", ".join(t_.replace("_", " ") for t_ in room_types) + " that fits will do")
    if "computers" in needs and "lab_cs" not in room_types:
        room_types = ["lab_cs"]

    # --- compulsory groups
    mand = []
    if re.search(r"\b(compulsory|mandatory|must attend|attendance required|attendance is compulsory)\b", low):
        mand = groups_in(t, groups)
        if not mand:
            missing.append("which groups")

    if att is None and mand:
        size = {g["id"]: g["size"] for g in groups}
        att = sum(size[g] for g in mand)
        assumptions.append(f"No headcount given, so the size of {', '.join(mand)} ({att}) is used")

    # --- category
    cat = None
    if re.search(r"\b(institute level|institute-level|official spectra|institute event)\b", low):
        cat = "institute_event"
    elif re.search(r"\b(guest lecture|guest talk|speaker|scientist|industry talk|founder)\b", low):
        cat = "guest_lecture"
    elif re.search(r"\b(department|dept|alumni|farewell|placement)\b", low):
        cat = "department_event"
    else:
        cat = {"admin": "institute_event", "faculty": "guest_lecture",
               "department_coordinator": "department_event"}.get(role, "club_event")

    title = re.split(r"[.,;]", t)[0][:60].strip() or "New event"
    if att is None:
        missing.append("attendance")

    if requested_room in rooms:
        r = rooms[requested_room]
        if "accessible" in needs and not r["accessible"]:
            assumptions.append(f"{requested_room} is not wheelchair accessible. Pick a different room, or the form will offer one that is")

    follow = None
    ask = {"attendance": "How many people are coming?", "day": "Which day do you need it?",
           "time": "What time should it start?", "duration": "How long will it run?",
           "which groups": "Which student groups must attend?"}
    for k in ("day", "time", "attendance", "duration", "which groups"):
        if k in missing:
            follow = ask[k]
            break
    form = {
        "title": title, "requested_category": cat, "attendance": att,
        "duration_periods": duration,
        "windows": [w for w in windows if w["day"] and w["from_period"]],
        "time_hint": next(({"from_period": w["from_period"], "to_period": w["to_period"]} for w in windows
                           if not w["day"] and w["from_period"] and w["to_period"]), None),
        "room_types": room_types, "needs": needs, "requested_room": requested_room,
        "mandatory_for_groups": mand, "series": series, "follow_up": follow,
        "assumptions": assumptions, "missing": sorted(set(missing)), "source": "rules",
    }
    if windows and duration and form["windows"]:
        for w in form["windows"]:
            if w["to_period"] is not None and w["to_period"] - w["from_period"] + 1 < duration:
                w["to_period"] = w["from_period"] + duration - 1
    return form


# ----------------------------------------------------------------------------- Claude path
SYSTEM = """You turn a short room-booking message (English or Hinglish) into JSON for a campus scheduler.
Return ONLY a JSON object with keys: title, requested_category (institute_event|guest_lecture|department_event|club_event),
attendance (int|null), duration_periods (int|null), windows (list of {day: MON..FRI, from_period, to_period}),
room_types (subset of classroom, lecture_hall, auditorium, seminar_hall, outdoor, lab_cs, lab_elec, lab_phy, workshop, lab_civil),
needs (subset of projector, pa_system, stage, computers, power_benches, accessible, ac), requested_room (string|null),
mandatory_for_groups (list of group ids), series (true if every listed day is needed, false if they are alternatives),
follow_up (a single question if something essential is missing, else null), assumptions (list of short strings).
Periods: P1 08:00 ... P5 12:00, lunch 13:00-14:00, P6 14:00 ... P9 17:00, P10 18:00 ... P13 21:00 (ends 22:00). A window is the
range the event may start and end in; duration_periods is its length. "kal" means tomorrow. "mic"/"sound" means pa_system.
Never invent values: use null and a follow_up instead."""


def parse_claude(text, data, role, today, api_key):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    groups = ", ".join(g["id"] for g in data["student_groups"])
    rooms = ", ".join(r["id"] for r in data["rooms"])
    msg = (f"Today is {today.strftime('%A %d %B %Y')}. The user's role is {role}. Group ids: {groups}. Room ids: {rooms}.\n"
           f"Message: {text}")
    r = client.messages.create(model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"), max_tokens=900,
                               system=SYSTEM, messages=[{"role": "user", "content": msg}])
    raw = "".join(b.text for b in r.content if getattr(b, "text", None))
    raw = raw[raw.index("{"): raw.rindex("}") + 1]
    return json.loads(raw)


def normalise(form, data):
    """Make any form (from Claude or the rules) safe: real days, periods, types, groups."""
    valid_types = {r["type"] for r in data["rooms"]}
    valid_needs = {"projector", "pa_system", "stage", "computers", "power_benches", "accessible", "ac"}
    group_ids = {g["id"] for g in data["student_groups"]}
    cats = data["priority_order"]
    out = dict(form)
    out["requested_category"] = form.get("requested_category") if form.get("requested_category") in cats else "club_event"
    out["room_types"] = [x for x in form.get("room_types", []) if x in valid_types] or ["classroom", "lecture_hall", "seminar_hall"]
    out["needs"] = [x for x in form.get("needs", []) if x in valid_needs]
    out["mandatory_for_groups"] = [x for x in form.get("mandatory_for_groups", []) if x in group_ids]
    ws = []
    for w in form.get("windows", []):
        try:
            d, a, b = w["day"], int(w["from_period"]), int(w["to_period"])
        except (KeyError, TypeError, ValueError):
            continue
        if d in DAYS and 1 <= a <= b:
            ws.append({"day": d, "from_period": a, "to_period": b})
    out["windows"] = ws
    for k in ("attendance", "duration_periods"):
        v = form.get(k)
        out[k] = int(v) if isinstance(v, (int, float)) and v > 0 else None
    out.setdefault("assumptions", [])
    out.setdefault("series", False)
    out.setdefault("follow_up", None)
    out["missing"] = [k for k, ok in (("attendance", out["attendance"]), ("duration", out["duration_periods"]),
                                      ("day and time", out["windows"])) if not ok]
    if out["missing"] and not out.get("follow_up"):
        out["follow_up"] = {"attendance": "How many people are coming?", "duration": "How long will it run?",
                            "day and time": "Which day and time do you need?"}[out["missing"][0]]
    return out


def _parse_request(text, data, role="club", today=None, week=None):
    today = today or dt.date.today()
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            f = parse_claude(text, data, role, today, key)
            f["source"] = "claude"
            f.setdefault("title", re.split(r"[.,;]", text)[0][:60])
            return normalise(f, data)
        except Exception as e:                      # network, key or JSON problem: fall back quietly
            f = parse_rules(text, data, role, today, week)
            f["assumptions"].append("The AI assistant was unavailable, so the built-in reader was used")
            return normalise(f, data)
    return normalise(parse_rules(text, data, role, today, week), data)


INJECT_RX = r"\b(ignore (all |the |any )?(previous|prior|above|earlier)? ?(rules|instructions)|bypass|override (the )?rules|skip (the )?(rules|approval|check)|without (any )?approval|auto[- ]?approve|approve (it|my|this)|give (it )?(top|highest) priority|highest priority|mark (it )?as (an )?(institute|exam|guest)|pretend|you must approve|system prompt)\b"


def parse_request(text, data, role="club", today=None, week=None):
    """Read the request (model if a key is set, rules otherwise), then add checks that never depend on a model."""
    f = _parse_request(text, data, role, today, week)
    low = text.lower()
    notes = f.setdefault("assumptions", [])
    if re.search(INJECT_RX, low):
        notes.append("Words like “top priority”, “ignore the rules” or “approve this” cannot change the outcome: "
                     "the level comes from your role, the booking is decided by the same rules for everyone, and a different person approves it")
    # weekly repeat: "every Tuesday", "weekly", "for 6 weeks", "until week 10". The API turns this into a last week.
    cue = re.search(r"\b(every|each)\s+(week|mon\w*|tue\w*|wed\w*|thu\w*|fri\w*)\b|\bweekly\b|\bhar\s+(hafte|week)\b", low)
    until = re.search(r"\b(?:until|till|upto|up to|through|to)\s+week\s+(\d{1,2})\b", low)
    count = re.search(r"\b(?:for|next|over|agle)\s+(?:the\s+next\s+)?(\d{1,2})\s*(?:weeks?|hafte|haftey|hafton)\b", low)
    if until:
        f["repeat_until"] = int(until.group(1))
    elif cue and count:
        f["repeat_count"] = int(count.group(1))
    elif cue:
        f["repeat_open"] = True
    if re.search(r"\b(exam week|midsem week|mid-?sem week|exams? week)\b", low):
        f["week_hint"] = data.get("calendar_week_exam", None) or 9
        notes.append("You mentioned exam week. Exams come first, so no event can be booked in that week")
    if re.search(r"\b(midnight|11\s*pm|10[:.]?(30|45)?\s*pm|12\s*am|1\s*am|2\s*am)\b", low) or re.search(r"\bto (11|12)\s*(pm)?\b.*\b(am|midnight)\b", low):
        notes.append("Rooms can be booked only until 22:00 (period P13). Nothing later exists, so choose an earlier time")
        if not f.get("windows"):
            f["follow_up"] = "Rooms close at 22:00. What earlier time would work?"
    return f
