"""
Assignment 4.2 - Knowledge representation + live REST API (MealPilot)

Knowledge lives in knowledge.json (dish tags, weather rules, substitutions, city coordinates).
Live data comes from the Open-Meteo REST API (free, no API key needed):
    https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&current=...

Flow: fetch JSON -> parse into a Weather object -> match rule from the knowledge base
      -> overwrite the agent's profile properties -> re-rank dishes.

If the network call fails the client falls back to cache/weather_snapshot.json and says so in
the log (it never pretends the data was live). Use --require-live to disable the fallback.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

from common import Logger, DISHES, BASE_DIR

log = Logger("a4_2_knowledge_api")
API = "https://api.open-meteo.com/v1/forecast"


class KnowledgeBase:
    def __init__(self, path=os.path.join(BASE_DIR, "knowledge.json")):
        with open(path) as fh:
            self.k = json.load(fh)

    def tags(self, dish):
        return self.k["dish_tags"].get(dish, [])

    def rule_for(self, w):
        """first rule whose 'if' block matches the weather, otherwise default profile"""
        for rule in self.k["weather_rules"]:
            c = rule["if"]
            if ("temp_c_gte" in c and w["temp_c"] >= c["temp_c_gte"]) or \
               ("temp_c_lte" in c and w["temp_c"] <= c["temp_c_lte"]) or \
               ("rain_mm_gte" in c and w["rain_mm"] >= c["rain_mm_gte"]):
                return rule["name"], rule["then"]
        return "default", self.k["default_profile"]

    def substitute(self, item):
        return self.k["substitutions"].get(item, [])


class WeatherClient:
    def __init__(self, kb, require_live=False):
        self.kb, self.require_live = kb, require_live
        self.live_ok = 0
        self.fallback_used = 0

    def fetch(self, city):
        pos = self.kb.k["cities"][city]
        q = urllib.parse.urlencode({"latitude": pos["lat"], "longitude": pos["lon"],
                                    "current": "temperature_2m,relative_humidity_2m,precipitation"})
        url = API + "?" + q
        log("HTTP", "GET %s" % url)
        try:
            with urllib.request.urlopen(url, timeout=6) as resp:
                raw = json.loads(resp.read().decode())
            cur = raw["current"]                          # parse the unstructured JSON
            self.live_ok += 1
            log("HTTP", "200 OK  LIVE FETCH OK for %s" % city)
            return {"temp_c": cur["temperature_2m"], "humidity": cur["relative_humidity_2m"],
                    "rain_mm": cur["precipitation"], "source": "live"}
        except Exception as e:                            # URLError, timeout, bad json ...
            log("HTTP", "request failed: %s" % e)
            if self.require_live:
                raise
            snap = json.load(open(os.path.join(BASE_DIR, "cache", "weather_snapshot.json")))[city]
            self.fallback_used += 1
            log("HTTP", "FALLBACK: using cached SAMPLE snapshot for %s (not live data)" % city)
            return dict(snap, source="snapshot")


class MealAgent:
    def __init__(self, kb):
        self.kb = kb
        self.profile = dict(kb.k["default_profile"])

    def dish_score(self, d):
        tags = self.kb.tags(d)
        s = 1.0 + 0.5 * sum(t in self.profile["prefer"] for t in tags) \
            - 1.0 * sum(t in self.profile["avoid"] for t in tags)
        if DISHES[d]["prep"] > self.profile["cook_time_cap_min"]:
            s -= 2
        return round(s, 2)

    def rank(self, top=3):
        return sorted(((self.dish_score(d), d) for d in DISHES), key=lambda x: (-x[0], x[1]))[:top]

    def adapt(self, city, weather):
        rule, then = self.kb.rule_for(weather)
        before = dict(self.profile)
        self.profile.update(then)                         # properties change instantly
        log("ADAPT", "%s: %.1fC, rain %.1fmm (%s) -> rule '%s'"
            % (city, weather["temp_c"], weather["rain_mm"], weather["source"], rule))
        for k in ("menu_style", "water_litres", "cook_time_cap_min", "prefer", "avoid"):
            if before[k] != self.profile[k]:
                log("PROFILE", "  %-18s %s -> %s" % (k, before[k], self.profile[k]))
        log("RANK", "  top dishes now: %s" % self.rank())


def main():
    log.open()
    kb = KnowledgeBase()
    client = WeatherClient(kb, require_live="--require-live" in sys.argv)
    agent = MealAgent(kb)
    log("KB", "loaded %d dish tags, %d weather rules, %d substitution entries"
        % (len(kb.k["dish_tags"]), len(kb.k["weather_rules"]), len(kb.k["substitutions"])))
    log("RANK", "default ranking: %s" % agent.rank())
    for city in ("Delhi", "Mumbai", "Shimla"):
        agent.adapt(city, client.fetch(city))
    log("KB", "substitutes for tomato (if price spikes): %s" % kb.substitute("tomato"))
    log("SUMMARY", "live fetches ok=%d, fallbacks used=%d" % (client.live_ok, client.fallback_used))


if __name__ == "__main__":
    main()
