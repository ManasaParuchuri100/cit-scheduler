import sys, json, datetime as dt
sys.path.insert(0,'.')
from cit.data import load_dataset
from cit.parser import parse_request
d = load_dataset()
today = dt.date(2027,2,3)   # a Wednesday; "kal" -> Thursday
ok = tot = 0
def periods(w): return {(x["day"],x["from_period"],x["to_period"]) for x in w}
seen=set()
for b in d["booking_requests"]:
    if b["series_id"] and b["series_id"] in seen and b["series_id"]!="SER-DANCE": continue
    f = parse_request(b["raw_text"], d, role=b["role"], today=today)
    checks = {
      "att": f["attendance"]==b["attendance"],
      "dur": f["duration_periods"]==b["duration_periods"],
      "types": set(f["room_types"])&set(b["room_types"])!=set() ,
      "needs": set(b["needs"])<=set(f["needs"]),
      "mand": set(f["mandatory_for_groups"])==set(b["mandatory_for_groups"]),
    }
    # days: all true days present
    fd = {w["day"] for w in f["windows"]}; td = {w["day"] for w in b["windows"]}
    checks["days"] = td<=fd
    # window contains the true window start
    checks["time"] = any(w["from_period"]<=tw["from_period"] and (w["to_period"]>=min(tw["to_period"],13)) and w["day"]==tw["day"] for tw in b["windows"] for w in f["windows"]) or not b["windows"]
    seen.add(b["series_id"])
    bad=[k for k,v in checks.items() if not v]
    tot+=1; ok+= (not bad)
    if bad: print(b["id"], bad, '\n   got', {k:f[k] for k in ("attendance","duration_periods","windows","room_types","needs","mandatory_for_groups")}, '\n   want', {k:b[k] for k in ("attendance","duration_periods","windows","room_types","needs","mandatory_for_groups")}, f["follow_up"])
print(ok,"/",tot,"fully matching")
print("---- sample requests")
S=["Need a room for 45 people on Tuesday 6 to 8 pm, projector please.",
"Book the auditorium for the CSE department farewell, Friday evening, around 400 people, need stage and mic.",
"Can I get a lab with computers for a 3-hour coding contest on Thursday afternoon? About 60 participants.",
"Our club meets every Monday and Wednesday 7 to 8 pm, 30 people, any small room is fine.",
"Mechanical third years need a 2 hour session with an industry speaker on Wednesday, it's compulsory for them.",
"seminar hall kal shaam 6 baje, 2 ghante, 100 log, mic chahiye",
"I want SH-2 on Friday at 10 am for a wheelchair-accessible poster session, 60 people.",
"Need somewhere for the quiz finals after lunch on Thursday, maybe 150 people."]
for s in S:
    f=parse_request(s,d,role="club",today=today)
    print(s[:60],'\n  ',{k:f[k] for k in ("attendance","duration_periods","windows","room_types","needs","mandatory_for_groups","series","requested_room")},'\n   ask:',f["follow_up"],'| assume:',f["assumptions"])
