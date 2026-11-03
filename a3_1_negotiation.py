"""
Assignment 3.1 - Multi-agent negotiation (MealPilot buyer vs vegetable supplier)

Two separate agent objects, no shared memory, they only talk through messages
(an inbox each). Protocol is a small version of contract net + alternating offers:

   Buyer  --CFP-->        Supplier       (call for proposals: weekly veg basket)
   Buyer  <-PROPOSE--     Supplier       (opening ask)
   Buyer  --COUNTER-->    Supplier       (keep going until someone ACCEPTs)
   ...
   X      --ACCEPT-->     Y
   Y      --CONFIRM-->    X
   X      --ACK-->        Y              (3 way handshake = consensus)

Each agent has a utility in [0,1] for a price and gives up utility slowly over time:
    target(k) = 1 - (1 - u_min) * (k / T) ** (1 / beta)
beta < 1 means stubborn (concedes late), beta > 1 means concedes early.
It ACCEPTS when the offer it just received is at least as good as what it would have offered next.
"""
import json
from common import Logger

log = Logger("a3_1_negotiation")


class Agent:
    def __init__(self, name, role, start, reserve, beta, T=10, u_min=0.05):
        self.name, self.role = name, role
        self.start, self.reserve = start, reserve      # best price for me / worst I can live with
        self.beta, self.T, self.u_min = beta, T, u_min
        self.inbox, self.turn = [], 0
        self.trace = []                                # (turn, my offer price)
        self.agreed = None

    def utility(self, price):
        if self.role == "buyer":
            return (self.reserve - price) / (self.reserve - self.start)
        return (price - self.reserve) / (self.start - self.reserve)

    def target(self, k):
        return 1 - (1 - self.u_min) * (min(k, self.T) / self.T) ** (1 / self.beta)

    def price_for(self, u):
        if self.role == "buyer":
            return round(self.reserve - u * (self.reserve - self.start))
        return round(self.reserve + u * (self.start - self.reserve))

    def send(self, other, msg_type, price=None, note=""):
        msg = {"type": msg_type, "from": self.name, "turn": self.turn, "price": price}
        other.inbox.append(msg)
        u = "" if price is None else " U(self)=%.2f" % self.utility(price)
        log("MSG", "%-8s -> %-8s %-8s %s%s %s"
            % (self.name, other.name, msg_type, "" if price is None else "price=Rs.%d" % price, u, note))
        return msg

    def react(self, other):
        """read the newest message and answer it. returns True when negotiation is over."""
        msg = self.inbox.pop(0)
        if msg["type"] == "CFP":
            self.send(other, "PROPOSE", self.price_for(1.0), "(opening ask)")
            self.trace.append((0, self.price_for(1.0)))
            return False
        if msg["type"] == "ACCEPT":
            self.agreed = msg["price"]
            self.send(other, "CONFIRM", msg["price"])
            return False
        if msg["type"] == "CONFIRM":
            self.send(other, "ACK", msg["price"], "(handshake done)")
            return True
        if msg["type"] == "ACK":
            return True
        # PROPOSE or COUNTER
        self.turn += 1
        u_recv, u_next = self.utility(msg["price"]), self.target(self.turn)
        log("THINK", "%-8s turn %d: got Rs.%d (U=%.2f), my target U=%.2f -> %s"
            % (self.name, self.turn, msg["price"], u_recv, u_next,
               "ACCEPT" if u_recv >= u_next else "counter"))
        if u_recv >= u_next and u_recv >= 0:
            self.agreed = msg["price"]
            self.send(other, "ACCEPT", msg["price"])
            return False
        if self.turn > self.T:
            self.send(other, "REJECT", None, "(deadline passed)")
            return True
        offer = self.price_for(u_next)
        self.trace.append((self.turn, offer))
        self.send(other, "COUNTER", offer)
        return False


def negotiate(buyer, supplier):
    log("START", "item = weekly vegetable basket (5 kg mix). buyer window Rs.%d-%d, supplier window Rs.%d-%d"
        % (buyer.start, buyer.reserve, supplier.reserve, supplier.start))
    buyer.send(supplier, "CFP", None, "(need basket, max %d rounds)" % buyer.T)
    done = supplier.react(buyer)                       # supplier answers the CFP with PROPOSE
    turn_owner = buyer
    while not done:
        other = supplier if turn_owner is buyer else buyer
        if not turn_owner.inbox:
            turn_owner = other
            continue
        done = turn_owner.react(other)
        # whoever got the message acts next, so just alternate
        turn_owner = other
        if done and other.inbox:                       # let the last ACK be consumed too
            other.react(turn_owner)
    return buyer.agreed


if __name__ == "__main__":
    log.open()
    buyer = Agent("BUYER", "buyer", start=600, reserve=900, beta=1.0)
    supplier = Agent("SUPPLIER", "supplier", start=1100, reserve=720, beta=0.7)
    final = negotiate(buyer, supplier)
    log("RESULT", "agreed price Rs.%d  U(buyer)=%.2f  U(supplier)=%.2f  (sum=%.2f)"
        % (final, buyer.utility(final), supplier.utility(final),
           buyer.utility(final) + supplier.utility(final)))
    json.dump({"buyer": buyer.trace, "supplier": supplier.trace, "final": final},
              open("logs/a3_1_trace.json", "w"))
