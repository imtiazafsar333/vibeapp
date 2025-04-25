import streamlit as st
import pandas as pd
from io import BytesIO
import altair as alt

st.set_page_config(page_title="Vibe-Based Master Tracker", layout="wide")
st.title("📊 Multi-File Master Tracker")

uploaded_files = st.file_uploader("📁 Upload daily Excel files", type=["xlsx"], accept_multiple_files=True)

# -------------------- Helper Functions -------------------- #

def detect_productivity_by_hours(hours):
    return "✅ Productivity Achieved" if hours >= 8 else "❌ Productivity Not Achieved"

def to_excel_bytes(summary, full):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        summary.to_excel(writer, sheet_name="Summary by Employee", index=False)
        full.to_excel(writer, sheet_name="Master Tracker", index=False)
    return buffer.getvalue()

def get_similar_column(columns, target):
    for col in columns:
        if target.lower() in col.lower():
            return col
    return None

def clean_task_dataframe(df):
    df.columns = [col.strip() for col in df.columns]

    # Auto-detect relevant columns
    task_col = get_similar_column(df.columns, "Task Description")
    spent_col = get_similar_column(df.columns, "Time Spent")
    assigned_col = get_similar_column(df.columns, "Assigned Hrs")
    elapsed_col = get_similar_column(df.columns, "Elapsed Hrs")

    if not task_col or not spent_col or not assigned_col or not elapsed_col:
        raise ValueError("Required columns not found in the Excel sheet")

    df = df.rename(columns={
        task_col: "Task Description",
        spent_col: "Time Spent (hrs)",
        assigned_col: "Assigned Hrs",
        elapsed_col: "Elapsed Hrs"
    })

    # Trim to top section only
    break_keywords = ["Pending Tasks", "Planned Tasks for Tomorrow", "Challenges and Recommendations", "Completed Tasks"]
    stop_row = None
    for i, row in df.iterrows():
        row_text = " ".join(str(cell).strip().lower() for cell in row if pd.notna(cell))
        if any(keyword.lower() in row_text for keyword in break_keywords):
            stop_row = i
            break
    if stop_row is not None:
        df = df.iloc[:stop_row]

    # Clean task rows
    df = df[df["Task Description"].notna()]
    df = df[~df["Task Description"].astype(str).str.lower().str.strip().isin(["none", "project", "recommendation"])]
    df = df[~df["Task Description"].astype(str).str.match(r"^\d+(\.\d+)?$")]
    df = df[~df["Task Description"].astype(str).str.lower().str.contains("expected completion|estimated time|priority", na=False)]

    # Remove unlogged tasks unless marked completed
    if "Status" in df.columns:
        df = df[~((df["Time Spent (hrs)"].isna()) & (~df["Status"].astype(str).str.lower().str.contains("complete")))]

    return df

# -------------------- Main App Logic -------------------- #

if uploaded_files:
    combined_df = []

    for uploaded_file in uploaded_files:
        try:
            excel_file = pd.ExcelFile(uploaded_file)

            # Extract metadata
            try:
                employee_info = pd.read_excel(excel_file, sheet_name=0, nrows=6, usecols="B", header=None)
                report_date = str(employee_info.iloc[1, 0]) if not pd.isna(employee_info.iloc[1, 0]) else "Unknown"
                employee_name = str(employee_info.iloc[4, 0]) if not pd.isna(employee_info.iloc[4, 0]) else "Unknown"
            except:
                report_date, employee_name = "Unknown", "Unknown"

            df = pd.read_excel(excel_file, sheet_name=0, skiprows=7, usecols="B:J")
            df = clean_task_dataframe(df)
            df["Employee Name"] = employee_name
            df["Date"] = report_date
            combined_df.append(df)

        except Exception as e:
            st.warning(f"⚠️ Could not process `{uploaded_file.name}`: {e}")

    if combined_df:
        master_df = pd.concat(combined_df, ignore_index=True)

        # Summary table
        df_summary = master_df.groupby("Employee Name", as_index=False).agg({
            "Time Spent (hrs)": "sum",
            "Assigned Hrs": "sum",
            "Elapsed Hrs": "sum"
        })
        df_summary["Productivity Status"] = df_summary["Time Spent (hrs)"].apply(detect_productivity_by_hours)

        # Display
        st.markdown("### 🧾 Summary by Employee")
        st.dataframe(df_summary, use_container_width=True)

        st.markdown("### 📊 Productivity Chart")
        chart = alt.Chart(df_summary).mark_bar().encode(
            x='Employee Name',
            y='Time Spent (hrs)',
            color='Productivity Status',
            tooltip=['Employee Name', 'Time Spent (hrs)', 'Productivity Status']
        ).properties(width='container')
        st.altair_chart(chart, use_container_width=True)

        st.markdown("### 📋 Full Task Log")
        st.dataframe(master_df, use_container_width=True)

        # Export
        excel_data = to_excel_bytes(df_summary, master_df)
        st.download_button("📥 Download Combined Report", data=excel_data, file_name="Compiled_Master_Tracker.xlsx")
else:
    st.info("⬆️ Upload daily Excel task sheets to generate your master tracker.")
