import os
from pdfkit import *

L = lambda n: "logs/%s.log" % n
D = lambda n: "diagrams/%s.png" % n
OUT = "pdfs"
os.makedirs(OUT, exist_ok=True)


def logtext(n):
    return open(L(n), encoding="utf-8").read()


# =================================================================== 1.1
s = []
s += [H2("1. Domain and persona"),
      P("My agent is <b>MealPilot</b>, a personal meal-planning agent for an Indian household. A family of four to six "
        "people usually has the same weekly headache: what to cook each day, what is left in the pantry, whether the "
        "budget will last, and what to do when something changes (a guest turns up, somebody has fever, tomatoes "
        "suddenly cost Rs. 90 a kilo). MealPilot takes that job over. It senses the kitchen and the market, decides "
        "a weekly menu on its own, builds the shopping list and talks to a grocery agent to buy it."),
      P("I chose this domain because the environment is messy in the way real agent problems are: prices move, family "
        "needs differ (weight loss, elderly care, muscle gain) and the agent has to react without being told."),
      H2("2. PEAS profile")]
s += table([
    ["Element", "Description for MealPilot"],
    ["Performance measure",
     "Nutrition fit to the family goal (calories, protein, fibre); weekly cost within budget; family rating of the "
     "dishes; low food waste; variety (no dish repeated within 2 days); safety (no allergens, soft food when someone is ill); "
     "time taken to react to a change."],
    ["Environment",
     "The household kitchen and pantry; family members with health flags and allergies; the weekly budget; local vegetable "
     "market (mandi) prices; the weather; vendors and the grocery agent; festivals / fasting days."],
    ["Actuators",
     "Weekly menu and daily dinner choice; shopping list; notifications to the cook and family; quote / order messages "
     "to the grocery agent; negotiation offers to the vendor; dashboard updates."],
    ["Sensors",
     "Pantry stock levels; gas cylinder level; budget left; live price feed; weather API; family inputs (guests coming, "
     "member is sick, festival); messages received from other agents."],
], [3.6, 13.4])
s += img(D("d1_1"), 15.5, "Figure 1. PEAS view of MealPilot: the agent loop between its environment, sensors and actuators.")
s += [H2("3. Environment characteristics")]
s += table([
    ["Property", "Classification", "Why"],
    ["Observability", "Partially observable", "The agent cannot see what is really in every container or whether the cook followed the plan. "
                                              "It only has sensor readings and what the family tells it."],
    ["Determinism", "Stochastic", "Prices, guests and illness are not predictable. The same action (plan a menu) can end in different outcomes."],
    ["Episodic or sequential", "Sequential", "Today's dinner affects tomorrow's pantry stock, the remaining budget and the variety rule."],
    ["Static or dynamic", "Dynamic", "Prices and family situation change while the agent is still thinking, so it needs background monitoring."],
    ["Discrete or continuous", "Mostly discrete", "Dishes and days are discrete. Quantities, prices and temperature are continuous values."],
    ["Agents", "Multi-agent", "Cooperative with the grocery agent, competitive (self-interested) with the vendor during price negotiation."],
    ["Known or unknown", "Known rules, uncertain values", "Recipes and nutrition are known. Market prices and family preferences have to be learnt or sensed."],
], [3.2, 3.6, 10.2])
s += [H2("4. Autonomous agent vs standard object-oriented program"),
      P("To be clear about why MealPilot is an agent and not just a class with methods, here is how the same job would look "
        "in a normal OO program compared to my agent.")]
s += table([
    ["Aspect", "Standard OO program", "MealPilot as an autonomous agent"],
    ["Control", "Methods run only when some other code or the user calls them.", "The agent decides when to act. It runs its own sense-decide-act loop."],
    ["Initiative", "Reactive to calls only. Nothing happens without a caller.", "Proactive. It raises a shopping alert or changes the menu by itself when a price jumps."],
    ["Behaviour", "Fixed sequence written by the programmer for each method.", "Chooses behaviour from goals (desires) and the current situation, and replans when beliefs change."],
    ["State", "Object fields, no notion of beliefs or goals.", "Beliefs about the world, desires, and committed intentions (BDI)."],
    ["Interaction", "Direct method calls on known objects in the same process.", "Asynchronous typed messages (QUOTE, PRICE_ALERT) over sockets, can be remote."],
    ["Autonomy over failure", "An exception is thrown to the caller.", "The agent tries an alternative, for example replaces tomato dishes or falls back to cached data."],
    ["Environment awareness", "Does not sense anything by itself.", "Continuously senses pantry, budget, prices, weather and acts on them."],
    ["Social ability", "None built in.", "Negotiates with a vendor agent using offers and counter-offers and checks who it is talking to."],
    ["Threading", "Usually one thread of control.", "Own thread of control plus background workers (price monitor)."],
], [3.2, 6.0, 7.8])
s += [H2("5. Project plan for the next assignments"),
      P("Each later assignment adds one layer to the same agent: a reflex rule engine (1.2), background workers (2.1), "
        "socket messaging (2.2), vendor negotiation (3.1), a utility function (3.2), a BDI model (4.1), a knowledge base with a "
        "live weather API (4.2), message signing (5.1) and finally everything combined in a capstone (5.2).")]
build(f"{OUT}/Assignment_1.1_PEAS_Design_Spec.pdf", "1.1", "Project Ideation, Environment Modeling and PEAS Matrix",
      "Pick an agent persona, describe its PEAS profile, classify its environment, and compare the agent with a "
      "normal object-oriented program.", s)

# =================================================================== 1.2
s = [H2("1. What I built"),
     P("A <b>simple reflex agent</b> for the kitchen. Every tick it reads one percept (pantry levels, gas %, budget left, tomato "
       "price, a possible event such as guests or fever) and checks a table of condition-action rules. It has no memory between ticks, "
       "which is the whole point of a simple reflex agent. The telemetry is a mocked stream (seeded random numbers plus a few scripted events) "
       "because I do not have a real smart kitchen."),
     P("There are nine rules: low gas, member fever, guests arriving, festival (Ekadashi) menu, low budget, tomato price spike, low stock, and "
       "two time based reminders (7am breakfast, 7pm dinner). The list order is the priority order, with safety rules first."),
     P("<b>A bug I hit while testing:</b> my first version let the last matching rule overwrite the menu mode, so the economy mode "
       "replaced no_gas even though no gas is clearly more urgent. I fixed it by giving every mode a rank so a mode can only be replaced "
       "by a more important one. You can see this in the log as the lines starting with 'keeping no_gas'.")]
s += img(D("d1_2"), 15.0, "Figure 1. Simple reflex agent loop used in this assignment.")
s += [H2("2. Source code")] + code("a1_2_reflex_agent.py")
s += [H2("3. Execution log")] + logblock("a1_2_reflex")[:] + [
    H2("4. What the log shows"),
    P("The reactive log shows each rule firing only when its condition is true for the current tick: guests arriving at tick 3 "
      "scale the portions, the fever at tick 6 moves the menu to soft food, the tomato spike at ticks 8 to 9 triggers a substitution, "
      "and as gas drops under 15% the agent switches to no-flame meals and keeps that mode over the lower priority economy mode. "
      "Low stock items are added to the shopping list once and later ticks note they are already on it.")]
build(f"{OUT}/Assignment_1.2_Reflex_Reasoner.pdf", "1.2", "Rule-Based Environmental Reasoner",
      "Implement a simple reflex agent that processes a mocked sensor stream and fires condition-action rules with reactive logging.", s)

# =================================================================== 2.1
s = [H2("1. What I built"),
     P("MealPilot has to keep watching vegetable prices, but a network wait must not freeze the main loop. I used a <b>daemon "
       "thread</b> (PriceMonitor) that polls a mocked mandi feed every 0.6 s with a random 150 to 450 ms delay to imitate network latency."),
     P("Shared data is handled in three ways: a <b>threading.Lock</b> around the PriceBoard dictionary, a thread safe "
       "<b>queue.Queue</b> that carries PRICE_ALERT messages to the main loop, and a <b>threading.Event</b> for a clean shutdown. "
       "Slow scoring jobs (nutrition score of a day's menu) go to a <b>ThreadPoolExecutor</b> so the 'UI' loop (100 ms tick) "
       "just submits them and carries on."),
     P("The structure is the same idea as a Java Bean with its own thread: the monitor is a self-contained component with a "
       "start, a run loop and a stop signal, and the application talks to it only through the board and the queue.")]
s += img(D("d2_1"), 15.5, "Figure 1. Main thread, background threads and the shared objects between them.")
s += [H2("2. Source code")] + code("a2_1_threads.py")
s += [H2("3. Execution log")] + logblock("a2_1_threads")
s += [H2("4. Latency and responsiveness")] + img(D("c2_1"), 16.0,
        "Figure 2. Left: how long each background poll took. Right: gap between UI ticks while polling and scoring ran.")
s += [P("Each poll took roughly 160 to 330 ms, but the UI loop kept its 100 ms rhythm (see the PERF lines in the log). If the same polling "
        "had been done on the main thread, the interface would have stalled for about that long on every poll. The forced tomato spike at "
        "poll 4 arrived through the queue and was handled in the main loop without any blocking. The three scoring jobs overlapped in the "
        "pool, so they finished almost together instead of one after another.")]
build(f"{OUT}/Assignment_2.1_Threads_and_Workers.pdf", "2.1", "Concurrent Task Daemonization using Threads and Workers",
      "Run background work (price monitoring) without blocking the main loop, sharing data safely with queues and locks.", s)

# =================================================================== 2.2
s = [H2("1. What I built"),
     P("A client-server pair over raw TCP sockets on localhost. <b>Agent-B</b> is the grocery agent (server, Terminal 1). "
       "<b>Agent-A</b> is the meal planner (client, Terminal 2). TCP is just a byte stream, so every message is sent as a 4 byte "
       "length followed by a JSON body (msgproto.py). That is the serialization layer."),
     P("Agent-A sends its state (menu, headcount, budget). Agent-B replies with a QUOTE. Then Agent-B <b>pushes a PRICE_ALERT on its own</b> "
       "without being asked. Agent-A's receive loop dispatches the message to a handler which works out which dishes are tomato heavy, "
       "replaces them and sends a MENU_UPDATE, so the planner reacts autonomously to the payload. B then sends a new QUOTE and A says BYE."),
     P("How to run: Terminal 1: <font face='Courier'>python3 a2_2_agent_b.py</font>. Terminal 2: <font face='Courier'>python3 a2_2_agent_a.py</font>.")]
s += img(D("d2_2"), 15.0, "Figure 1. Dual terminal setup and the message types exchanged.")
s += [H2("2. Source code")] + code("msgproto.py", "msgproto.py (shared framing)") + code("a2_2_agent_b.py") + code("a2_2_agent_a.py")
s += [H2("3. Execution logs (two terminals)")]
s += logblock("a2_2_agent_b", "TERMINAL 1 - Agent-B (grocery agent) output", colors.HexColor("#EEF6EE"))
s += [Spacer(1, 6)]
s += logblock("a2_2_agent_a", "TERMINAL 2 - Agent-A (meal planner) output", colors.HexColor("#EAF1FB"))
s += [H2("4. Reading the two logs together"),
      P("Agent-A's first STATE produced a QUOTE within budget. Right after that Agent-B pushed the tomato alert at Rs. 92/kg. "
        "Agent-A found two tomato heavy dishes (paneer masala and rajma chawal), replaced them with moong chilla and veg khichdi, and "
        "the second QUOTE was lower. Agent-A then closed the session. The active parameters of Agent-A (menu, headcount, budget) were "
        "transferred to Agent-B in the STATE and MENU_UPDATE payloads.")]
build(f"{OUT}/Assignment_2.2_Socket_Messaging.pdf", "2.2", "Distributed Agent Messaging using Sockets",
      "Let two agents exchange typed, serialized messages over a TCP socket and act on proactive messages without human help.", s)

# =================================================================== 3.1
s = [H2("1. What I built"),
     P("Two separate agent objects, <b>BUYER</b> (the MealPilot household) and <b>SUPPLIER</b> (a vegetable vendor), that only talk "
       "through messages in an inbox. The protocol is a small contract-net style exchange followed by alternating offers: "
       "CFP, PROPOSE, COUNTER ..., ACCEPT, CONFIRM, ACK. The last three form the consensus handshake."),
     P("Each agent has a utility between 0 and 1 for a price. For the buyer U = (reserve - price) / (reserve - start). For the supplier "
       "U = (price - reserve) / (start - reserve). Each turn k the agent lowers the utility it demands with the time dependent formula "
       "<font face='Courier'>target(k) = 1 - (1 - u_min) * (k/T)^(1/beta)</font>. An agent accepts when the offer it just received gives "
       "at least the utility it would have asked for next."),
     table([["", "Buyer", "Supplier"],
            ["Best price (start)", "Rs. 600", "Rs. 1100"], ["Worst acceptable (reserve)", "Rs. 900", "Rs. 720"],
            ["beta", "1.0 (linear)", "0.7 (stubborn, concedes late)"], ["Deadline T", "10 turns", "10 turns"]],
           [5, 5, 7])[0]]
s += img(D("d3_1"), 12.5, "Figure 1. Message flow between the two agents.")
s += [H2("2. Source code")] + code("a3_1_negotiation.py")
s += [H2("3. Execution timeline")] + logblock("a3_1_negotiation", "Negotiation turns (terminal timeline)")
s += img(D("c3_1"), 11.5, "Figure 2. Offers per turn. Both sides give ground and meet at the agreed price.")
s += [P("The buyer started at Rs. 629 and the supplier at Rs. 1100. Because the supplier concedes late it held a high price for most of "
        "the rounds, so the buyer had to move up almost linearly. They finally agreed at turn 9 at Rs. 838, a price inside both reserve limits "
        "(Rs. 720 to 900). Both utilities are positive, so both sides accepted willingly.")]
build(f"{OUT}/Assignment_3.1_Multi_Agent_Negotiation.pdf", "3.1", "Multi-Agent Coordination Protocol Execution",
      "Spawn two agents that exchange proposals, change their stance using utility formulas and finish with a consensus handshake.", s)

# =================================================================== 3.2
s = [H2("1. Utility function"),
     P("MealPilot is self interested: it only maximises its own score. For each candidate dinner it computes four terms in the range 0 to 1 and a penalty:"),
     P("<font face='Courier'>U(d) = 0.35*N + 0.20*C + 0.15*T + 0.30*P - penalty</font>"),
     table([["Term", "Meaning", "Formula"],
            ["N", "Nutrition fit", "0.4 * kcal_fit + 0.4 * min(protein/30,1) + 0.2 * min(fibre/12,1), kcal_fit = 1 - |kcal - 550|/550"],
            ["C", "Cost score", "1 - cost/150 (cost per serving in Rs.)"],
            ["T", "Time score", "1 - prep_minutes/60"],
            ["P", "Family preference", "rating / 5 (from past feedback)"],
            ["penalty", "Variety", "0.15 if the dish was served in the last 2 days"]], [2, 3.5, 11.5])[0],
     P("<b>Hard constraints</b> are applied first and throw options away completely: no egg (allergy), cost at most Rs. 100 per serving, "
       "preparation at most 55 minutes. The remaining feasible options are scored and the agent picks the argmax.")]
s += img(D("d3_2"), 15.5, "Figure 1. Decision pipeline of the utility agent.")
s += [H2("2. Source code")] + code("a3_2_utility.py")
s += [H2("3. Execution log (10 options)")] + logblock("a3_2_utility")
s += img(D("c3_2"), 12.5, "Figure 2. Utility of each of the 10 options.")
s += [P("Four options were filtered out by the hard constraints: egg curry (allergy), chicken curry and paneer masala (cost above Rs. 100) and "
        "rajma chawal (60 minute prep). Rajma chawal actually scores 0.701, higher than the winner, so the NOTE line shows that the filter really matters. "
        "Among the 6 survivors the agent picked chole roti with U = 0.655. The VERIFY line is an assertion that checks every feasible option "
        "one by one and confirms none beats the choice. The WHATIF lines show that the answer depends on the weights: a budget-first family "
        "would get curd rice instead, which is what I expect from a utility based agent.")]
build(f"{OUT}/Assignment_3.2_Utility_Optimization.pdf", "3.2", "Self-Interested Agent Utility Optimization",
      "Define an explicit utility function and show the agent selecting the mathematically best option out of 10 candidates.", s)

# =================================================================== 4.1
s = [H2("1. What I built"),
     P("A Belief-Desire-Intention layer with three explicit classes:"),
     table([["BDI part", "Class", "In MealPilot"],
            ["Beliefs", "Beliefs", "budget_left, guests, sick_member, gas_pct, tomato_price. Any change is logged and remembered until the agent has looked at it."],
            ["Desires", "Desire", "plan_weekly_menu (priority 3), care_for_sick_member (priority 5). Each has an 'active when' test and a plan builder."],
            ["Intentions", "Intention", "The chosen desire with its list of steps and a step pointer. Paused intentions go on a stack."]],
           [2.4, 2.8, 11.8])[0],
     P("Every step the agent re-deliberates: find the active desires, take the highest priority, shift the intention if it changed, "
       "and replan if a belief that the plan depends on has changed. Each desire says which step a belief makes stale (for example a sick member "
       "makes the already finished 'shortlist dishes' step stale), so the agent <b>rewinds</b> to that step and rebuilds the remaining plan."),
     P("<b>Bug I fixed on the way:</b> at first the weekly plan did not notice the sick member because the change happened while the plan was "
       "paused. I added a 'pending changes' set to each paused intention so it replans when it resumes.")]
s += img(D("d4_1"), 15.5, "Figure 1. BDI deliberation cycle.")
s += [H2("2. Source code")] + code("a4_1_bdi.py")
s += [H2("3. Test verification run")] + logblock("a4_1_bdi")
s += [P("At step 3 the unexpected belief update 'Dad (fever)' arrives. The agent suspends plan_weekly_menu, commits to care_for_sick_member "
        "and runs its four steps. When that is done it resumes the weekly plan, rewinds to the stale shortlist step and recalculates it with soft "
        "dishes. A second surprise (gas at 8%) adds the no pressure cooker restriction. The TEST lines at the end assert the shift, the resume "
        "and the recalculated plan, and all of them pass.")]
build(f"{OUT}/Assignment_4.1_BDI_Model.pdf", "4.1", "Belief-Desire-Intention Goal-Driven Modeling",
      "Implement beliefs, desires and intentions in code and show an intention shift when an unexpected belief update arrives.", s)

# =================================================================== 4.2
live = "LIVE FETCH OK" in logtext("a4_2_knowledge_api")
s = [H2("1. What I built"),
     P("Domain knowledge is stored in <font face='Courier'>knowledge.json</font>: dish tags (cooling, light, warming, heavy), weather rules "
       "(heatwave, rainy, cold) with the profile they set, ingredient substitutions, and city coordinates. A KnowledgeBase class loads it and answers queries."),
     P("For real world data I used the <b>Open-Meteo REST API</b> (free, no API key). The WeatherClient does an HTTP GET, parses the JSON "
       "(temperature, humidity, precipitation), the rule matcher picks the first matching rule and the agent's profile properties "
       "(menu style, water target, cooking time cap, prefer / avoid tags) are overwritten immediately. Dishes are then re-ranked."),
     P("The client has a timeout and, if the network call fails, uses a clearly labelled sample snapshot instead of pretending the data was live. "
       "Run with <font face='Courier'>--require-live</font> to turn the fallback off.")]
if not live:
    s += [P("<b>Note about this log:</b> it was produced in an environment with no internet access, so the HTTP requests failed and the "
            "agent used the cached SAMPLE snapshot (the log says so). To get a log with live data, run "
            "<font face='Courier'>python3 a4_2_knowledge_api.py --require-live</font> on a machine with internet and replace the log below.", note)]
s += img(D("d4_2"), 15.5, "Figure 1. From live API data to changed agent properties.")
s += [H2("2. Source code")] + code("a4_2_knowledge_api.py") + code("knowledge.json")
s += [H2("3. Execution log")] + logblock("a4_2_knowledge_api")
s += [P("For each city the agent's profile changed as soon as the weather was parsed: a heatwave switched it to cooling light food and a bigger "
        "water target, and cold weather switched it to hearty warming food. The ranking changes with the profile, for example curd rice and moong "
        "chilla move to the top in the heat, warm comfort dishes such as dal tadka rank high for the rainy Mumbai reading, and hearty dishes (chicken curry, "
        "paneer masala, rajma chawal) lead in the cold.")]
build(f"{OUT}/Assignment_4.2_Knowledge_and_API.pdf", "4.2", "Knowledge Representation and Adaptive API Integration",
      "Store domain knowledge in a structured format and adapt the agent's plans using a live REST API.", s)

# =================================================================== 5.1
s = [H2("1. What I built"),
     P("Every command that reaches MealPilot is wrapped in a signed envelope containing sender, timestamp, nonce and payload, and an "
       "<b>Ed25519 signature</b> over the canonical JSON of those four fields (Python <i>cryptography</i> library). The receiving agent only keeps "
       "the <b>public keys</b> of trusted hosts in a keyring, so it can verify but cannot forge."),
     P("The checks run in this order and the first failure rejects the message: known sender, fresh timestamp (30 s), unused nonce (replay), "
       "valid signature, and command permitted for that sender. A nonce is only remembered after the whole message is accepted. "
       "The test sends messages through a real localhost socket, using the same framing as assignment 2.2.")]
s += img(D("d5_1"), 16.0, "Figure 1. Verification pipeline in front of the agent.")
s += [H2("2. Source code")] + code("a5_1_security.py")
s += [H2("3. Runtime test log (including blocked requests)")] + logblock("a5_1_security")
s += table([["Test", "Attack", "Result"],
            ["T1, T2", "Normal commands from grocery_agent and planner", "Accepted"],
            ["T3", "Payload changed after signing (qty 2 to 500)", "Blocked: bad signature"],
            ["T4", "Attacker with own key claims to be grocery_agent", "Blocked: bad signature"],
            ["T5", "Unknown sender evil_bot", "Blocked: not in keyring"],
            ["T6", "Replay of a captured valid message", "Blocked: nonce reuse"],
            ["T7", "Valid signature but 5 minutes old", "Blocked: stale timestamp"],
            ["T8", "Trusted host sending a command it is not allowed to", "Blocked: not permitted"]], [2.2, 9.3, 5.5])
build(f"{OUT}/Assignment_5.1_Authentication_and_Integrity.pdf", "5.1", "Agent Authentication and Host Integrity Verification",
      "Add cryptographic validation so the agent only acts on authentic, unmodified commands from trusted hosts, and show a blocked attack.", s)

# =================================================================== 5.2
s = [H2("1. What I built"),
     P("The capstone joins all earlier modules into one agent (a5_2_capstone.py). It does not re-implement anything, it imports the modules:"),
     table([["Unit", "Module used", "Role in the final agent"],
            ["1", "a1_2 reflex rules + sensor stream", "Senses telemetry; guests arriving raises the headcount from 4 to 7"],
            ["2", "a2_1 PriceMonitor, TCP sockets", "Background thread feeds prices; planner and grocery agent talk over TCP"],
            ["3", "a3_2 utility, a3_1 negotiation", "Utility picks the dinners; grocery agent negotiates the basket price with the vendor"],
            ["4", "a4_1 BDI, a4_2 knowledge + weather", "BDI decides what to do and shifts intention on a price spike; weather changes the profile"],
            ["5", "a5_1 signatures", "Every request and reply is signed and verified, attacks are blocked"]], [1.2, 5.8, 10.0])[0],
     P("<b>Production cycle shown in the log:</b> (1) normal planning: sense, pick dinners, send a signed quote request, get a signed reply, "
       "show the dashboard; (2) the background monitor reports a tomato price jump, the belief updates and BDI commits to a new intention "
       "(react_to_price_spike) and repeats the cycle with the new price; (3) an attacker sends a forged and a replayed request and both are blocked.")]
s += img(D("d5_2"), 15.5, "Figure 1. System architecture of the capstone agent.")
s += [H2("2. Source code (integration module)")] + code("a5_2_capstone.py")
s += [H2("3. Final execution log with CLI dashboard")] + logblock("a5_2_capstone")
s += [H2("4. Submission items"),
      P("<b>Source code repository link:</b> ______________________________ (push the project folder and paste the link here)"),
      P("<b>3 minute video outline</b> (screen record <font face='Courier'>python3 a5_2_capstone.py</font>):")]
s += table([["Time", "What to show"],
            ["0:00 - 0:30", "Introduce MealPilot and the architecture diagram above."],
            ["0:30 - 1:15", "Run the capstone. Point at cycle 1: sensing, weather profile change, utility picking dinners."],
            ["1:15 - 2:00", "Signed quote request, grocery agent verifying, vendor negotiation result, dashboard."],
            ["2:00 - 2:35", "Background price alert, belief update, BDI switching to react_to_price_spike."],
            ["2:35 - 3:00", "Attack with forged and replayed requests being blocked. Final summary lines."]], [3, 14])
s += [P("<b>Honest limits:</b> the sensors and market are simulated, the grocery agent and vendor run on the same machine, and the weather data is "
        "live only when internet is available (otherwise a labelled snapshot is used). Keys are generated fresh each run, a real deployment would "
        "store them safely and distribute public keys in advance.")]
build(f"{OUT}/Assignment_5.2_Capstone_Integration.pdf", "5.2", "Capstone Project Consolidation and Secure Deployment",
      "Combine the work of all five units in one autonomous agent with a live dashboard, coordination and secure message handling.", s)
print("built")
