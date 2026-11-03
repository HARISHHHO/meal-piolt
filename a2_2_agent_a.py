
import socket
import time

from common import Logger, DISHES, RECIPES
from msgproto import send_msg, recv_msg

HOST, PORT = "127.0.0.1", 5055
log = Logger("a2_2_agent_a")


class PlannerAgent:
    def __init__(self):
        self.menu = ["paneer_masala", "dal_tadka", "rajma_chawal"]
        self.headcount, self.budget = 5, 450
        self.quotes_seen = 0
        self.done = False

    def state_msg(self):
        return {"type": "STATE", "agent": "planner-agent-A", "menu": self.menu,
                "headcount": self.headcount, "budget": self.budget}

    # ---- handlers (the "act on network payload" part of the assignment) ----
    def on_quote(self, msg, sock):
        self.quotes_seen += 1
        log("A", "quote Rs.%.2f vs budget Rs.%s -> %s"
            % (msg["total"], msg["budget"], "OK" if msg["within_budget"] else "TOO EXPENSIVE"))
        if not msg["within_budget"]:
            # drop the most expensive dish by cost per serving and replace with cheapest soft one
            worst = max(self.menu, key=lambda d: DISHES[d]["cost"])
            self.menu.remove(worst)
            self.menu.append("veg_khichdi")
            log("A", "dropping %s, adding veg_khichdi, re-sending menu" % worst)
            send_msg(sock, {"type": "MENU_UPDATE", "agent": "planner-agent-A", "menu": self.menu,
                            "headcount": self.headcount, "budget": self.budget})
        elif self.quotes_seen >= 2:
            log("A", "final basket accepted, saying BYE")
            send_msg(sock, {"type": "BYE", "agent": "planner-agent-A"})
            self.done = True

    def on_price_alert(self, msg, sock):
        item = msg["item"]
        heavy = [d for d in self.menu if RECIPES[d].get(item, 0) >= 0.06]
        log("A", "alert: %s is Rs.%s/kg. Tomato-heavy dishes in my menu: %s" % (item, msg["price"], heavy))
        spare = [d for d in ("moong_chilla", "veg_khichdi", "curd_rice") if d not in self.menu]
        for d in heavy:
            new = spare.pop(0)
            self.menu[self.menu.index(d)] = new
            log("A", "replacing %s with %s" % (d, new))
        if not heavy:
            return                                   # nothing affected, no need to bother B
        send_msg(sock, {"type": "MENU_UPDATE", "agent": "planner-agent-A", "menu": self.menu,
                        "headcount": self.headcount, "budget": self.budget})


def main():
    log.open()
    agent = PlannerAgent()
    sock = socket.socket()
    for attempt in range(20):                         # B may still be starting up
        try:
            sock.connect((HOST, PORT))
            break
        except ConnectionRefusedError:
            time.sleep(0.2)
    log("A", "connected to Agent-B at %s:%d" % (HOST, PORT))
    send_msg(sock, agent.state_msg())
    log("A ->", "STATE menu=%s" % agent.menu)

    handlers = {"QUOTE": agent.on_quote, "PRICE_ALERT": agent.on_price_alert}
    while not agent.done:
        msg = recv_msg(sock)
        if msg is None:
            break
        log("A <-", msg["type"])
        handlers.get(msg["type"], lambda m, s: log("A", "unknown message ignored"))(msg, sock)
    sock.close()
    log("A", "closed")


if __name__ == "__main__":
    main()
