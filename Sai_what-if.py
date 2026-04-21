import streamlit as st

# This is the main title of our app
st.title("What-If Analysis Dashboard")

# Small line to explain what this page is doing
st.write("Select different options below to test different cases.")

# -----------------------------
# CHECKBOXES (for constraints)
# -----------------------------

# If user wants to apply budget limit
budget = st.checkbox("Apply Budget Limit")

# If user wants to apply time limit
time = st.checkbox("Apply Time Constraint")

# If user wants only low risk actions
risk = st.checkbox("Low Risk Only")

# -----------------------------
# SLIDER (for number of actions)
# -----------------------------

# This slider lets user choose how many actions are allowed
max_actions = st.slider("Maximum Actions Allowed", 1, 10, 5)

# -----------------------------
# SHOWING OUTPUT
# -----------------------------

# Heading for output
st.subheader("Selected Constraints")

# Empty text first
result = ""

# Check which options are selected and add to result
if budget:
    result += "• Budget limit is ON\n"

if time:
    result += "• Time constraint is ON\n"

if risk:
    result += "• Only low risk actions selected\n"

# Always show slider value
result += f"\nMax actions allowed: {max_actions}"

# Print everything on screen
st.text(result)

# -----------------------------
# EXTRA PART (for connecting with A*)
# -----------------------------

# Setting some values which can be used later in algorithm

if budget:
    max_cost = 50   # if budget ON, limit cost
else:
    max_cost = 100  # otherwise normal cost

if risk:
    risk_level = "LOW"
else:
    risk_level = "ANY"

# Just showing values for now (for testing)
st.subheader("Values to use in algorithm")
st.write("Max Cost:", max_cost)
st.write("Risk Level:", risk_level)
st.write("Max Actions:", max_actions)