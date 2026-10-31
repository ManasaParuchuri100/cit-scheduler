"""Command line: python -m cit.cli generate | apply <change.json> | check
Uses the same code as the website. `apply` files the change as the Dean's office and approves it as the Registrar."""
import json, sys
from .store import Store
import validator as official


def main():
    S = Store()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    dean, reg = S.users["dean@cit.example"], S.users["registrar@cit.example"]
    if cmd == "generate":
        S.reset()
        S.generate(dean)
        print(S.job)
    elif cmd == "apply":
        dis = json.load(open(sys.argv[2]))
        ch = S.create_change(dean, dis, "Applied from the command line")
        print(ch["id"], "feasible" if ch["feasible"] else "NOT feasible", ch.get("why_not", ""))
        if ch["feasible"]:
            ch = S.decide_change(reg, ch["id"], True, "Approved from the command line")
            print("approved;", ch.get("after_check"))
    elif cmd == "check":
        for n, w in (("schedule.json", "baseline"), ("schedule_after.json", "current")):
            rep = official.run(S.validation_data(original=(w == "baseline")), S.export_schedule(w), None)
            print(n, "hard", rep["hard_violation_count"], "soft", rep["soft_total"], rep.get("bookings"))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
