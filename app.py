import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Vibe-Based Master Tracker", layout="wide")
st.title("🗂️ Multi-File Master Tracker")

uploaded_files = st.file_uploader("📁 Upload daily Excel files", type=["xlsx"], accept_multiple_files=True)

# Logic: 8 hrs or more = Achieved
def detect_productivity_by_hours(hours):
    return "✅ Productivity Achieved" if hours >= 8 else "❌ Productivity Not Achieved"

if uploaded_files:
    combined_df = []

    for uploaded_file in uploaded_files:
        try:
            excel_file = pd.ExcelFile(uploaded_file)

            # Read values from B2 and B5 directly
            employee_info = pd.read_excel(excel_file, sheet_name=0, nrows=6, usecols="B", header=None)
            report_date = str(employee_info.iloc[1, 0]) if not pd.isna(employee_info.iloc[1, 0]) else "Unknown"
            employee_name = str(employee_info.iloc[4, 0]) if not pd.isna(employee_info.iloc[4, 0]) else "Unknown"

            # Read the task log starting from B8 to J (columns B to J, skip first 7 rows)
            df = pd.read_excel(excel_file, sheet_name=0, skiprows=7, usecols="B:J")
            df.columns = [col.strip() for col in df.columns]
            df = df.rename(columns={
                "Today's Time Spent (hrs)": "Time Spent (hrs)",
                "Total Elapsed Hrs": "Elapsed Hrs"
            })

            # Filter out garbage rows
            df = df[df["Task Description"].notna()]
            df = df[~df["Task Description"].astype(str).str.lower().str.strip().isin(["none", "project", "recommendation"])]
            df = df[~df["Task Description"].astype(str).str.match(r"^\d+(\.\d+)?$")]
            df = df[~df["Task Description"].astype(str).str.lower().str.contains("expected completion|estimated time|priority", na=False)]

            # Inject metadata
            df["Employee Name"] = employee_name
            df["Date"] = report_date

            combined_df.append(df)

        except Exception as e:
            st.warning(f"⚠️ Could not process {uploaded_file.name}: {e}")

    if combined_df:
        master_df = pd.concat(combined_df, ignore_index=True)

        # Group summary by Employee
        df_summary = master_df.groupby("Employee Name", as_index=False).agg({
            "Time Spent (hrs)": "sum",
            "Assigned Hrs": "sum",
            "Elapsed Hrs": "sum",
        })

        df_summary["Productivity Status"] = df_summary["Time Spent (hrs)"].apply(detect_productivity_by_hours)

        # Show Summary
        st.subheader("📊 Summary by Employee")
        st.dataframe(df_summary, use_container_width=True)

        st.subheader("📋 Full Task Log")
        st.dataframe(master_df, use_container_width=True)

        # Export to Excel
        def to_excel_bytes(summary, full):
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                summary.to_excel(writer, sheet_name="Summary by Employee", index=False)
                full.to_excel(writer, sheet_name="Master Tracker", index=False)
            return buffer.getvalue()

        excel_data = to_excel_bytes(df_summary, master_df)
        st.download_button("📥 Download Combined Report", data=excel_data, file_name="Compiled_Master_Tracker.xlsx")

else:
    st.info("👆 Upload daily Excel task sheets to generate your master tracker.")
