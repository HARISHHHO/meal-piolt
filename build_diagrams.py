"""Draws the architecture diagrams (graphviz) and the three result charts (matplotlib)."""
import json
import subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HEAD = ('digraph G { rankdir=%s; bgcolor="white"; pad=0.2; nodesep=0.35; ranksep=0.5;\n'
        'node [shape=box, style="rounded,filled", fillcolor="#EAF2FB", color="#3B6EA8", '
        'fontname="DejaVu Sans", fontsize=11, margin="0.15,0.08"];\n'
        'edge [fontname="DejaVu Sans", fontsize=9, color="#555555"];\n')


def dot(name, body, rankdir="LR"):
    src = HEAD % rankdir + body + "}\n"
    open("diagrams/%s.dot" % name, "w").write(src)
    subprocess.run(["dot", "-Tpng", "-Gdpi=170", "diagrams/%s.dot" % name, "-o", "diagrams/%s.png" % name],
                   check=True)


ENV = 'fillcolor="#FFF4DD", color="#C58A1B"'
ACT = 'fillcolor="#E6F5E6", color="#3C8C3C"'
SEC = 'fillcolor="#FBE5E5", color="#B03A3A"'

dot("d1_1", f'''
env [label="Environment\\nIndian household kitchen\\n(pantry, budget, members,\\nmandi prices, weather)", {ENV}];
sens [label="Sensors\\npantry levels, gas %,\\nbudget, price feed,\\nuser messages, weather API"];
brain [label="MealPilot agent program\\npercept -> beliefs -> utility\\n-> menu decision"];
act [label="Actuators\\nweekly menu, shopping list,\\ncook notifications,\\norders to grocery agent", {ACT}];
perf [label="Performance measure\\nnutrition fit, cost within budget,\\nfamily rating, low waste", {SEC}];
env -> sens [label="percepts"]; sens -> brain; brain -> act [label="actions"]; act -> env [label="changes"];
perf -> brain [style=dashed, label="evaluates"];
''')

dot("d1_2", f'''
s [label="Mock sensor stream\\n(pantry, gas, budget,\\nprice, events)", {ENV}];
p [label="Percept\\n(current tick only)"];
r [label="Condition-action rules\\nlow_gas, fever, guests,\\nfestival, budget, tomato,\\nstock, meal time"];
a [label="Actuators\\nmenu mode, shopping list,\\nnotifications", {ACT}];
l [label="Reaction log"];
s -> p -> r -> a -> l; a -> s [style=dashed, label="world changes"];
''')

dot("d2_1", f'''
subgraph cluster_main {{ label="Main thread (UI loop, 100 ms tick)"; fontname="DejaVu Sans"; style=dashed; color="#888888";
  ui [label="UI loop\\nnever blocks"]; drain [label="drain alerts\\nget_nowait()"]; submit [label="submit jobs"]; }}
subgraph cluster_w {{ label="Background threads"; fontname="DejaVu Sans"; style=dashed; color="#888888";
  mon [label="PriceMonitor\\n(daemon thread)\\npolls every 0.6 s", {ACT}];
  pool [label="ThreadPoolExecutor\\n3 scorer workers", {ACT}]; }}
board [label="PriceBoard\\n(shared dict + Lock)", {SEC}];
q [label="queue.Queue\\nPRICE_ALERT", {ENV}];
ev [label="threading.Event\\n(stop)", {ENV}];
mon -> board [label="update()"]; ui -> board [label="snapshot()"];
mon -> q [label="put"]; q -> drain; drain -> ui; ui -> submit -> pool; ev -> mon [style=dashed];
''', rankdir="LR")

dot("d2_2", f'''
subgraph cluster_t2 {{ label="Terminal 2"; fontname="DejaVu Sans"; style=rounded;
  A [label="Agent-A\\nMeal Planner\\n(client)"]; ha [label="handlers\\non_quote\\non_price_alert", {ACT}]; }}
subgraph cluster_t1 {{ label="Terminal 1"; fontname="DejaVu Sans"; style=rounded;
  B [label="Agent-B\\nGrocery / Market\\n(server :5055)"]; hb [label="quote engine\\nprice table", {ACT}]; }}
A -> B [label="STATE / MENU_UPDATE / BYE\\n(4-byte length + JSON over TCP)"];
B -> A [label="QUOTE\\nPRICE_ALERT (proactive)"];
A -> ha [dir=both, style=dashed]; B -> hb [dir=both, style=dashed];
''')

dot("d3_1", f'''
B [label="BUYER agent\\nstart Rs.600  reserve Rs.900\\nbeta=1.0 (linear)"];
S [label="SUPPLIER agent\\nstart Rs.1100  reserve Rs.720\\nbeta=0.7 (stubborn)"];
B -> S [label="1. CFP"]; S -> B [label="2. PROPOSE (opening ask)"];
B -> S [label="3. COUNTER (rising)"]; S -> B [label="4. COUNTER (falling)"];
B -> S [label="5. ACCEPT"]; S -> B [label="6. CONFIRM"]; B -> S [label="7. ACK"];
''', rankdir="TB")

dot("d3_2", f'''
o [label="10 candidate dinners", {ENV}];
f [label="Hard constraint filter\\nallergy, cost cap,\\nprep time cap", {SEC}];
t [label="Term scoring\\nN nutrition, C cost,\\nT time, P family rating,\\nvariety penalty"];
u [label="Utility U = sum(w * term) - penalty"];
m [label="argmax over feasible\\n= chosen dinner", {ACT}];
v [label="Brute-force verification\\n(assert no option beats it)"];
o -> f -> t -> u -> m -> v;
''')

dot("d4_1", f'''
env [label="Environment\\n(unexpected events)", {ENV}];
bel [label="BELIEFS\\nbudget, guests, sick_member,\\ngas_pct, tomato_price"];
des [label="DESIRES\\nplan_weekly_menu (3)\\ncare_for_sick_member (5)"];
filt [label="Deliberation\\nactive desires -> highest priority"];
int [label="INTENTION\\ncurrent plan + step pointer\\n(suspended stack)", {ACT}];
rep [label="Replan / rewind\\nstale steps recalculated", {SEC}];
env -> bel [label="perceive"]; bel -> des [label="activates"]; des -> filt -> int;
bel -> rep [label="change"]; rep -> int; int -> env [label="execute step"];
''')

dot("d4_2", f'''
api [label="Open-Meteo REST API\\n(live JSON)", {ENV}];
cli [label="WeatherClient\\nurllib + timeout\\nfallback snapshot"];
par [label="Parser\\ntemp, humidity, rain"];
kb [label="knowledge.json\\ndish tags, weather rules,\\nsubstitutions, cities", {SEC}];
rule [label="Rule matcher"];
ag [label="MealAgent profile\\nmenu_style, water, cook cap,\\nprefer / avoid tags", {ACT}];
rk [label="Re-ranked dishes"];
api -> cli -> par -> rule; kb -> rule; rule -> ag -> rk;
''')

dot("d5_1", f'''
snd [label="Sender host\\nholds PRIVATE key\\nsigns envelope (Ed25519)"];
net [label="TCP socket\\n{{sender, ts, nonce, payload, sig}}", {ENV}];
c1 [label="1 known sender?\\n(keyring of public keys)", {SEC}];
c2 [label="2 fresh timestamp?\\n(30 s window)", {SEC}];
c3 [label="3 nonce unused?\\n(replay)", {SEC}];
c4 [label="4 signature valid?", {SEC}];
c5 [label="5 command permitted\\nfor this sender?", {SEC}];
ok [label="Agent executes", {ACT}];
no [label="Reject + log BLOCKED", {SEC}];
snd -> net -> c1 -> c2 -> c3 -> c4 -> c5 -> ok;
c1 -> no [style=dashed]; c2 -> no [style=dashed]; c3 -> no [style=dashed]; c4 -> no [style=dashed]; c5 -> no [style=dashed];
''', rankdir="LR")

dot("d5_2", f'''
subgraph cluster_u1 {{ label="Unit 1: core loop"; fontname="DejaVu Sans"; style=dashed; refl [label="Reflex rules\\n+ sensor stream"]; }}
subgraph cluster_u4 {{ label="Unit 4: cognition"; fontname="DejaVu Sans"; style=dashed; bdi [label="BDI loop\\n(beliefs, desires,\\nintentions)"]; kb [label="Knowledge base\\n+ weather API"]; }}
subgraph cluster_u3 {{ label="Unit 3: decisions"; fontname="DejaVu Sans"; style=dashed; ut [label="Utility chooser"]; ng [label="Negotiation\\nbuyer vs vendor"]; }}
subgraph cluster_u2 {{ label="Unit 2: concurrency + network"; fontname="DejaVu Sans"; style=dashed; pm [label="PriceMonitor thread\\n+ queue + lock", {ACT}]; sk [label="TCP sockets\\nplanner <-> grocery", {ACT}]; }}
subgraph cluster_u5 {{ label="Unit 5: security"; fontname="DejaVu Sans"; style=dashed; sg [label="Ed25519 sign / verify\\nnonce, timestamp, permissions", {SEC}]; }}
ui [label="CLI dashboard", {ENV}];
refl -> bdi; kb -> bdi; pm -> bdi [label="alerts"]; bdi -> ut [label="PICK"]; ut -> sk [label="ORDER"];
sk -> sg [dir=both]; sk -> ng [label="grocery agent"]; ng -> sk; bdi -> ui;
''', rankdir="TB")

# ----------------------------------------------------------------- charts
d = json.load(open("logs/a2_1_latency.json"))
fig, ax = plt.subplots(1, 2, figsize=(9, 3.1))
ax[0].bar(range(1, len(d["latency"]) + 1), [x * 1000 for x in d["latency"]], color="#3B6EA8")
ax[0].set_title("Background poll latency (ms)", fontsize=10); ax[0].set_xlabel("poll #")
ax[1].plot([x * 1000 for x in d["gaps"][1:]], color="#3C8C3C")
ax[1].axhline(100, color="grey", ls="--", lw=1); ax[1].set_ylim(0, 200)
ax[1].set_title("UI loop gap per tick (ms), target 100", fontsize=10); ax[1].set_xlabel("tick")
plt.tight_layout(); plt.savefig("diagrams/c2_1.png", dpi=170); plt.close()

t = json.load(open("logs/a3_1_trace.json"))
fig, ax = plt.subplots(figsize=(6, 3.2))
ax.plot([x[0] for x in t["buyer"]], [x[1] for x in t["buyer"]], "o-", label="Buyer offers", color="#3B6EA8")
ax.plot([x[0] for x in t["supplier"]], [x[1] for x in t["supplier"]], "s-", label="Supplier offers", color="#B03A3A")
ax.axhline(t["final"], color="grey", ls="--", lw=1); ax.text(0.1, t["final"] + 12, "agreed Rs.%d" % t["final"], fontsize=8)
ax.set_xlabel("negotiation turn"); ax.set_ylabel("price (Rs.)"); ax.legend(fontsize=8); ax.set_title("Offers converge to a deal", fontsize=10)
plt.tight_layout(); plt.savefig("diagrams/c3_1.png", dpi=170); plt.close()

r = json.load(open("logs/a3_2_rows.json"))
rows = sorted(r["rows"], key=lambda x: -x[6])
fig, ax = plt.subplots(figsize=(6.5, 3.4))
cols = ["#BBBBBB" if x[7] else ("#3C8C3C" if x[0] == r["best"] else "#3B6EA8") for x in rows]
ax.barh([x[0] for x in rows][::-1], [x[6] for x in rows][::-1], color=cols[::-1])
ax.set_title("Utility per option (grey = filtered, green = chosen)", fontsize=10); ax.tick_params(labelsize=8)
plt.tight_layout(); plt.savefig("diagrams/c3_2.png", dpi=170); plt.close()
print("diagrams done")
