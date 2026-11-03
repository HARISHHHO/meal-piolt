"""Extra pictures for the review guide: BDI timeline, lifecycle sequence, dashboard screenshot."""
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ------------------------------------------------ 1. BDI intention timeline from the real log
steps, n, cur_step = [], 0, None
events = {}
for line in open("logs/a4_1_bdi.log"):
    m = re.search(r"\[STEP\s*\] ----- (\d+)", line)
    if m:
        n = int(m.group(1))
    m = re.search(r"\[EXEC\s*\] \[(\w+)\] step (\d+)/(\d+): (.*)", line)
    if m:
        steps.append((n, m.group(1), int(m.group(2)), m.group(4)))
    if "[EVENT" in line:
        events[n] = line.split("arrives: ")[1].strip()
    if "[REWIND" in line or "[REPLAN" in line:
        events.setdefault(n, "")
lanes = {"plan_weekly_menu": 1, "care_for_sick_member": 0}
fig, ax = plt.subplots(figsize=(9, 3.4))
for (n, d, i, txt) in steps:
    y = lanes[d]
    col = "#3B6EA8" if y else "#B03A3A"
    ax.add_patch(FancyBboxPatch((n - 0.42, y - 0.28), 0.84, 0.56, boxstyle="round,pad=0.02", fc=col, ec="none"))
    ax.text(n, y, "s%d" % i, ha="center", va="center", color="white", fontsize=8)
for n, e in events.items():
    if e:
        ax.annotate("EVENT: " + e, (n, 1.55), ha="center", fontsize=8, color="#444",
                    bbox=dict(boxstyle="round", fc="#FFF4DD", ec="#C58A1B"))
        ax.plot([n, n], [-0.45, 1.45], ls=":", color="#C58A1B", lw=1)
ax.set_yticks([0, 1]); ax.set_yticklabels(["care_for_sick_member\n(priority 5)", "plan_weekly_menu\n(priority 3)"], fontsize=8)
ax.set_xticks(range(1, max(s[0] for s in steps) + 1)); ax.set_xlabel("agent step", fontsize=9)
ax.set_xlim(0.4, max(s[0] for s in steps) + 0.6); ax.set_ylim(-0.6, 1.95)
ax.set_title("Which intention the BDI agent is executing at each step (from the real run)", fontsize=10)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig("diagrams/r_bdi_timeline.png", dpi=170); plt.close()

# ------------------------------------------------ 2. lifecycle sequence diagram
actors = ["Price monitor\n(thread)", "MealPilot\n(BDI + utility)", "Grocery agent\n(TCP server)", "Vendor\n(negotiation)", "Attacker"]
xs = [0, 2.2, 4.6, 6.8, 9]
msgs = [
    (1, 1, "1 sense: telemetry + weather -> beliefs", True),
    (1, 1, "2 BDI picks intention, utility picks dinners", True),
    (1, 2, "3 signed REQUEST_QUOTE (Ed25519)", False),
    (2, 2, "4 verify: sender, time, nonce, signature, permission", True),
    (2, 3, "5 CFP", False), (3, 2, "6 PROPOSE / COUNTER ... ACCEPT, ACK", False),
    (2, 1, "7 signed QUOTE", False),
    (0, 1, "8 PRICE_ALERT via queue -> belief update", False),
    (1, 1, "9 intention shifts, replans, new quote", True),
    (4, 2, "10 forged / replayed request", False),
    (2, 4, "11 REJECTED (blocked)", False),
]
fig, ax = plt.subplots(figsize=(9.5, 5.6))
for x, a in zip(xs, actors):
    ax.text(x, 0.4, a, ha="center", va="bottom", fontsize=8, bbox=dict(boxstyle="round", fc="#EAF2FB", ec="#3B6EA8"))
    ax.plot([x, x], [0.3, -len(msgs) - 0.5], color="#999", lw=1, ls="--")
for i, (a, b, t, selfm) in enumerate(msgs):
    y = -i - 0.4
    if selfm:
        ax.annotate("", xy=(xs[a] + 0.02, y - 0.25), xytext=(xs[a] + 0.02, y), arrowprops=dict(arrowstyle="->", color="#3C8C3C"))
        ax.text(xs[a] + 0.12, y - 0.1, t, fontsize=7.5, va="center", color="#2d6a2d")
    else:
        bad = "REJECTED" in t or "forged" in t
        ax.annotate("", xy=(xs[b], y), xytext=(xs[a], y),
                    arrowprops=dict(arrowstyle="->", color="#B03A3A" if bad else "#3B6EA8", lw=1.3))
        ax.text((xs[a] + xs[b]) / 2, y + 0.08, t, ha="center", fontsize=7.5)
ax.set_xlim(-1, 10.3); ax.set_ylim(-len(msgs) - 0.6, 1.0); ax.axis("off")
ax.set_title("Full lifecycle of one production run", fontsize=10)
plt.tight_layout(); plt.savefig("diagrams/r_sequence.png", dpi=170); plt.close()

# ------------------------------------------------ 3. dashboard screenshots from the real log
blocks, cur = [], []
for line in open("logs/a5_2_capstone.log"):
    line = line.rstrip("\n")
    if line.startswith("+----") or line.startswith("| "):
        cur.append(line)
        if line.startswith("+----") and len(cur) > 1:
            blocks.append(cur); cur = []
    elif cur and not line.startswith("+----"):
        cur = []
for idx, b in ((1, blocks[1]), (2, blocks[-1])):
    fig = plt.figure(figsize=(7.4, 2.05), facecolor="#1e1e1e")
    fig.text(0.03, 0.95, "$ python3 a5_2_capstone.py", color="#9cdcfe", family="monospace", fontsize=8, va="top")
    fig.text(0.03, 0.83, "\n".join(b), color="#d4d4d4", family="monospace", fontsize=7.6, va="top", linespacing=1.35)
    plt.savefig("diagrams/r_dashboard%d.png" % idx, dpi=170, facecolor="#1e1e1e"); plt.close()
print("pics ok", len(blocks), "dashboards")
