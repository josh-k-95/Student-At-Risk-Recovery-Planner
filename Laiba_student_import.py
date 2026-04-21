import streamlit as st
import pandas as pd

st.title("Student At-Risk Recovery Planner")

uploaded_file = st.file_uploader("Upload Student CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("Dataset Preview")
    st.dataframe(df)

    selected_student = st.selectbox(
        "Select a Student",
        df["student_id"]
    )