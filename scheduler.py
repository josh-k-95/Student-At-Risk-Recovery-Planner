"""
scheduler.py — Daily Timetable Builder
Takes the action list from A* and arranges it into an
hour-by-hour schedule, managing fatigue and rest automatically.
CSAI 350 · Spring 2026 · AURAK
"""

import math

# ============================================================
# PIECE 1 — FATIGUE COSTS
# ============================================================

FATIGUE_DEFAULTS = {
    "Study":              3,
    "Attend Class":       6,
    "Submit Assignment":  3,
    "Practice Exam":      4,
    "Meet Tutor":         6,
    "Rest":               0,
}

MAX_FATIGUE = 10


def get_fatigue_cost(action_name, fatigue_costs=None):
    """
    Returns the fatigue cost of an action.
    Merges user overrides with defaults.

    Parameters:
        action_name   : str  — name of the action
        fatigue_costs : dict — optional {action: fatigue} overrides

    Returns:
        int — fatigue cost of the action
    """
    fc = FATIGUE_DEFAULTS.copy()
    if fatigue_costs:
        fc.update(fatigue_costs)
    return min(fc[action_name], MAX_FATIGUE)


def can_perform(action_name, current_fatigue, fatigue_costs=None):
    """
    Returns True if the student has enough energy to perform
    the action without exceeding MAX_FATIGUE.

    Parameters:
        action_name     : str   — name of the action
        current_fatigue : float — student's current fatigue
        fatigue_costs   : dict  — optional overrides

    Returns:
        bool
    """
    return current_fatigue + get_fatigue_cost(action_name, fatigue_costs) <= MAX_FATIGUE


# ============================================================
# PIECE 2 — REST RECOVERY
# ============================================================

DEFAULT_REST_DURATION     = 1.0   # hours
DEFAULT_REST_RECOVERY     = 0.6   # 60% fatigue removed per rest


def apply_rest(current_fatigue, recovery_rate=DEFAULT_REST_RECOVERY):
    """
    Reduces fatigue by recovery_rate percentage, rounded to
    nearest integer.

    Why percentage-based?
        - More fatigued  → more recovery (realistic)
        - Less fatigued  → less recovery (diminishing returns)
        - Always reaches 0 due to rounding

    Proof it always terminates:
        fatigue=10, rate=0.6:
          10 → 4 → 2 → 1 → 0  (4 rests max)

    Parameters:
        current_fatigue : float — fatigue before rest
        recovery_rate   : float — percentage removed (0.0–1.0)

    Returns:
        int — fatigue after rest
    """

    if current_fatigue == 0:
        return 0
    recovered = round(current_fatigue * (1 - recovery_rate))
    # Guarantee at least 1 point of fatigue is always removed
    return min(recovered, current_fatigue - 1)


def rests_needed(action_name, current_fatigue,
                 fatigue_costs=None, recovery_rate=DEFAULT_REST_RECOVERY):
    """
    Calculates how many rest actions are needed before
    the student can perform the given action.

    Parameters:
        action_name     : str   — action the student wants to do
        current_fatigue : float — current fatigue level
        fatigue_costs   : dict  — optional overrides
        recovery_rate   : float — rest effectiveness (0.0–1.0)

    Returns:
        int — number of rests needed (0 if already possible)
    """
    fatigue = current_fatigue
    count   = 0


    while not can_perform(action_name, fatigue, fatigue_costs):
        fatigue = apply_rest(fatigue, recovery_rate)
        count  += 1
        if count > MAX_FATIGUE:   # safety guard
            break

    return count



# ============================================================
# PIECE 3 — BUILD TIMETABLE 
# ============================================================

# Define how many times an action can be performed in a single day
DAILY_CAPS = {
    "Attend Class":       1,
    "Practice Exam":      1,
    "Meet Tutor":         1,
    "Study":              99,  # Unlimited chunks
    "Submit Assignment":  99,  # Unlimited chunks
    "Rest":               99,
}

def build_timetable(action_list, available_hours_per_day, deadline_days,
                    time_costs=None, fatigue_costs=None,
                    rest_duration=DEFAULT_REST_DURATION,
                    recovery_rate=DEFAULT_REST_RECOVERY):
    """
    Converts an A* action list into a realistic timetable.
    Acts as a 'Smart Arranger' — skips actions that are on cooldown
    and fills the day with other available actions.
    
    Returns None if the plan mathematically cannot fit within the deadline.
    """
    tc = {
        "Study":             1.0,
        "Attend Class":      1.0,
        "Submit Assignment": 1.0,
        "Practice Exam":     2.0,
        "Meet Tutor":        3.0,
        "Rest":              rest_duration,
    }
    if time_costs: tc.update(time_costs)

    timetable        = []       
    current_day      = []       
    day_number       = 1
    hours_used_today = 0.0
    fatigue          = 0
    
    # Track cooldowns per day
    actions_done_today = {k: 0 for k in DAILY_CAPS}

    # Treat the A* plan as a pool of required ingredients
    pool = list(action_list)

    while pool:
        #  HARD DEADLINE CHECK
        if day_number > deadline_days:
            return None # The plan is physically impossible in the given timeframe

        # Look through the pool for the first action that hasn't hit its daily cap
        chosen_action = None
        for action in pool:
            if actions_done_today.get(action, 0) < DAILY_CAPS.get(action, 1):
                chosen_action = action
                break
        
        #  IF ALL ACTIONS ARE ON COOLDOWN, FORCE ROLLOVER
        if not chosen_action:
            if current_day:
                timetable.append(current_day)
            current_day = []
            day_number += 1
            hours_used_today = 0.0
            fatigue = 0
            actions_done_today = {k: 0 for k in DAILY_CAPS}
            continue

        action_time = tc[chosen_action]
        hours_left_today = available_hours_per_day - hours_used_today

        if action_time > hours_left_today and hours_used_today > 0:
            if current_day:
                timetable.append(current_day)
            current_day = []
            day_number += 1
            hours_used_today = 0.0
            fatigue = 0
            actions_done_today = {k: 0 for k in DAILY_CAPS}
            continue

        if not can_perform(chosen_action, fatigue, fatigue_costs):
            rest_time = tc["Rest"]
            
            if rest_time > (available_hours_per_day - hours_used_today) and hours_used_today > 0:
                if current_day:
                    timetable.append(current_day)
                current_day = []
                day_number += 1
                hours_used_today = 0.0
                fatigue = 0
                actions_done_today = {k: 0 for k in DAILY_CAPS}
                continue

            # Perform Rest
            fatigue_before = fatigue
            fatigue = apply_rest(fatigue, recovery_rate)
            
            current_day.append({
                "day":            day_number,
                "start_hour":     round(hours_used_today, 1),
                "end_hour":       round(hours_used_today + rest_time, 1),
                "action":         "Rest",
                "fatigue_before": fatigue_before,
                "fatigue_after":  fatigue,
                "duration":       rest_time,
            })
            hours_used_today = round(hours_used_today + rest_time, 1)
            actions_done_today["Rest"] += 1
            continue # Re-evaluate the chosen_action now that we are rested

        # 6. PERFORM THE ACTION
        fatigue_before = fatigue
        fatigue += get_fatigue_cost(chosen_action, fatigue_costs)
        
        current_day.append({
            "day":            day_number,
            "start_hour":     round(hours_used_today, 1),
            "end_hour":       round(hours_used_today + action_time, 1),
            "action":         chosen_action,
            "fatigue_before": fatigue_before,
            "fatigue_after":  fatigue,
            "duration":       action_time,
        })
        
        hours_used_today = round(hours_used_today + action_time, 1)
        actions_done_today[chosen_action] += 1
        
        # Remove from the pool so we don't do it again
        pool.remove(chosen_action)

        # 7. END OF DAY CHECK
        if hours_used_today >= available_hours_per_day:
            timetable.append(current_day)
            current_day = []
            day_number += 1
            hours_used_today = 0.0
            fatigue = 0
            actions_done_today = {k: 0 for k in DAILY_CAPS}

    if current_day:
        timetable.append(current_day)
        
    # Final check: did the very last day push us over the deadline?
    if day_number > deadline_days and not (day_number == deadline_days + 1 and len(current_day) == 0):
        return None

    return timetable


def format_timetable(timetable):
    """
    Prints the timetable in a readable format for terminal testing.

    Parameters:
        timetable : list of days from build_timetable()
    """
    SEP  = "=" * 55
    THIN = "-" * 55

    print(f"\n{SEP}")
    print("  SCHEDULED TIMETABLE")
    print(SEP)

    for day in timetable:
        if not day:
            continue

        day_number = day[0]["day"]
        print(f"\n  DAY {day_number}")
        print(f"  {THIN}")

        for entry in day:
            hour   = entry["hour"]
            action = entry["action"]
            dur    = entry["duration"]
            fb     = entry["fatigue_before"]
            fa     = entry["fatigue_after"]

            # Format hour as HH:MM
            h      = int(8 + hour)        # assume 8am start
            m      = int((hour % 1) * 60)
            time   = f"{h:02d}:{m:02d}"

            fatigue_bar = "█" * fa + "░" * (10 - fa)

            print(f"  {time}  {action:<22} "
                  f"({dur}h)  "
                  f"fatigue: {fb}→{fa}  "
                  f"[{fatigue_bar}]")

    print(f"\n{SEP}\n")

if __name__ == "__main__":

    # ... keep existing piece 1+2 tests ...

    # ── Test build_timetable ─────────────────────────────────
    print("\n[ PIECE 3 ] build_timetable()")

    # Simulate A* output for S005
    s005_plan = [
        "Attend Class", "Attend Class", "Attend Class",
        "Attend Class", "Attend Class", "Attend Class",
        "Attend Class", "Attend Class", "Attend Class",
        "Practice Exam",
        "Submit Assignment", "Submit Assignment",
        "Submit Assignment", "Submit Assignment",
        "Submit Assignment",
    ]

    timetable = build_timetable(
        action_list             = s005_plan,
        available_hours_per_day = 8,
    )

    format_timetable(timetable)
    print(f"  Total days needed: {len(timetable)}")
    print(f"  Total entries (inc. rest): "
          f"{sum(len(d) for d in timetable)}")