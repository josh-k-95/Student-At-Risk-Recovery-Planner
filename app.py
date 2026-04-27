import matplotlib.pyplot as plt
import streamlit as st
import random
import pandas as pd
from collections import Counter

import core
import plots
from baseline import run_greedy, run_ucs
import scheduler

# ── Page configuration ──────────────────────────────────────
st.set_page_config(
    page_title="Student At-Risk Recovery Planner",
    page_icon="📊",
    layout="wide",
)

#── Simple UI styling ───────────────────────────────────────
st.markdown(
    """
    <style>

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        div[data-testid="stMetric"] {
            padding: 18px;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .section-card {
            padding: 18px;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 16px;
        }
    </style>
    """
    ,
    unsafe_allow_html=True,
)


# ── Session state initialisation ────────────────────────────
if "student_df" not in st.session_state:
    st.session_state.student_df = None

if "current_state" not in st.session_state:
    st.session_state.current_state = None

if "result" not in st.session_state:
    st.session_state.result = None

if "whatif_results" not in st.session_state:
    st.session_state.whatif_results = None


# ── Helper function: summary text ───────────────────────────
def build_action_summary(plan):
    """Creates a short friendly summary of what the student should focus on."""
    if not plan:
        return "No plan was found. Try increasing available hours or relaxing the risk thresholds."

    actions = [action_name for action_name, _, _ in plan]
    counts = Counter(actions)

    action_descriptions = {
        "Study": "study more to improve quiz performance",
        "Attend Class": "attend more classes to improve attendance",
        "Submit Assignment": "submit missing assignments",
        "Practice Exam": "practice exams to improve quiz score",
        "Meet Tutor": "meet the tutor for extra support",
        "Rest": "rest to manage fatigue",
    }

    summary_parts = []
    for action_name, count in counts.items():
        description = action_descriptions.get(action_name, action_name)
        summary_parts.append(f"{description} ({count} time{'s' if count > 1 else ''})")

    return "This student should focus on: " + "; ".join(summary_parts) + "."

def render_timetable_ui(timetable, deadline_days):
    """Renders the scheduled timetable beautifully in Streamlit as a scrollable text box."""
    if timetable is None:
        st.error(
            f"⚠️ **DEADLINE MISSED!** A theoretical plan exists, but it is physically "
            f"impossible to complete it within the {deadline_days}-day deadline due to "
            f"fatigue limits, required rests, and daily action caps."
        )
        return

    total_days = len(timetable)
    st.success(f"✅ **SCHEDULE VALID:** Realistic plan fits within {total_days} days (Deadline: {deadline_days} days).")
    
    # Build a single clean text block for the entire schedule
    schedule_lines = []
    for day in timetable:
        if not day: continue
        day_num = day[0]["day"]
        
        schedule_lines.append(f"═══ DAY {day_num} ═══")
        for entry in day:
            start  = entry["start_hour"]
            end    = entry["end_hour"]
            action = entry["action"]
            dur    = entry["duration"]
            fb     = entry["fatigue_before"]
            fa     = entry["fatigue_after"]
            
            # Format: Hour  0.0 ➔  1.5 : Study              (1.5h)  | Fatigue:  0 ➔  3
            schedule_lines.append(
                f"Hour {start:>4.1f} ➔ {end:<4.1f} : {action:<20} "
                f"({dur:>3.1f}h)  | Fatigue: {fb:>2} ➔ {fa:<2}"
            )
        schedule_lines.append("") # Blank line between days

    full_text = "\n".join(schedule_lines)
    
    # Render as a scrollable text area
    st.text_area(
        label="Detailed Itinerary", 
        value=full_text, 
        height=320, 
        disabled=True, 
        label_visibility="collapsed"
    )


# ── App header ───────────────────────────────────────────────
st.title("📊 Student Success Recovery Dashboard")
st.caption("Helping identify at-risk students and build smarter recovery plans.")
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
            help=(
                "Must contain: student_id, attendance_rate, missing_submissions, "
                "avg_quiz_score, lms_activity, study_hours_per_week, days_to_deadline"
            ),
        )

        if uploaded_file is not None:
            st.session_state.student_df = pd.read_csv(uploaded_file)
            st.success(f"Loaded {len(st.session_state.student_df)} students.")

        if st.session_state.student_df is not None:
            student_ids = st.session_state.student_df["student_id"].tolist()
            chosen_id = st.selectbox("Select a student:", student_ids)

            if st.button("✅ Load Selected Student"):
                row = st.session_state.student_df[
                    st.session_state.student_df["student_id"] == chosen_id
                ].iloc[0]

                st.session_state.current_state = core.csv_row_to_state(row)
                st.session_state.result = None
                st.session_state.whatif_results = None

                st.success(f"Student {chosen_id} loaded.")

    # ── Random scenario ──────────────────────────────────────
    elif input_mode == "Generate Random Scenario":
        if st.button("🎲 Generate Random Scenario"):
            st.session_state.current_state = core.State(
                attendance=round(random.uniform(40, 85), 1),
                missing=random.randint(1, 5),
                score=round(random.uniform(30, 70), 1),
                activity=round(random.uniform(20, 80), 1),
                study_hours=random.randint(1, 15),
                days=random.randint(2, 14),
                fatigue=0,
            )

            st.session_state.result = None
            st.session_state.whatif_results = None

            st.success("Random scenario generated.")

    # ── Manual entry ─────────────────────────────────────────
    else:
        with st.form("manual_entry_form"):
            st.write("Enter student values manually:")

            att = st.slider("Attendance Rate (%)", 0, 100, 70)
            miss = st.number_input("Missing Submissions", 0, 10, 2, step=1)
            quiz = st.slider("Avg Quiz Score", 0, 100, 55)
            lms = st.slider("LMS Activity", 0, 100, 50)
            hours = st.slider("Study Hours / Week", 0, 168, 14)
            days = st.number_input("Days to Deadline", 1, 30, 7, step=1)

            submitted = st.form_submit_button("✅ Apply Values")

        if submitted:
            st.session_state.current_state = core.State(
                attendance=att,
                missing=int(miss),
                score=quiz,
                activity=lms,
                study_hours=hours,
                days=int(days),
                fatigue=0,
            )

            st.session_state.result = None
            st.session_state.whatif_results = None

            st.success("Manual values applied.")

    st.divider()

    # ── Section 2: Planner Settings ──────────────────────────
    st.subheader("🔧 Planner Settings")

    available_hours = st.slider(
        "Available Hours / Day",
        min_value=2,
        max_value=16,
        value=8,
        step=1,
        help="Total hours the student can dedicate per day.",
    )

    tutor_available = st.checkbox(
        "Tutor Available",
        value=True,
    )

    st.markdown("**📊 Risk Thresholds**")

    attendance_threshold = st.slider(
        "Attendance Threshold (%)",
        min_value=50,
        max_value=100,
        value=75,
        step=5,
        help="Below this attendance rate = at-risk.",
    )

    quiz_threshold = st.slider(
        "Quiz Score Threshold",
        min_value=40,
        max_value=100,
        value=60,
        step=5,
        help="Below this quiz score = at-risk.",
    )

    submission_threshold = st.slider(
        "Acceptable Missing Submissions",
        min_value=0,
        max_value=5,
        value=0,
        step=1,
        help="Student is safe if missing submissions ≤ this value.",
    )

    st.divider()

    sidebr_risk_threshold = {
        "ATTENDANCE_THRESHOLD": attendance_threshold,
        "QUIZ_THRESHOLD": quiz_threshold,
        "SUBMISSION_THRESHOLD": submission_threshold,
    }

    run_button = st.button(
        "▶️ Run A* Planner",
        type="primary",
        use_container_width=True,
        disabled=(st.session_state.current_state is None),
    )


# ── Execute A* when Run button pressed ───────────────────────
if run_button and st.session_state.current_state is not None:
    with st.spinner("Running A* search algorithm…"):
        plan, total_cost, final_state, runtime_ms, nodes_expanded = core.run_astar(
            initial_state=st.session_state.current_state,
            available_hours_per_day=available_hours,
            risk_threshold=sidebr_risk_threshold,
            tutor_available=tutor_available,
        )

    if plan is None:
        st.session_state.result = None
        st.error(
            "❌ No recovery plan found within the deadline. "
            "Try increasing available hours or extending the deadline."
        )
    else:
        st.session_state.result = {
            "plan": plan,
            "total_cost": round(total_cost, 2),
            "final_state": final_state,
            "runtime_ms": runtime_ms,
            "nodes_expanded": nodes_expanded,
            "risk_before": core.risk_score(
                st.session_state.current_state,
                sidebr_risk_threshold,
            ),
            "risk_after": core.risk_score(
                final_state,
                sidebr_risk_threshold,
            ),
            "threshold": (
                sidebr_risk_threshold["ATTENDANCE_THRESHOLD"],
                sidebr_risk_threshold["QUIZ_THRESHOLD"],
                sidebr_risk_threshold["SUBMISSION_THRESHOLD"],
            ),
        }


# ════════════════════════════════════════════════════════════
#  MAIN AREA: FOUR TABS
# ════════════════════════════════════════════════════════════
tab_dashboard, tab_dataset, tab_comparison, tab_whatif = st.tabs(
    [
        "📊 Dashboard",
        "📂 Dataset",
        "⚖️ Algorithm Comparison",
        "🔁 What-If Simulation",
    ]
)


# ────────────────────────────────────────────────────────────
#  TAB 1 – DASHBOARD
# ────────────────────────────────────────────────────────────
with tab_dashboard:

    if st.session_state.current_state is None:
        st.info("👈 Load a student using the sidebar, then press **Run A* Planner**.")

    else:
        init = st.session_state.current_state
        res = st.session_state.result
        init_risk = core.risk_score(init, sidebr_risk_threshold)

        # TOP METRICS
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Initial Risk Score", f"{init_risk:.1%}")
        col2.metric("Final Risk Score", f"{res['risk_after']:.1%}" if res else "—")
        col3.metric("Plan Steps", len(res["plan"]) if res else "—")
        col4.metric("Total Cost", res["total_cost"] if res else "—")

        st.divider()

        # INITIAL AND FINAL STATE SIDE BY SIDE
        state_col1, state_col2 = st.columns(2)

        with state_col1:
            st.subheader("📋 Initial State")

            initial_text = (
                f"attendance_rate      : {init.attendance:.1f}\n"
                f"missing_submissions  : {init.missing}\n"
                f"avg_quiz_score       : {init.score:.1f}\n"
                f"lms_activity         : {init.activity:.1f}\n"
                f"study_hours_per_week : {init.study_hours}\n"
                f"days_to_deadline     : {init.days}\n"
                f"fatigue_level        : {init.fatigue}\n"
                f"─────────────────────────────\n"
                f"risk_score           : {init_risk:.4f}\n"
                f"status               : {'⚠️ AT RISK' if init_risk > 0 else '✅ NOT AT RISK'}"
            )

            st.text_area(
                "Initial student state",
                value=initial_text,
                height=260,
                disabled=True,
                label_visibility="collapsed",
            )

        with state_col2:
            st.subheader("🏁 Final State")

            if res:
                fs = res["final_state"]
                risk_after = res["risk_after"]

                final_text = (
                    f"attendance_rate      : {fs.attendance:.1f}\n"
                    f"missing_submissions  : {fs.missing}\n"
                    f"avg_quiz_score       : {fs.score:.1f}\n"
                    f"lms_activity         : {fs.activity:.1f}\n"
                    f"study_hours_per_week : {fs.study_hours:.1f}\n"
                    f"days_to_deadline     : {fs.days}\n"
                    f"fatigue_level        : {fs.fatigue}\n"
                    f"─────────────────────────────\n"
                    f"risk_score           : {risk_after:.4f}\n"
                    f"status               : {'✅ NOT AT RISK' if risk_after <= 0 else '⚠️ STILL AT RISK'}"
                )
            else:
                final_text = "Run the planner to see the final state."

            st.text_area(
                "Final student state",
                value=final_text,
                height=260,
                disabled=True,
                label_visibility="collapsed",
            )

        st.divider()

        # RECOVERY PLAN UNDER STATES
        st.subheader("📝 Recovery Plan")

        if res:
            if res["plan"]:
                plan_lines = []

                for i, (action_name, _, _) in enumerate(res["plan"], 1):
                    plan_lines.append(f"{i}. {action_name}")

                plan_lines.append("─" * 40)
                plan_lines.append(f"Total cost     : {res['total_cost']}")
                plan_lines.append(f"Runtime        : {res['runtime_ms']} ms")
                plan_lines.append(f"Nodes expanded : {res['nodes_expanded']}")

                plan_text = "\n".join(plan_lines)
            else:
                plan_text = "No plan found. Try relaxing the constraints."

            st.text_area(
                "A* recovery plan",
                value=plan_text,
                height=260,
                disabled=True,
                label_visibility="collapsed",
            )
        else:
            st.info("Run the planner to see the recovery plan.")

        st.divider()
        st.subheader("📅 Realistic Daily Timetable")

        if res and res["plan"]:
            # Extract just the action names from the A* plan
            action_list = [action_name for action_name, _, _ in res["plan"]]
            
            # Run the Smart Arranger Scheduler
            timetable = scheduler.build_timetable(
                action_list=action_list,
                available_hours_per_day=available_hours,
                deadline_days=init.days
            )
            
            # Draw the UI
            render_timetable_ui(timetable, init.days)
        else:
            st.info("Run the planner to generate a timetable.")

        
        st.divider()

        # GRAPHS SIDE BY SIDE UNDER RECOVERY PLAN
        st.subheader("📊 Graphs")

        if res:
            with st.expander("📉 Click to show/hide graphs", expanded=False):

                graph_col1, graph_col2 = st.columns(2)

                with graph_col1:
                    st.markdown("**Risk Before vs After**")

                    fig_risk = plots.plot_risk_before_after(
                        res["risk_before"],
                        res["risk_after"],
                        res["threshold"],
                    )

                    # Make graph smaller
                    fig_risk.set_size_inches(4.5, 3.2)

                    st.pyplot(fig_risk)

            with graph_col2:
                st.markdown("**Action Counts**")

                fig_actions = plots.plot_action_counts(
                    [action_name for action_name, _, _ in res["plan"]]
                )

                # Make graph smaller
                fig_actions.set_size_inches(4.5, 3.2)

                st.pyplot(fig_actions)

        else:
            st.info("Graphs will appear here after you run the planner.")

        st.divider()

        # SUMMARY AT THE BOTTOM
        st.subheader("📌 Summary")

        if res and res["plan"]:
            action_names = [action_name for action_name, _, _ in res["plan"]]

            st.info(
                "This student should focus on: "
                + ", ".join(sorted(set(action_names)))
                + " to reduce their risk score."
            )
        elif res:
            st.warning("No recovery plan was found. Try changing the planner settings.")
        else:
            st.info("Run the planner to generate a summary.")


# ────────────────────────────────────────────────────────────
#  TAB 2 – DATASET VIEW
# ────────────────────────────────────────────────────────────
with tab_dataset:
    st.subheader("📂 Student Dataset")

    if st.session_state.student_df is None:
        st.info("Upload a CSV file in the sidebar to view the dataset here.")

    else:
        df = st.session_state.student_df.copy()

        df["risk_score"] = df.apply(
            lambda r: round(core.risk_score(core.csv_row_to_state(r)), 3),
            axis=1,
        )

        df["status"] = df["risk_score"].apply(
            lambda x: "⚠️ At-Risk" if x > 0 else "✅ Safe"
        )

        at_risk_count = (df["risk_score"] > 0).sum()

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Students", len(df))
        col_b.metric("At-Risk Students", at_risk_count)
        col_c.metric("Safe Students", len(df) - at_risk_count)

        st.dataframe(df, use_container_width=True, height=380)

        csv_download = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Download with Risk Scores",
            data=csv_download,
            file_name="students_with_risk.csv",
            mime="text/csv",
        )


# ────────────────────────────────────────────────────────────
#  TAB 3 – ALGORITHM COMPARISON
# ────────────────────────────────────────────────────────────
with tab_comparison:
    st.subheader("⚖️ Algorithm Comparison")

    if st.session_state.current_state is None or st.session_state.result is None:
        st.info("Run the planner first to see the comparison table.")

    else:
        init = st.session_state.current_state

        with st.spinner("Running comparison algorithms…"):
            plan_a, cost_a, _, rt_a, exp_a = core.run_astar(
                initial_state=init,
                available_hours_per_day=available_hours,
                risk_threshold=sidebr_risk_threshold,
                tutor_available=tutor_available,
            )

            plan_g, cost_g, _, rt_g, exp_g = run_greedy(
                initial_state=init,
                available_hours_per_day=available_hours,
                risk_threshold=sidebr_risk_threshold,
                tutor_available=tutor_available,
            )

            plan_u, cost_u, _, rt_u, exp_u = run_ucs(
                initial_state=init,
                available_hours_per_day=available_hours,
                risk_threshold=sidebr_risk_threshold,
                tutor_available=tutor_available,
            )

        comparison_df = pd.DataFrame(
            {
                "Algorithm": ["A* (Optimal)", "Greedy", "UCS"],
                "Total Cost": [cost_a, cost_g, cost_u],
                "Runtime (ms)": [rt_a, rt_g, rt_u],
                "Nodes Expanded": [exp_a, exp_g, exp_u],
                "Plan Length": [
                    len(plan_a) if plan_a else 0,
                    len(plan_g) if plan_g else 0,
                    len(plan_u) if plan_u else 0,
                ],
            }
        )

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
                value= 8,
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
                max_value=100,
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
                help="Student is safe if missing submissions ≤ this value.",
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
                min_value=10,
                max_value=100,
                value=60,
                step=10,
                key="wif_recovery",
                help="Percentage of fatigue removed per rest.",
            )

        st.divider()

        if st.button("▶️ Run What-If Analysis", use_container_width=True):
            wif_time_costs = {
                "Study": wif_tc_study,
                "Attend Class": wif_tc_attend,
                "Submit Assignment": wif_tc_submit,
                "Practice Exam": wif_tc_exam,
                "Meet Tutor": wif_tc_tutor,
                "Rest": wif_tc_rest,
            }

            wif_fatigue_costs = {
                "Study": wif_fc_study,
                "Attend Class": wif_fc_attend,
                "Submit Assignment": wif_fc_submit,
                "Practice Exam": wif_fc_exam,
                "Meet Tutor": wif_fc_tutor,
            }

            wif_risk_threshold = {
                "ATTENDANCE_THRESHOLD": wif_att_threshold,
                "QUIZ_THRESHOLD": wif_quiz_threshold,
                "SUBMISSION_THRESHOLD": wif_sub_threshold,
            }

            wif_state = st.session_state.current_state.copy()
            wif_state["days"] = wif_days

            with st.spinner("Running what-if analysis…"):
                wif_plan, wif_cost, wif_final, wif_rt, wif_exp = core.run_astar(
                    initial_state=wif_state,
                    available_hours_per_day=wif_hours,
                    time_costs=wif_time_costs,
                    fatigue_costs=wif_fatigue_costs,
                    risk_threshold=wif_risk_threshold,
                    tutor_available=wif_tutor,
                )

            st.session_state.whatif_results = {
                "plan": wif_plan,
                "cost": round(wif_cost, 2) if wif_cost else None,
                "final_state": wif_final,
                "runtime_ms": wif_rt,
                "nodes_expanded": wif_exp,
                "risk_after": (
                    core.risk_score(wif_final, wif_risk_threshold)
                    if wif_final
                    else None
                ),
                "time_costs": wif_time_costs,
                "fatigue_costs": wif_fatigue_costs,
            }

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
                    plan_lines.append(f"Total cost     : {wres['cost']}h")
                    plan_lines.append(f"Runtime        : {wres['runtime_ms']}ms")
                    plan_lines.append(f"Nodes expanded : {wres['nodes_expanded']}")
                    plan_lines.append(f"Final risk     : {wres['risk_after']:.4f}")

                    plan_text = "\n".join(plan_lines)

                st.text_area(
                    label="What-if plan",
                    value=plan_text,
                    height=320,
                    disabled=True,
                    label_visibility="collapsed",
                )

                if wres["plan"]:
                    st.info("📌 " + build_action_summary(wres["plan"]))

            with res_col2:
                st.markdown("**📊 Risk Comparison**")

                orig_risk = (
                    st.session_state.result["risk_before"]
                    if st.session_state.result
                    else None
                )

                wif_risk = wres["risk_after"]

                if orig_risk is not None and wif_risk is not None:
                    comp_df = pd.DataFrame(
                        {
                            "": ["Original", "What-If"],
                            "Risk Before": [orig_risk, orig_risk],
                            "Risk After": [
                                st.session_state.result["risk_after"],
                                wif_risk,
                            ],
                            "Total Cost": [
                                st.session_state.result["total_cost"],
                                wres["cost"],
                            ],
                            "Steps": [
                                len(st.session_state.result["plan"]),
                                len(wres["plan"]) if wres["plan"] else 0,
                            ],
                        }
                    )

                    st.dataframe(
                        comp_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                else:
                    st.info("Run the main planner first to enable comparison.")

            if wres["plan"]:
                    
                    st.markdown("**📅 Simulated Timetable**")
                    # Extract actions
                    wif_action_list = [action_name for action_name, _, _ in wres["plan"]]
                    
                    # Generate the schedule using ALL the What-If sliders!
                    wif_timetable = scheduler.build_timetable(
                        action_list=wif_action_list,
                        available_hours_per_day=wif_hours,
                        deadline_days=wif_days,
                        time_costs=wres["time_costs"],
                        fatigue_costs=wres["fatigue_costs"],
                        rest_duration=wres["time_costs"].get("Rest", 1.0),
                        recovery_rate=wif_recovery / 100.0  # Convert 20-90 slider to 0.2-0.9
                    )
                    
                    render_timetable_ui(wif_timetable, wif_days)