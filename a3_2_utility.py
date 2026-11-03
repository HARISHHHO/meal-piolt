"""
Assignment 3.2 - Self interested utility agent (MealPilot picks tonight's dinner)

The agent only cares about its own utility score. It first throws away options
that break hard constraints (allergy, budget, time), then scores the rest and
picks the argmax. A brute force check at the end proves the pick is really the max.

    U(d) = w_n*N(d) + w_c*C(d) + w_t*T(d) + w_p*P(d) - penalty(d)

  N = nutrition fit   0.4*kcal_fit + 0.4*protein_score + 0.2*fibre_score
  C = cost score      1 - cost/150
  T = time score      1 - prep/60
  P = family rating   rating/5   (from past feedback)
  penalty = 0.15 if the dish was served in the last 2 days (variety)
"""
from common import Logger, DISHES

log = Logger("a3_2_utility")

# what the family thinks of each dish (1-5) and how many days ago it was last served
FAMILY = {
    "dal_tadka": (4, 1), "rajma_chawal": (5, 6), "chole_roti": (4, 3), "paneer_masala": (5, 4),
    "veg_khichdi": (3, 9), "idli_sambar": (4, 2), "egg_curry": (3, 5), "chicken_curry": (5, 7),
    "curd_rice": (3, 8), "moong_chilla": (2, 10),
}
OPTIONS = list(FAMILY.keys())                    # the 10 options on the table tonight

CONSTRAINTS = {"allergies": {"egg"}, "max_cost": 100, "max_prep": 55, "kcal_target": 550}
WEIGHTS = {"n": 0.35, "c": 0.20, "t": 0.15, "p": 0.30}


def clip(x):
    return max(0.0, min(1.0, x))


def terms(dish_id):
    d = DISHES[dish_id]
    rating, last = FAMILY[dish_id]
    kcal_fit = clip(1 - abs(d["kcal"] - CONSTRAINTS["kcal_target"]) / CONSTRAINTS["kcal_target"])
    n = 0.4 * kcal_fit + 0.4 * clip(d["protein"] / 30) + 0.2 * clip(d["fibre"] / 12)
    c = clip(1 - d["cost"] / 150)
    t = clip(1 - d["prep"] / 60)
    p = rating / 5
    pen = 0.15 if last <= 2 else 0.0
    return n, c, t, p, pen


def utility(dish_id, w=None):
    w = w or WEIGHTS
    n, c, t, p, pen = terms(dish_id)
    return w["n"] * n + w["c"] * c + w["t"] * t + w["p"] * p - pen


def violation(dish_id):
    d = DISHES[dish_id]
    if set(d["allergens"]) & CONSTRAINTS["allergies"]:
        return "allergen (%s)" % ",".join(d["allergens"])
    if d["cost"] > CONSTRAINTS["max_cost"]:
        return "cost Rs.%d > Rs.%d" % (d["cost"], CONSTRAINTS["max_cost"])
    if d["prep"] > CONSTRAINTS["max_prep"]:
        return "prep %d min > %d" % (d["prep"], CONSTRAINTS["max_prep"])
    return None


def choose(options, w=None):
    feasible = [o for o in options if violation(o) is None]
    return max(feasible, key=lambda o: utility(o, w)), feasible


def main():
    log.open()
    log("CONFIG", "weights=%s" % WEIGHTS)
    log("CONFIG", "constraints=%s" % {k: sorted(v) if isinstance(v, set) else v
                                       for k, v in CONSTRAINTS.items()})
    log.raw("")
    log.raw("%-15s %5s %5s %5s %5s %5s | %6s  %s" % ("dish", "N", "C", "T", "P", "pen", "U", "status"))
    log.raw("-" * 78)
    rows = []
    for o in OPTIONS:
        n, c, t, p, pen = terms(o)
        bad = violation(o)
        u = utility(o)
        rows.append((o, n, c, t, p, pen, u, bad))
        log.raw("%-15s %5.2f %5.2f %5.2f %5.2f %5.2f | %6.3f  %s"
                % (o, n, c, t, p, pen, u, "FILTERED: " + bad if bad else ""))
    log.raw("")

    best, feasible = choose(OPTIONS)
    log("FILTER", "%d of %d options survive the hard constraints" % (len(feasible), len(OPTIONS)))
    ranked = sorted(feasible, key=lambda o: -utility(o))
    for i, o in enumerate(ranked[:3], 1):
        log("RANK", "#%d %-15s U=%.3f" % (i, o, utility(o)))
    log("DECIDE", "agent picks '%s' (%s) with U=%.3f" % (best, DISHES[best]["label"], utility(best)))

    # --- proof it is the real maximum: check every feasible option one by one ---
    brute = max(feasible, key=lambda o: utility(o))
    assert brute == best and all(utility(best) >= utility(o) for o in feasible)
    log("VERIFY", "brute force over %d feasible options agrees, nothing scores higher: PASS"
        % len(feasible))
    # --- also report any illegal option that would have scored higher (shows the filter matters) ---
    for o, *_, u, bad in rows:
        if bad and u > utility(best):
            log("NOTE", "%s scored %.3f (higher than winner) but is illegal: %s" % (o, u, bad))

    # --- sensitivity: does the pick change if the family cares more about cost / health? ---
    for name, w in {"budget-first": {"n": 0.15, "c": 0.55, "t": 0.15, "p": 0.15},
                    "health-first": {"n": 0.60, "c": 0.10, "t": 0.10, "p": 0.20},
                    "kids-favourite": {"n": 0.10, "c": 0.10, "t": 0.10, "p": 0.70}}.items():
        b, _ = choose(OPTIONS, w)
        log("WHATIF", "%-14s weights -> picks %s (U=%.3f)" % (name, b, utility(b, w)))

    import json
    json.dump({"rows": rows, "best": best}, open("logs/a3_2_rows.json", "w"))


if __name__ == "__main__":
    main()
