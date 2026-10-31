"""Load the CIT dataset from the CSV files (plus data/config.json for the calendar and
priority rules, which are not tabular). Falls back to the single JSON file if CSVs are missing."""
import csv, json, os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

JSON_COLS = {
    "rooms": ["features", "allowed_uses"],
    "faculty": ["unavailable", "preferences"],
    "sessions": ["groups", "room_types", "fixed_slot"],
    "booking_requests": ["windows", "room_types", "needs", "mandatory_for_groups"],
    "room_unavailability": ["periods"],
    "exams": ["course_ids", "groups"],
}
BOOL_COLS = {"rooms": ["accessible"], "faculty": ["needs_accessible"],
             "sessions": ["needs_accessible"], "student_groups": ["needs_accessible"]}
INT_COLS = {"rooms": ["capacity"], "faculty": ["max_hours_per_day"], "student_groups": ["year", "size"],
            "courses": ["year", "lecture_hours", "tutorial_hours", "lab_blocks"],
            "sessions": ["size", "duration"], "booking_requests": ["attendance", "duration_periods"],
            "exams": ["size", "duration_hours"]}
NULLABLE = {"sessions": ["basket_slot", "fixed_slot"], "booking_requests": ["department", "requested_room", "series_id"]}


def _read(table, csv_dir):
    path = os.path.join(csv_dir, table + ".csv")
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            for c in JSON_COLS.get(table, []):
                r[c] = json.loads(r[c]) if r[c].strip() else None
            for c in BOOL_COLS.get(table, []):
                r[c] = r[c].strip().lower() == "true"
            for c in INT_COLS.get(table, []):
                r[c] = int(r[c])
            for c in NULLABLE.get(table, []):
                if r.get(c) in ("", None):
                    r[c] = None
            rows.append(r)
    return rows


def load_dataset(data_dir=DATA_DIR):
    csv_dir = os.path.join(data_dir, "csv")
    cfg = json.load(open(os.path.join(data_dir, "config.json"), encoding="utf-8"))
    if not os.path.isdir(csv_dir):
        return json.load(open(os.path.join(data_dir, "cit_public.json"), encoding="utf-8"))
    d = dict(cfg)
    for table in ("rooms", "room_unavailability", "faculty", "student_groups", "courses", "sessions",
                  "booking_requests", "exams"):
        d[table] = _read(table, csv_dir)
    d["cancellations"] = _read_plain(csv_dir, "cancellations")
    # keep the same key order as cit_public.json
    order = ["dataset_id", "institute", "calendar", "priority_order", "role_category_cap", "rooms",
             "room_unavailability", "faculty", "student_groups", "courses", "sessions",
             "booking_requests", "cancellations", "exams"]
    return {k: d[k] for k in order}


def _read_plain(csv_dir, table):
    with open(os.path.join(csv_dir, table + ".csv"), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
