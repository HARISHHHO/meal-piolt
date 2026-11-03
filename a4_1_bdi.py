"""
Assignment 4.1 - Belief / Desire / Intention model for MealPilot

  Beliefs    : what the agent currently thinks is true (budget, guests, sick member, gas ...)
  Desires    : abstract goals with a priority; each one knows when it is ACTIVE
  Intentions : the goal the agent has COMMITTED to, plus the step-by-step plan for it

Deliberation loop (runs every step):
    1. perceive      -> update beliefs
    2. options       -> which desires are active now?
    3. filter        -> pick the highest priority one (this is the intention)
    4. if intention changed -> suspend old plan, build new plan
    5. if a belief that the plan depends on changed -> REPLAN the remaining steps
    6. execute next step
"""
from common import Logger

log = Logger("a4_1_bdi")


class Beliefs:
    def __init__(self, **facts):
        self.facts = dict(facts)
        self.changed = set()                       # keys changed since the agent last looked

    def update(self, key, value, source="sensor"):
        old = self.facts.get(key)
        if old != value:
            self.facts[key] = value
            self.changed.add(key)
            log("BELIEF", "%s: %r -> %r (via %s)" % (key, old, value, source))

    def get(self, key):
        return self.facts.get(key)


class Desire:
    def __init__(self, name, priority, active_when, make_plan, redo_from):
        self.name, self.priority = name, priority
        self.active_when = active_when             # function(beliefs) -> bool
        self.make_plan = make_plan                 # function(beliefs) -> list of step strings
        self.redo_from = redo_from                 # belief key -> index of the first step that is now stale
        self.depends_on = set(redo_from)           # belief keys that force a replan
        self.satisfied = False


class Intention:
    def __init__(self, desire, steps):
        self.desire, self.steps, self.pc = desire, steps, 0
        self.pending = set()                       # relevant belief changes that happened while paused

    @property
    def finished(self):
        return self.pc >= len(self.steps)


class BDIAgent:
    def __init__(self, beliefs, desires):
        self.b, self.desires = beliefs, desires
        self.current = None
        self.suspended = []                        # stack of paused intentions
        self.shift_count = 0
        self.last_step = None
        self.history = []                          # (step number, desire name) for the test at the end

    def deliberate(self):
        active = [d for d in self.desires if not d.satisfied and d.active_when(self.b)]
        log("DESIRES", "active: %s" % [(d.name, d.priority) for d in active])
        return max(active, key=lambda d: d.priority) if active else None

    def step(self, n):
        best = self.deliberate()
        if best is None and self.current is None:
            return False

        # paused intentions still need to know what changed while they slept
        for p in self.suspended:
            p.pending |= self.b.changed & p.desire.depends_on

        # ---- intention change? ----
        if best is not None and (self.current is None or best is not self.current.desire):
            if self.current is not None and not self.current.finished:
                log("SHIFT", "suspending '%s' at step %d/%d, new top desire is '%s' (priority %d)"
                    % (self.current.desire.name, self.current.pc, len(self.current.steps),
                       best.name, best.priority))
                self.current.pending |= self.b.changed & self.current.desire.depends_on
                self.suspended.append(self.current)
                self.shift_count += 1
            resumed = next((i for i in self.suspended if i.desire is best), None)
            if resumed:
                self.suspended.remove(resumed)
                self.current = resumed
                log("RESUME", "going back to '%s' (paused at step %d)" % (best.name, resumed.pc))
                self._replan("resuming", resumed.pending | (self.b.changed & best.depends_on))
            else:
                self.current = Intention(best, best.make_plan(self.b))
                log("INTEND", "committed to '%s' with plan:" % best.name)
                for i, s in enumerate(self.current.steps, 1):
                    log("PLAN", "  %d. %s" % (i, s))

        # ---- belief changes that matter for the running plan? ----
        elif self.b.changed & self.current.desire.depends_on:
            self._replan("beliefs changed", self.b.changed & self.current.desire.depends_on)
        self.b.changed.clear()

        # ---- execute one step ----
        cur = self.current
        if cur.finished:
            cur.desire.satisfied = True
            log("DONE", "desire '%s' satisfied" % cur.desire.name)
            self.current = self.suspended.pop() if self.suspended else None
            if self.current is not None:
                log("RESUME", "going back to '%s' (paused at step %d)"
                    % (self.current.desire.name, self.current.pc))
                self._replan("resuming", self.current.pending | (self.b.changed & self.current.desire.depends_on))
            return self.current is not None
        log("EXEC", "[%s] step %d/%d: %s" % (cur.desire.name, cur.pc + 1, len(cur.steps), cur.steps[cur.pc]))
        self.last_step = (cur.desire.name, cur.steps[cur.pc])
        self.history.append((n, cur.desire.name))
        cur.pc += 1
        return True

    def _replan(self, why, keys):
        cur = self.current
        cur.pending = set()
        new_steps = cur.desire.make_plan(self.b)
        # earliest step whose result is no longer valid because of the changed beliefs
        restart = min([cur.desire.redo_from[k] for k in keys] + [cur.pc])
        if new_steps == cur.steps and restart >= cur.pc:
            log("REPLAN", "%s %s -> plan still valid, no change" % (why, sorted(keys)))
            return
        if restart < cur.pc:
            log("REWIND", "step %d already done but is stale because of %s -> going back to step %d"
                % (restart + 1, sorted(keys), restart + 1))
            cur.pc = restart
        cur.steps = new_steps
        log("REPLAN", "%s %s -> steps %d..%d recalculated:" % (why, sorted(keys), cur.pc + 1, len(new_steps)))
        for i in range(cur.pc, len(new_steps)):
            log("PLAN", "  %d. %s" % (i + 1, new_steps[i]))


# --------------------------------------------------------------------- MealPilot knowledge
def weekly_plan(b):
    pool = "soft, low-spice dishes only" if b.get("sick_member") else "full dish library"
    if b.get("gas_pct") < 10:
        pool += ", no pressure-cooker dishes (gas nearly empty)"
    extra = "+%d guest portions" % b.get("guests") if b.get("guests") else "family portions only"
    return ["read pantry and budget beliefs",
            "shortlist dishes (%s)" % pool,
            "score shortlist with utility function (budget Rs.%d)" % b.get("budget_left"),
            "assign dishes to 7 days (%s)" % extra,
            "publish plan and shopping list"]


def care_plan(b):
    return ["switch next 2 dinners to khichdi / idli (%s)" % b.get("sick_member"),
            "tell cook: no fried food, low spice",
            "add ORS and coconut water to shopping list",
            "re-check health belief after 2 meals"]


def build_agent():
    beliefs = Beliefs(budget_left=2400, guests=0, sick_member=None, gas_pct=55, tomato_price=40)
    desires = [
        Desire("plan_weekly_menu", 3, lambda b: True, weekly_plan,
               {"sick_member": 1, "gas_pct": 1, "guests": 3, "budget_left": 2}),
        Desire("care_for_sick_member", 5, lambda b: b.get("sick_member") is not None, care_plan,
               {"sick_member": 0}),
    ]
    return BDIAgent(beliefs, desires)


def main():
    log.open()
    agent = build_agent()
    # unexpected environment updates, injected at given step numbers
    surprises = {3: ("sick_member", "Dad (fever)"), 8: ("gas_pct", 8)}
    log("START", "initial beliefs = %s" % agent.b.facts)
    n = 0
    while True:
        n += 1
        log("STEP", "----- %d -----" % n)
        if n in surprises:
            k, v = surprises[n]
            log("EVENT", "unexpected update arrives: %s = %r" % (k, v))
            agent.b.update(k, v, "environment")
        if not agent.step(n):
            break
        if n > 40:
            break

    # ------------------------------------------------------------ verification
    log("TEST", "intention history (step, desire): %s" % agent.history)
    names = [d for _, d in agent.history]
    assert names[0] == "plan_weekly_menu"
    log("TEST", "starts with plan_weekly_menu ................ PASS")
    assert "care_for_sick_member" in names
    assert names.index("care_for_sick_member") == 2
    log("TEST", "shifts to care_for_sick_member at step 3 ..... PASS")
    assert names[-1] == "plan_weekly_menu" and agent.shift_count == 1
    log("TEST", "resumes plan_weekly_menu afterwards ........... PASS (shifts=%d)" % agent.shift_count)
    final_plan = agent.desires[0].make_plan(agent.b)
    assert "soft" in final_plan[1] and "no pressure-cooker" in final_plan[1]
    log("TEST", "recalculated plan uses soft dishes + no pressure cooker .. PASS")
    assert all(d.satisfied for d in agent.desires)
    log("TEST", "all desires satisfied at the end ............. PASS")


if __name__ == "__main__":
    main()
