"""
Assignment 5.2 - MealPilot capstone: all modules wired into one agent

  Unit 1  a1_2  reflex rules + sensor stream       (core loop, percepts)
  Unit 2  a2_1  PriceMonitor worker thread         (background price feed)
          msgproto + sockets                       (planner <-> grocery agent over TCP)
  Unit 3  a3_1  negotiation with the vendor        (grocery agent haggles for the basket)
          a3_2  utility function                   (choose the dinners)
  Unit 4  a4_1  BDI loop                           (what to do now, replan on belief change)
          a4_2  knowledge base + weather           (profile adapts to weather)
  Unit 5  a5_1  Ed25519 signed envelopes           (every message authenticated)

Run:  python3 a5_2_capstone.py
"""
import queue
import socket
import threading
import time

from common import Logger, DISHES, RECIPES, PRICES, shopping_list, price_of
from msgproto import send_msg, recv_msg
import a1_2_reflex_agent as reflex
import a2_1_threads as workers
import a3_1_negotiation as neg
import a3_2_utility as util
import a4_1_bdi as bdi
import a4_2_knowledge_api as know
import a5_1_security as sec

log = Logger("a5_2_capstone")
HOST, PORT = "127.0.0.1", 5057
STATS = {"quotes": 0, "blocked": 0, "alerts": 0}


# ---------------------------------------------------------------- grocery agent (server)
def grocery_server(board, verifier, signer, ready, stop):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(5)
    srv.settimeout(0.3)
    ready.set()

    def handle(conn):
        while True:
            env = recv_msg(conn)
            if env is None:
                break
            ok, why = verifier.check(env)
            if not ok:
                STATS["blocked"] += 1
                log("GROCERY", "BLOCKED request from '%s': %s" % (env.get("sender"), why))
                send_msg(conn, {"status": "REJECTED", "reason": why})
                continue
            p = env["payload"]
            prices = dict(PRICES)
            prices.update({k: v for k, v in board.snapshot().items() if k in prices})
            market = price_of(p["need"], prices)
            log("GROCERY", "verified request from '%s', market value of basket Rs.%.0f"
                % (env["sender"], market))
            # haggle with the vendor (Unit 3)
            buyer = neg.Agent("BUYER", "buyer", start=round(market * 0.7), reserve=round(min(p["budget"], market * 1.15)), beta=1.0)
            vendor = neg.Agent("VENDOR", "supplier", start=round(market * 1.25), reserve=round(market * 0.95), beta=0.7)
            final = neg.negotiate(buyer, vendor)
            log("GROCERY", "vendor deal closed at Rs.%d after %d turns (asked Rs.%d)"
                % (final, buyer.turn, vendor.start))
            send_msg(conn, signer.sign({"cmd": "QUOTE", "market": market, "final": final,
                                        "asked": vendor.start}))

    threads = []
    while not stop.is_set():
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        t = threading.Thread(target=handle, args=(conn,), daemon=True)
        t.start()
        threads.append(t)
    srv.close()


# ------------------------------------------------------------------- the main agent
class MealPilot:
    def __init__(self):
        self.kb = know.KnowledgeBase()
        self.profile_agent = know.MealAgent(self.kb)
        self.signer = sec.Signer("planner")
        self.grocery_signer = sec.Signer("grocery_agent")
        self.verifier_g = sec.Verifier({"planner": self.signer.public})          # grocery checks planner
        self.verifier_p = sec.Verifier({"grocery_agent": self.grocery_signer.public})  # planner checks grocery
        self.board = workers.PriceBoard()
        self.alerts, self.stop = queue.Queue(), threading.Event()
        self.state = {"menu": [], "quote": None, "headcount": 4, "mode": "normal"}
        self.last_request = None
        self.sock = None

    # ---- Unit 1 + 4.2: sense the world
    def act_sense(self):
        rules, act = reflex.build_rules(), reflex.Actuators()
        for p in reflex.sensor_stream(4):
            for r in rules:
                if r.cond(p):
                    r.act(p, act)
        self.state["headcount"] = 4 + act.portions_extra
        self.state["mode"] = act.menu_mode
        weather = know.WeatherClient(self.kb).fetch("Delhi")
        self.profile_agent.adapt("Delhi", weather)

    # ---- Unit 3.2: choose dinners with utility (+ weather profile, - expensive tomato)
    def act_pick(self, avoid_tomato=False):
        def score(o):
            s = util.utility(o) + 0.08 * self.profile_agent.dish_score(o)
            if avoid_tomato and RECIPES[o].get("tomato", 0) >= 0.06:
                s -= 0.30
            return s
        feasible = [o for o in util.OPTIONS if util.violation(o) is None]
        menu = sorted(feasible, key=lambda o: -score(o))[:3]
        self.state["menu"] = menu
        log("PICK", "dinners chosen: %s" % [(m, round(score(m), 3)) for m in menu])

    # ---- Unit 2 + 3 + 5: signed request over TCP
    def act_order(self):
        if self.sock is None:
            self.sock = socket.create_connection((HOST, PORT))
        need = shopping_list(self.state["menu"], self.state["headcount"])
        env = self.signer.sign({"cmd": "REQUEST_QUOTE", "need": need, "budget": 2200})
        self.last_request = env
        log("ORDER", "signed REQUEST_QUOTE sent (sig %s...), basket=%s" % (env["sig"][:10], need))
        send_msg(self.sock, env)
        reply = recv_msg(self.sock)
        ok, why = self.verifier_p.check(reply)
        if not ok:
            log("ORDER", "reply rejected: %s" % why)
            return
        STATS["quotes"] += 1
        self.state["quote"] = reply["payload"]
        log("ORDER", "reply signature verified, vendor price Rs.%d (market Rs.%.0f)"
            % (reply["payload"]["final"], reply["payload"]["market"]))

    # ---- dashboard
    def act_show(self, beliefs, intention):
        q = self.state["quote"]
        prices = self.board.snapshot()
        line = "+" + "-" * 66 + "+"
        rows = [
            "MEALPILOT LIVE DASHBOARD",
            "intention : %s" % intention,
            "menu      : %s" % ", ".join(self.state["menu"]),
            "headcount : %d   mode: %s   style: %s" % (self.state["headcount"], self.state["mode"],
                                                       self.profile_agent.profile["menu_style"]),
            "tomato    : Rs.%s/kg   onion: Rs.%s/kg" % (prices["tomato"], prices["onion"]),
            "quote     : %s" % ("Rs.%d (vendor)  market Rs.%.0f" % (q["final"], q["market"]) if q else "none"),
            "security  : %d quotes verified, %d requests blocked" % (STATS["quotes"], STATS["blocked"]),
        ]
        log.raw(line)
        for r in rows:
            log.raw("| %-64s |" % r)
        log.raw(line)


def run_bdi(agent_core, bdi_agent, label):
    """run the BDI loop until nothing is left to do, executing each step for real"""
    n = 0
    while True:
        n += 1
        if not bdi_agent.step(n):
            break
        desire, text = bdi_agent.last_step
        kind = text.split(":")[0]
        if kind == "SENSE" and desire == "plan_dinners":
            agent_core.act_sense()
        elif kind == "PICK":
            agent_core.act_pick(avoid_tomato=bool(bdi_agent.b.get("tomato_price") > 60))
        elif kind == "ORDER":
            agent_core.act_order()
        elif kind == "SHOW":
            agent_core.act_show(bdi_agent.b, desire)


def main():
    log.open()
    Logger.redirect = log
    neg.log = lambda tag, msg: None          # keep the negotiation quiet here, summary is logged below
    core = MealPilot()

    log("BOOT", "starting workers: price monitor + grocery agent")
    mon = workers.PriceMonitor(core.board, core.alerts, core.stop, interval=0.4)
    mon.start()
    ready = threading.Event()
    threading.Thread(target=grocery_server, daemon=True,
                     args=(core.board, core.verifier_g, core.grocery_signer, ready, core.stop)).start()
    ready.wait()

    # BDI set up for the capstone
    beliefs = bdi.Beliefs(tomato_price=40, budget_left=2200)
    desires = [
        bdi.Desire("plan_dinners", 3, lambda b: True,
                   lambda b: ["SENSE: read telemetry, weather and guests",
                              "PICK: choose 3 dinners by utility",
                              "ORDER: signed quote request to grocery agent",
                              "SHOW: refresh dashboard"], {"tomato_price": 1}),
        bdi.Desire("react_to_price_spike", 4, lambda b: b.get("tomato_price") > 60,
                   lambda b: ["SENSE: price monitor reported tomato spike",
                              "PICK: re-choose dinners, avoid tomato-heavy dishes",
                              "ORDER: signed quote request to grocery agent",
                              "SHOW: refresh dashboard"], {"tomato_price": 1}),
    ]
    agent = bdi.BDIAgent(beliefs, desires)

    log("CYCLE", "===== cycle 1: normal planning =====")
    run_bdi(core, agent, "c1")

    log("CYCLE", "===== waiting for background price alert (worker thread) =====")
    kind, item, old, new = core.alerts.get(timeout=6)
    STATS["alerts"] += 1
    log("ALERT", "%s: %s Rs.%.1f -> Rs.%.1f (from price-monitor thread)" % (kind, item, old, new))
    beliefs.update("tomato_price", new, "price-monitor")

    log("CYCLE", "===== cycle 2: intention updated because of new belief =====")
    run_bdi(core, agent, "c2")

    log("CYCLE", "===== cycle 3: someone attacks the grocery agent =====")
    fake = sec.Signer("planner")                                   # attacker claims to be planner
    forged = fake.sign({"cmd": "REQUEST_QUOTE", "need": {"saffron": 40}, "budget": 99999})
    for label, env in (("forged signature", forged), ("replayed old request", core.last_request)):
        log("ATTACK", "sending %s" % label)
        send_msg(core.sock, env)
        reply = recv_msg(core.sock)
        log("ATTACK", "agent answered: %s" % reply["status"])
    core.act_show(beliefs, "idle (after attack)")

    core.stop.set()
    time.sleep(0.4)
    log("SUMMARY", "price polls=%d, alerts handled=%d, intention shifts/replans via BDI=%d"
        % (len(mon.latencies), STATS["alerts"], len(agent.history)))
    log("SUMMARY", "verified quotes=%d, blocked attacks=%d, final menu=%s"
        % (STATS["quotes"], STATS["blocked"], core.state["menu"]))


if __name__ == "__main__":
    main()
