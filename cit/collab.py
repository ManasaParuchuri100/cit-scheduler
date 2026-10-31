"""Two small workflows that sit beside the timetable:

1. Class swaps. A teacher offers one of their classes and asks to take another teacher's class. The other
   teacher answers first. Then the department head(s) decide. Only then is the timetable changed, and the
   change is checked with the official validator before it is kept.
2. Online guest lectures. No room is needed, but the audience must not have a class or an exam then.
"""
import datetime as dt
import re
from urllib.parse import urlparse

import validator as official
from . import repair as repair_mod
from .bookings import SLOT_LABEL, END_LABEL

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
DAYF = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday"}
OPEN = ("waiting_teacher", "waiting_head")


def mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def fac_email(fid):
    return f"faculty.{fid.lower()}@cit.example"


def detect_platform(url):
    host = (urlparse(url).hostname or "").lower()
    if "zoom" in host:
        return "Zoom"
    if "meet.google" in host:
        return "Google Meet"
    if "teams.microsoft" in host or "teams.live" in host:
        return "Microsoft Teams"
    if "webex" in host:
        return "Webex"
    return host or "Link"


class CollabMixin:
    # ------------------------------------------------------------------ shared
    def _lookups(self):
        S = {s["id"]: s for s in self.data["sessions"]}
        F = {f["id"]: f for f in self.data["faculty"]}
        C = {c["id"]: c for c in self.data["courses"]}
        return S, F, C

    def week_monday(self, week=None):
        """Calendar date of the Monday of a week. The current week is this week, or the coming one at a weekend."""
        t = dt.date.today()
        mon = t - dt.timedelta(days=t.weekday()) + (dt.timedelta(days=7) if t.weekday() > 4 else dt.timedelta(0))
        return mon + dt.timedelta(days=7 * ((week or self.current_week) - self.current_week))

    def week_date(self, week, day):
        return self.week_monday(week) + dt.timedelta(days=DAYS.index(day))

    @staticmethod
    def pretty_date(d):
        return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"

    def oneoff(self, week):
        """session id -> teacher for that one week, from approved one-day swaps."""
        m = {}
        for w in self.swaps:
            if w["status"] == "approved" and w.get("scope") == "day" and w.get("week") == week:
                m[w["give"]], m[w["take"]] = w["b"], w["a"]
        return m

    def _slot_of(self, sid, week=None):
        S, _, C = self._lookups()
        d, st, rid = (self.week_assign(week) if week else self.assign)[sid]
        s = S[sid]
        fid = self.oneoff(week).get(sid, s["faculty_id"]) if week else s["faculty_id"]
        date = self.week_date(week, d) if week else None
        return {"id": sid, "course_id": s["course_id"], "title": C[s["course_id"]]["title"], "kind": s["kind"], "day": d,
                "date": date.isoformat() if date else None, "date_label": f"{date.day} {date.strftime('%b')}" if date else None,
                "start": st, "dur": s["duration"], "room": rid, "groups": s["groups"], "faculty_id": fid,
                "from": SLOT_LABEL[st], "to": END_LABEL[st + s["duration"] - 1]}

    def swapped_from(self):
        """session id -> faculty id who first taught it, for classes that changed teacher through a swap."""
        out = {}
        for dis in self.applied:
            for c in dis.get("changes", []):
                if c.get("type") == "swap_faculty":
                    out.setdefault(c["session_a"], c["faculty_a"])
                    out.setdefault(c["session_b"], c["faculty_b"])
        return out

    # ------------------------------------------------------------------ class swaps
    def swap_check(self, give, take, week=None):
        """Can the teacher of `give` and the teacher of `take` exchange them? Same rules as the validator.
        With a week, only that week's two classes change hands."""
        S, F, C = self._lookups()
        X, Y = S.get(give), S.get(take)
        if not X or not Y or give not in self.assign or take not in self.assign:
            return {"ok": False, "problems": ["One of these classes is no longer in the timetable"], "notes": []}
        assign = self.week_assign(week) if week else self.assign
        one = self.oneoff(week) if week else {}
        eff = lambda sid: one.get(sid, S[sid]["faculty_id"])
        a, b = eff(give), eff(take)
        problems, notes = [], []
        if week:
            if week == self.sem["exam_week"]:
                return {"ok": False, "problems": ["Classes do not run in exam week"], "notes": []}
            if not 1 <= week <= self.sem["weeks"]:
                return {"ok": False, "problems": ["Pick a week of the semester"], "notes": []}
            for sid in (give, take):
                d, st, _r = assign[sid]
                if self._is_past(week, d, END_LABEL[st + S[sid]["duration"] - 1]):
                    problems.append(f"{S[sid]['course_id']} on {DAYF[d]} of week {week} has already taken place")
            if problems:
                return {"ok": False, "problems": problems, "notes": []}
        if a == b:
            return {"ok": False, "problems": ["Both classes are taught by the same person"], "notes": []}
        rooms = {r["id"]: r for r in self.data["rooms"]}

        def incoming(t, new, old):
            f, out = F[t], []
            dn, stn, rn = assign[new]
            pn = set(range(stn, stn + S[new]["duration"]))
            hours = S[new]["duration"]
            for sid, (d, st, _r) in assign.items():
                s = S.get(sid)
                if not s or eff(sid) != t or sid == old:
                    continue
                if d == dn:
                    hours += s["duration"]
                    if pn & set(range(st, st + s["duration"])):
                        out.append(f"{f['name']} already teaches {s['course_id']} at that time")
            for u in f.get("unavailable", []):
                if u["day"] == dn and pn & set(u["periods"]):
                    out.append(f"{f['name']} is away then" + (f" ({u['reason']})" if u.get("reason") else ""))
            if hours > f.get("max_hours_per_day", 4):
                out.append(f"{f['name']} would teach {hours} hours on {DAYF[dn]}, the most allowed is {f.get('max_hours_per_day', 4)}")
            if f.get("needs_accessible") and not rooms.get(rn, {}).get("accessible", True):
                out.append(f"{rn} is not step-free and {f['name']} needs an accessible room")
            for pref in f.get("preferences", []):
                if pref.get("type") == "avoid" and dn in pref.get("days", []) and pn & set(pref["periods"]):
                    notes.append(f"{f['name']} would rather not teach then: {pref.get('note', 'a stated preference')}")
            return out

        problems += incoming(a, take, give)
        problems += incoming(b, give, take)
        if X["kind"] != Y["kind"]:
            notes.append(f"One is a {X['kind']} and the other is a {Y['kind']}")
        da, db = C[X["course_id"]]["department"], C[Y["course_id"]]["department"]
        if da != db:
            notes.append(f"The two classes belong to different departments ({da} and {db})")
        return {"ok": not problems, "problems": problems, "notes": notes}

    def _open_swaps_for(self, sid, week=None):
        """Open requests that already involve this class. A one-day swap only clashes with the same week or a permanent one."""
        return [w for w in self.swaps if w["status"] in OPEN and sid in (w["give"], w["take"])
                and (week is None or w.get("scope") != "day" or w.get("week") == week)]

    def swap_options(self, user, give, week=None):
        if user["role"] != "faculty":
            raise PermissionError("Only teachers can ask for a swap")
        S, F, C = self._lookups()
        X = S.get(give)
        one = self.oneoff(week) if week else {}
        eff = lambda sid: one.get(sid, S[sid]["faculty_id"])
        if not X or eff(give) != user["faculty_id"] or give not in self.assign:
            raise ValueError("Pick one of your own classes")
        rows = []
        for sid, s in S.items():
            if eff(sid) == user["faculty_id"] or sid not in self.assign:
                continue
            chk = self.swap_check(give, sid, week)
            busy = bool(self._open_swaps_for(sid, week))
            slot = self._slot_of(sid, week)
            f = F[slot["faculty_id"]]
            rows.append({**slot, "teacher": f["name"], "department": f["department"], "course_department": C[s["course_id"]]["department"],
                         "ok": chk["ok"] and not busy, "problems": chk["problems"] + (["Another swap request already involves this class"] if busy else []),
                         "notes": chk["notes"], "same_course": s["course_id"] == X["course_id"]})
        order = {d: i for i, d in enumerate(DAYS)}
        rows.sort(key=lambda r: (not r["ok"], not r["same_course"], r["course_department"] != C[X["course_id"]]["department"], order[r["day"]], r["start"]))
        return {"give": self._slot_of(give, week), "options": rows, "week": week}

    def _heads(self, a, b):
        S, F, _ = self._lookups()
        heads = []
        for dept in sorted({F[a]["department"], F[b]["department"]}):
            email = f"coordinator.{dept.lower()}@cit.example"
            if email in self.users:
                heads.append({"dept": dept, "head": f"{dept} coordinator", "head_role": "department_coordinator", "status": "waiting"})
            else:
                heads.append({"dept": dept, "head": "Dean's office", "head_role": "admin", "status": "waiting"})
        return heads

    def create_swap(self, user, give, take, note="", week=None, scope="day"):
        with self.lock:
            if user["role"] != "faculty":
                raise PermissionError("Only teachers can ask for a swap")
            if not self.generated:
                raise ValueError("The timetable has not been generated yet")
            scope = "always" if scope == "always" else "day"
            week = int(week) if scope == "day" and week else None
            if scope == "day" and not week:
                raise ValueError("Pick the week of the day you want to swap")
            S, F, _ = self._lookups()
            X, Y = S.get(give), S.get(take)
            one = self.oneoff(week) if week else {}
            if not X or one.get(give, X["faculty_id"]) != user["faculty_id"]:
                raise ValueError("Pick one of your own classes to give")
            if not Y:
                raise ValueError("Pick the class you would like to take")
            if self._open_swaps_for(give, week) or self._open_swaps_for(take, week):
                raise ValueError("Another swap request already involves one of these classes")
            chk = self.swap_check(give, take, week)
            if not chk["ok"]:
                raise ValueError("This swap does not work: " + "; ".join(chk["problems"]))
            a, b = one.get(give, X["faculty_id"]), one.get(take, Y["faculty_id"])
            sw = {"id": f"SW-{len(self.swaps) + 1:02d}", "at": self._now(), "by": user["email"], "by_name": user["name"], "a": a, "b": b,
                  "give": give, "take": take, "note": (note or "")[:300], "status": "waiting_teacher", "teacher": None,
                  "scope": scope, "week": week, "heads": self._heads(a, b), "history": [], "reason": ""}
            if scope == "day":
                wa = self.week_assign(week)
                when = f"for week {week} only ({self.pretty_date(self.week_date(week, wa[give][0]))} and {self.pretty_date(self.week_date(week, wa[take][0]))})"
            else:
                when = "for every week"
            sw["history"].append({"at": sw["at"], "text": f"{user['name']} asked {F[b]['name']} to swap, {when}"})
            self.swaps.append(sw)
            self.notify(fac_email(b), f"{user['name']} would like to swap classes with you {when} ({sw['id']}). Open Swap classes to answer")
            self.log(user, f"Asked for swap {sw['id']}")
            self._save()
            return sw

    def respond_swap(self, user, sid, approve, reason=""):
        with self.lock:
            sw = self._swap(sid)
            if user["role"] != "faculty" or user["faculty_id"] != sw["b"]:
                raise PermissionError("Only the teacher who was asked can answer")
            if sw["status"] != "waiting_teacher":
                raise ValueError("This request was already answered")
            _, F, _ = self._lookups()
            now = self._now()
            sw["teacher"] = {"by": user["email"], "at": now, "approve": bool(approve), "reason": reason}
            if not approve:
                sw["status"], sw["reason"] = "declined", reason
                sw["history"].append({"at": now, "text": f"{user['name']} said no" + (f": {reason}" if reason else "")})
                self.notify(sw["by"], f"{user['name']} said no to swap {sw['id']}" + (f": {reason}" if reason else ""))
            else:
                chk = self.swap_check(sw["give"], sw["take"], sw.get("week"))
                if not chk["ok"]:
                    raise ValueError("This swap no longer works: " + "; ".join(chk["problems"]))
                sw["status"] = "waiting_head"
                sw["history"].append({"at": now, "text": f"{user['name']} agreed. Waiting for " + " and ".join(h["head"] for h in sw["heads"])})
                self.notify(sw["by"], f"{user['name']} agreed to swap {sw['id']}. It now goes to the department head")
                for u in self.users.values():
                    if u["role"] == "admin" or any(h["head_role"] == "department_coordinator" and u["role"] == "department_coordinator"
                                                    and u.get("department") == h["dept"] for h in sw["heads"]):
                        if u["role"] == "admin" and not any(h["head_role"] == "admin" for h in sw["heads"]):
                            continue
                        self.notify(u["email"], f"Swap {sw['id']} between {F[sw['a']]['name']} and {F[sw['b']]['name']} needs your approval")
            self.log(user, f"{'Agreed to' if approve else 'Declined'} swap {sid}")
            self._save()
            return sw

    def _can_head(self, user, sw):
        if sw["status"] != "waiting_head":
            return False
        if user["role"] == "admin":
            return True
        return user["role"] == "department_coordinator" and any(
            h["head_role"] == "department_coordinator" and h["dept"] == user.get("department") and h["status"] == "waiting" for h in sw["heads"])

    def decide_swap(self, user, sid, approve, reason=""):
        with self.lock:
            sw = self._swap(sid)
            if not self._can_head(user, sw):
                raise PermissionError("This swap is not waiting for you")
            _, F, _ = self._lookups()
            now = self._now()
            if not approve:
                sw["status"], sw["reason"] = "rejected", reason
                sw["history"].append({"at": now, "text": f"{user['name']} turned it down" + (f": {reason}" if reason else "")})
                for e in (sw["by"], fac_email(sw["b"])):
                    self.notify(e, f"Swap {sw['id']} was turned down by {user['name']}" + (f": {reason}" if reason else ""))
                self.log(user, f"Rejected swap {sid}")
                self._save()
                return sw
            for h in sw["heads"]:
                if h["status"] == "waiting" and (user["role"] == "admin" or (h["head_role"] == "department_coordinator" and h["dept"] == user.get("department"))):
                    h.update(status="approved", by=user["email"], by_name=user["name"], at=now)
            sw["history"].append({"at": now, "text": f"{user['name']} approved"})
            if all(h["status"] == "approved" for h in sw["heads"]):
                self._apply_swap(user, sw)
            self.log(user, f"Approved swap {sid}")
            self._save()
            return sw

    def _apply_swap(self, user, sw):
        _, F, _ = self._lookups()
        now = self._now()
        chk = self.swap_check(sw["give"], sw["take"], sw.get("week"))
        if not chk["ok"]:
            sw["status"], sw["reason"] = "failed", "; ".join(chk["problems"])
            sw["history"].append({"at": now, "text": "Not applied, the timetable changed: " + sw["reason"]})
            for e in (sw["by"], fac_email(sw["b"])):
                self.notify(e, f"Swap {sw['id']} could not be applied because the timetable changed")
            return
        if sw.get("scope") == "day":              # one day only: the weekly timetable and exports stay as they are
            sw["status"], sw["decided_at"] = "approved", now
            wa = self.week_assign(sw["week"])
            dates = f"{self.pretty_date(self.week_date(sw['week'], wa[sw['give']][0]))} and {self.pretty_date(self.week_date(sw['week'], wa[sw['take']][0]))}"
            sw["history"].append({"at": now, "text": f"Applied for {dates} only. Every other week stays the same"})
            for e in (sw["by"], fac_email(sw["b"])):
                self.notify(e, f"Swap {sw['id']} is approved for {dates} only")
            return
        before = official.run(self.validation_data(), self.export_schedule(), None)["hard_violation_count"]
        dis = {"id": sw["id"], "changes": [{"type": "swap_faculty", "session_a": sw["give"], "faculty_a": sw["a"],
                                            "session_b": sw["take"], "faculty_b": sw["b"]}]}
        ctx = self._undo_open()
        old = self.data
        new = repair_mod.apply_disruption(self.data, dis)
        new["booking_requests"], new["cancellations"] = old["booking_requests"], old["cancellations"]
        self.data = new
        after = official.run(self.validation_data(), self.export_schedule(), None)["hard_violation_count"]
        if after > before:
            self.data = old
            sw["status"], sw["reason"] = "failed", "The official checker found a clash, so nothing was changed"
            sw["history"].append({"at": now, "text": sw["reason"]})
            return
        self.applied.append(dis)
        self._undo_close("swap", sw["id"], ctx, user, after)
        sw["status"], sw["decided_at"] = "approved", now
        sw["history"].append({"at": now, "text": "Applied to the timetable"})
        for e in (sw["by"], fac_email(sw["b"])):
            self.notify(e, f"Swap {sw['id']} is approved and now in the timetable")
        self.write_exports()

    def undo_swap(self, user, sid, reason=""):
        with self.lock:
            sw = self._swap(sid)
            if sw["status"] != "approved":
                raise ValueError("Only an approved swap can be undone")
            _, F, _ = self._lookups()
            now = self._now()
            if sw.get("scope") == "day":              # one week only: nothing in the weekly timetable to put back
                if user["role"] != "admin":
                    raise PermissionError("Only the Dean's office can undo a swap")
                check = {"hard": None, "soft": None, "classes_restored": 2}
            else:
                check = self._undo_restore(user, "swap", sid)
            sw["status"] = "undone"
            sw["undone"] = {"by": user["email"], "by_name": user["name"], "at": now, "reason": reason, "check": check}
            sw["history"].append({"at": now, "text": f"Undone by {user['name']}. Both classes are back with their usual teachers" + (f": {reason}" if reason else "")})
            for e in (sw["by"], fac_email(sw["b"])):
                self.notify(e, f"Swap {sw['id']} was undone by {user['name']}")
            self.log(user, f"Undid swap {sid}")
            self._save()
            if sw.get("scope") != "day":
                self.write_exports()
            return sw

    def cancel_swap(self, user, sid):
        with self.lock:
            sw = self._swap(sid)
            if sw["by"] != user["email"]:
                raise PermissionError("Only the teacher who asked can withdraw it")
            if sw["status"] not in OPEN:
                raise ValueError("This request is already closed")
            sw["status"] = "cancelled"
            sw["history"].append({"at": self._now(), "text": "Withdrawn by the teacher who asked"})
            self.notify(fac_email(sw["b"]), f"Swap {sw['id']} was withdrawn")
            self._save()
            return sw

    def _swap(self, sid):
        sw = next((w for w in self.swaps if w["id"] == sid), None)
        if not sw:
            raise KeyError(sid)
        return sw

    def swap_view(self, sw, user):
        S, F, _ = self._lookups()
        wk = sw.get("week") if sw.get("scope") == "day" else None
        try:
            give, take = self._slot_of(sw["give"], wk), self._slot_of(sw["take"], wk)
            if wk and sw["status"] == "approved":      # show them as they were before the swap
                give["faculty_id"], take["faculty_id"] = sw["a"], sw["b"]
        except KeyError:
            give = take = None
        # After approval the classes belong to the other teacher, so show who held them when it was asked
        return {**sw, "a_name": F[sw["a"]]["name"], "b_name": F[sw["b"]]["name"], "a_dept": F[sw["a"]]["department"], "b_dept": F[sw["b"]]["department"],
                "give_slot": give, "take_slot": take,
                "mine": sw["by"] == user["email"], "for_me": user["role"] == "faculty" and user.get("faculty_id") == sw["b"],
                "can_respond": user["role"] == "faculty" and user.get("faculty_id") == sw["b"] and sw["status"] == "waiting_teacher",
                "can_decide": self._can_head(user, sw), "can_cancel": sw["by"] == user["email"] and sw["status"] in OPEN,
                "can_undo": sw["status"] == "approved" and user["role"] == "admin" and (sw.get("scope") == "day" or self.can_undo(user, "swap", sw["id"])),
                "undo_blocked": sw["status"] == "approved" and sw.get("scope") != "day" and user["role"] == "admin" and not self.can_undo(user, "swap", sw["id"])}

    def list_swaps(self, user):
        out = []
        for sw in reversed(self.swaps):
            if user["role"] == "admin":
                pass
            elif user["role"] == "faculty":
                if user["email"] != sw["by"] and user.get("faculty_id") != sw["b"]:
                    continue
            elif user["role"] == "department_coordinator":
                if not any(h["head_role"] == "department_coordinator" and h["dept"] == user.get("department") for h in sw["heads"]):
                    continue
                if sw["status"] == "waiting_teacher":
                    continue
            else:
                continue
            out.append(self.swap_view(sw, user))
        return out

    # ------------------------------------------------------------------ online guest lectures
    def _clean_online(self, f):
        errs = []
        title = (f.get("title") or "").strip()
        speaker = (f.get("speaker") or "").strip()
        if not title:
            errs.append("Give the lecture a title")
        if not speaker:
            errs.append("Say who is speaking")
        try:
            week = int(f.get("week"))
        except (TypeError, ValueError):
            week = 0
        if not 1 <= week <= self.sem["weeks"]:
            errs.append(f"Week must be between 1 and {self.sem['weeks']}")
        day = f.get("day")
        if day not in DAYS:
            errs.append("Pick a day")
        start, end = f.get("start") or "", f.get("end") or ""
        if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end):
            errs.append("Set a start and end time")
        else:
            if mins(end) <= mins(start):
                errs.append("The end time must be after the start time")
            elif mins(end) - mins(start) > 240:
                errs.append("An online lecture can run for at most 4 hours")
            if mins(start) < 7 * 60 or mins(end) > 22 * 60:
                errs.append("Times must be between 07:00 and 22:00")
        link = (f.get("link") or "").strip()
        u = urlparse(link)
        if u.scheme not in ("http", "https") or not u.hostname or len(link) > 400 or " " in link:
            errs.append("Paste the full meeting link, starting with https://")
        groups = [g for g in (f.get("groups") or [])]
        known = {g["id"] for g in self.data["student_groups"]}
        if not groups:
            errs.append("Choose who should attend")
        elif any(g not in known for g in groups):
            errs.append("One of the student groups is not known")
        clean = {"title": title[:120], "speaker": speaker[:80], "org": (f.get("org") or "").strip()[:80], "week": week, "day": day,
                 "start": start, "end": end, "link": link, "platform": detect_platform(link) if link else "", "groups": sorted(set(groups)),
                 "notes": (f.get("notes") or "").strip()[:400]}
        return clean, errs

    def online_clashes(self, c, exclude=None):
        S, F, C = self._lookups()
        out = []
        if not c["day"] or not c["start"] or not c["end"] or mins(c["end"]) <= mins(c["start"]) or not c["groups"]:
            return out
        a, b = mins(c["start"]), mins(c["end"])
        sel = set(c["groups"])
        if c["week"] == self.sem["exam_week"]:
            ex_by = {e["id"]: e for e in self.data.get("exams", [])}
            times = {x["id"]: x for x in self.data["calendar"]["exam_week"]["sessions"]}
            for r in self.exams:
                e = ex_by.get(r["exam_id"])
                t = times.get(r["session"])
                if e and t and r["day"] == c["day"] and sel & set(e["groups"]) and a < mins(t["end"]) and mins(t["start"]) < b:
                    out.append(f"Exam {', '.join(e['course_ids'])} for {', '.join(sorted(sel & set(e['groups'])))}, {t['start']} to {t['end']}")
        else:
            for sid, (d, st, _r) in self.week_assign(c["week"]).items():
                s = S.get(sid)
                if not s or d != c["day"] or not sel & set(s["groups"]):
                    continue
                s0, s1 = mins(SLOT_LABEL[st]), mins(END_LABEL[st + s["duration"] - 1])
                if a < s1 and s0 < b:
                    out.append(f"{s['course_id']} {s['kind']} for {', '.join(sorted(sel & set(s['groups'])))}, {SLOT_LABEL[st]} to {END_LABEL[st + s['duration'] - 1]}")
        for o in self.online:
            if o["id"] == exclude or o["status"] not in ("scheduled", "waiting"):
                continue
            if o["week"] == c["week"] and o["day"] == c["day"] and sel & set(o["groups"]) and a < mins(o["end"]) and mins(o["start"]) < b:
                out.append(f"Online lecture {o['id']} \"{o['title']}\" for {', '.join(sorted(sel & set(o['groups'])))}, {o['start']} to {o['end']}")
        return out

    def check_online(self, form, exclude=None):
        c, errs = self._clean_online(form)
        clashes = self.online_clashes(c, exclude) if not any(e for e in errs if "time" in e or "day" in e.lower() or "Week" in e or "attend" in e) else []
        return {"errors": errs, "clashes": clashes, "ok": not errs and not clashes, "platform": c["platform"]}

    def create_online(self, user, form):
        with self.lock:
            if user["role"] not in ("admin", "department_coordinator", "faculty"):
                raise PermissionError("Your role cannot schedule guest lectures")
            c, errs = self._clean_online(form)
            if errs:
                raise ValueError(". ".join(errs))
            clashes = self.online_clashes(c)
            if clashes:
                raise ValueError("Students have something else then: " + "; ".join(clashes))
            rec = {"id": f"OL-{len(self.online) + 1:02d}", **c, "by": user["email"], "by_name": user["name"], "role": user["role"], "at": self._now(),
                   "status": "scheduled" if user["role"] == "admin" else "waiting", "reason": ""}
            self.online.append(rec)
            if rec["status"] == "waiting":
                for u in self.users.values():
                    if u["role"] == "admin":
                        self.notify(u["email"], f"Online guest lecture {rec['id']} \"{rec['title']}\" from {user['name']} needs approval")
            self.log(user, f"Scheduled online lecture {rec['id']}")
            self._save()
            return rec

    def decide_online(self, user, oid, approve, reason=""):
        with self.lock:
            if user["role"] != "admin":
                raise PermissionError("Only the Dean's office approves online guest lectures")
            rec = self._online(oid)
            if rec["status"] != "waiting":
                raise ValueError("Already decided")
            if rec["by"] == user["email"]:
                raise PermissionError("Nobody approves their own request")
            if approve:
                clashes = self.online_clashes({k: rec[k] for k in ("week", "day", "start", "end", "groups")}, exclude=oid)
                if clashes:
                    raise ValueError("Students now have something else then: " + "; ".join(clashes))
                rec["status"] = "scheduled"
            else:
                rec["status"], rec["reason"] = "rejected", reason
            rec["decided_by"] = user["email"]
            self.notify(rec["by"], f"Online lecture {oid} was {'approved' if approve else 'turned down'}" + (f": {reason}" if reason and not approve else ""))
            self.log(user, f"{'Approved' if approve else 'Rejected'} online lecture {oid}")
            self._save()
            return rec

    def cancel_online(self, user, oid):
        with self.lock:
            rec = self._online(oid)
            if user["role"] != "admin" and rec["by"] != user["email"]:
                raise PermissionError("Only the person who scheduled it or the Dean's office can cancel")
            if rec["status"] in ("cancelled", "rejected"):
                raise ValueError("Already closed")
            rec["status"] = "cancelled"
            if rec["by"] != user["email"]:
                self.notify(rec["by"], f"Online lecture {oid} was cancelled by {user['name']}")
            self.log(user, f"Cancelled online lecture {oid}")
            self._save()
            return rec

    def _online(self, oid):
        r = next((o for o in self.online if o["id"] == oid), None)
        if not r:
            raise KeyError(oid)
        return r

    def list_online(self, user):
        out = []
        order = {d: i for i, d in enumerate(DAYS)}
        for o in sorted(self.online, key=lambda o: (o["week"], order[o["day"]], o["start"])):
            if o["status"] in ("waiting", "rejected") and user["role"] != "admin" and o["by"] != user["email"]:
                continue
            out.append({**o, "own": o["by"] == user["email"],
                        "can_decide": user["role"] == "admin" and o["status"] == "waiting" and o["by"] != user["email"],
                        "can_cancel": o["status"] in ("scheduled", "waiting") and (user["role"] == "admin" or o["by"] == user["email"])})
        return out


# ====================================================================== extra classes in exam week
class ExtraMixin:
    """A teacher asks for an extra or revision class in exam week, at any time up to 22:00.
    The only hard rule is the exams themselves: the students' own exams and the rooms exams use.
    Everything else is a soft rule: it adds to a score and shows as a warning the head can read."""

    def _exam_times(self):
        return {x["id"]: (mins(x["start"]), mins(x["end"]), x["start"], x["end"]) for x in self.data["calendar"]["exam_week"]["sessions"]}

    def _extra_form(self, f, user):
        S, F, C = self._lookups()
        errs = []
        sess = S.get(f.get("session_id") or "")
        if not sess or sess["faculty_id"] != user.get("faculty_id"):
            errs.append("Pick one of your own classes")
        day = f.get("day")
        if day not in self.data["calendar"]["exam_week"]["days"]:
            errs.append("Pick a day")
        start, end = f.get("start") or "", f.get("end") or ""
        a = b = 0
        if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end):
            errs.append("Set a start and end time")
        else:
            a, b = mins(start), mins(end)
            if b <= a:
                errs.append("The end time must be after the start time")
            elif b - a > 240:
                errs.append("An extra class can run for at most 4 hours")
            if a < 7 * 60 or b > 22 * 60:
                errs.append("Times must be between 07:00 and 22:00")
        try:
            size = int(f.get("size") or (sess or {}).get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        if sess and not 1 <= size <= 1000:
            errs.append("Say how many students will come")
        clean = {"session_id": (sess or {}).get("id"), "course_id": (sess or {}).get("course_id"), "groups": (sess or {}).get("groups", []),
                 "faculty_id": (sess or {}).get("faculty_id"), "day": day, "start": start, "end": end, "a": a, "b": b, "size": size,
                 "room": (f.get("room") or "").strip() or None, "topic": (f.get("topic") or "").strip()[:200]}
        return clean, errs, sess

    def _extra_hard(self, c, exclude=None):
        """Exams only. Returns plain sentences."""
        hard = []
        if not c["day"] or c["b"] <= c["a"]:
            return hard
        ex_by = {e["id"]: e for e in self.data.get("exams", [])}
        times = self._exam_times()
        for r in self.exams:
            e, t = ex_by.get(r["exam_id"]), times.get(r["session"])
            if not e or not t or r["day"] != c["day"] or not (c["a"] < t[1] and t[0] < c["b"]):
                continue
            both = sorted(set(c["groups"]) & set(e["groups"]))
            if both:
                hard.append(f"{', '.join(both)} {'has' if len(both) == 1 else 'have'} the {', '.join(e['course_ids'])} exam then ({t[2]} to {t[3]})")
            if c.get("room") and c["room"] in r["rooms"]:
                hard.append(f"{c['room']} is used for the {', '.join(e['course_ids'])} exam then ({t[2]} to {t[3]})")
        return hard

    def _extra_soft(self, c, sess, exclude=None):
        S, F, C = self._lookups()
        out = []
        fac = F.get(c["faculty_id"], {})
        a, b, day = c["a"], c["b"], c["day"]
        rooms = {r["id"]: r for r in self.data["rooms"]}
        for x in self.extras:
            if x["id"] == exclude or x["status"] not in ("waiting", "approved") or x["day"] != day or not (a < x["b"] and x["a"] < b):
                continue
            if x["faculty_id"] == c["faculty_id"]:
                out.append((f"You already have extra class {x['id']} then", 5))
            if set(x["groups"]) & set(c["groups"]):
                out.append((f"{', '.join(sorted(set(x['groups']) & set(c['groups'])))} already have extra class {x['id']} then", 3))
            if c.get("room") and x["room"] == c["room"]:
                out.append((f"{c['room']} is already asked for by extra class {x['id']} then", 5))
        for o in self.online:
            if o["status"] in ("scheduled", "waiting") and o["week"] == self.sem["exam_week"] and o["day"] == day and set(o["groups"]) & set(c["groups"]) \
                    and a < mins(o["end"]) and mins(o["start"]) < b:
                out.append((f"Online lecture {o['id']} is on for the same students then", 2))

        def span(p):
            return mins(SLOT_LABEL[p]), mins(END_LABEL[p])
        for u in fac.get("unavailable", []):
            if u["day"] == day and any(a < span(p)[1] and span(p)[0] < b for p in u["periods"]):
                out.append((f"{fac['name']} has marked this time as away" + (f" ({u['reason']})" if u.get("reason") else ""), 3)); break
        for pref in fac.get("preferences", []):
            if pref.get("type") == "avoid" and day in pref.get("days", []) and any(a < span(p)[1] and span(p)[0] < b for p in pref["periods"]):
                out.append((f"Preference: {pref.get('note', 'would rather not teach then')}", 2)); break
        hours = (b - a) + sum(x["b"] - x["a"] for x in self.extras if x["id"] != exclude and x["status"] in ("waiting", "approved") and x["faculty_id"] == c["faculty_id"] and x["day"] == day)
        if hours > fac.get("max_hours_per_day", 4) * 60:
            out.append((f"{fac.get('name', 'The teacher')} would teach {hours / 60:g} hours that day, the usual limit is {fac.get('max_hours_per_day', 4)}", 2))
        if a < 14 * 60 and b > 13 * 60:
            out.append(("It runs into the lunch hour", 1))
        if b > 21 * 60:
            out.append(("It ends after 21:00", 2))
        elif b > 19 * 60:
            out.append(("It ends after 19:00", 1))
        if b - a > 180:
            out.append(("It is longer than 3 hours", 1))
        rm = rooms.get(c.get("room") or "")
        if rm:
            if rm["capacity"] < c["size"]:
                out.append((f"{rm['id']} seats {rm['capacity']}, fewer than the {c['size']} students", 4))
            if "lecture" not in rm["allowed_uses"] and "tutorial" not in rm["allowed_uses"]:
                out.append((f"{rm['id']} is not normally used for classes", 3))
            if sess and sess.get("needs_accessible") and not rm["accessible"]:
                out.append((f"{rm['id']} is not step-free and this class needs a step-free room", 4))
            if sess and sess.get("room_types") and rm["type"] not in sess["room_types"]:
                out.append((f"This class is usually in a {' or '.join(sess['room_types'][:2]).replace('_', ' ')}, {rm['id']} is a {rm['type'].replace('_', ' ')}", 1))
            for u in self.data.get("room_unavailability", []):
                if u["room_id"] == rm["id"] and u["day"] == day and any(a < span(p)[1] and span(p)[0] < b for p in u["periods"]):
                    out.append((f"{rm['id']} is closed then ({u.get('reason', 'closed')})", 3)); break
        return out

    @staticmethod
    def _level(pts):
        return "none" if pts == 0 else "minor" if pts <= 3 else "some" if pts <= 8 else "many"

    def check_extra(self, user, form, exclude=None):
        c, errs, sess = self._extra_form(form, user)
        res = {"errors": errs, "hard": [], "soft": [], "penalty": 0, "level": "none", "rooms": [], "exams": []}
        if errs and (not c["session_id"] or not c["day"] or c["b"] <= c["a"]):
            return {**res, "ok": False}
        res["hard"] = self._extra_hard(c, exclude)
        soft = self._extra_soft(c, sess, exclude)
        res["soft"] = [{"text": t, "pts": p} for t, p in soft]
        res["penalty"] = sum(p for _, p in soft)
        res["level"] = self._level(res["penalty"])
        # context: exams those students have that day
        ex_by = {e["id"]: e for e in self.data.get("exams", [])}
        times = self._exam_times()
        for r in self.exams:
            e, t = ex_by.get(r["exam_id"]), times.get(r["session"])
            if e and t and r["day"] == c["day"] and set(c["groups"]) & set(e["groups"]):
                res["exams"].append(f"{', '.join(e['course_ids'])} exam, {r['session']}, {t[2]} to {t[3]}")
        # rooms ranked by how few soft issues they bring, exam rooms left out
        sug = []
        for r in self.data["rooms"]:
            if r["id"] == "OAT":
                continue
            cc = {**c, "room": r["id"]}
            if self._extra_hard(cc, exclude):
                continue
            s = self._extra_soft(cc, sess, exclude)
            sug.append({"id": r["id"], "name": r["name"], "capacity": r["capacity"], "type": r["type"], "penalty": sum(p for _, p in s),
                        "issues": [t for t, _ in s if r["id"] in t or "seats" in t]})
        sug.sort(key=lambda x: (x["penalty"], abs(x["capacity"] - c["size"])))
        res["rooms"] = sug[:8]
        res["ok"] = not errs and not res["hard"]
        return res

    def _extra_head(self, course_id):
        dept = next((x["department"] for x in self.data["courses"] if x["id"] == course_id), "")
        email = f"coordinator.{dept.lower()}@cit.example"
        return dept, (email if email in self.users else None)

    def create_extra(self, user, form):
        with self.lock:
            if user["role"] != "faculty":
                raise PermissionError("Only teachers ask for extra classes")
            if not self.generated:
                raise ValueError("The timetable has not been generated yet")
            c, errs, sess = self._extra_form(form, user)
            if not c["topic"]:
                errs.append("Say what the class is for")
            if errs:
                raise ValueError(". ".join(errs))
            res = self.check_extra(user, form)
            if not c["room"]:
                if not res["rooms"]:
                    raise ValueError("No room is free of exams at that time")
                c["room"] = res["rooms"][0]["id"]
                form = {**form, "room": c["room"]}
                res = self.check_extra(user, form)
            if res["hard"]:
                raise ValueError("Exams come first: " + "; ".join(res["hard"]))
            dept, _ = self._extra_head(c["course_id"])
            C = {x["id"]: x for x in self.data["courses"]}
            rec = {"id": f"XC-{len(self.extras) + 1:02d}", **c, "title": C[c["course_id"]]["title"], "week": self.sem["exam_week"], "dept": dept,
                   "by": user["email"], "by_name": user["name"], "at": self._now(), "status": "waiting", "reason": "",
                   "warnings": res["soft"], "penalty": res["penalty"], "level": res["level"]}
            self.extras.append(rec)
            for u in self.users.values():
                if u["role"] == "admin" or (u["role"] == "department_coordinator" and u.get("department") == dept):
                    self.notify(u["email"], f"{user['name']} asks for an extra class {rec['id']} in exam week ({rec['course_id']}, {DAYF[rec['day']]} {rec['start']} to {rec['end']})")
            self.log(user, f"Asked for extra class {rec['id']}")
            self._save()
            return rec

    def _can_head_extra(self, user, x):
        return x["status"] == "waiting" and (user["role"] == "admin" or (user["role"] == "department_coordinator" and user.get("department") == x["dept"]))

    def decide_extra(self, user, xid, approve, reason=""):
        with self.lock:
            x = self._extra(xid)
            if not self._can_head_extra(user, x):
                raise PermissionError("This request is not waiting for you")
            if approve:
                hard = self._extra_hard(x, exclude=xid)
                if hard:
                    raise ValueError("Exams now come in the way: " + "; ".join(hard))
                x["status"] = "approved"
                res = self._extra_soft(x, None, exclude=xid)
                x["warnings"], x["penalty"] = [{"text": t, "pts": p} for t, p in res], sum(p for _, p in res)
                x["level"] = self._level(x["penalty"])
            else:
                x["status"], x["reason"] = "declined", reason
            x["decided_by"] = user["name"]
            self.notify(x["by"], f"Extra class {xid} was {'approved' if approve else 'turned down'} by {user['name']}" + (f": {reason}" if reason and not approve else ""))
            self.log(user, f"{'Approved' if approve else 'Declined'} extra class {xid}")
            self._save()
            return x

    def cancel_extra(self, user, xid):
        with self.lock:
            x = self._extra(xid)
            if x["by"] != user["email"] and user["role"] != "admin":
                raise PermissionError("Only the teacher who asked can cancel")
            if x["status"] not in ("waiting", "approved"):
                raise ValueError("Already closed")
            x["status"] = "cancelled"
            self.log(user, f"Cancelled extra class {xid}")
            self._save()
            return x

    def _extra(self, xid):
        x = next((e for e in self.extras if e["id"] == xid), None)
        if not x:
            raise KeyError(xid)
        return x

    def list_extras(self, user):
        order = {d: i for i, d in enumerate(DAYS)}
        out = []
        for x in sorted(self.extras, key=lambda x: (x["status"] != "waiting", order.get(x["day"], 9), x["start"])):
            if user["role"] == "faculty" and x["by"] != user["email"]:
                continue
            if user["role"] == "department_coordinator" and x["dept"] != user.get("department"):
                continue
            if user["role"] not in ("admin", "department_coordinator", "faculty"):
                continue
            out.append({**x, "own": x["by"] == user["email"], "can_decide": self._can_head_extra(user, x),
                        "can_cancel": x["status"] in ("waiting", "approved") and (x["by"] == user["email"] or user["role"] == "admin")})
        return out

    def approved_extras(self, week):
        return [x for x in self.extras if x["status"] == "approved" and x["week"] == week]
