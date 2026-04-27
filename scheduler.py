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
    "Attend Class":       4,
    "Submit Assignment":  3,
    "Practice Exam":      4,
    "Meet Tutor":         4,
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

def build_timetable(action_list, available_hours_per_day=8,
                    time_costs=None, fatigue_costs=None,
                    rest_duration=DEFAULT_REST_DURATION,
                    recovery_rate=DEFAULT_REST_RECOVERY):
    """
    Converts an A* action list into a scheduled timetable.

    Parameters:
        action_list             : list of action name strings from A*
        available_hours_per_day : float — daily hour budget
        time_costs              : dict  — {action: hours} overrides
        fatigue_costs           : dict  — {action: fatigue} overrides
        rest_duration           : float — hours per rest session
        recovery_rate           : float — fatigue recovery rate (0.0–1.0)

    Returns:
        timetable : list of days, each day is a list of entries:
            {
                "day":            int,
                "hour":           float,  # hour within the day
                "action":         str,
                "fatigue_before": int,
                "fatigue_after":  int,
                "duration":       float,
            }
    """

    # Merge time cost overrides
    tc = {
        "Study":             1.0,
        "Attend Class":      1.0,
        "Submit Assignment": 1.0,
        "Practice Exam":     2.0,
        "Meet Tutor":        3.0,
        "Rest":              rest_duration,
    }
    if time_costs:
        tc.update(time_costs)

    # Working variables
    timetable        = []       # final output — list of days
    current_day      = []       # entries for the current day
    day_number       = 1
    hours_used_today = 0.0
    fatigue          = 0

    actions_remaining = list(action_list)   # copy so we don't modify original

    while actions_remaining:

        next_action = actions_remaining[0]
        action_time = tc[next_action]

        # ── Check if action fits in today's remaining hours ──
        hours_left_today = available_hours_per_day - hours_used_today

        # Does the action itself fit today? If not, start a new day
        if action_time > hours_left_today:
            # Save current day and start fresh
            if current_day:
                timetable.append(current_day)
            current_day       = []
            day_number       += 1
            hours_used_today  = 0.0
            fatigue           = 0        # overnight reset
            continue                     # retry same action tomorrow

        # ── Insert rest if needed before this action ────────
        while not can_perform(next_action, fatigue, fatigue_costs):

            rest_time = tc["Rest"]

            # Check if rest fits today
            if hours_used_today + rest_time > available_hours_per_day:
                # No room for rest today — start new day
                if current_day:
                    timetable.append(current_day)
                current_day       = []
                day_number       += 1
                hours_used_today  = 0.0
                fatigue           = 0    # overnight reset
                break                   # recheck action tomorrow

            # Insert rest entry
            fatigue_before = fatigue
            fatigue        = apply_rest(fatigue, recovery_rate)

            current_day.append({
                "day":            day_number,
                "hour":           round(hours_used_today, 1),
                "action":         "Rest",
                "fatigue_before": fatigue_before,
                "fatigue_after":  fatigue,
                "duration":       rest_time,
            })

            hours_used_today = round(hours_used_today + rest_time, 1)
        
        # Recheck: after rest, does action still fit today?
        if hours_used_today + action_time > available_hours_per_day:
            if current_day:
                timetable.append(current_day)
            current_day       = []
            day_number       += 1
            hours_used_today  = 0.0
            fatigue           = 0
            continue

        # ── Re-check after possible day rollover ────────────
        if not can_perform(next_action, fatigue, fatigue_costs):
            continue    # still can't perform — loop will retry

        # ── Perform the action ───────────────────────────────
        fatigue_before = fatigue
        fatigue       += get_fatigue_cost(next_action, fatigue_costs)

        current_day.append({
            "day":            day_number,
            "hour":           round(hours_used_today, 1),
            "action":         next_action,
            "fatigue_before": fatigue_before,
            "fatigue_after":  fatigue,
            "duration":       action_time,
        })

        hours_used_today = round(hours_used_today + action_time, 1)
        actions_remaining.pop(0)    # action complete, remove from list

        # ── End of day check ─────────────────────────────────
        if hours_used_today >= available_hours_per_day:
            timetable.append(current_day)
            current_day       = []
            day_number       += 1
            hours_used_today  = 0.0
            fatigue           = 0        # overnight reset

        print(f"DEBUG: hours_used={hours_used_today}, "
            f"next={next_action}, "
            f"fatigue={fatigue}, "
            f"can_perform={can_perform(next_action, fatigue, fatigue_costs)}")

    # Save any remaining entries in the last day
    if current_day:
        timetable.append(current_day)
    
    
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