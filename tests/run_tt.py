import json, sys, time
sys.path.insert(0, '.')
from cit.data import load_dataset
from cit.timetable import solve
import validator
data = load_dataset()
t=time.time()
assign, info = solve(data, time_limit=float(sys.argv[1]) if len(sys.argv)>1 else 60, log=False)
print(info)
if assign:
    sched = {"team":"t","dataset_id":data["dataset_id"],"sessions":[{"session_id":k,"day":v[0],"start_period":v[1],"room_id":v[2]} for k,v in assign.items()]}
    rep = validator.run(data, sched)
    print(rep["hard_violation_count"], rep["hard_by_rule"], rep["soft_total"], rep["soft_penalties"])
    json.dump(sched, open('/tmp/tt.json','w'))
