import json, sys, time
sys.path.insert(0, '.')
from cit.data import load_dataset
from cit.engine import generate_all, to_schedule
import validator
data = load_dataset()
r = generate_all(data, tt_time=float(sys.argv[1]) if len(sys.argv)>1 else 45)
print(r["info"])
sched = to_schedule(data, r["assign"], r["decisions"], r["overrides"], r["exams"])
json.dump(sched, open('exports/schedule.json','w'), indent=1)
rep = validator.run(data, sched)
print("hard", rep["hard_violation_count"], rep["hard_by_rule"])
print("soft", rep["soft_total"], rep["soft_penalties"], "exam pen", rep.get("exam_soft_penalty"))
b=rep["bookings"]; print({k:v for k,v in b.items() if k!='priority_inversions'}, b["priority_inversions"])
for v in rep["hard_violations"][:10]: print(v)
for d in r["decisions"]: print(d["request_id"], d["status"], d.get("room_id"), d.get("day"), d.get("start_period"), d.get("end_period"), '|', d["reason"][:110])
