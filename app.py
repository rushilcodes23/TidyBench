import pandas as pd
import streamlit as st

from cleaning import (
    profile_data,
    fill_missing,
    drop_missing_rows,
    drop_duplicate_rows,
    strip_whitespace,
    fix_dtype,
    text_columns,
    build_summary_report,
)

st.set_page_config(page_title="Data Doctor", page_icon="🩺", layout="wide")

st.title("🩺 Data Doctor")
st.caption("Upload a messy CSV, see what's wrong with it, fix it in a few clicks, and leave with a clean file and a report.")

# --- session state ---
if "df" not in st.session_state:
    st.session_state.df = None
if "original_profile" not in st.session_state:
    st.session_state.original_profile = None
if "actions_log" not in st.session_state:
    st.session_state.actions_log = []

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None and st.session_state.df is None:
    st.session_state.df = pd.read_csv(uploaded_file)
    st.session_state.original_profile = profile_data(st.session_state.df)
    st.session_state.actions_log = []

if st.session_state.df is None:
    st.info("Upload a CSV to get started, or point it at `sample_data/messy_sales.csv` to try it out first.")
    st.stop()

if st.button("Start over with a new file"):
    st.session_state.df = None
    st.session_state.original_profile = None
    st.session_state.actions_log = []
    st.rerun()

df = st.session_state.df
profile = profile_data(df)

# --- diagnosis ---
st.header("Diagnosis")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", profile["rows"])
col2.metric("Columns", profile["columns"])
col3.metric("Missing values", profile["missing_total"])
col4.metric("Duplicate rows", profile["duplicate_rows"])

with st.expander("See column details"):
    details = pd.DataFrame({
        "dtype": profile["dtypes"],
        "missing values": profile["missing_by_column"],
    })
    st.dataframe(details, use_container_width=True)

if profile["missing_total"] > 0:
    st.caption("Missing values by column")
    st.bar_chart(pd.Series(profile["missing_by_column"]))

# --- treatment ---
st.header("Treatment")
tab1, tab2, tab3 = st.tabs(["Missing values", "Duplicates & text", "Column types"])

with tab1:
    col = st.selectbox("Column to fix", df.columns, key="missing_col")
    is_numeric = pd.api.types.is_numeric_dtype(df[col])
    strategy_options = ["mean", "median", "mode", "custom", "drop rows"] if is_numeric else ["mode", "custom", "drop rows"]
    strategy = st.radio("Strategy", strategy_options, horizontal=True)
    custom_val = None
    if strategy == "custom":
        custom_val = st.text_input("Fill with")
    if st.button("Apply fix", key="apply_missing"):
        try:
            if strategy == "drop rows":
                st.session_state.df = drop_missing_rows(df, column=col)
                st.session_state.actions_log.append(f"Dropped rows with missing values in '{col}'")
            else:
                st.session_state.df = fill_missing(df, col, strategy=strategy, custom_value=custom_val)
                st.session_state.actions_log.append(f"Filled missing values in '{col}' using {strategy}")
            st.rerun()
        except Exception as e:
            st.error(f"That fix didn't work: {e}")

with tab2:
    left, right = st.columns(2)
    with left:
        st.write("Exact duplicate rows")
        if st.button("Remove duplicate rows"):
            before_count = len(df)
            st.session_state.df = drop_duplicate_rows(df)
            removed = before_count - len(st.session_state.df)
            st.session_state.actions_log.append(f"Removed {removed} duplicate rows")
            st.rerun()
    with right:
        st.write("Stray whitespace in text")
        cols = text_columns(df)
        if cols:
            text_col = st.selectbox("Column", cols, key="strip_col")
            if st.button("Strip whitespace"):
                st.session_state.df = strip_whitespace(df, text_col)
                st.session_state.actions_log.append(f"Stripped whitespace in '{text_col}'")
                st.rerun()
        else:
            st.caption("No text columns found.")

with tab3:
    type_col = st.selectbox("Column", df.columns, key="type_col")
    new_type = st.selectbox("Convert to", ["numeric", "datetime", "text"])
    if st.button("Convert"):
        try:
            st.session_state.df = fix_dtype(df, type_col, new_type)
            st.session_state.actions_log.append(f"Converted '{type_col}' to {new_type}")
            st.rerun()
        except Exception as e:
            st.error(f"That conversion didn't work: {e}")

# --- result ---
st.header("Result")
st.dataframe(st.session_state.df.head(20), use_container_width=True)

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.download_button("Download cleaned CSV", csv_bytes, "cleaned_data.csv", "text/csv")

# --- summary report ---
st.header("Summary report")
after_profile = profile_data(st.session_state.df)
report_md = build_summary_report(st.session_state.original_profile, after_profile, st.session_state.actions_log)
st.markdown(report_md)
st.download_button("Download report (.md)", report_md, "cleaning_report.md", "text/markdown")
