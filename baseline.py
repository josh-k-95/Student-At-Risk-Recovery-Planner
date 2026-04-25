"""
baseline.py — Baseline Comparison Algorithms
Greedy Search and Uniform Cost Search for comparison with A*.
Uses identical state, actions and goal as core.py.
CSAI 350 · Spring 2026 · AURAK
"""

import heapq
import time
from core import (
    State, state_key, is_goal, heuristic,
    cost, make_actions, ACTION_DEFAULTS
)


# ============================================================
# GREEDY SEARCH
# ============================================================

def greedy_search(initial_state, available_hours_per_day=8,
                  time_costs=None, tutor_available=True):
    """
    Greedy Best-First Search.
    Always expands the node that appears closest to the goal
    based on the heuristic alone. Ignores actual cost spent.

    Parameters:
        initial_state           : State
        available_hours_per_day : float
        time_costs              : dict — optional time overrides
        tutor_available         : bool

    Returns:
        plan           : list of (action_name, state_before, state_after)
        total_cost     : float — total hours
        final_state    : State
        nodes_expanded : int
    """
    hours_budget = initial_state.days * available_hours_per_day
    actions      = make_actions(hours_budget, available_hours_per_day,
                                time_costs, None, tutor_available)

    tie        = 0
    h0         = heuristic(initial_state, time_costs)

    # Key difference from A*: heap sorted by h(n) ONLY, not f = g + h
    open_set   = [(h0, tie, initial_state, [])]
    closed_set = set()
    nodes_expanded = 0

    while open_set:
        h, _, current, path = heapq.heappop(open_set)

        key = state_key(current)
        if key in closed_set:
            continue
        closed_set.add(key)
        nodes_expanded += 1

        if is_goal(current):
            total_cost = sum(
                cost(action_name, time_costs)
                for action_name, _, _ in path
            )
            return path, total_cost, current, nodes_expanded

        for action_name, action_fn in actions.items():
            new_state = action_fn(current)
            if new_state is None:
                continue

            new_key = state_key(new_state)
            if new_key in closed_set:
                continue

            # Greedy: priority = h(n) only
            new_h = heuristic(new_state, time_costs)
            tie  += 1

            step     = (action_name, current.copy(), new_state.copy())
            new_path = path + [step]

            heapq.heappush(open_set, (new_h, tie, new_state, new_path))

    return None, None, None, nodes_expanded


# ============================================================
# UNIFORM COST SEARCH (UCS)
# f(n) = g(n) only — ignores heuristic, expands cheapest
# path first. Guaranteed optimal but slower than A*.
# ============================================================

def uniform_cost_search(initial_state, available_hours_per_day=8,
                        time_costs=None, tutor_available=True):
    """
    Uniform Cost Search.
    Always expands the node with the lowest cumulative cost.
    Equivalent to A* with h(n) = 0.
    Guaranteed to find the optimal plan but explores more nodes.

    Parameters:
        initial_state           : State
        available_hours_per_day : float
        time_costs              : dict — optional time overrides
        tutor_available         : bool

    Returns:
        plan           : list of (action_name, state_before, state_after)
        total_cost     : float — total hours
        final_state    : State
        nodes_expanded : int
    """
    hours_budget = initial_state.days * available_hours_per_day
    actions      = make_actions(hours_budget, available_hours_per_day,
                                time_costs,None, tutor_available)

    tie        = 0
    g0         = 0.0

    # Key difference from A*: heap sorted by g(n) ONLY, h(n) = 0
    open_set   = [(g0, tie, initial_state, [])]
    closed_set = set()
    nodes_expanded = 0

    while open_set:
        g, _, current, path = heapq.heappop(open_set)

        key = state_key(current)
        if key in closed_set:
            continue
        closed_set.add(key)
        nodes_expanded += 1

        if is_goal(current):
            return path, g, current, nodes_expanded

        for action_name, action_fn in actions.items():
            new_state = action_fn(current)
            if new_state is None:
                continue

            new_key = state_key(new_state)
            if new_key in closed_set:
                continue

            # UCS: priority = g(n) only, no heuristic
            action_cost = cost(action_name, time_costs)
            new_g       = g + action_cost
            tie        += 1

            step     = (action_name, current.copy(), new_state.copy())
            new_path = path + [step]

            heapq.heappush(open_set, (new_g, tie, new_state, new_path))

    return None, None, None, nodes_expanded


# ============================================================
# RUN WRAPPERS — same signature as run_astar()
# ============================================================

def run_greedy(initial_state, available_hours_per_day=8,
               time_costs=None, fatigue_costs=None,
               tutor_available=True):
    """Wrapper for greedy_search() matching run_astar() signature."""
    start = time.time()

    plan, total_cost, final_state, nodes_expanded = greedy_search(
        initial_state           = initial_state,
        available_hours_per_day = available_hours_per_day,
        time_costs              = time_costs,
        tutor_available         = tutor_available,
    )

    runtime_ms = round((time.time() - start) * 1000, 2)
    return plan, total_cost, final_state, runtime_ms, nodes_expanded


def run_ucs(initial_state, available_hours_per_day=8,
            time_costs=None, fatigue_costs=None,
            tutor_available=True):
    """Wrapper for uniform_cost_search() matching run_astar() signature."""
    start = time.time()

    plan, total_cost, final_state, nodes_expanded = uniform_cost_search(
        initial_state           = initial_state,
        available_hours_per_day = available_hours_per_day,
        time_costs              = time_costs,
        tutor_available         = tutor_available,
    )

    runtime_ms = round((time.time() - start) * 1000, 2)
    return plan, total_cost, final_state, runtime_ms, nodes_expanded


# ============================================================
# MAIN — Comparison test against A*
# ============================================================

if __name__ == "__main__":
    from core import State, risk_score, run_astar

    SEP  = "=" * 65
    THIN = "-" * 65

    print(f"\n{SEP}")
    print("  BASELINE COMPARISON — A* vs Greedy vs UCS")
    print(SEP)

    test_cases = [
        ("S001 — only submissions",  75.7, 3,  63.8, 66.6, 0.1, 4),
        ("S004 — only quiz",         83.3, 1,  45.4, 52.1, 4.9, 6),
        ("S005 — all problems",      48.6, 5,  48.5, 61.1, 3.9, 13),
        ("No tutor available",       75.7, 3,  45.0, 66.6, 0.1, 7),
    ]

    for label, att, miss, score, act, sh, days in test_cases:
        st    = State(att, miss, score, act, sh, days)
        tutor = "No tutor" in label

        print(f"\n  {label}")
        print(f"  Initial risk: {risk_score(st):.3f}")
        print(f"  {THIN}")
        print(f"  {'Algorithm':<10} {'Cost':>6} {'Nodes':>8} "
              f"{'Runtime':>10} {'Found?':>7}")
        print(f"  {THIN}")

        for algo_name, run_fn in [
            ("A*",     run_astar),
            ("Greedy", run_greedy),
            ("UCS",    run_ucs),
        ]:
            plan, total_cost, final, runtime_ms, nodes = run_fn(
                initial_state           = st,
                available_hours_per_day = 8,
                tutor_available         = not tutor,
            )

            if plan is None:
                print(f"  {algo_name:<10} {'—':>6} {nodes:>8} "
                      f"{runtime_ms:>9.2f}ms {'❌ No':>7}")
            else:
                action_counts = {}
                for action_name, _, _ in plan:
                    action_counts[action_name] = \
                        action_counts.get(action_name, 0) + 1
                actions_str = "  ".join(
                    f"{a}×{c}" for a, c in action_counts.items()
                )
                print(f"  {algo_name:<10} {total_cost:>6.1f} {nodes:>8} "
                      f"{runtime_ms:>9.2f}ms {'✅ Yes':>7}")
                print(f"  {'':10} {actions_str}")

    print(f"\n{SEP}\n")