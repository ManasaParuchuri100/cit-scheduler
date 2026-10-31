"""Application state: users, timetable, bookings, changes, audit. One JSON file on disk."""
import copy
import datetime as dt
import json
import os
import re
import secrets
import threading
import time
from collections import defaultdict

import validator as official
from .data import load_dataset, DATA_DIR
from .engine import generate_all, to_schedule
from .bookings import (decide_batch, effective_category, rank_key, room_ok_for, free_for, Occupancy,
                       reservations_for, why_not, pretty, MAX_PERIOD, END_LABEL)
from .exams import schedule_exams
from .repair import repair
from . import repair as repair_mod
from .explain import Board, slot_table, why_here
from .timetable import Problem
from .collab import CollabMixin, ExtraMixin

STATE_PATH = os.environ.get("CIT_STATE", os.path.join(os.path.dirname(DATA_DIR), "var", "state.json"))
SEM = {"weeks": 16, "fest_week": 7, "exam_week": 9}
LAB_DEPT = {"lab_cs": ["CSE"], "lab_elec": ["ECE", "EE"], "lab_phy": ["PH"], "workshop": ["ME"], "lab_civil": ["CE"]}
PERIOD_START = {1: "08:00", 2: "09:00", 3: "10:00", 4: "11:00", 5: "12:00", 6: "14:00", 7: "15:00", 8: "16:00", 9: "17:00",
                10: "18:00", 11: "19:00", 12: "20:00", 13: "21:00"}
ROLE_LABEL = {"admin": "Admin", "department_coordinator": "Department coordinator", "faculty": "Faculty", "club": "Club representative"}
TABS = {
    "admin": ["overview", "timetable", "rooms", "bookings", "changes", "swaps", "exams"],
    "department_coordinator": ["overview", "timetable", "rooms", "bookings", "changes", "swaps"],
    "faculty": ["overview", "timetable", "swaps", "requests"],
    "club": ["overview", "rooms", "newrequest", "myrequests"],
}
PRIORITY_LABEL = {"exam": "Exams", "regular_session": "Regular classes", "institute_event": "Institute events",
                  "guest_lecture": "Guest lectures", "department_event": "Department events", "club_event": "Club events"}
ROLE_RANK = {"admin": None, "department_coordinator": "department_event", "faculty": "regular_session", "club": "club_event"}


BOOK_KEYS = ("request_id", "status", "day", "start_period", "end_period", "room_id", "reason")


def slug(name):
    s = re.sub(r"\b(club|society|cell|team|the|office|of)\b", " ", name.lower())
    s = re.sub(r"[^a-z0-9]+", " ", s).split()
    return s[0] if s else "club"


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Store(CollabMixin, ExtraMixin):
    _now = staticmethod(lambda: now())

    def __init__(self, path=STATE_PATH):
        self.path = path
        self.lock = threading.RLock()
        self.tokens = {}
        self.job = {"state": "idle", "message": ""}
        if os.path.exists(path):
            try:
                self._load()
                return
            except Exception:
                pass
        if self.load_seed():                         # first start: begin with the ready-made timetable
            return
        self.reset()

    def load_seed(self):
        """Load the timetable, exams and booking decisions made earlier, so nobody has to wait for the solver."""
        seed = os.path.join(DATA_DIR, "seed_state.json")
        if not os.path.exists(seed) or self.path == seed:
            return False
        keep, toks = self.path, dict(self.tokens)
        self.path = seed
        try:
            self._load()
        except Exception:
            self.path = keep
            return False
        self.path, self.tokens = keep, toks
        self.job = {"state": "idle", "message": ""}
        self._save()
        self.write_exports()
        return True

    # ------------------------------------------------------------------ persistence
    def _upload_path(self):
        return os.path.join(os.path.dirname(self.path), "dataset.json")

    def _dataset(self):
        """The dataset an Admin loaded, if any, otherwise the bundled one."""
        up = self._upload_path()
        if os.path.exists(up):
            try:
                return json.load(open(up, encoding="utf-8"))
            except Exception:
                os.remove(up)
        return load_dataset()

    DATASET_KEYS = ("calendar", "priority_order", "role_category_cap", "rooms", "room_unavailability", "faculty",
                    "student_groups", "courses", "sessions", "booking_requests")

    def load_uploaded_dataset(self, user, blob):
        """Replace the dataset (same format as cit_public.json). Everything built so far is cleared."""
        if user["role"] != "admin":
            raise PermissionError("Only the Dean's office can load a dataset")
        if not isinstance(blob, dict):
            raise ValueError("That is not a dataset file")
        miss = [k for k in self.DATASET_KEYS if k not in blob]
        if miss:
            raise ValueError("The file is missing: " + ", ".join(miss))
        blob.setdefault("cancellations", [])
        blob.setdefault("exams", [])
        for need_, lst in (("rooms", ("id", "capacity", "type", "allowed_uses")), ("sessions", ("id", "faculty_id", "groups", "duration")),
                           ("faculty", ("id", "name")), ("student_groups", ("id",))):
            for row in blob[need_][:5]:
                bad = [k for k in lst if k not in row]
                if bad:
                    raise ValueError(f"A row in {need_} is missing {', '.join(bad)}")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self._upload_path(), "w", encoding="utf-8") as f:
            json.dump(blob, f)
        self.reset(keep_upload=True)
        self.log(user, f"Loaded a dataset: {len(blob['sessions'])} sessions, {len(blob['rooms'])} rooms, {len(blob['faculty'])} teachers")
        self._save()
        return {"sessions": len(blob["sessions"]), "rooms": len(blob["rooms"]), "faculty": len(blob["faculty"]), "groups": len(blob["student_groups"]),
                "requests": len(blob["booking_requests"])}

    def reset(self, keep_upload=False):
        with self.lock:
            if not keep_upload and os.path.exists(self._upload_path()):
                os.remove(self._upload_path())
            d = self._dataset()
            self.base_data = copy.deepcopy(d)           # untouched dataset
            self.data = d                              # current (changes applied)
            self.sem = dict(SEM)
            self.current_week = 3
            self.users = self._make_users(d)
            self.archive = {"requests": [], "decisions": {}}
            self.undo = []              # snapshots taken before each applied change, newest last
            self.requests = []
            for r in d["booking_requests"]:
                rr = dict(r)
                rr["week"] = SEM["fest_week"]
                rr["owner"] = self._owner_for(rr)
                self.requests.append(rr)
            self.cancel_log = list(d.get("cancellations", []))
            self.assign = {}            # permanent weekly timetable (current)
            self.baseline = {}          # as first generated (for stability / schedule_after)
            self.reservations = {"rooms": [], "groups": []}
            self.exams = []
            self.decisions = {}         # request id -> decision with state
            self.changes = []
            self.swaps = []             # class swaps between teachers
            self.online = []            # online guest lectures
            self.extras = []            # extra classes asked for in exam week
            self.applied = []           # disruption dicts already applied
            self.audit = []
            self.notes = defaultdict(list)
            self.generated = False
            self.baseline_book = None
            self.job = {"state": "idle", "message": ""}
            self._save()

    def _make_users(self, d):
        users = {}
        def add(email, name, role, **kw):
            users[email] = {"email": email, "name": name, "role": role, **kw}
        add("dean@cit.example", "Dean's office", "admin")
        add("registrar@cit.example", "Registrar's office", "admin")
        for dept in ("CSE", "ECE", "EE", "ME", "CE"):
            add(f"coordinator.{dept.lower()}@cit.example", f"{dept} coordinator", "department_coordinator", department=dept)
        for f in d["faculty"]:
            if f["department"] != "ADMIN":
                add(f"faculty.{f['id'].lower()}@cit.example", f["name"], "faculty", department=f["department"], faculty_id=f["id"])
        for r in d["booking_requests"]:
            if r["role"] == "club":
                add(f"club.{slug(r['requester'])}@cit.example", r["requester"], "club")
        return users

    def _owner_for(self, r):
        role = r["role"]
        if role == "club":
            return f"club.{slug(r['requester'])}@cit.example"
        if role == "department_coordinator":
            return f"coordinator.{(r['department'] or 'cse').lower()}@cit.example"
        if role == "faculty":
            m = re.search(r"\((F\d+)\)", r["requester"])
            if m:
                return f"faculty.{m.group(1).lower()}@cit.example"
        return "dean@cit.example"

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        blob = {"sem": self.sem, "current_week": self.current_week, "requests": self.requests,
                "cancel_log": self.cancel_log, "assign": self.assign, "baseline": self.baseline,
                "reservations": self.reservations, "exams": self.exams, "decisions": self.decisions,
                "changes": self.changes, "applied": self.applied, "audit": self.audit[-500:], "baseline_book": self.baseline_book,
                "notes": dict(self.notes), "generated": self.generated, "swaps": self.swaps, "online": self.online, "extras": self.extras, "archive": self.archive, "undo": self.undo}
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(blob, f)
        os.replace(tmp, self.path)

    def _load(self):
        b = json.load(open(self.path))
        d = self._dataset()
        self.base_data = copy.deepcopy(d)
        self.sem, self.current_week = b["sem"], b["current_week"]
        self.requests, self.cancel_log = b["requests"], b["cancel_log"]
        self.assign = {k: tuple(v) for k, v in b["assign"].items()}
        self.baseline = {k: tuple(v) for k, v in b["baseline"].items()}
        self.reservations = b["reservations"]
        self.exams, self.decisions = b["exams"], b["decisions"]
        self.changes, self.applied, self.audit = b["changes"], b["applied"], b["audit"]
        self.baseline_book = b.get("baseline_book")
        self.notes = defaultdict(list, b["notes"])
        self.generated = b["generated"]
        self.swaps, self.online, self.extras = b.get("swaps", []), b.get("online", []), b.get("extras", [])
        self.archive = b.get("archive") or {"requests": [], "decisions": {}}
        self.undo = b.get("undo") or []
        data = d
        for dis in self.applied:
            data = repair_mod.apply_disruption(data, dis)
        data["cancellations"] = list(self.cancel_log)
        self.data = data
        self._sync_requests()
        self.users = self._make_users(d)
        self.tokens = {}

    def _sync_requests(self):
        self.data["booking_requests"] = [{k: v for k, v in r.items() if k not in ("week", "owner")} for r in self.requests]
        self.data["cancellations"] = list(self.cancel_log)

    def log(self, user, what):
        self.audit.append({"at": now(), "by": user["email"] if user else "system", "what": what})

    def notify(self, email, text):
        self.notes[email].append({"at": now(), "text": text, "read": False})

    # ------------------------------------------------------------------ auth
    def login(self, email, password):
        u = self.users.get(email.strip().lower())
        if not u or password != "demo":
            return None
        tok = secrets.token_hex(16)
        self.tokens[tok] = u["email"]
        return tok, u

    def user_for(self, token):
        e = self.tokens.get(token)
        return self.users.get(e) if e else None

    # ------------------------------------------------------------------ week views
    def week_overrides(self, w):
        out = []
        for d in self.decisions.values():
            if d.get("state") == "published" and d.get("week") == w:
                out += d.get("overrides", [])
        return out

    def week_assign(self, w):
        a = dict(self.assign)
        for o in self.week_overrides(w):
            a[o["session_id"]] = (o["day"], o["start_period"], o["room_id"])
        return a

    def week_decisions(self, w, states=("published", "proposed")):
        return [d for d in self.decisions.values() if d.get("week") == w and d.get("state") in states]

    # ------------------------------------------------------------------ generate
    def generate(self, user, tt_time=45):
        with self.lock:
            self.job = {"state": "running", "message": "Building the weekly timetable"}
        try:
            r = generate_all(self.data, tt_time=tt_time, log=lambda m: self._job_msg(m))
            with self.lock:
                if r is None:
                    self.job = {"state": "error", "message": "No timetable satisfies every rule with the current data"}
                    return
                self.assign = {k: tuple(v) for k, v in r["assign"].items()}
                self.baseline = dict(self.assign)
                self.reservations = r["reservations"]
                self.exams = r["exams"]
                self.applied, self.changes, self.undo = [], [], []
                self.data = copy.deepcopy(self.base_data)
                self._sync_requests()
                self.decisions = {}
                self._store_decisions(self.sem["fest_week"], r["decisions"], r["overrides"], state="proposed")
                self.baseline_book = {"bookings": [{k: v for k, v in d.items() if k in BOOK_KEYS} for d in r["decisions"]],
                                      "overrides": list(r["overrides"])}
                self.generated = True
                self.log(user, f"Generated timetable, bookings and exams in {r['info']['seconds']} s")
                self._save()
                self.write_exports()
                self.job = {"state": "done", "message": "Done", "info": r["info"]}
        except Exception as e:                         # surface, do not hang the UI
            self.job = {"state": "error", "message": f"{type(e).__name__}: {e}"}

    def _job_msg(self, m):
        self.job = {"state": "running", "message": m}

    def _store_decisions(self, week, decisions, overrides, state="proposed"):
        by_req = {r["id"]: r for r in self.requests}
        rooms = {r["id"]: r for r in self.data["rooms"]}
        ov_by = defaultdict(list)
        for o in overrides:
            ov_by[o["displaced_by"]].append(o)
        for d in decisions:
            rq = by_req[d["request_id"]]
            rec = dict(d)
            rec.update({"week": week, "state": state, "decided_at": now(), "overrides": ov_by.get(d["request_id"], []),
                        "category": effective_category(self.data, rq)})
            need_dept = []
            if d["status"] in ("approved", "alternative_offered") and d.get("room_id"):
                need_dept = LAB_DEPT.get(rooms[d["room_id"]]["type"], [])
            rec["lab_departments"] = need_dept
            rec["needs_admin"] = bool(rec["overrides"])
            self.decisions[d["request_id"]] = rec

    # ------------------------------------------------------------------ bookings
    def decide_week(self, user, week, redo=False):
        with self.lock:
            self._sync_requests()
            published = {k: v for k, v in self.decisions.items() if v.get("week") == week and v.get("state") == "published"}
            if redo:
                for k in [k for k, v in self.decisions.items() if v.get("week") == week and v.get("state") != "published"]:
                    del self.decisions[k]
            locked = {k: v for k, v in published.items()}
            pending = [r for r in self.requests if r["week"] == week and r["id"] not in locked]
            if not pending:
                return 0
            decisions, overrides, trace = self._decide_with_locked(week, pending, locked)
            self._store_decisions(week, decisions, overrides, "proposed")
            self.log(user, f"Decided {len(decisions)} request(s) for week {week}")
            self._save()
            return len(decisions)

    def _decide_with_locked(self, week, pending, locked):
        # published bookings block their rooms; they are passed as already-placed decisions
        locked_dec = {k: {kk: vv for kk, vv in v.items() if kk in
                      ("request_id", "status", "day", "start_period", "end_period", "room_id", "reason")} for k, v in locked.items()}
        wa = self.week_assign(week)
        d_all, overrides, trace = decide_batch(self.data, wa, requests=pending + [r for r in self.requests if r["id"] in locked],
                                               locked=locked_dec, allow_override=True)
        keep = [d for d in d_all if d["request_id"] not in locked]
        return keep, overrides, trace

    def can_publish(self, user, rec):
        if user["role"] == "admin":
            return True
        if user["role"] == "department_coordinator" and rec.get("lab_departments"):
            return user.get("department") in rec["lab_departments"] and not rec.get("overrides")
        return False

    def publish(self, user, ids):
        done, refused = [], []
        with self.lock:
            for i in ids:
                rec = self.decisions.get(i)
                if not rec or rec.get("state") == "published":
                    continue
                req = next(r for r in self.requests if r["id"] == i)
                if not self.can_publish(user, rec):
                    refused.append(i)
                    continue
                if req["owner"] == user["email"]:
                    refused.append(i)
                    continue
                rec["state"] = "published"
                rec["published_by"] = user["email"]
                rec["published_at"] = now()
                self.notify(req["owner"], f"{i} {req['title']}: {rec['status'].replace('_', ' ')}. {rec.get('reason', '')}")
                for o in rec.get("overrides", []):
                    s = next(x for x in self.data["sessions"] if x["id"] == o["session_id"])
                    self.notify(f"faculty.{s['faculty_id'].lower()}@cit.example",
                                f"{o['session_id']} moves in week {rec['week']} to {o['day'].title()} P{o['start_period']} in {o['room_id']}")
                done.append(i)
                self.log(user, f"Published {i} as {rec['status']}")
            self._save()
        return done, refused

    def create_booking(self, user, form):
        with self.lock:
            self._sync_requests()
            week = int(form.get("week") or self.sem["fest_week"])
            if week == self.sem["exam_week"]:
                raise ValueError("Week %d is exam week. Exams come first, so no events can be booked." % week)
            if not 1 <= week <= self.sem["weeks"]:
                raise ValueError("Week must be between 1 and %d" % self.sem["weeks"])
            nums = [int(re.sub(r"\D", "", r["id"].split("-")[1])[:3] or 0) for r in self.requests]
            created = []
            windows = form["windows"]
            groups = [windows] if not form.get("series") else [[w] for w in windows]
            for w in windows:
                if not (1 <= w["from_period"] <= w["to_period"] <= MAX_PERIOD):
                    raise ValueError(f"Periods must be between P1 and P{MAX_PERIOD} (22:00)")
            weeks, _skipped = self.repeat_weeks(week, form.get("repeat_until"))
            if len(weeks) > 1:                       # weekly repeat: one request per week, one id with a letter each
                jobs = [(w, ws) for w in weeks for ws in groups]
                if len(jobs) > 26:
                    raise ValueError(f"That is {len(jobs)} bookings. One repeat can hold at most 26, so shorten it or split it in two")
                base = max(nums) + 1
            else:
                jobs = [(week, ws) for ws in groups]
                base = None
            for k, (wk, ws) in enumerate(jobs):
                n = (base if base else max(nums) + 1 + k)
                req = {
                    "id": f"BR-{n:02d}{chr(97 + k)}" if base else f"BR-{n:02d}", "submitted_at": now(), "requester": user["name"], "role": user["role"],
                    "department": user.get("department"),
                    "requested_category": form.get("requested_category") or "club_event",
                    "title": form["title"] + (f" ({ws[0]['day'].title()})" if len(groups) > 1 else ""),
                    "attendance": int(form["attendance"]), "duration_periods": int(form["duration_periods"]),
                    "windows": ws, "room_types": form["room_types"], "needs": form.get("needs", []),
                    "requested_room": form.get("requested_room") or None,
                    "mandatory_for_groups": form.get("mandatory_for_groups", []),
                    "series_id": f"SER-{max(nums) + 1}" if len(jobs) > 1 else None, "raw_text": form.get("raw_text", ""),
                    "week": wk, "owner": user["email"]}
                self.requests.append(req)
                created.append(req["id"])
            self._sync_requests()
            for wk in sorted({j[0] for j in jobs}):
                self.decide_week(user, wk)
            self.log(user, f"Requested {', '.join(created)} for week{'s' if len(weeks) > 1 else ''} " + (f"{weeks[0]} to {weeks[-1]}" if len(weeks) > 1 else str(week)))
            for a in self.users.values():
                if a["role"] == "admin":
                    self.notify(a["email"], f"New booking request {', '.join(created)} from {user['name']}")
            self._save()
            return created

    def repeat_weeks(self, week, until):
        """Weeks a weekly repeat covers, and the ones it skips (exam week, and weeks already gone)."""
        week = int(week)
        until = int(until or week)
        if until < week:
            raise ValueError("The last week of a repeat cannot come before the first week")
        if until > self.sem["weeks"]:
            raise ValueError("The semester has %d weeks" % self.sem["weeks"])
        weeks = [week] + [w for w in range(week + 1, until + 1) if w != self.sem["exam_week"] and w >= self.current_week]
        return weeks, [w for w in range(week + 1, until + 1) if w not in weeks]

    def series_of(self, sid):
        return [r for r in self.requests if r.get("series_id") == sid]

    def publish_series(self, user, sid):
        """One approval for a whole repeating booking: every week of it that is still waiting."""
        ids = [r["id"] for r in self.series_of(sid)]
        if not ids:
            raise KeyError(sid)
        return self.publish(user, ids)

    def cancel_series(self, user, sid, from_week=None):
        """Cancel a repeating booking, or only the weeks from `from_week` on."""
        reqs = [r for r in self.series_of(sid) if not from_week or r["week"] >= int(from_week)]
        if not reqs:
            raise KeyError(sid)
        n = 0
        for r in reqs:
            if not any(c["request_id"] == r["id"] for c in self.cancel_log):
                self.cancel_booking(user, r["id"])
                n += 1
        return n

    def cancel_booking(self, user, rid):
        with self.lock:
            req = next((r for r in self.requests if r["id"] == rid), None)
            if not req:
                raise KeyError(rid)
            prior = self.decisions.get(rid) or {}
            approver = bool(prior) and self.can_publish(user, prior) and req["owner"] != user["email"]
            if user["role"] != "admin" and req["owner"] != user["email"] and not approver:
                raise PermissionError("Only the person who asked, the one who approves it, or the Dean's office can cancel")
            if any(c["request_id"] == rid for c in self.cancel_log):
                return
            other = req["owner"] != user["email"]
            self.cancel_log.append({"request_id": rid, "cancelled_at": now(), "by": user["name"], "note": "Cancelled in the app"})
            if other:
                self.notify(req["owner"], f"{rid} {req['title']} was cancelled by {user['name']}")
            self.decisions[rid] = {"request_id": rid, "status": "rejected", "reason": f"Cancelled by {user['name']}, so no room is held" if other else "Cancelled by the requester, so no room is held",
                                   "week": req["week"], "state": "published", "overrides": [], "lab_departments": []}
            self._sync_requests()
            self.decide_week(user, req["week"], redo=True)
            self.log(user, f"Cancelled {rid}")
            self._save()


    # ------------------------------------------------------------------ events that are over
    def _is_past(self, week, day, end_hhmm, today=None):
        """Has this slot already happened? Weekends count as 'before Monday', as on the overview."""
        n = today or dt.datetime.now()
        if week < self.current_week:
            return True
        if week > self.current_week or not day:
            return False
        order = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
        t = n.weekday() if n.weekday() < 5 else -1
        i = order.index(day) if day in order else 9
        return i < t or (i == t and end_hhmm <= n.strftime("%H:%M"))

    def purge_past(self, force=False):
        """Delete bookings, online lectures and extra classes whose time has passed. Returns how many."""
        with self.lock:
            if not force and time.time() - getattr(self, "_purged_at", 0) < 20:
                return 0
            self._purged_at = time.time()
            gone = 0
            fw = self.sem["fest_week"]
            keep = []
            for r in self.requests:
                rec = self.decisions.get(r["id"]) or {}
                day, end = rec.get("day"), END_LABEL.get(rec.get("end_period") or 0, "00:00")
                if not day:                                   # no slot was given: judge by the last day asked for
                    order = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
                    days = [w["day"] for w in r.get("windows", []) if w.get("day") in order]
                    day = max(days, key=order.index) if days else None
                    end = "23:59"
                if self._is_past(r["week"], day, end):
                    if r["week"] == fw:                       # the official export still needs it
                        self.archive["requests"].append(r)
                        if r["id"] in self.decisions:
                            self.archive["decisions"][r["id"]] = self.decisions[r["id"]]
                    self.decisions.pop(r["id"], None)
                    gone += 1
                else:
                    keep.append(r)
            if len(keep) != len(self.requests):
                self.requests = keep
                self._sync_requests()
            n = len(self.online)
            self.online = [o for o in self.online if not self._is_past(o["week"], o["day"], o["end"])]
            gone += n - len(self.online)
            n = len(self.extras)
            self.extras = [x for x in self.extras if not self._is_past(x["week"], x["day"], x["end"])]
            gone += n - len(self.extras)
            n = len(self.swaps)
            order = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
            def swap_over(w):
                if w.get("scope") != "day" or not w.get("week") or w["give"] not in self.assign or w["take"] not in self.assign:
                    return False
                wa = self.week_assign(w["week"])
                day = max((wa[w["give"]][0], wa[w["take"]][0]), key=order.index)
                return self._is_past(w["week"], day, "23:59")
            self.swaps = [w for w in self.swaps if not swap_over(w)]
            gone += n - len(self.swaps)
            if gone:
                self._save()
            return gone

    # ------------------------------------------------------------------ changes
    def _authorise_change(self, user, dis):
        courses = {c["id"]: c for c in self.data["courses"]}
        sess = {s["id"]: s for s in self.data["sessions"]}
        for ch in dis["changes"]:
            t = ch["type"]
            if user["role"] == "admin":
                continue
            if t == "move_session":
                sx = sess.get(ch["session_id"])
                if not sx:
                    raise ValueError(f"No class {ch['session_id']}")
                if user["role"] == "faculty" and sx["faculty_id"] == user.get("faculty_id"):
                    continue
                if user["role"] == "department_coordinator" and courses.get(sx["course_id"], {}).get("department") == user["department"]:
                    continue
                raise PermissionError("You can ask to move your own classes. A coordinator can ask for their department's classes")
            if user["role"] == "faculty":
                if t == "faculty_unavailable" and ch["faculty_id"] == user.get("faculty_id"):
                    continue
                if t == "add_session" and ch["session"]["faculty_id"] == user.get("faculty_id"):
                    continue
                raise PermissionError("Faculty can mark their own absence or ask for an extra session of their own")
            if user["role"] == "department_coordinator":
                dept = user["department"]
                if t == "add_session" and courses.get(ch["session"]["course_id"], {}).get("department") == dept:
                    continue
                if t == "remove_session" and courses.get(sess.get(ch["session_id"], {}).get("course_id"), {}).get("department") == dept:
                    continue
                if t == "faculty_unavailable" and next((f for f in self.data["faculty"] if f["id"] == ch["faculty_id"]), {}).get("department") == dept:
                    continue
                raise PermissionError(f"A {dept} coordinator can change {dept} sessions and {dept} faculty only")
            raise PermissionError("Your role cannot request timetable changes")

    def _reservations(self):
        return reservations_for(self.data, [d for d in self.decisions.values() if d.get("state") == "published"
                                            and d["status"] in ("approved", "alternative_offered")])

    def explain_session(self, sid):
        if sid not in self.assign:
            raise KeyError(sid)
        return why_here(self.data, self.assign, sid, self._reservations())

    def session_slots(self, sid):
        if sid not in self.assign:
            raise KeyError(sid)
        return slot_table(self.data, self.assign, sid, self._reservations())

    def preview_change(self, user, dis, note=""):
        return self.create_change(user, dis, note, store=False)

    def create_change(self, user, dis, note="", store=True):
        with self.lock:
            if not self.generated:
                raise ValueError("Generate the timetable first")
            self._authorise_change(user, dis)
            res = self._reservations()
            nd, na, diff, info = repair(self.data, dis, self.assign, reservations=res, time_limit=40)
            cid = f"CH-{len(self.changes) + 1:02d}"
            ch = {"id": cid, "by": user["email"], "by_name": user["name"], "role": user["role"], "at": now(),
                  "dis": dis, "note": note, "status": "pending", "diff": diff, "feasible": na is not None,
                  "info": {k: v for k, v in info.items() if k in ("status", "stage", "seconds")}}
            if na is None:
                ch["why_not"] = self.explain_infeasible(dis, info)
            else:
                ch["moved"] = sum(1 for d in diff if d["type"] == "moved")
                ch["room_only"] = sum(1 for d in diff if d["type"] == "room")
                ch["added"] = sum(1 for d in diff if d["type"] == "added")
                ch["removed"] = sum(1 for d in diff if d["type"] == "removed")
            if not store:
                return ch
            self.changes.append(ch)
            self.log(user, f"Requested change {cid}")
            for a in self.users.values():
                if a["role"] == "admin" and a["email"] != user["email"]:
                    self.notify(a["email"], f"Change request {cid} from {user['name']} needs approval")
            self._save()
            return ch

    def explain_infeasible(self, dis, info):
        reasons = []
        for ch in dis.get("changes", []):
            if ch["type"] == "move_session" and ch.get("to"):
                from .explain import slot_check, span
                B = Board(self.data, self.assign, self._reservations())
                s = B.P.sessions[ch["session_id"]]
                c = slot_check(B, ch["session_id"], ch["to"]["day"], int(ch["to"]["start_period"]))
                head = f"{B.title(ch['session_id'])} cannot go to {span(ch['to']['day'], int(ch['to']['start_period']), s['duration'])}"
                for b in c["blockers"]:
                    reasons.append(f"{head}: {b['text']}" + ("" if not b["movable"] else ", and moving that class too would break another rule"))
                if ch["to"].get("room_id") and ch["to"]["room_id"] not in c["rooms"]:
                    reasons.append(f"{ch['to']['room_id']} is not free and suitable at that time")
        new = repair_mod.apply_disruption(self.data, dis)
        P = Problem(new)
        for s in new["sessions"]:
            if not P.time_options(s):
                reasons.append(f"{s['id']} ({P.fac[s['faculty_id']]['name']}) has no allowed time left")
            elif not P.eligible_rooms(s):
                reasons.append(f"{s['id']} has no room that fits it")
        if not reasons:
            reasons.append("Taken together, the changes leave no timetable that keeps every rule, even if every class moves")
        return reasons

    def decide_change(self, user, cid, approve, reason=""):
        with self.lock:
            ch = next((c for c in self.changes if c["id"] == cid), None)
            if not ch:
                raise KeyError(cid)
            if user["role"] != "admin":
                raise PermissionError("Only the Dean's office approves timetable changes")
            if ch["by"] == user["email"]:
                raise PermissionError("Nobody can approve their own request. Ask another admin")
            if ch["status"] != "pending":
                raise ValueError("Already decided")
            if not approve:
                ch["status"] = "rejected"
                ch["decided_by"], ch["reason"] = user["email"], reason
                self.notify(ch["by"], f"Change {cid} was rejected. {reason}")
                self.log(user, f"Rejected {cid}")
                self._save()
                return ch
            if not ch["feasible"]:
                raise ValueError("This change has no valid timetable. Edit it first")
            res = reservations_for(self.data, [d for d in self.decisions.values() if d.get("state") == "published"
                                               and d["status"] in ("approved", "alternative_offered")])
            nd, na, diff, info = repair(self.data, ch["dis"], self.assign, reservations=res, time_limit=40)
            if na is None:
                raise ValueError("The timetable changed since this was previewed and no longer works. Preview it again")
            ctx = self._undo_open()
            self.data = nd
            self.data["booking_requests"] = [{k: v for k, v in r.items() if k not in ("week", "owner")} for r in self.requests]
            self.data["cancellations"] = list(self.cancel_log)
            self.assign = {k: tuple(v) for k, v in na.items()}
            self.applied.append(ch["dis"])
            ch["status"], ch["decided_by"], ch["reason"], ch["decided_at"] = "approved", user["email"], reason, now()
            fac = {s["id"]: s for s in nd["sessions"]}
            told = set()
            for d in diff:
                s = fac.get(d["session_id"]) or {}
                if s.get("faculty_id"):
                    told.add(s["faculty_id"])
            for f in told:
                self.notify(f"faculty.{f.lower()}@cit.example", f"Timetable change {cid} was approved and moves some of your classes")
            self.notify(ch["by"], f"Change {cid} was approved")
            # bookings still valid? re-check with the official rules
            sched = self.export_schedule()
            rep = official.run(self.validation_data(), sched, None)
            for _ in range(3):                       # bookings hit by the change are decided again
                bad = set(re.findall(r"BR-\d+[a-z]?", " ".join(v["detail"] for v in rep["hard_violations"])))
                bad = {b for b in bad if b in self.decisions}
                if not bad:
                    break
                for b in bad:
                    req = next(r for r in self.requests if r["id"] == b)
                    self.notify(req["owner"], f"{b} {req['title']} is being decided again because of timetable change {cid}")
                    del self.decisions[b]
                for w in {r["week"] for r in self.requests if r["id"] in bad}:
                    self.decide_week(user, w)
                rep = official.run(self.validation_data(), self.export_schedule(), None)
            ch["after_check"] = {"hard": rep["hard_violation_count"], "soft": rep["soft_total"]}
            self._undo_close("change", cid, ctx, user, rep["hard_violation_count"])
            self.log(user, f"Approved {cid}: {len(diff)} change(s)")
            self._save()
            self.write_exports()
            return ch


    # ------------------------------------------------------------------ undo
    def _undo_open(self):
        """Remember how things were just before a change is applied."""
        return {"assign": {k: list(v) for k, v in self.assign.items()}, "applied": copy.deepcopy(self.applied), "dec": copy.deepcopy(self.decisions)}

    @staticmethod
    def _norm(x):
        return json.loads(json.dumps(x, sort_keys=True, default=list))

    def _undo_close(self, kind, rid, ctx, user, hard_after):
        before, after = ctx["dec"], self.decisions
        ids = [i for i in set(before) | set(after) if self._norm(before.get(i)) != self._norm(after.get(i))]
        self.undo.append({"kind": kind, "id": rid, "at": now(), "by": user["email"], "assign": ctx["assign"], "applied": ctx["applied"],
                          "dec_before": {i: copy.deepcopy(before.get(i)) for i in ids}, "dec_after": {i: copy.deepcopy(after.get(i)) for i in ids},
                          "hard_after": hard_after})

    def undo_top(self):
        return self.undo[-1] if self.undo else None

    def can_undo(self, user, kind, rid):
        top = self.undo_top()
        return bool(top and user["role"] == "admin" and top["kind"] == kind and top["id"] == rid)

    def _rebuild_data(self):
        data = copy.deepcopy(self.base_data)
        for dis in self.applied:
            data = repair_mod.apply_disruption(data, dis)
        data["cancellations"] = list(self.cancel_log)
        self.data = data
        self._sync_requests()

    def _undo_restore(self, user, kind, rid):
        """Put the timetable back the way it was before change `rid`, then run the official checker again.
        If anything is off, nothing is changed."""
        top = self.undo_top()
        if user["role"] != "admin":
            raise PermissionError("Only the Dean's office can undo a change")
        if not top or top["kind"] != kind or top["id"] != rid:
            last = f" Undo {top['id']} first." if top else ""
            raise ValueError("Only the most recent change can be undone, because later changes build on it." + last)
        for i, a in top["dec_after"].items():
            if self._norm(self.decisions.get(i)) != self._norm(a):
                raise ValueError(f"Booking {i} was decided again after this change, so it cannot be undone safely")
        keep = {"assign": dict(self.assign), "applied": copy.deepcopy(self.applied), "dec": copy.deepcopy(self.decisions), "data": self.data}
        self.assign = {k: tuple(v) for k, v in top["assign"].items()}
        self.applied = copy.deepcopy(top["applied"])
        for i, b in top["dec_before"].items():
            if b is None:
                self.decisions.pop(i, None)
            else:
                self.decisions[i] = copy.deepcopy(b)
        self._rebuild_data()
        rep = official.run(self.validation_data(), self.export_schedule(), None)
        if rep["hard_violation_count"] > top["hard_after"]:
            self.assign, self.applied, self.decisions, self.data = keep["assign"], keep["applied"], keep["dec"], keep["data"]
            self._sync_requests()
            raise ValueError("The official checker found clashes after going back, so nothing was changed")
        restored = sum(1 for k in set(keep["assign"]) | set(self.assign) if keep["assign"].get(k) != self.assign.get(k))
        self.undo.pop()
        return {"hard": rep["hard_violation_count"], "soft": rep["soft_total"], "classes_restored": restored}

    def undo_change(self, user, cid, reason=""):
        with self.lock:
            ch = next((c for c in self.changes if c["id"] == cid), None)
            if not ch:
                raise KeyError(cid)
            if ch["status"] != "approved":
                raise ValueError("Only an approved change can be undone")
            check = self._undo_restore(user, "change", cid)
            ch["status"] = "undone"
            ch["undone"] = {"by": user["email"], "by_name": user["name"], "at": now(), "reason": reason, "check": check}
            self.notify(ch["by"], f"Change {cid} was undone by {user['name']}. The timetable is back as it was" + (f": {reason}" if reason else ""))
            for d in ch.get("diff", []):
                s = next((x for x in self.data["sessions"] if x["id"] == d["session_id"]), None)
                if s:
                    self.notify(f"faculty.{s['faculty_id'].lower()}@cit.example", f"Timetable change {cid} was undone, so {d['session_id']} is back where it was")
            self.log(user, f"Undid {cid}")
            self._save()
            self.write_exports()
            return ch

    # ------------------------------------------------------------------ exams
    def reschedule_exams(self, user):
        with self.lock:
            ex, info = schedule_exams(self.data)
            if ex is None:
                raise ValueError("No valid exam schedule with the current rooms")
            self.exams = ex
            self.log(user, "Rescheduled exams")
            self._save()
            return ex

    # ------------------------------------------------------------------ export
    def export_schedule(self, which="current"):
        fw = self.sem["fest_week"]
        arch = self.archive["decisions"]
        decs = [self.decisions.get(r["id"]) or arch.get(r["id"]) for r in self.requests + self.archive["requests"]
                if r["week"] == fw and (r["id"] in self.decisions or r["id"] in arch)]
        ovs = [o for d in decs for o in d.get("overrides", [])]
        clean = [{k: v for k, v in d.items() if k in BOOK_KEYS} for d in decs]
        assign = self.baseline if which == "baseline" else self.assign
        if which == "baseline" and self.baseline_book:
            clean, ovs = self.baseline_book["bookings"], self.baseline_book["overrides"]
        return {"team": "CIT Scheduler", "dataset_id": self.data["dataset_id"],
                "sessions": [{"session_id": k, "day": v[0], "start_period": v[1], "room_id": v[2]} for k, v in sorted(assign.items())],
                "fest_week": {"bookings": clean, "session_overrides": ovs}, "exams": self.exams}

    def write_exports(self):
        """Keep schedule.json and schedule_after.json in exports/ up to date (the app produces them)."""
        out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "exports")
        os.makedirs(out, exist_ok=True)
        for name, which in (("schedule.json", "baseline"), ("schedule_after.json", "current")):
            with open(os.path.join(out, name), "w") as f:
                json.dump(self.export_schedule(which), f, indent=1)

    def validation_data(self, original=False):
        d = copy.copy(self.base_data if original else self.data)
        allr = self.requests + self.archive["requests"]          # events already held are gone from the app, but stay in the export
        d["booking_requests"] = [{k: v for k, v in r.items() if k not in ("week", "owner")} for r in allr]
        if original:
            d["cancellations"] = list(self.cancel_log)
        fw = self.sem["fest_week"]
        ids = {r["id"] for r in allr if r["week"] == fw}
        d["booking_requests"] = [r for r in d["booking_requests"] if r["id"] in ids]
        return d

    def health(self):
        sched = self.export_schedule()
        rep = official.run(self.validation_data(), sched, None)
        by = defaultdict(int)
        for v in rep["hard_violations"]:
            by[v["rule"]] += 1
        return {"hard": rep["hard_violation_count"], "by_rule": dict(by), "soft": rep["soft_total"],
                "soft_by": rep["soft_penalties"], "booking": rep.get("bookings", {}), "exam_penalty": rep.get("exam_soft_penalty")}
