import streamlit as st
import pandas as pd
from io import BytesIO
from xhtml2pdf import pisa
import altair as alt
from datetime import datetime
import tempfile

st.set_page_config(page_title="Vibe-Based Master Tracker", layout="wide")
st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Upload & Process", "Additional Information", "Admin Panel"])

# -------------------- Helper Functions -------------------- #

# --- Page Config ---
st.set_page_config(page_title="Vibe-Based Master Tracker", layout="wide")


# --- Helper Functions ---

def to_excel_bytes(daily, weekly, monthly, summary, full):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        daily.to_excel(writer, sheet_name="Daily Productivity", index=False)
        weekly.to_excel(writer, sheet_name="Weekly Productivity", index=False)
        monthly.to_excel(writer, sheet_name="Monthly Productivity", index=False)
        summary.to_excel(writer, sheet_name="Summary by Employee", index=False)
        full.to_excel(writer, sheet_name="Master Tracker", index=False)
    return buffer.getvalue()


def create_pdf_from_html(html_content):
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    with open(temp_pdf.name, "w+b") as result_file:
        pisa.CreatePDF(src=html_content, dest=result_file)
    return temp_pdf.name


def generate_pdf_content(daily, weekly, monthly, total_team_hours, total_employees, average_hours_per_employee):
    today_date = datetime.now().strftime("%d %B %Y")
    company_logo_url = "https://yourcompany.com/logo.png"  # Replace with your company logo link if you want
    html_content = f"""
    <html>
    <head>
    <style>
    body {{ font-family: Arial, sans-serif; margin: 30px; }}
    h1 {{ color: #333; text-align: center; }}
    h2 {{ color: #555; margin-top: 40px; }}
    p {{ font-size: 14px; }}
    .logo {{ text-align: center; margin-bottom: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ border: 1px solid #dddddd; text-align: center; padding: 8px; }}
    th {{ background-color: #f2f2f2; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    </style>
    </head>
    <body>

    <div class="logo">
        <img src="{company_logo_url}" width="120">
    </div>

    <h1>Vibe Tracker - Team Productivity Report</h1>
    <p style="text-align:center;">Generated on: {today_date}</p>

    <h2>📋 Overall Team Summary</h2>
    <p><strong>Total Team Hours:</strong> {total_team_hours:,.2f} hrs</p>
    <p><strong>Employees:</strong> {total_employees}</p>
    <p><strong>Average Hours per Employee:</strong> {average_hours_per_employee:,.2f} hrs</p>

    <h2>🕒 Daily Productivity</h2>
    {daily.to_html(index=False)}

    <h2>📆 Weekly Productivity</h2>
    {weekly.to_html(index=False)}

    <h2>📅 Monthly Productivity</h2>
    {monthly.to_html(index=False)}

    </body>
    </html>
    """
    return html_content


# --- Session State Init ---
if "master_df" not in st.session_state:
    st.session_state.master_df = pd.DataFrame()
    st.session_state.df_summary = pd.DataFrame()

# --- Sidebar Navigation ---
st.sidebar.title("📂 Navigation")
page = st.sidebar.radio("Go to", ["Upload & Process", "Dashboard"])

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

def extract_section(df, start_keyword):
    start_idx = df[df.apply(lambda row: row.astype(str).str.contains(start_keyword, case=False, na=False).any(), axis=1)].index
    if start_idx.empty:
        return pd.DataFrame()
    start = start_idx[0] + 1

    headings = ["Pending Tasks", "Planned Tasks for Tomorrow", "Challenges and Recommendations"]
    end = len(df)
    for i in range(start, len(df)):
        row_text = " ".join(str(cell).strip().lower() for cell in df.iloc[i] if pd.notna(cell))
        if any(h.lower() in row_text for h in headings) or df.iloc[i].isnull().all():
            end = i
            break

    section = df.iloc[start:end]
    section = section.dropna(how="all")
    section.columns = section.iloc[0] if len(section) > 1 else section.columns
    section = section[1:] if len(section) > 1 else section
    section = section.dropna(how="all", axis=1)
    return section.reset_index(drop=True)

def clean_task_dataframe(df):
    df.columns = [col.strip() for col in df.columns]
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
    break_keywords = ["Pending Tasks", "Planned Tasks for Tomorrow", "Challenges and Recommendations", "Completed Tasks"]
    stop_row = None
    for i, row in df.iterrows():
        row_text = " ".join(str(cell).strip().lower() for cell in row if pd.notna(cell))
        if any(keyword.lower() in row_text for keyword in break_keywords):
            stop_row = i
            break
    if stop_row is not None:
        df = df.iloc[:stop_row]
    df = df[df["Task Description"].notna()]
    df = df[~df["Task Description"].astype(str).str.lower().str.strip().isin(["none", "project", "recommendation"])]
    df = df[~df["Task Description"].astype(str).str.match(r"^\d+(\.\d+)?$")]
    df = df[~df["Task Description"].astype(str).str.lower().str.contains("expected completion|estimated time|priority", na=False)]
    if "Status" in df.columns:
        df = df[~((df["Time Spent (hrs)"].isna()) & (~df["Status"].astype(str).str.lower().str.contains("complete")))]
    return df

# -------------------- Session State for Shared Data -------------------- #
if "master_df" not in st.session_state:
    st.session_state.master_df = pd.DataFrame()
    st.session_state.df_summary = pd.DataFrame()
    st.session_state.pending_tasks = []
    st.session_state.challenges = []
    st.session_state.planned_tasks = []

# -------------------- Upload & Process Page -------------------- #
if page == "Upload & Process":
    st.title("📥 Upload & Process Daily Task Files")
    uploaded_files = st.file_uploader("📁 Upload Excel files", type=["xlsx"], accept_multiple_files=True)
    if uploaded_files:
        combined_df = []
        pending_sections = []
        challenge_sections = []
        plan_sections = []
        for uploaded_file in uploaded_files:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                employee_info = pd.read_excel(excel_file, sheet_name=0, nrows=6, usecols="B", header=None)
                report_date = str(employee_info.iloc[1, 0]) if not pd.isna(employee_info.iloc[1, 0]) else "Unknown"
                employee_name = str(employee_info.iloc[4, 0]) if not pd.isna(employee_info.iloc[4, 0]) else "Unknown"
                raw_df = pd.read_excel(excel_file, sheet_name=0, skiprows=7, usecols="B:J")

                df = clean_task_dataframe(raw_df.copy())
                df["Employee Name"] = employee_name
                df["Date"] = report_date
                combined_df.append(df)

                pending_sections.append(extract_section(raw_df.copy(), "Pending Tasks"))
                challenge_sections.append(extract_section(raw_df.copy(), "Challenges and Recommendations"))
                plan_sections.append(extract_section(raw_df.copy(), "Planned Tasks for Tomorrow"))

            except Exception as e:
                st.warning(f"⚠️ Could not process `{uploaded_file.name}`: {e}")

        if combined_df:
            st.session_state.master_df = pd.concat(combined_df, ignore_index=True)
            st.session_state.df_summary = st.session_state.master_df.groupby("Employee Name", as_index=False).agg({
                "Time Spent (hrs)": "sum",
                "Assigned Hrs": "sum",
                "Elapsed Hrs": "sum"
            })
            st.session_state.df_summary["Productivity Status"] = st.session_state.df_summary["Time Spent (hrs)"].apply(detect_productivity_by_hours)
            st.session_state.pending_tasks = pending_sections
            st.session_state.challenges = challenge_sections
            st.session_state.planned_tasks = plan_sections
            st.success("✅ Files processed successfully. View results in Dashboard.")

# -------------------- Dashboard Page -------------------- #
elif page == "Dashboard":
    st.title("📊 Team Productivity Dashboard")
    if st.session_state.df_summary.empty:
        st.info("No data available. Please upload and process Excel files.")
    else:
        df_summary = st.session_state.df_summary
        master_df = st.session_state.master_df

        emp_filter = st.multiselect("Filter by Employee", options=master_df["Employee Name"].unique())
        prod_filter = st.radio("Filter by Productivity", ["All", "✅ Productivity Achieved", "❌ Productivity Not Achieved"])

        filtered_summary = df_summary.copy()
        if emp_filter:
            filtered_summary = filtered_summary[filtered_summary["Employee Name"].isin(emp_filter)]
        if prod_filter != "All":
            filtered_summary = filtered_summary[filtered_summary["Productivity Status"] == prod_filter]

        df_filtered = master_df[master_df["Employee Name"].isin(filtered_summary["Employee Name"])]

        st.markdown("### 🧾 Summary by Employee")
        st.dataframe(filtered_summary, use_container_width=True)

        chart = alt.Chart(filtered_summary).mark_bar().encode(
            x='Employee Name',
            y='Time Spent (hrs)',
            color='Productivity Status',
            tooltip=['Employee Name', 'Time Spent (hrs)', 'Productivity Status']
        ).properties(width='container')
        st.altair_chart(chart, use_container_width=True)

        st.markdown("### 📋 Full Task Log")
        st.dataframe(df_filtered, use_container_width=True)

        excel_data = to_excel_bytes(filtered_summary, master_df)
        st.download_button("📥 Download Combined Report", data=excel_data, file_name="Compiled_Master_Tracker.xlsx")

# -------------------- Additional Information Page -------------------- #
elif page == "Additional Information":
    st.title("🗂️ Additional Task Sections")
    tabs = st.tabs(["📌 Pending Tasks", "⚠️ Challenges & Recommendations", "📅 Planned Tasks for Tomorrow"])

    with tabs[0]:
        st.subheader("📌 Pending Tasks")
        for i, df in enumerate(st.session_state.pending_tasks):
            if not df.empty:
                st.markdown(f"**Report #{i+1}**")
                st.dataframe(df)

    with tabs[1]:
        st.subheader("⚠️ Challenges and Recommendations")
        for i, df in enumerate(st.session_state.challenges):
            if not df.empty:
                st.markdown(f"**Report #{i+1}**")
                st.dataframe(df)

    with tabs[2]:
        st.subheader("📅 Planned Tasks for Tomorrow")
        for i, df in enumerate(st.session_state.planned_tasks):
            if not df.empty:
                st.markdown(f"**Report #{i+1}**")
                st.dataframe(df)

# -------------------- Admin Panel -------------------- #
elif page == "Admin Panel":
    st.title("🔐 Admin Panel")
    st.markdown("Version 1.0.0 | Last updated: " + datetime.now().strftime("%Y-%m-%d"))
