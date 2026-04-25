import matplotlib.pyplot as plt
import streamlit as st
import random
import pandas as pd
import time

import core
import plots
from baseline import run_greedy, run_ucs

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
#  SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Control Panel")

    # ── Section 1: Data Input ────────────────────────────────
    st.subheader("📂 Data Input")

    input_mode = st.radio(
        "Choose input method:",
        ["Upload CSV File", "Generate Random Scenario", "Enter Manually"],
    )

    # ── CSV upload ───────────────────────────────────────────
    if input_mode == "Upload CSV File":
        uploaded_file = st.file_uploader(
            "Upload student CSV file",
            type=["csv"],
            help="Must contain: attendance_rate, missing_submissions, "
                 "avg_quiz_score, lms_activity, study_hours_per_week, "
                 "days_to_deadline",
        )

        if uploaded_file is not None:
            st.session_state.student_df = pd.read_csv(uploaded_file)
            st.success(f"Loaded {len(st.session_state.student_df)} students.")

        if st.session_state.student_df is not None:
            student_ids = st.session_state.student_df["student_id"].tolist()
            chosen_id   = st.selectbox("Select a student:", student_ids)

            if st.button("✅ Load Selected Student"):
                row = st.session_state.student_df[
                    st.session_state.student_df["student_id"] == chosen_id
                ].iloc[0]
                st.session_state.current_state = core.csv_row_to_state(row)
                st.session_state.result        = None
                st.success(f"Student {chosen_id} loaded.")

    # ── Random scenario ──────────────────────────────────────
    elif input_mode == "Generate Random Scenario":
        if st.button("🎲 Generate Random Scenario"):
            st.session_state.current_state = core.State(
                attendance  = round(random.uniform(40, 85), 1),
                missing     = random.randint(1, 5),
                score       = round(random.uniform(30, 70), 1),
                activity    = round(random.uniform(20, 80), 1),
                study_hours = random.randint(1, 15),
                days        = random.randint(2, 14),
                fatigue     = 0,
            )
            st.session_state.result = None
            st.success("Random scenario generated.")

    # ── Manual entry ─────────────────────────────────────────
    else:
        with st.form("manual_entry_form"):
            st.write("Enter student values manually:")
            att   = st.slider("Attendance Rate (%)",  0,   100, 70)
            miss  = st.number_input("Missing Submissions", 0, 10, 2, step=1)
            quiz  = st.slider("Avg Quiz Score",        0,   100, 55)
            lms   = st.slider("LMS Activity",          0,   100, 50)
            hours = st.slider("Study Hours / Week",    0,   168, 14)
            days  = st.number_input("Days to Deadline", 1,   30,  7, step=1)
            submitted = st.form_submit_button("✅ Apply Values")

        if submitted:
            st.session_state.current_state = core.State(
                attendance  = att,
                missing     = int(miss),
                score       = quiz,
                activity    = lms,
                study_hours = hours,
                days        = int(days),
                fatigue     = 0,      # always starts fresh
            )
            st.session_state.result = None
            st.success("Manual values applied.")

    st.divider()

    # ── Section 2: Planner Settings ──────────────────────────
    st.subheader("🔧 Planner Settings")

    available_hours = st.slider(
        "Available Hours / Day",
        min_value = 2,
        max_value = 16,
        value     = 8,
        step      = 1,
        help      = "Total hours the student can dedicate per day",
    )

    tutor_available = st.checkbox(
        "Tutor Available",
        value = True,
    )

    st.markdown("**📊 Risk Thresholds**")

    attendance_threshold = st.slider(
        "Attendance Threshold (%)",
        min_value = 50,
        max_value = 95,
        value     = 75,
        step      = 5,
        help      = "Below this attendance rate = at-risk",
    )

    quiz_threshold = st.slider(
        "Quiz Score Threshold",
        min_value = 40,
        max_value = 80,
        value     = 60,
        step      = 5,
        help      = "Below this quiz score = at-risk",
    )

    submission_threshold = st.slider(
        "Acceptable Missing Submissions",
        min_value = 0,
        max_value = 5,
        value     = 0,
        step      = 1,
        help      = "Student is safe if missing submissions ≤ this value",
    )

    st.divider()

    sidebr_risk_threshold = {
        "ATTENDENCE_THRESHOLD":     attendance_threshold,
        "QUIZ_THRESHOLD":           quiz_threshold,
        "SUBMISSION_THRESHOLD":     submission_threshold,
    }

    # ── RUN BUTTON ───────────────────────────────────────────
    run_button = st.button(
        "▶️  Run A* Planner",
        type             = "primary",
        use_container_width = True,
        disabled         = (st.session_state.current_state is None),
    )

# ── Execute A* when Run button pressed ───────────────────────
if run_button and st.session_state.current_state is not None:
    with st.spinner("Running A* search algorithm…"):
        plan, total_cost, final_state, runtime_ms, nodes_expanded = core.run_astar(
            initial_state            = st.session_state.current_state,
            available_hours_per_day  = available_hours,
            risk_threshold           = sidebr_risk_threshold,
            tutor_available          = tutor_available,
        )

    if plan is None:
        st.session_state.result = None
        st.error("❌ No recovery plan found within the deadline. "
                 "Try increasing available hours or extending the deadline.")
    else:
        st.session_state.result = {
            "plan":            plan,
            "total_cost":      round(total_cost, 2),
            "final_state":     final_state,
            "runtime_ms":      runtime_ms,
            "nodes_expanded":  nodes_expanded,
            "risk_before":     core.risk_score(
                                   st.session_state.current_state,
                                   sidebr_risk_threshold
                               ),
            "risk_after":      core.risk_score(
                                   final_state,
                                   sidebr_risk_threshold
                               ),
            "threshold":       (sidebr_risk_threshold["ATTENDENCE_THRESHOLD"],
                                sidebr_risk_threshold["QUIZ_THRESHOLD"],
                                sidebr_risk_threshold["SUBMISSION_THRESHOLD"]),
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

        print(res)

        # ── Top metric cards ─────────────────────────────────
        # Four summary numbers shown at the top of the dashboard
        col1, col2, col3, col4 = st.columns(4)
        init_risk = core.risk_score(init)

        with col1:
            st.metric("Initial Risk Score",
                      f"{(init_risk):.1%}",
                      help="Risk before any recovery actions")
        with col2:
            if res:
                delta = res["risk_after"] - init_risk
                st.metric("Final Risk Score",
                          f"{(res['risk_after']/3):.1%}",
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
                f"study_hour_per_week: {init.study_hours} \n"
                f"days_to_deadline   : {init.days}\n"
                f"fatigue_level      : {init.fatigue}\n"  
                f"─────────────────────────────\n"
                f"risk_score         : {init_risk:.4f}\n"
                f"status             : {'⚠️ AT RISK' if init_risk > 0 else '✅ NOT AT RISK'}"
            )
            # TEXT AREA – displays initial student state
            st.text_area(
                label="Initial student state",
                value=state_text,
                height=240,
                disabled=True,
                label_visibility="collapsed",
            )

            # Recovery plan text area (shown after A* runs)
            if res:
                st.subheader("📝 Recovery Plan  (A*)")

                # if res["plan"]:
                #     plan_lines = []
                #     for i, (action, cost) in enumerate(res["plan"], 1):
                #         icon = ACTIONS.get(action, {}).get("icon", "•")
                #         plan_lines.append(f"{i:>2}. {icon} {action:<22}  cost={cost}")
                #     plan_lines.append("─" * 42)
                #     plan_lines.append(f"    Total cost  : {res['total_cost']}")
                #     plan_lines.append(f"    Runtime     : {res['runtime_ms']} ms")
                #     plan_lines.append(f"    Nodes expand: {res['nodes_expanded']}")
                #     plan_text = "\n".join(plan_lines)
                # else:
                #     plan_text = "No plan found. Try relaxing the constraints."

                if res["plan"]:
                    plan_lines = []
                    for i,(action_name,_,_) in enumerate(res["plan"], 1):
                        icon = "•"
                        plan_lines.append(f"{i:>2}. {icon} {action_name:<22}")
                    plan_lines.append("─" * 42)
                    plan_lines.append(f"    Total cost  : {res['total_cost']}")
                    # plan_lines.append(f"    Runtime     : {res['runtime_ms']} ms")
                    # plan_lines.append(f"    Nodes expand: {res['nodes_expanded']}")
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
                    f"attendance_rate   : {fs.attendance:.1f}\n"
                    f"missing_submissions: {fs.missing}\n"
                    f"avg_quiz_score     : {fs.score:.1f}\n"
                    f"lms_activity       : {fs.activity:.1f}\n"
                    f"study_hours_per_week       : {fs.study_hours:.1f}\n"
                    f"days_to_deadline   : {fs.days}\n"
                    f"fatigue_level      : {fs.fatigue}\n"
                    f"─────────────────────────────\n"
                    f"risk_score         : {risk_after:.4f}\n"
                    f"status             : {'✅ NOT AT RISK' if risk_after <= 0 else '⚠️ STILL AT RISK'}"
                )
                # TEXT AREA – displays final state after recovery plan
                st.text_area(
                    label="Final student state",
                    value=final_text,
                    height=240,
                    disabled=True,
                    label_visibility="collapsed",
                )

        # ── Right column: plots (Member D) ───────────────────
        with right_col:
            if res:
                st.subheader("📊 Risk: Before vs After")
                # ← Member D's plot_risk_before_after() is called here
                fig_risk = plots.plot_risk_before_after(
                    res["risk_before"], res["risk_after"], res["threshold"]
                )
                st.pyplot(fig_risk, use_container_width=True)
                # plt.close(fig_risk)

                st.subheader("📊 Action Counts")
                # ← Member D's plot_action_counts() is called here
                fig_actions = plots.plot_action_counts([action_plan for i,(action_plan,_,_) in enumerate(res["plan"],1)])
                st.pyplot(fig_actions, use_container_width=True)
                # plt.close(fig_actions)
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
            core.csv_row_to_state(r)), 3), axis=1)
        df["status"] = df["risk_score"].apply(
            lambda x: "⚠️ At-Risk" if x > 0 else "✅ Safe"
        )

        # Summary numbers
        at_risk_count = (df["risk_score"] > 0).sum()
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
            plan_a, cost_a, _, rt_a, exp_a = core.run_astar(
                init,available_hours,None,None,sidebr_risk_threshold,
                tutor_available)


            # Running greey and UCS algorithms for comparison 

            plan_g, cost_g, _, rt_g, exp_g = run_greedy(
            initial_state           = init,
            available_hours_per_day = available_hours,
            tutor_available         = tutor_available,
            )

            plan_u, cost_u, _, rt_u, exp_u = run_ucs(
                initial_state           = init,
                available_hours_per_day = available_hours,
                tutor_available         = tutor_available,
            )

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
# ────────────────────────────────────────────────────────────
with tab_whatif:
    st.subheader("🔁 What-If Simulation")
    st.write("Adjust constraints below and re-run to see how the plan changes.")

    if st.session_state.current_state is None:
        st.info("Load a student first.")
    else:
        # ── Three columns for controls ───────────────────────
        col_scenario, col_actions, col_fatigue = st.columns(3)

        # ── Column 1: Scenario Constraints ───────────────────
        with col_scenario:
            st.markdown("**🎯 Scenario Constraints**")

            wif_tutor = st.checkbox(
                "Tutor Available",
                value=True,
                key="wif_tutor",
            )

            wif_hours = st.slider(
                "Available Hours / Day",
                min_value=2,
                max_value=16,
                value=8,
                step=1,
                key="wif_hours",
            )

            wif_days = st.slider(
                "Days to Deadline",
                min_value=1,
                max_value=30,
                value=int(st.session_state.current_state.days),
                step=1,
                key="wif_days",
            )

            st.markdown("**📊 Risk Thresholds**")

            wif_att_threshold = st.slider(
                "Attendance Threshold (%)",
                min_value=50,
                max_value=95,
                value=75,
                step=5,
                key="wif_att_threshold",
            )

            wif_quiz_threshold = st.slider(
                "Quiz Score Threshold",
                min_value=40,
                max_value=80,
                value=60,
                step=5,
                key="wif_quiz_threshold",
            )

            wif_sub_threshold = st.slider(
                "Acceptable Missing Submissions",
                min_value=0,
                max_value=5,
                value=0,
                step=1,
                key="wif_sub_threshold",
                help="Student is safe if missing submissions ≤ this value",
            )

        # ── Column 2: Action Time Costs ───────────────────────
        with col_actions:
            st.markdown("**⏱️ Action Durations (hours)**")

            wif_tc_study = st.slider(
                "Study",
                min_value=0.5,
                max_value=3.0,
                value=1.0,
                step=0.5,
                key="wif_tc_study",
            )

            wif_tc_attend = st.slider(
                "Attend Class",
                min_value=0.5,
                max_value=3.0,
                value=1.0,
                step=0.5,
                key="wif_tc_attend",
            )

            wif_tc_submit = st.slider(
                "Submit Assignment",
                min_value=0.5,
                max_value=3.0,
                value=1.0,
                step=0.5,
                key="wif_tc_submit",
            )

            wif_tc_exam = st.slider(
                "Practice Exam",
                min_value=0.5,
                max_value=4.0,
                value=2.0,
                step=0.5,
                key="wif_tc_exam",
            )

            wif_tc_tutor = st.slider(
                "Meet Tutor",
                min_value=0.5,
                max_value=4.0,
                value=3.0,
                step=0.5,
                key="wif_tc_tutor",
            )

            wif_tc_rest = st.slider(
                "Rest Duration",
                min_value=0.5,
                max_value=2.0,
                value=1.0,
                step=0.5,
                key="wif_tc_rest",
            )

        # ── Column 3: Fatigue Costs ───────────────────────────
        with col_fatigue:
            st.markdown("**😓 Fatigue Costs**")

            wif_fc_study = st.slider(
                "Study Fatigue",
                min_value=1,
                max_value=8,
                value=3,
                step=1,
                key="wif_fc_study",
            )

            wif_fc_attend = st.slider(
                "Attend Class Fatigue",
                min_value=1,
                max_value=8,
                value=4,
                step=1,
                key="wif_fc_attend",
            )

            wif_fc_submit = st.slider(
                "Submit Assignment Fatigue",
                min_value=1,
                max_value=8,
                value=3,
                step=1,
                key="wif_fc_submit",
            )

            wif_fc_exam = st.slider(
                "Practice Exam Fatigue",
                min_value=1,
                max_value=8,
                value=4,
                step=1,
                key="wif_fc_exam",
            )

            wif_fc_tutor = st.slider(
                "Meet Tutor Fatigue",
                min_value=1,
                max_value=8,
                value=4,
                step=1,
                key="wif_fc_tutor",
            )

            wif_recovery = st.slider(
                "Rest Recovery Rate (%)",
                min_value=20,
                max_value=90,
                value=60,
                step=10,
                key="wif_recovery",
                help="Percentage of fatigue removed per rest",
            )

        st.divider()

        # ── Run What-If Button ────────────────────────────────
        if st.button("▶️  Run What-If Analysis", use_container_width=True):

            # Build time_costs and fatigue_costs dicts
            wif_time_costs = {
                "Study":              wif_tc_study,
                "Attend Class":       wif_tc_attend,
                "Submit Assignment":  wif_tc_submit,
                "Practice Exam":      wif_tc_exam,
                "Meet Tutor":         wif_tc_tutor,
                "Rest":               wif_tc_rest,
            }
            wif_fatigue_costs = {
                "Study":              wif_fc_study,
                "Attend Class":       wif_fc_attend,
                "Submit Assignment":  wif_fc_submit,
                "Practice Exam":      wif_fc_exam,
                "Meet Tutor":         wif_fc_tutor,
            }
            wif_risk_threshold = {
                "ATTENDENCE_THRESHOLD": wif_att_threshold,
                "QUIZ_THRESHOLD": wif_quiz_threshold,
                "SUBMISSION_THRESHOLD": wif_sub_threshold,
            }

            # Build modified state with what-if deadline
            wif_state = st.session_state.current_state.copy()
            wif_state["days"] = wif_days

            with st.spinner("Running what-if analysis…"):
                wif_plan, wif_cost, wif_final, wif_rt, wif_exp = core.run_astar(
                    initial_state            = wif_state,
                    available_hours_per_day  = wif_hours,
                    time_costs               = wif_time_costs,
                    fatigue_costs            = wif_fatigue_costs,
                    risk_threshold           = wif_risk_threshold,
                    tutor_available          = wif_tutor,
                )

            st.session_state.whatif_results = {
                "plan":           wif_plan,
                "cost":           round(wif_cost, 2) if wif_cost else None,
                "final_state":    wif_final,
                "runtime_ms":     wif_rt,
                "nodes_expanded": wif_exp,
                "risk_after":     core.risk_score(
                                      wif_final,
                                      wif_risk_threshold
                                  ) if wif_final else None,
                "time_costs":     wif_time_costs,
                "fatigue_costs":  wif_fatigue_costs,
            }

        # ── Results Display ───────────────────────────────────
        if st.session_state.whatif_results:
            wres = st.session_state.whatif_results

            st.divider()
            res_col1, res_col2 = st.columns(2)

            with res_col1:
                st.markdown("**📋 What-If Plan**")

                if wres["plan"] is None:
                    plan_text = "❌ No plan found under these constraints."
                else:
                    plan_lines = []
                    for i, (action_name, _, _) in enumerate(wres["plan"], 1):
                        plan_lines.append(f"{i:>2}. {action_name}")
                    plan_lines.append("─" * 35)
                    plan_lines.append(f"    Total cost     : {wres['cost']}h")
                    plan_lines.append(f"    Runtime        : {wres['runtime_ms']}ms")
                    plan_lines.append(f"    Nodes expanded : {wres['nodes_expanded']}")
                    plan_lines.append(f"    Final risk     : {wres['risk_after']:.4f}")
                    plan_text = "\n".join(plan_lines)

                st.text_area(
                    label="What-if plan",
                    value=plan_text,
                    height=320,
                    disabled=True,
                    label_visibility="collapsed",
                )

            with res_col2:
                st.markdown("**📊 Risk Comparison**")

                # Compare original run vs what-if run
                orig_risk = st.session_state.result["risk_before"] \
                            if st.session_state.result else None
                wif_risk  = wres["risk_after"]

                if orig_risk is not None and wif_risk is not None:
                    comp_df = pd.DataFrame({
                        "":            ["Original", "What-If"],
                        "Risk Before": [orig_risk,  orig_risk],
                        "Risk After":  [
                            st.session_state.result["risk_after"],
                            wif_risk
                        ],
                        "Total Cost":  [
                            st.session_state.result["total_cost"],
                            wres["cost"],
                        ],
                        "Steps": [
                            len(st.session_state.result["plan"]),
                            len(wres["plan"]) if wres["plan"] else 0,
                        ],
                    })
                    st.dataframe(
                        comp_df,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Run the main planner first to enable comparison.")