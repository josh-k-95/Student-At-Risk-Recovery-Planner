import heapq
import copy
import math
import time


# ============================================================
# PIECE 1 — STATE CLASS
# ============================================================

class State:
    """
    A snapshot of a student's academic situation at any point.
    Immutable fields are used as the A* node.

    Attributes used by A* (academic metrics):
        attendance   : float  — attendance rate (0–100)
        missing      : int    — missing submissions (0–5)
        score        : float  — avg quiz score (0–100)
        days         : int    — days remaining until deadline

    Attributes tracked but NOT part of A* search:
        activity     : float  — LMS activity (0–100), used for display only
        study_hours  : float  — study hours per week, used for display only
        fatigue      : float  — fatigue level (0–10), used by Scheduler only
    """

    def __init__(self, attendance, missing, score, activity,
                 study_hours, days, fatigue=0, hours_used=0, tutor_used_today = False, practice_used_today=False):
        self.attendance   = float(attendance)
        self.missing      = int(missing)
        self.score        = float(score)
        self.activity     = float(activity)
        self.study_hours  = float(study_hours)
        self.days         = int(days)
        self.fatigue      = float(fatigue)
        self.hours_used = float(hours_used)
        self.tutor_used_today = bool(tutor_used_today)
        self.practice_used_today = bool(practice_used_today)

    def copy(self):
        return State(
            attendance       = self.attendance,
            missing          = self.missing,
            score            = self.score,
            activity         = self.activity,
            study_hours      = self.study_hours,
            days             = self.days,
            fatigue          = self.fatigue,
            hours_used       = self.hours_used,        
            tutor_used_today = self.tutor_used_today,  
            practice_used_today  = self.practice_used_today,
        )

    def __getitem__(self, key):
        """Allows dict-like read access: state["days"]"""
        return getattr(self, key)

    def __setitem__(self, key, value):
        """Allows dict-like write access: state["days"] = 5"""
        setattr(self, key, value)

    def __repr__(self):
        return (
            f"State(attendance={self.attendance}, missing={self.missing}, "
            f"score={self.score}, days={self.days}, fatigue={self.fatigue})"
        )


# ============================================================
# PIECE 2 — CSV ROW TO STATE
# ============================================================

def csv_row_to_state(row):
    """
    Converts a CSV/DataFrame row into a State object.

    Expected columns:
        attendance_rate, missing_submissions, avg_quiz_score,
        lms_activity, study_hours_per_week, days_to_deadline

    Parameters:
        row : pandas Series (one row from the loaded DataFrame)

    Returns:
        State object with fatigue defaulting to 0
    """
    return State(
        attendance  = float(row["attendance_rate"]),
        missing     = int(row["missing_submissions"]),
        score       = float(row["avg_quiz_score"]),
        activity    = float(row["lms_activity"]),
        study_hours = float(row["study_hours_per_week"]),
        days        = int(row["days_to_deadline"]),
        fatigue     = 0.0,
        hours_used  = 0.0,
    )


# ============================================================
# PIECE 3 — RISK SCORE + GOAL CHECK
# ============================================================

# Thresholds — below these values the student is at risk
RISK_DEFAULTS = {
    "ATTENDANCE_THRESHOLD" : 75.0,
    "QUIZ_THRESHOLD"       : 60.0,
    "SUBMISSION_THRESHOLD" : 0
}


def risk_score(state, risk_threshold=None):
    """
    Calculates the student's total risk score.

    Each of the 3 metrics contributes 0.0–1.0 to the total:
        - 0.0 means that metric is fully safe
        - 1.0 means that metric is at its worst possible value

    Total scale: 0.0 (perfectly safe) → 3.0 (worst case)

    Parameters:
        state : State object

    Returns:
        float — risk score between 0.0 and 3.0
    """
    rt = RISK_DEFAULTS.copy()
    if risk_threshold:
        rt.update(risk_threshold)
    
    attendance_risk = max(0.0, (rt["ATTENDANCE_THRESHOLD"] - state.attendance) / 100)
    quiz_risk       = max(0.0, (rt["QUIZ_THRESHOLD"]       - state.score)      / 100)

    missing_gap_sub = max(0.0, state.missing - rt["SUBMISSION_THRESHOLD"])
    submission_risk = min(missing_gap_sub / 10, 1.0)

    return round(attendance_risk + quiz_risk + submission_risk, 4)

def is_goal(state,risk_threshold=None):
    """
    Returns True when the student is fully no longer at risk.
    All three metrics must be at or above their thresholds.

    Parameters:
        state : State object

    Returns:
        bool
    """
    return risk_score(state,risk_threshold) == 0.0

# ============================================================
# STATE KEY — for A* closed set
# ============================================================

def state_key(state):
    """
    Returns a hashable tuple representing the student's
    academic situation. Used by A* to avoid revisiting
    the same state via different action paths.

    Rounds floats to 1 decimal to handle floating point
    precision differences between paths.
    """
    return (
        round(state.attendance, 1),
        state.missing,
        round(state.score,3),
        state.tutor_used_today,
        state.practice_used_today,
    )

# ============================================================
# PIECE 4 — ACTION DEFINITIONS
# ============================================================

# Default time cost per action in hours (user adjustable in what-if)
ACTION_DEFAULTS = {
    "Study":              1.0,
    "Attend Class":       1.0,
    "Submit Assignment":  1.0,
    "Practice Exam":      2.0,
    "Meet Tutor":         3.0,
}


def make_actions(hours_budget,available_hours_per_day=8, time_costs=None, risk_threshold=None,tutor_available=True):
    """
    Builds and returns the ACTIONS dictionary.
    Called once at the start of each A* run.

    Parameters:
        hours_budget    : float — total hours available (days × daily_hours)
        time_costs      : dict  — optional {action_name: hours} overrides
        tutor_available : bool  — if False, Meet Tutor is excluded

    Returns:
        dict of {action_name: function(state) -> State or None}
    """

    # Merge user overrides with defaults
    tc = ACTION_DEFAULTS.copy()
    if time_costs:
        tc.update(time_costs)

    rt = RISK_DEFAULTS.copy()
    if risk_threshold:
        rt.update(risk_threshold)

    def _crossed_day(state, action_time):
        """
        Returns True if this action pushes hours_used
        into a new day — meaning tutor resets.
        """
        current_day = math.floor(state.hours_used / available_hours_per_day)
        new_day     = math.floor((state.hours_used + action_time)
                                  / available_hours_per_day)
        return new_day > current_day

    def action_study(state):
        if state.hours_used + tc["Study"] > hours_budget:
            return None
        s = state.copy()
        s.score      = min(100.0, s.score + (1.5 * tc["Study"]))
        s.activity   = min(100.0, s.activity + (1.0 * tc["Study"]))
        s.hours_used = round(s.hours_used + tc["Study"], 1)
        if _crossed_day(state, tc["Study"]):
            s.tutor_used_today = False      # new day, reset flag
        return s

    def action_attend_class(state):
        if state.hours_used + tc["Attend Class"] > hours_budget:
            return None
        if state.attendance >= rt["ATTENDANCE_THRESHOLD"]:
            return None                          # main requirement done, block action
        s = state.copy()
        s.attendance = min(100.0, s.attendance + 3.0)                    # fixed per action
        s.score      = round(min(100.0, s.score    + 0.7 * tc["Attend Class"]),1) # scales with time
        s.activity   = min(100.0, s.activity + 1.0 * tc["Attend Class"]) # scales with time
        s.hours_used = round(s.hours_used + tc["Attend Class"], 1)
        if _crossed_day(state, tc["Attend Class"]):
            s.tutor_used_today = False
        return s

    def action_submit_assignment(state):
        if state.hours_used + tc["Submit Assignment"] > hours_budget:
            return None
        if state.missing <= 0:
            return None
        s = state.copy()
        s.score     = round(min(100.0, s.score + (0.5 * tc["Submit Assignment"])),1)
        s.missing    = s.missing - 1
        s.activity   = min(100.0, s.activity + (2.0 * tc["Submit Assignment"]))
        s.hours_used = round(s.hours_used + tc["Submit Assignment"], 1)
        if _crossed_day(state, tc["Submit Assignment"]):
            s.tutor_used_today = False
        return s

    def action_practice_exam(state):
        if state.hours_used + tc["Practice Exam"] > hours_budget:
            return None
        if state.practice_used_today:
            return None                        
        s = state.copy()
        s.score                = round(min(100.0, s.score + (2.5 * tc["Practice Exam"])), 1)
        s.activity             = min(100.0, s.activity + 2.0)
        s.hours_used           = round(s.hours_used + tc["Practice Exam"], 1)
        s.practice_used_today  = True          
        if _crossed_day(state, tc["Practice Exam"]):
            s.practice_used_today = False      
        return s

    def action_meet_tutor(state):
        if state.hours_used + tc["Meet Tutor"] > hours_budget:
            return None
        if state.tutor_used_today:
            return None                     # already met tutor today
        s = state.copy()
        s.score            = round(min(100.0, s.score + (2.0 * tc["Meet Tutor"])),1)
        s.activity         = min(100.0, s.activity + 3.0)
        s.hours_used       = round(s.hours_used + tc["Meet Tutor"], 1)
        s.tutor_used_today = True           # flag used
        if _crossed_day(state, tc["Meet Tutor"]):
            s.tutor_used_today = False      
            s.practice_used_today = False
        return s

    actions = {
        "Study":              action_study,
        "Attend Class":       action_attend_class,
        "Submit Assignment":  action_submit_assignment,
        "Practice Exam":      action_practice_exam,
    }
    if tutor_available:
        actions["Meet Tutor"] = action_meet_tutor

    return actions

# ============================================================
# PIECE 5 — HEURISTIC + COST FUNCTION
# ============================================================

def heuristic(state, time_costs=None, risk_threshold=None):
    """
    Estimates the minimum hours still needed to reach the goal.
    Must be ADMISSIBLE — never overestimate the true remaining cost.

    Strategy: for each at-risk metric, calculate the minimum
    hours needed using the BEST available action for that metric.
    Take the MAX since only one action runs at a time.

    Parameters:
        state      : State object
        time_costs : dict — optional action time overrides

    Returns:
        float — estimated minimum hours remaining
    """
    tc = ACTION_DEFAULTS.copy()
    if time_costs:
        tc.update(time_costs)
    
    rt = RISK_DEFAULTS.copy()
    if risk_threshold:
        rt.update(risk_threshold)

    # Gap between current value and safe threshold
    attendance_gap = max(0.0, rt["ATTENDANCE_THRESHOLD"] - state.attendance)
    quiz_gap       = max(0.0, rt["QUIZ_THRESHOLD"]       - state.score)
    submissions    = state.missing

    # Minimum hours needed per metric using best action:
    #   Attend Class → +1.5 attendance per action
    #   Meet Tutor   → +4.0 quiz points per action (best quiz gain)
    #   Submit       → -1 missing per action
    hours_attendance = (attendance_gap / 3.0) * tc["Attend Class"]
    hours_submissions = submissions * tc["Submit Assignment"]

    total_free_score = (hours_attendance * 0.7) + (hours_submissions * 0.5)
    remaining_quiz_gap = max(0,quiz_gap - total_free_score)
    hours_quiz = remaining_quiz_gap / 2.5                      

    return max(hours_attendance, hours_quiz, hours_submissions)


def cost(action_name, time_costs=None):
    """
    Cost of taking an action = time it takes in hours.
    Simple, honest, and consistent with the heuristic.

    Parameters:
        action_name : str  — name of the action
        time_costs  : dict — optional time overrides

    Returns:
        float — hours this action consumes
    """
    tc = ACTION_DEFAULTS.copy()
    if time_costs:
        tc.update(time_costs)
    return tc[action_name]


# ============================================================
# PIECE 6 — A* ALGORITHM
# ============================================================

def a_star(initial_state, available_hours_per_day=8,
           time_costs=None, risk_threshold = None, tutor_available=True):
    """
    Finds the optimal recovery plan for a student using A* search.

    Parameters:
        initial_state        : State — student's starting situation
        available_hours_per_day : float — daily hour budget (user setting)
        time_costs           : dict  — optional action time overrides
        tutor_available      : bool  — if False, Meet Tutor is excluded

    Returns:
        plan           : list of (action_name, state_before, state_after)
        total_cost     : float — total hours the plan takes
        final_state    : State — student's situation after the plan
        nodes_expanded : int   — how many nodes A* explored
    """

    # ── Setup ────────────────────────────────────────────────
    hours_budget = initial_state.days * available_hours_per_day
    actions      = make_actions(hours_budget,available_hours_per_day, time_costs,risk_threshold, tutor_available)

    # Each heap entry: (f, tiebreaker, g, state, path)
    # f = g + h  (total estimated cost)
    # g = hours spent so far
    # tiebreaker = counter to break equal f values cleanly
    tie         = 0
    h0          = heuristic(initial_state, time_costs, risk_threshold)
    g0          = 0.0
    f0          = g0 + h0

    open_set   = [(f0, tie, g0, initial_state, [])]
    closed_set = set()
    nodes_expanded = 0

    # ── Search ───────────────────────────────────────────────
    while open_set:

        f, _, g, current, path = heapq.heappop(open_set)

        # Skip if already explored this state
        key = state_key(current)
        if key in closed_set:
            continue
        closed_set.add(key)
        nodes_expanded += 1

        # ── Goal check ───────────────────────────────────────
        if is_goal(current, risk_threshold):
            return path, g, current, nodes_expanded

        # ── Expand neighbours ────────────────────────────────
        for action_name, action_fn in actions.items():
            new_state = action_fn(current)

            # Action returned None — invalid (budget exceeded
            # or nothing left to submit)
            if new_state is None:
                continue

            new_key = state_key(new_state)
            if new_key in closed_set:
                continue

            # Calculate new costs
            action_cost = cost(action_name, time_costs)
            new_g       = g + action_cost
            new_h       = heuristic(new_state, time_costs,risk_threshold)
            new_f       = new_g + new_h
            tie        += 1

            # Record this step for the plan output
            step     = (action_name, current.copy(), new_state.copy())
            new_path = path + [step]

            heapq.heappush(open_set,
                           (new_f, tie, new_g, new_state, new_path))

    # ── No plan found ────────────────────────────────────────
    return None, None, None, nodes_expanded

# ============================================================
# PIECE 7 — RUN_ASTAR
# ============================================================

def run_astar(initial_state, available_hours_per_day=8,
              time_costs=None, fatigue_costs=None,
              risk_threshold=None, tutor_available=True):
    """
    Main entry point for the GUI to run the A* planner.

    Parameters:
        initial_state           : State — loaded from CSV or manual input
        available_hours_per_day : float — daily hour budget (what-if)
        time_costs              : dict  — {action: hours} overrides (what-if)
        fatigue_costs           : dict  — {action: fatigue} overrides
                                          passed to scheduler, not used by A*
        tutor_available         : bool  — if False, Meet Tutor excluded

    Returns:
        plan           : list of (action_name, state_before, state_after)
                         or None if no plan found
        total_cost     : float — total hours the plan takes
        final_state    : State — student's situation after completing plan
        runtime_ms     : float — how long A* took in milliseconds
        nodes_expanded : int   — how many nodes A* explored
    """

    start = time.time()

    plan, total_cost, final_state, nodes_expanded = a_star(
        initial_state       = initial_state,
        available_hours_per_day = available_hours_per_day,
        time_costs          = time_costs,
        risk_threshold      = risk_threshold,
        tutor_available     = tutor_available,
    )

    runtime_ms = round((time.time() - start) * 1000, 2)

    return plan, total_cost, final_state, runtime_ms, nodes_expanded


# ============================================================
# MAIN — Quick test of all pieces
# ============================================================

if __name__ == "__main__":
    import pandas as pd

    SEP  = "=" * 55
    THIN = "-" * 55

    print(f"\n{SEP}")
    print("  CORE.PY — COMPONENT TEST")
    print(SEP)

    # ── Test 1: State class ──────────────────────────────────
    print("\n[ PIECE 1 ] State Class")
    s = State(attendance=65.0, missing=3, score=55.0,
              activity=60.0, study_hours=4.0, days=7)
    print(f"  Created  : {s}")
    s2 = s.copy()
    s2.score = 99.0
    print(f"  Original unchanged: score={s.score}")
    print(f"  Copy changed      : score={s2.score}")
    print(f"  Dict access       : days={s['days']}")

    # ── Test 2: csv_row_to_state ─────────────────────────────
    print(f"\n[ PIECE 2 ] csv_row_to_state()")
    row = pd.Series({
        "attendance_rate":      65.0,
        "missing_submissions":  3,
        "avg_quiz_score":       55.0,
        "lms_activity":         60.0,
        "study_hours_per_week": 4.0,
        "days_to_deadline":     7,
    })
    state_from_csv = csv_row_to_state(row)
    print(f"  State from CSV: {state_from_csv}")

    # ── Test 3: risk_score + is_goal ─────────────────────────
    print(f"\n[ PIECE 3 ] risk_score() + is_goal()")

    students = [
        ("All problems (S005)",  48.6, 5,  48.5),
        ("Only attendance",      65.0, 0,  65.0),
        ("Only quiz",            80.0, 0,  50.0),
        ("Only submissions",     80.0, 3,  70.0),
        ("Fully safe",           76.0, 0,  61.0),
        ("GUI max submissions",  76.0, 10, 61.0),
    ]

    for label, att, miss, score in students:
        st = State(att, miss, score, 50.0, 4.0, 7)
        r  = risk_score(st)
        g  = is_goal(st)
        print(f"  {label:<28}: risk={r:.3f}  goal={g}")

    # ── Test 4: state_key ────────────────────────────────────
    print(f"\n[ state_key ]")
    s1 = State(75.70000001, 3, 63.8, 60.0, 4.0, 7, hours_used=2.0)
    s2 = State(75.7,        3, 63.8, 60.0, 4.0, 7, hours_used=2.0)
    print(f"  Key 1: {state_key(s1)}")
    print(f"  Key 2: {state_key(s2)}")
    print(f"  Keys match: {state_key(s1) == state_key(s2)}")

    # ── Test 5: heuristic + cost ─────────────────────────────
    print(f"\n[ PIECE 5 ] heuristic() + cost()")
    st = State(48.6, 5, 48.5, 61.1, 3.9, 13)
    print(f"  S005 heuristic (default): {heuristic(st)}")
    print(f"  S005 heuristic (2h tutor): {heuristic(st, {'Meet Tutor': 2.0})}")
    for action in ACTION_DEFAULTS:
        print(f"  cost({action}): {cost(action)}")

    # ── Test 6 + 7: run_astar ────────────────────────────────
    print(f"\n[ PIECE 6+7 ] a_star() + run_astar()")
    print(THIN)

    test_cases = [
        ("S001 — only submissions",  75.7, 3, 63.8, 66.6, 0.1, 4),
        ("S004 — only quiz",         83.3, 1, 45.4, 52.1, 4.9, 6),
        ("S005 — all problems",      48.6, 5, 48.5, 61.1, 3.9, 13),
        ("No tutor available",       75.7, 3, 45.0, 66.6, 0.1, 7),
    ]

    for label, att, miss, score, act, sh, days in test_cases:
        st = State(att, miss, score, act, sh, days)

        # Special case — no tutor
        tutor = "No tutor" in label

        plan, total_cost, final, runtime_ms, nodes = run_astar(
            initial_state           = st,
            available_hours_per_day = 8,
            tutor_available         = not tutor,
        )

        print(f"\n  {label}")
        print(f"  Initial risk : {risk_score(st):.3f}")

        if plan is None:
            print(f"  ❌ No plan found — nodes expanded: {nodes}")
        else:
            print(f"  ✅ Plan found!")
            print(f"  Steps        : {len(plan)}")
            print(f"  Total hours  : {total_cost}")
            print(f"  Final risk   : {risk_score(final):.3f}")
            print(f"  Nodes expanded: {nodes}")
            print(f"  Runtime      : {runtime_ms}ms")
            print(f"  Actions      : ", end="")
            action_counts = {}
            for action_name, _, _ in plan:
                action_counts[action_name] = action_counts.get(action_name, 0) + 1
            for a, c in action_counts.items():
                print(f"{a}×{c}  ", end="")
            print()
            print(f"  Final score: {final.score}")
            print(f"  Final attendance: {final.attendance}")
            print(f"  Final missing: {final.missing}")

    print(f"\n{SEP}")
    print("  ALL TESTS COMPLETE")
    print(f"{SEP}\n")