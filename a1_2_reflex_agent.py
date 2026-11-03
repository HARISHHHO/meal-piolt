
import random
from common import Logger

log = Logger("a1_2_reflex")

WEEKLY_BUDGET = 3000          # Rs
LOW_STOCK = {"rice_kg": 1.5, "dal_kg": 0.5, "onion_kg": 0.6, "milk_l": 1.0, "atta_kg": 1.2}


# ---------------------------------------------------------------- environment
def sensor_stream(ticks=14, seed=7):
    """Fake live feed, one percept per tick. 1 tick = 1 hour of the day starting at 6am."""
    rnd = random.Random(seed)
    pantry = {"rice_kg": 6.0, "dal_kg": 2.0, "onion_kg": 3.0, "milk_l": 4.0, "atta_kg": 5.0}
    use = {"rice_kg": (0.1, 0.5), "dal_kg": (0.03, 0.2), "onion_kg": (0.05, 0.3),
           "milk_l": (0.05, 0.4), "atta_kg": (0.05, 0.4)}
    budget, gas = 2200, 45
    scripted = {3: "guests_arriving:3", 6: "member_fever:Dad", 10: "festival:ekadashi"}
    for t in range(ticks):
        for k, (lo, hi) in use.items():
            pantry[k] = round(max(0.0, pantry[k] - rnd.uniform(lo, hi)), 2)
        budget -= rnd.randint(100, 170)
        gas = max(0, gas - rnd.randint(2, 4))
        tomato = 38 + rnd.randint(-3, 4)
        if t >= 8 and t <= 9:
            tomato = 96                     # sudden mandi price spike
        yield {"tick": t, "hour": 6 + t, "pantry": dict(pantry), "budget_left": budget,
               "gas_pct": gas, "tomato_price": tomato, "event": scripted.get(t)}


# ------------------------------------------------------------------ actuators
class Actuators:
    """The things the agent can actually change in the world."""
    # a menu mode can only be replaced by a more important one, otherwise the
    # last rule in the list would always win (found this the hard way in testing)
    MODE_RANK = {"normal": 0, "economy": 1, "satvik": 2, "soft_food": 3, "no_gas": 4}

    def __init__(self):
        self.shopping, self.menu_mode, self.portions_extra = [], "normal", 0

    def set_mode(self, mode):
        if self.MODE_RANK[mode] > self.MODE_RANK[self.menu_mode]:
            log("MODE", "%s -> %s" % (self.menu_mode, mode))
            self.menu_mode = mode
        elif mode != self.menu_mode:
            log("MODE", "keeping %s (outranks %s)" % (self.menu_mode, mode))

    def add_to_list(self, item):
        if item in self.shopping:
            return False
        self.shopping.append(item)
        return True

    def notify(self, who, text):
        log("NOTIFY", "to %s: %s" % (who, text))


# ---------------------------------------------------------------------- rules
class Rule:
    def __init__(self, name, cond, act):
        self.name, self.cond, self.act = name, cond, act


def build_rules():
    """Condition-action table. Order = priority (safety things first)."""
    R = []

    def low_gas(p, a):
        a.set_mode("no_gas")
        a.notify("Mom", "gas at %d%%, book cylinder, plan no-flame meals (curd rice, chilla pan)"
                 % p["gas_pct"])
    R.append(Rule("low_gas", lambda p: p["gas_pct"] < 15, low_gas))

    def fever(p, a):
        a.set_mode("soft_food")
        a.notify("Cook", "%s has fever -> khichdi / idli, less spice, no fried food"
                 % p["event"].split(":")[1])
    R.append(Rule("member_fever", lambda p: (p["event"] or "").startswith("member_fever"), fever))

    def guests(p, a):
        n = int(p["event"].split(":")[1])
        a.portions_extra = n
        log("ACTION", "guests_arriving: scaling all recipes by +%d portions" % n)
    R.append(Rule("guests_arriving", lambda p: (p["event"] or "").startswith("guests"), guests))

    def festival(p, a):
        a.set_mode("satvik")
        a.notify("Cook", "Ekadashi today, no onion/garlic/grains in today's menu")
    R.append(Rule("festival_menu", lambda p: (p["event"] or "").startswith("festival"), festival))

    def budget(p, a):
        a.set_mode("economy")
        log("ACTION", "budget_left Rs.%d (<25%% of weekly), switching to economy menu (dal, khichdi)"
            % p["budget_left"])
    R.append(Rule("budget_low", lambda p: p["budget_left"] < 0.25 * WEEKLY_BUDGET, budget))

    def tomato(p, a):
        log("ACTION", "tomato Rs.%d/kg is too high, swapping tomato gravies for tamarind/curd base"
            % p["tomato_price"])
    R.append(Rule("tomato_spike", lambda p: p["tomato_price"] > 80, tomato))

    def stock(p, a):
        for k, v in p["pantry"].items():
            if v < LOW_STOCK[k]:
                if a.add_to_list(k):
                    log("ACTION", "%s down to %.2f, added to shopping list" % (k, v))
                else:
                    log("ACTION", "%s still low (%.2f), already on the list" % (k, v))
    R.append(Rule("low_stock", lambda p: any(p["pantry"][k] < LOW_STOCK[k] for k in LOW_STOCK),
                  stock))

    def breakfast(p, a):
        a.notify("Cook", "7am: breakfast prep (check batter / atta)")
    R.append(Rule("breakfast_time", lambda p: p["hour"] == 7, breakfast))

    def dinner(p, a):
        a.notify("Cook", "7pm: start dinner prep, mode=%s" % a.menu_mode)
    R.append(Rule("dinner_time", lambda p: p["hour"] == 19, dinner))
    return R


# ------------------------------------------------------------------ main loop
def run(ticks=14):
    rules, act = build_rules(), Actuators()
    log("BOOT", "MealPilot reflex agent up, %d rules loaded" % len(rules))
    for p in sensor_stream(ticks):                           # 1. SENSE
        log("PERCEPT", "t=%02d %02d:00 gas=%d%% budget=Rs.%d tomato=Rs.%d event=%s"
            % (p["tick"], p["hour"], p["gas_pct"], p["budget_left"], p["tomato_price"], p["event"]))
        fired = 0
        for r in rules:                                      # 2. DECIDE (match rules on THIS percept)
            if r.cond(p):
                log("RULE", "%s fired" % r.name)
                r.act(p, act)                                # 3. ACT
                fired += 1
        if fired == 0:
            log("IDLE", "no rule matched")
    log("SUMMARY", "shopping list = %s" % act.shopping)
    log("SUMMARY", "final menu mode = %s, extra portions = %d" % (act.menu_mode, act.portions_extra))


if __name__ == "__main__":
    log.open()
    run()
