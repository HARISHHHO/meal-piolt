"""
Assignment 2.2 - Agent-B (Grocery / Market agent)  [run this in Terminal 1]

Plain TCP server on localhost. It receives Agent-A's STATE payload, works out
what the shopping basket costs and replies with a QUOTE. After that it pushes a
PROACTIVE PRICE_ALERT that Agent-A has to handle by itself.
"""
import socket
import sys

from common import Logger, RECIPES, PRICES, shopping_list, price_of
from msgproto import send_msg, recv_msg

HOST, PORT = "127.0.0.1", 5055
log = Logger("a2_2_agent_b")


def make_quote(menu, headcount, budget, prices):
    need = shopping_list(menu, headcount)
    total = price_of(need, prices)
    return {"type": "QUOTE", "from": "grocery-agent-B", "items": need, "total": total,
            "within_budget": total <= budget, "budget": budget}


def main():
    log.open()
    prices = dict(PRICES)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    log("B", "listening on %s:%d" % (HOST, PORT))
    conn, addr = srv.accept()
    log("B", "connection from %s:%d" % addr)

    while True:
        msg = recv_msg(conn)
        if msg is None:
            log("B", "peer closed connection")
            break
        log("B <-", "%s from %s" % (msg["type"], msg.get("agent", "?")))

        if msg["type"] == "STATE":
            log("B", "state: menu=%s headcount=%d budget=Rs.%s"
                % (msg["menu"], msg["headcount"], msg["budget"]))
            q = make_quote(msg["menu"], msg["headcount"], msg["budget"], prices)
            send_msg(conn, q)
            log("B ->", "QUOTE total=Rs.%.2f within_budget=%s" % (q["total"], q["within_budget"]))

            # B notices something on its own and pushes it WITHOUT being asked
            prices["tomato"] = 92
            alert = {"type": "PRICE_ALERT", "item": "tomato", "price": 92,
                     "instruction": "avoid tomato-heavy dishes, suggest substitute"}
            send_msg(conn, alert)
            log("B ->", "PRICE_ALERT (proactive) tomato -> Rs.92/kg")

        elif msg["type"] == "MENU_UPDATE":
            log("B", "new menu received: %s" % msg["menu"])
            q = make_quote(msg["menu"], msg["headcount"], msg["budget"], prices)
            send_msg(conn, q)
            log("B ->", "QUOTE total=Rs.%.2f within_budget=%s" % (q["total"], q["within_budget"]))

        elif msg["type"] == "BYE":
            log("B", "BYE received, shutting down")
            break
    conn.close()
    srv.close()


if __name__ == "__main__":
    main()
