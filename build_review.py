from pdfkit import *

D = lambda n: "diagrams/%s.png" % n
s = []

s += [P("This sheet follows the four marking areas one by one. For each area: what to <b>say</b>, what to <b>show</b> (pictures included), "
        "which <b>code file</b> proves it, and the <b>questions</b> you are most likely to get. Run <font face='Courier'>python3 a5_2_capstone.py</font> "
        "once before the review so you know what the screen will look like."),
      H2("Rubric at a glance")]
s += table([
    ["Marking area (2.5 each)", "What they check", "My evidence"],
    ["1. Architecture and BDI integration", "Modular layers, separate Belief / Desire / Intention structures, background workers, structured knowledge or API.",
     "a4_1_bdi.py, a2_1_threads.py, knowledge.json + a4_2, capstone imports all modules"],
    ["2. Autonomous execution and optimization", "Senses input alone, uses a utility function, adapts plans when the environment changes, no human help.",
     "a1_2 rules, a3_2 utility, BDI replan, capstone cycle 1 and 2"],
    ["3. Coordination and security", "Stable sockets, multi-turn negotiation with consensus handshake, signature checks that block attacks.",
     "a2_2 sockets, a3_1 negotiation, a5_1 security, capstone cycle 3"],
    ["4. UI and documentation", "Clean CLI/GUI with live state, accurate architecture schematic, presentation of the full lifecycle.",
     "Dashboard in a5_2, architecture diagrams, 3-minute video"],
], [4.2, 7.0, 5.8])
s += [H2("Opening (about 30 seconds)"),
      P("\"My agent is <b>MealPilot</b>, a weekly meal planner for an Indian household. It senses the kitchen, market prices and weather. "
        "It chooses dinners with a utility function, orders groceries from another agent over sockets, negotiates the price with a vendor, "
        "and every message is digitally signed. I will now run one complete lifecycle.\"")]
s += img(D("d5_2"), 15.8, "System architecture: one layer per unit, all consolidated by the capstone. Use this as your opening slide.")

# ---------------------------------------------------------------- area 1
s += [H2("Area 1: Architecture and BDI integration")]
s += [P("<b>Say:</b> The system is built in layers, one per unit, and each layer is its own module. The capstone does not copy code, "
        "it imports the modules. The BDI part is kept structurally separate: <b>Beliefs</b> (what the agent thinks is true), "
        "<b>Desires</b> (goals with a priority and an 'active when' test) and <b>Intentions</b> (the committed plan with a step pointer, "
        "plus a stack of paused plans). A deliberation loop connects them.")]
s += img(D("d4_1"), 15.0, "BDI architecture. Beliefs activate desires, deliberation picks the highest priority, the intention executes step by step.")
s += [P("<b>Show the BDI behaviour:</b> the picture below is drawn from the real test run. At step 3 the belief 'Dad has fever' arrives. "
        "The agent suspends the weekly plan and switches to the higher priority care plan. When that finishes it resumes the weekly plan, "
        "<b>rewinds</b> to the step that is now stale (shortlisting dishes) and recalculates it with soft dishes. At step 8 a second belief (gas 8%) "
        "changes the plan again.")]
s += img("diagrams/r_bdi_timeline.png", 16.0, "Intention shift and replanning, taken from logs/a4_1_bdi.log.")
s += [P("<b>Efficient concurrent workers:</b> the price monitor runs as a daemon thread. It shares data with the main loop only through a "
        "lock protected board and a thread safe queue, and stops through an Event. Measured result: polls took 163 to 327 ms while the main loop "
        "kept its 100 ms rhythm (worst gap 101 ms).")]
s += img(D("d2_1"), 15.0, "Concurrency design. The UI loop never waits for the network.")
s += [P("<b>Structured knowledge and API:</b> <font face='Courier'>knowledge.json</font> stores dish tags, weather rules and substitutions. "
        "The Open-Meteo REST API result is parsed and changes the agent's profile (menu style, water target, cooking time cap).")]
s += img(D("d4_2"), 14.0, "Knowledge base plus live API feeding the agent profile.")
s += table([["Question you may get", "Short answer"],
            ["Why separate Beliefs, Desires and Intentions?", "Beliefs change often, desires are stable goals, intentions are commitments. Separating them lets the agent "
                                                               "change its plan without losing its goals, and replan only the stale part."],
            ["What is the difference between a desire and an intention?", "A desire is something I would like (plan menu, care for sick member). An intention is the one I have "
                                                                           "committed to right now, with a concrete step list."],
            ["Why a daemon thread?", "It runs in the background and ends with the program. The queue and lock avoid race conditions, the Event gives a clean stop."],
            ["What happens if the API is down?", "The client times out, logs the failure and uses a labelled sample snapshot. It never pretends the data was live."]],
           [6.0, 11.0])

# ---------------------------------------------------------------- area 2
s += [H2("Area 2: Autonomous execution and optimization")]
s += [P("<b>Say:</b> After I start the program nobody types anything. The agent runs sense, decide, act on its own. Sensing: reflex rules read "
        "telemetry (guests arriving raised the headcount from 4 to 7) and the weather API changes the profile. Deciding: a mathematical "
        "utility function chooses the dinners. Adapting: when the background monitor reports a tomato price jump, a belief changes, BDI "
        "switches to the <font face='Courier'>react_to_price_spike</font> intention and the cycle runs again.")]
s += [P("<font face='Courier'>U(d) = 0.35*Nutrition + 0.20*Cost + 0.15*Time + 0.30*Preference - Variety penalty</font>", note),
      P("Hard constraints (allergy, cost cap Rs. 100, prep at most 55 minutes) remove options before scoring. The agent then takes the "
        "maximum. A brute force assertion confirms nothing scores higher.")]
s += img(D("c3_2"), 12.5, "Utility of the 10 options. Grey = removed by constraints, green = chosen (chole roti, U = 0.655).")
s += img(D("d3_2"), 15.5, "Decision pipeline.")
s += table([["Question you may get", "Short answer"],
            ["Why is it called autonomous?", "It has its own control loop, senses by itself, chooses actions from goals and utility, and reacts to changes with no user input."],
            ["Why utility and not just rules?", "Rules give one fixed answer. Utility lets me weigh nutrition, cost, time and preference together and compare many options by one number."],
            ["What if the weights change?", "The choice changes. A budget-first family gets curd rice instead of chole roti (see the WHATIF lines in the 3.2 log)."],
            ["Where is the adaptation?", "In BDI: a belief change triggers a new intention or a replan, and in 4.2 the weather rule changes the profile."]],
           [6.0, 11.0])

# ---------------------------------------------------------------- area 3
s += [H2("Area 3: Multi-agent coordination and security")]
s += [P("<b>Say:</b> Agents never share memory, they only send messages. <b>Sockets:</b> TCP with a 4 byte length and a JSON body. The grocery agent also "
        "pushes a price alert on its own and the planner reacts by itself.")]
s += img(D("d2_2"), 13.5, "Socket messaging between the planner and the grocery agent.")
s += [P("<b>Negotiation:</b> buyer and vendor follow CFP, PROPOSE, COUNTER ... ACCEPT, CONFIRM, ACK (the consensus handshake). Each concedes over time "
        "using its own utility. They agreed at Rs. 838 in turn 9. Both utilities were positive, so both gain.")]
s += img(D("c3_1"), 11.0, "Offers converge: buyer rises from Rs. 629, supplier falls from Rs. 1100.")
s += [P("<b>Security:</b> every message carries an Ed25519 signature. The receiver checks five things in order and rejects on the first failure.")]
s += img(D("d5_1"), 16.0, "Verification pipeline. In the test, 6 of 8 messages were attacks and all 6 were blocked.")
s += table([["Question you may get", "Short answer"],
            ["How do you stop replay attacks?", "Each message has a timestamp and a one time nonce. A reused nonce or a message older than 30 s is rejected even if the signature is valid."],
            ["Why public key signatures and not a password?", "The receiver only stores public keys, so it can verify but never forge. A stolen receiver does not leak signing power."],
            ["What if a trusted agent misbehaves?", "Permission check: a valid grocery_agent signature still cannot run SET_BUDGET (test T8)."],
            ["How do the agents reach consensus?", "One side ACCEPTs an offer, the other CONFIRMs it and the first sends an ACK. Three step handshake."]],
           [6.0, 11.0])

# ---------------------------------------------------------------- area 4
s += [H2("Area 4: System UI and architectural documentation")]
s += [P("<b>Say:</b> The user interface is a CLI dashboard that prints the live state after each cycle: current intention, menu, headcount, "
        "weather style, prices, vendor quote and security counters. Below are two screenshots from the same run: before and after the price alert.")]
s += img("diagrams/r_dashboard1.png", 12.5, "Dashboard after cycle 1 (normal planning).")
s += img("diagrams/r_dashboard2.png", 12.5, "Dashboard after cycle 2: tomato Rs. 74.1/kg, intention react_to_price_spike, new vendor quote.")
s += [P("<b>Full lifecycle for the presentation:</b> follow this order in the video. It matches the log from top to bottom.")]
s += img("diagrams/r_sequence.png", 16.0, "Lifecycle sequence of one production run.")
s += table([["Time", "Do this in the video"],
            ["0:00 - 0:30", "Opening line and the system architecture diagram."],
            ["0:30 - 1:15", "Run the capstone. Explain cycle 1: sensing, weather profile, utility choosing dinners."],
            ["1:15 - 2:00", "Signed request, verification, vendor negotiation, dashboard."],
            ["2:00 - 2:35", "Price alert from the worker thread, belief change, BDI intention shift (show the BDI timeline)."],
            ["2:35 - 3:00", "Forged and replayed requests blocked, final summary line."]], [3, 14])
s += [H2("Be honest about the limits")]
s += [P("Sensors and the market are simulated. The grocery agent and vendor run on the same computer. The weather API needs internet, "
        "otherwise a labelled sample snapshot is used. In the capstone run the price spike changed the quote but not the menu, because the weather "
        "profile had already chosen low tomato dishes. The dashboard is a CLI that prints once per cycle, not a screen that refreshes continuously. "
        "Examiners usually respect a clear limitation more than an overclaim.")]

build("pdfs/MealPilot_Review_Guide.pdf", "Review", "Capstone Review Guide: Architecture, BDI and Demo",
      "Explain the MealPilot capstone clearly against the four marking areas, with the pictures you need to show.", s)
print("ok")
