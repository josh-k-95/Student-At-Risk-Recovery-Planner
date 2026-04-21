import streamlit as st
import pandas as pd
import core

# ── Page configuration ──────────────────────────────────────s
st.set_page_config(
    page_title="Student At-Risk Recovery Planner",
    page_icon="📊",
    layout="wide",
)

# ── Session state initialisation ────────────────────────────
# These variables persist across button clicks inside one session.
if "student_df"     not in st.session_state: st.session_state.student_df     = None
if "current_state"  not in st.session_state: st.session_state.current_state  = None
if "result"         not in st.session_state: st.session_state.result         = None
if "whatif_results" not in st.session_state: st.session_state.whatif_results = []

# ── App header ───────────────────────────────────────────────
st.title("Student At-Risk Recovery Planner")
st.caption("CSAI 350 · Spring 2026 · American University of Ras Al Khaimah")
st.divider()

# ════════════════════════════════════════════════════════════
#  SIDEBAR  (YOUR CODE – controls panel)
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Control Panel")

    # ── Section 1: Data Input ────────────────────────────────
    st.subheader("📂 Data Input")

    # Radio button: choose how to load a student
    input_mode = st.radio(
        "Choose input method:",
        ["Upload CSV File", "Generate Random Scenario", "Enter Manually"],
    )

    # ── CSV upload (hooks into Member A's loader) ────────────
    if input_mode == "Upload CSV File":
        uploaded_file = st.file_uploader(
            "Upload student CSV file",
            type=["csv"],
            help="Must contain: attendance_rate, missing_submissions, "
                 "avg_quiz_score, lms_activity, study_hours_per_week, days_to_deadline",
        )

        if uploaded_file is not None:
            # Load CSV into session state
            st.session_state.student_df = pd.read_csv(uploaded_file)
            st.success(f"Loaded {len(st.session_state.student_df)} students.")

        if st.session_state.student_df is not None:
            # Student selector dropdown
            student_ids = st.session_state.student_df["student_id"].tolist()
            chosen_id   = st.selectbox("Select a student:", student_ids)

            if st.button("✅ Load Selected Student"):
                row = st.session_state.student_df[
                    st.session_state.student_df["student_id"] == chosen_id
                ].iloc[0]
                # ← Member A's csv_row_to_state() converts the row
                st.session_state.current_state = csv_row_to_state(row)
                st.session_state.result        = None
                st.success(f"Student {chosen_id} loaded.")

    # ── Random scenario generator ────────────────────────────
    elif input_mode == "Generate Random Scenario":
        import random
        if st.button("🎲 Generate Random Scenario"):
            st.session_state.current_state = {
                "attendance": round(random.uniform(40, 85), 1),
                "missing":    random.randint(1, 5),
                "score":      round(random.uniform(30, 70), 1),
                "lms":        round(random.uniform(20, 80), 1),
                "days":       random.randint(2, 14),
                "fatigue":    random.randint(2, 7),
            }
            st.session_state.result = None
            st.success("Random scenario generated.")

    # ── Manual entry form ────────────────────────────────────
    else:
        with st.form("manual_entry_form"):
            st.write("Enter student values manually:")
            att  = st.slider("Attendance Rate (%)",   0, 100, 70)
            miss = st.number_input("Missing Submissions", 0, 10,  2, step=1)
            quiz = st.slider("Avg Quiz Score",         0, 100, 55)
            lms  = st.slider("LMS Activity",           0, 100, 50)
            days = st.number_input("Days to Deadline", 1,  30,  7, step=1)
            fat  = st.slider("Fatigue Level (0–10)",   0,  10,  4)
            submitted = st.form_submit_button("✅ Apply Values")

        if submitted:
            """
            st.session_state.current_state = {
                "attendance": att,
                "missing":    int(miss),
                "score":      quiz,
                "lms":        lms,
                "days":       int(days),
                "fatigue":    fat,
            }
            """
            st.session_state.current_state = core.State(att,int(miss),quiz,lms,8,int(days))        
            st.session_state.result = None
            st.success("Manual values applied.")

    st.divider()

    # ── Section 2: Planner Settings ─────────────────────────
    st.subheader("🔧 Planner Settings")

    risk_threshold   = st.slider("Risk Threshold (goal)",   0.05, 0.50, 0.25, 0.01,
                                  help="A* stops when risk falls below this value")
    max_steps        = st.slider("Max Plan Steps",           5,    30,   15,
                                  help="Maximum number of actions in the recovery plan")
    max_daily_study  = st.slider("Max Study Actions / Day",  1,     6,    3)
    tutor_available  = st.checkbox("Tutor Available", value=True)
    deadline_weight  = st.slider("Deadline Penalty Weight",  0.0,  5.0,  2.0, 0.5)
    fatigue_weight   = st.slider("Fatigue Penalty Weight",   0.0,  5.0,  1.0, 0.5)

    st.divider()

    # ── RUN BUTTON ───────────────────────────────────────────
    # This is the primary action button of the entire app.
    run_button = st.button(
        "▶️  Run A* Planner",
        type="primary",
        use_container_width=True,
        disabled=(st.session_state.current_state is None),
    )

# ── Execute A* when the Run button is pressed ────────────────
if run_button and st.session_state.current_state is not None:
    with st.spinner("Running A* search algorithm…"):
        # ← Member F's run_astar() is called here
        plan, total_cost, final_state, runtime_ms, nodes_expanded = run_astar(
            initial_state    = st.session_state.current_state,
            threshold        = risk_threshold,
            max_steps        = max_steps,
            max_daily_study  = max_daily_study,
            tutor_available  = tutor_available,
            deadline_weight  = deadline_weight,
            fatigue_weight   = fatigue_weight,
        )
    # Store results in session state so all tabs can read them
    st.session_state.result = {
        "plan":            plan,
        "total_cost":      round(total_cost, 2),
        "final_state":     final_state,
        "runtime_ms":      runtime_ms,
        "nodes_expanded":  nodes_expanded,
        "risk_before":     core.risk_score(st.session_state.current_state),
        "risk_after":      core.risk_score(final_state),
        "threshold":       risk_threshold,
    }

# ════════════════════════════════════════════════════════════
#  MAIN AREA: FOUR TABS
# ════════════════════════════════════════════════════════════
tab_dashboard, tab_dataset, tab_comparison, tab_whatif = st.tabs([
    "📊 Dashboard",
    "📂 Dataset",
    "⚖️ Algorithm Comparison",
    "🔁 What-If Simulation",
])

# ────────────────────────────────────────────────────────────
#  TAB 1 – DASHBOARD
# ────────────────────────────────────────────────────────────
with tab_dashboard:

    if st.session_state.current_state is None:
        st.info("👈  Load a student using the sidebar, then press **Run A* Planner**.")

    else:
        init  = st.session_state.current_state
        res   = st.session_state.result

        # ── Top metric cards ─────────────────────────────────
        # Four summary numbers shown at the top of the dashboard
        col1, col2, col3, col4 = st.columns(4)
        init_risk = core.risk_score(init)

        with col1:
            st.metric("Initial Risk Score",
                      f"{init_risk:.1%}",
                      help="Risk before any recovery actions")
        with col2:
            if res:
                delta = res["risk_after"] - init_risk
                st.metric("Final Risk Score",
                          f"{res['risk_after']:.1%}",
                          delta=f"{delta:+.1%}",
                          delta_color="inverse")
            else:
                st.metric("Final Risk Score", "—")
        with col3:
            st.metric("Plan Steps",
                      len(res["plan"]) if res else "—")
        with col4:
            st.metric("Total Cost",
                      res["total_cost"] if res else "—")

        st.divider()

        # ── Two-column layout: plan text | charts ────────────
        left_col, right_col = st.columns([1, 1], gap="large")

        # ── Left column: state display + plan steps ──────────
        with left_col:

            # Initial state text area
            st.subheader("📋 Initial State")
            state_text = (
                f"attendance_rate   : {init.attendance:.1f}\n"
                f"missing_submissions: {init.missing}\n"
                f"avg_quiz_score     : {init.score:.1f}\n"
                f"lms_activity       : {init.activity:.1f}\n"
                f"days_to_deadline   : {init.days}\n"
                f"fatigue_level      : {init['fatigue']}\n"
                f"─────────────────────────────\n"
                f"risk_score         : {init_risk:.4f}\n"
                f"status             : {'⚠️ AT RISK' if init_risk > risk_threshold else '✅ NOT AT RISK'}"
            )
            # TEXT AREA – displays initial student state
            st.text_area(
                label="Initial student state",
                value=state_text,
                height=220,
                disabled=True,
                label_visibility="collapsed",
            )

            # Recovery plan text area (shown after A* runs)
            if res:
                st.subheader("📝 Recovery Plan  (A*)")

                if res["plan"]:
                    plan_lines = []
                    for i, (action, cost) in enumerate(res["plan"], 1):
                        icon = ACTIONS.get(action, {}).get("icon", "•")
                        plan_lines.append(f"{i:>2}. {icon} {action:<22}  cost={cost}")
                    plan_lines.append("─" * 42)
                    plan_lines.append(f"    Total cost  : {res['total_cost']}")
                    plan_lines.append(f"    Runtime     : {res['runtime_ms']} ms")
                    plan_lines.append(f"    Nodes expand: {res['nodes_expanded']}")
                    plan_text = "\n".join(plan_lines)
                else:
                    plan_text = "No plan found. Try relaxing the constraints."

                # TEXT AREA – displays the A* recovery plan
                st.text_area(
                    label="A* plan output",
                    value=plan_text,
                    height=240,
                    disabled=True,
                    label_visibility="collapsed",
                )

                # Final state text area
                st.subheader("🏁 Final State")
                fs   = res["final_state"]
                risk_after = res["risk_after"]
                final_text = (
                    f"attendance_rate   : {fs['attendance']:.1f}\n"
                    f"missing_submissions: {fs['missing']}\n"
                    f"avg_quiz_score     : {fs['score']:.1f}\n"
                    f"lms_activity       : {fs['lms']:.1f}\n"
                    f"days_to_deadline   : {fs['days']}\n"
                    f"fatigue_level      : {fs['fatigue']}\n"
                    f"─────────────────────────────\n"
                    f"risk_score         : {risk_after:.4f}\n"
                    f"status             : {'✅ NOT AT RISK' if risk_after <= risk_threshold else '⚠️ STILL AT RISK'}"
                )
                # TEXT AREA – displays final state after recovery plan
                st.text_area(
                    label="Final student state",
                    value=final_text,
                    height=210,
                    disabled=True,
                    label_visibility="collapsed",
                )

        # ── Right column: plots (Member D) ───────────────────
        with right_col:
            if res:
                st.subheader("📊 Risk: Before vs After")
                # ← Member D's plot_risk_before_after() is called here
                fig_risk = plot_risk_before_after(
                    res["risk_before"], res["risk_after"], res["threshold"]
                )
                st.pyplot(fig_risk, use_container_width=True)
                plt.close(fig_risk)

                st.subheader("📊 Action Counts")
                # ← Member D's plot_action_counts() is called here
                fig_actions = plot_action_counts(res["plan"])
                st.pyplot(fig_actions, use_container_width=True)
                plt.close(fig_actions)
            else:
                st.info("Charts will appear here after you run the planner.")


# ────────────────────────────────────────────────────────────
#  TAB 2 – DATASET VIEW
#  Powered by Member A's CSV loader
# ────────────────────────────────────────────────────────────
with tab_dataset:
    st.subheader("📂 Student Dataset")

    if st.session_state.student_df is None:
        st.info("Upload a CSV file in the sidebar to view the dataset here.")
    else:
        df = st.session_state.student_df.copy()

        # Add computed risk score column (← Member A's core.risk_score)
        df["risk_score"] = df.apply(lambda r: round(core.risk_score(
            csv_row_to_state(r)), 3), axis=1)
        df["status"] = df["risk_score"].apply(
            lambda x: "⚠️ At-Risk" if x > risk_threshold else "✅ Safe"
        )

        # Summary numbers
        at_risk_count = (df["risk_score"] > risk_threshold).sum()
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Students",  len(df))
        col_b.metric("At-Risk Students", at_risk_count)
        col_c.metric("Safe Students", len(df) - at_risk_count)

        # Full dataset table
        st.dataframe(df, use_container_width=True, height=380)

        # Download button for enriched CSV
        csv_download = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️  Download with Risk Scores",
            data=csv_download,
            file_name="students_with_risk.csv",
            mime="text/csv",
        )


# ────────────────────────────────────────────────────────────
#  TAB 3 – ALGORITHM COMPARISON
#  A* vs Greedy vs UCS
#  Member F: add run_greedy() and run_ucs() functions above
#  (same signature as run_astar) so this tab can call them.
# ────────────────────────────────────────────────────────────
with tab_comparison:
    st.subheader("⚖️ Algorithm Comparison")

    if st.session_state.current_state is None or st.session_state.result is None:
        st.info("Run the planner first to see the comparison table.")
    else:
        init = st.session_state.current_state
        res  = st.session_state.result

        # ── Run all three algorithms ──────────────────────────
        # ← Member F: replace the greedy/ucs placeholders with real implementations.
        #   Each function should have the same signature as run_astar().
        with st.spinner("Running comparison algorithms…"):
            plan_a, cost_a, _, rt_a, exp_a = run_astar(
                init, risk_threshold, max_steps, max_daily_study,
                tutor_available, deadline_weight, fatigue_weight)

            # PLACEHOLDER: Member F adds run_greedy() here
            plan_g, cost_g, _, rt_g, exp_g = run_astar(
                init, risk_threshold, max_steps, max_daily_study,
                tutor_available, deadline_weight, fatigue_weight)

            # PLACEHOLDER: Member F adds run_ucs() here
            plan_u, cost_u, _, rt_u, exp_u = run_astar(
                init, risk_threshold, max_steps, max_daily_study,
                tutor_available, deadline_weight, fatigue_weight)

        # ── Comparison table ─────────────────────────────────
        comparison_df = pd.DataFrame({
            "Algorithm":       ["A* (Optimal)", "Greedy", "UCS"],
            "Total Cost":      [cost_a,         cost_g,   cost_u],
            "Runtime (ms)":    [rt_a,            rt_g,     rt_u],
            "Nodes Expanded":  [exp_a,           exp_g,    exp_u],
            "Plan Length":     [len(plan_a),     len(plan_g), len(plan_u)],
        })
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        st.caption("Lower cost and fewer nodes = better performance.")


# ────────────────────────────────────────────────────────────
#  TAB 4 – WHAT-IF SIMULATION
#  Member E: insert your 3 constraint widgets below
#  where the comments say "← MEMBER E: insert widget here"
# ────────────────────────────────────────────────────────────
with tab_whatif:
    st.subheader("🔁 What-If Simulation")
    st.write("Change constraints below and re-run the planner to see how the plan changes.")

    if st.session_state.current_state is None:
        st.info("Load a student first.")
    else:
        wif_col1, wif_col2 = st.columns(2)

        with wif_col1:
            st.markdown("**Constraint Controls**")

            # ── MEMBER E: What-If Widget 1 ───────────────────
            # Suggested: checkbox for tutor availability
            wif_tutor = st.checkbox(
                "Tutor Available",
                value=True,
                key="wif_tutor",
                help="Uncheck to simulate tutor being unavailable",
            )
            # ← MEMBER E: insert additional logic for this widget here

            # ── MEMBER E: What-If Widget 2 ───────────────────
            # Suggested: slider for deadline proximity
            wif_days = st.slider(
                "Days to Deadline (override)",
                min_value=1,
                max_value=14,
                value=st.session_state.current_state.get("days", 7),
                key="wif_days",
                help="Drag left to simulate a closer deadline",
            )
            # ← MEMBER E: insert additional logic for this widget here

            # ── MEMBER E: What-If Widget 3 ───────────────────
            # Suggested: slider for max study hours per day
            wif_max_study = st.slider(
                "Max Study Actions per Day",
                min_value=1,
                max_value=6,
                value=3,
                key="wif_max_study",
                help="Reduce to simulate limited available study time",
            )
            # ← MEMBER E: insert additional logic for this widget here

        with wif_col2:
            # ── Run what-if button ────────────────────────────
            if st.button("▶️  Run What-If Analysis", use_container_width=True):

                # Build a modified state using the what-if deadline override
                wif_state = st.session_state.current_state.copy()
                wif_state["days"] = wif_days

                with st.spinner("Running what-if scenarios…"):
                    # ← Member F's run_astar() is called with what-if constraints
                    wif_plan, wif_cost, wif_final, wif_rt, wif_exp = run_astar(
                        initial_state    = wif_state,
                        threshold        = risk_threshold,
                        max_steps        = max_steps,
                        max_daily_study  = wif_max_study,
                        tutor_available  = wif_tutor,
                        deadline_weight  = deadline_weight,
                        fatigue_weight   = fatigue_weight,
                    )

                st.session_state.whatif_results = {
                    "plan":           wif_plan,
                    "cost":           round(wif_cost, 2),
                    "final_state":    wif_final,
                    "runtime_ms":     wif_rt,
                    "nodes_expanded": wif_exp,
                    "risk_after":     core.risk_score(wif_final),
                }

        # ── What-if result text area ──────────────────────────
        if st.session_state.whatif_results:
            wres = st.session_state.whatif_results
            outcome = (
                "✅ Student recovered (Not At-Risk)"
                if wres["risk_after"] <= risk_threshold
                else "❌ Student still At-Risk"
            )
            wif_lines = [outcome, ""]
            wif_lines.append(f"Total cost      : {wres['cost']}")
            wif_lines.append(f"Runtime         : {wres['runtime_ms']} ms")
            wif_lines.append(f"Nodes expanded  : {wres['nodes_expanded']}")
            wif_lines.append(f"Final risk score: {wres['risk_after']:.4f}")
            wif_lines.append("")
            wif_lines.append("Plan steps:")
            if wres["plan"]:
                for i, (action, cost) in enumerate(wres["plan"], 1):
                    icon = ACTIONS.get(action, {}).get("icon", "•")
                    wif_lines.append(f"  {i:>2}. {icon} {action:<22}  cost={cost}")
            else:
                wif_lines.append("  No plan found under these constraints.")

            # TEXT AREA – displays what-if results
            st.text_area(
                label="What-if result",
                value="\n".join(wif_lines),
                height=320,
                disabled=True,
                label_visibility="collapsed",
            )