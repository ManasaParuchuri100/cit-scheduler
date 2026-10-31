import json, sys, time
sys.path.insert(0, '.')
from cit.data import load_dataset
from cit.engine import to_schedule
from cit.bookings import decide_batch
from cit.repair import repair
from cit.exams import schedule_exams
import validator
data = load_dataset()
sched = json.load(open('exports/schedule.json'))
base = {e["session_id"]:(e["day"],e["start_period"],e["room_id"]) for e in sched["sessions"]}
dis = json.load(open('examples/sample_disruption.json'))
t=time.time()
from cit.bookings import reservations_for
res = reservations_for(data, sched['fest_week']['bookings'])
nd, na, diff, info = repair(data, dis, base, reservations=res, time_limit=40)
print(info, round(time.time()-t,1))
for d in diff: print(d["type"], d["session_id"], d["before"], '->', d["after"], '|', d["why"])
decisions, overrides, _ = decide_batch(nd, na)
after = to_schedule(nd, na, decisions, overrides, sched["exams"])
json.dump(after, open('exports/schedule_after.json','w'), indent=1)
