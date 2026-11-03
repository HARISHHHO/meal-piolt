"""
Assignment 5.1 - Agent authentication and host integrity checks

Every command that reaches MealPilot is wrapped in a signed envelope:

    {"sender": "grocery_agent", "ts": 1730..., "nonce": "ab12..", "payload": {...}, "sig": "<hex>"}

Signature = Ed25519 over the canonical JSON of (sender, ts, nonce, payload).
The receiving agent only holds PUBLIC keys of trusted hosts, so it can verify but never forge.

Checks done in this order (first failure rejects the message):
  1. sender is in the trusted keyring
  2. timestamp is fresh (within 30 s)            -> stops old captured messages
  3. nonce never seen before                     -> stops replay inside the 30 s window
  4. signature verifies with that sender's key   -> stops tampering / forged identity
  5. sender is allowed to issue THIS command     -> stops a trusted host abusing power
"""
import hashlib
import json
import socket
import threading
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

from common import Logger
from msgproto import send_msg, recv_msg

log = Logger("a5_1_security")
HOST, PORT = "127.0.0.1", 5056
MAX_AGE = 30          # seconds

PERMISSIONS = {       # who may send which command
    "planner": {"SET_BUDGET", "ADD_TO_LIST", "SET_MENU", "REQUEST_QUOTE"},
    "grocery_agent": {"ADD_TO_LIST", "PRICE_UPDATE", "QUOTE"},
}


def canonical(env):
    body = {k: env[k] for k in ("sender", "ts", "nonce", "payload")}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def fingerprint(pub):
    raw = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()[:12]


class Signer:
    def __init__(self, name):
        self.name, self.key = name, Ed25519PrivateKey.generate()

    @property
    def public(self):
        return self.key.public_key()

    def sign(self, payload, ts=None, nonce=None):
        env = {"sender": self.name, "ts": ts if ts is not None else time.time(),
               "nonce": nonce or uuid.uuid4().hex[:12], "payload": payload}
        env["sig"] = self.key.sign(canonical(env)).hex()
        return env


class Verifier:
    def __init__(self, keyring):
        self.keyring = keyring              # name -> Ed25519PublicKey
        self.seen = set()

    def check(self, env):
        """returns (ok, reason)"""
        try:
            sender = env["sender"]
            if sender not in self.keyring:
                return False, "unknown sender '%s' (not in keyring)" % sender
            age = time.time() - env["ts"]
            if abs(age) > MAX_AGE:
                return False, "stale timestamp (%.0f s old)" % age
            if env["nonce"] in self.seen:
                return False, "replay detected (nonce %s already used)" % env["nonce"]
            try:
                self.keyring[sender].verify(bytes.fromhex(env["sig"]), canonical(env))
            except InvalidSignature:
                return False, "bad signature (payload altered or wrong key)"
            cmd = env["payload"].get("cmd")
            if cmd not in PERMISSIONS.get(sender, set()):
                return False, "'%s' is not allowed to run %s" % (sender, cmd)
        except (KeyError, ValueError, AttributeError) as e:
            return False, "malformed envelope (%s)" % e
        self.seen.add(env["nonce"])         # remember nonce only after the message is fully accepted
        return True, "ok"


def server(verifier, ready):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    ready.set()
    conn, _ = srv.accept()
    state = {"budget": 3000, "list": []}
    while True:
        env = recv_msg(conn)
        if env is None or env.get("payload", {}).get("cmd") == "QUIT_TEST":
            break
        ok, why = verifier.check(env)
        cmd = env.get("payload", {}).get("cmd")
        if ok:
            p = env["payload"]
            if cmd == "SET_BUDGET":
                state["budget"] = p["amount"]
            elif cmd == "ADD_TO_LIST":
                state["list"].append((p["item"], p["qty"]))
            log("AGENT", "ACCEPTED %s from %s -> state=%s" % (cmd, env["sender"], state))
            send_msg(conn, {"status": "ACCEPTED"})
        else:
            log("BLOCKED", "%s from '%s' REJECTED: %s" % (cmd, env.get("sender"), why))
            send_msg(conn, {"status": "REJECTED", "reason": why})
    conn.close()
    srv.close()


def main():
    log.open()
    planner, grocery, attacker = Signer("planner"), Signer("grocery_agent"), Signer("grocery_agent")
    keyring = {"planner": planner.public, "grocery_agent": grocery.public}
    for n, k in keyring.items():
        log("KEYRING", "trusted %-14s fingerprint %s" % (n, fingerprint(k)))
    log("KEYRING", "attacker's own key           fingerprint %s (NOT in keyring)" % fingerprint(attacker.public))

    ready = threading.Event()
    t = threading.Thread(target=server, args=(Verifier(keyring), ready), daemon=True)
    t.start()
    ready.wait()
    c = socket.create_connection((HOST, PORT))

    def send(label, env):
        log("SEND", "[%s] %s from '%s'" % (label, env["payload"].get("cmd"), env["sender"]))
        send_msg(c, env)
        reply = recv_msg(c)
        log("REPLY", "[%s] %s %s" % (label, reply["status"], reply.get("reason", "")))
        return reply

    results = []
    # 1. normal trusted traffic
    good = grocery.sign({"cmd": "ADD_TO_LIST", "item": "tomato", "qty": 2})
    results.append(("T1 valid command from grocery_agent", send("T1", good), "ACCEPTED"))
    results.append(("T2 valid SET_BUDGET from planner",
                    send("T2", planner.sign({"cmd": "SET_BUDGET", "amount": 2800})), "ACCEPTED"))

    # 2. attacks
    tampered = grocery.sign({"cmd": "ADD_TO_LIST", "item": "onion", "qty": 2})
    tampered["payload"]["qty"] = 500                      # changed AFTER signing
    results.append(("T3 tampered payload (qty 2 -> 500)", send("T3", tampered), "REJECTED"))

    forged = attacker.sign({"cmd": "ADD_TO_LIST", "item": "saffron", "qty": 50})   # claims to be grocery_agent
    results.append(("T4 attacker pretends to be grocery_agent", send("T4", forged), "REJECTED"))

    stranger = Signer("evil_bot").sign({"cmd": "SET_BUDGET", "amount": 99999})
    results.append(("T5 unknown sender evil_bot", send("T5", stranger), "REJECTED"))

    results.append(("T6 replay of T1 captured off the wire", send("T6", good), "REJECTED"))

    old = grocery.sign({"cmd": "ADD_TO_LIST", "item": "rice", "qty": 1}, ts=time.time() - 300)
    results.append(("T7 old message (5 min stale)", send("T7", old), "REJECTED"))

    over = grocery.sign({"cmd": "SET_BUDGET", "amount": 100000})   # valid signature, but not its job
    results.append(("T8 trusted host exceeding permissions", send("T8", over), "REJECTED"))

    send_msg(c, {"payload": {"cmd": "QUIT_TEST"}})
    c.close()
    t.join(timeout=2)

    log("SUMMARY", "-" * 60)
    passed = 0
    for name, reply, expected in results:
        ok = reply["status"] == expected
        passed += ok
        log("TEST", "%-42s expected %-8s got %-8s %s" % (name, expected, reply["status"], "PASS" if ok else "FAIL"))
    log("SUMMARY", "%d/%d checks passed, %d malicious requests blocked"
        % (passed, len(results), sum(1 for r in results if r[2] == "REJECTED" and r[1]["status"] == "REJECTED")))


if __name__ == "__main__":
    main()
