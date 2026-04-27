import matplotlib.pyplot as plt
from collections import Counter

# -------- DATA (MATCHED WITH RASHA OUTPUT) --------
students = [
    {"name": "Student 1", "initial": 36.2, "final": 0.0,
     "plan": ['Submit_Assignment','Submit_Assignment','Submit_Assignment','Practice_Quiz','Study_1_Hour']},

    {"name": "Student 2", "initial": 45.5, "final": 0.0,
     "plan": ['Submit_Assignment','Submit_Assignment','Submit_Assignment','Attend_Class','Attend_Class','Attend_Class','Attend_Class']},

    {"name": "Student 3", "initial": 25.0, "final": 0.0,
     "plan": ['Submit_Assignment','Meet_Tutor','Practice_Quiz','Study_1_Hour']},

    {"name": "Student 4", "initial": 34.6, "final": 0.0,
     "plan": ['Submit_Assignment','Meet_Tutor','Meet_Tutor','Meet_Tutor','Study_1_Hour']},

    {"name": "Student 5", "initial": 97.9, "final": 0.0,
     "plan": ['Submit_Assignment','Submit_Assignment','Submit_Assignment','Submit_Assignment','Submit_Assignment',
              'Meet_Tutor','Meet_Tutor','Attend_Class','Attend_Class','Attend_Class',
              'Practice_Quiz','Attend_Class','Attend_Class','Study_1_Hour','Attend_Class']}
]

def plot_risk_before_after(before_risk, after_risk, risk_thres):
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(["Before", "After"], [before_risk, after_risk], color=["#ff6b6b", "#51cf66"])
    ax.set_title("Risk Score Before and After A*")
    ax.set_ylabel("Risk Score")
    ax.set_ylim(0, max(before_risk, after_risk, 1))
    return fig

def plot_action_counts(plan):
    action_counter = Counter()
    action_counter.update(plan)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(action_counter.keys(), action_counter.values(), color="#4dabf7")
    ax.set_title("Recommended Action Frequency")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", rotation=35)
    return fig

if __name__ == "__main__":
    names = [s["name"] for s in students]
    initial = [s["initial"] for s in students]
    final = [s["final"] for s in students]

    # -------- GRAPH 1: INITIAL RISK --------
    plt.figure()
    plt.bar(names, initial)
    plt.title("Initial Risk (Before A*)")
    plt.ylabel("Risk Score")
    plt.xticks(rotation=45)
    plt.show()

    # -------- GRAPH 2: FINAL RISK (CLEAN FIX) --------
    plt.figure()
    bars = plt.bar(names, final)

    plt.title("Final Risk (After A*)")
    plt.ylabel("Risk Score")
    plt.xticks(rotation=45)

    # Keep axis tight near 0 so bars are visible but small
    plt.ylim(0, 1)

    # Add labels (0.0) slightly above baseline
    for i, v in enumerate(final):
        plt.text(i, 0.05, str(v), ha='center')

    plt.show()

    # -------- GRAPH 3: ACTION FREQUENCY --------
    action_counter = Counter()

    for s in students:
        action_counter.update(s["plan"])

    plt.figure()
    plt.bar(action_counter.keys(), action_counter.values())
    plt.title("Action Frequency")
    plt.ylabel("Count")
    plt.xticks(rotation=45)
    plt.show()