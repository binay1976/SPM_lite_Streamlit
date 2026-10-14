import streamlit as st
import pandas as pd
import os,socket
from datetime import datetime
import pytz
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph
import socket
from dotenv import load_dotenv
import mysql.connector
from db_connection import managed_connection
from pages.ai_engine import generate_ai_report


st.set_page_config(page_title="AI-Gen Report", page_icon=":bar_chart:", layout="wide")
# --- Custom CSS for Buttons and Links ---
st.markdown("""
    <style>
    /* Hide Sidebar Navigation, Menu, Deploy Button, Footer */
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarNavSeparator"],
    [data-testid="stToolbar"],  /* Settings Menu (three dots) */
    [data-testid="stDeployButton"],  /* Deploy button */
    footer { 
        display: none !important; 
        visibility: hidden !important;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ DB Credentials ------------------ #
# Load .env but do NOT override environment variables (so docker --env wins)
load_dotenv(override=False)

# Pick up DB settings
db_host = os.getenv("DB_HOST", "localhost")
db_port = int(os.getenv("DB_PORT", 3306))
db_user = os.getenv("DB_USER", "spmuser")
db_password = os.getenv("DB_PASSWORD", "")
db_name = os.getenv("DB_NAME", "")

# Fallback: if host is not resolvable, use localhost
try:
    socket.gethostbyname(db_host)
except socket.error:
    db_host = "localhost"

# ------------------ DB CONNECTION ------------------ #
# This function is no longer needed as we will use the managed_connection context manager
def get_connection():
    return mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        port=db_port,
        auth_plugin="mysql_native_password"
    )

# ------------------ Data to Action_log ------------------ #
def log_action(df):
    try:
        with managed_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                INSERT INTO action_logs
                (created_at, event, cli_name, cli_lobby, `date`, cms_id, crew_name, train_no, loco_no, head)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                if df is not None and not df.empty:
                    cli_name = st.session_state.get("user_name", None)
                    cli_lobby = st.session_state.get("user_lobby", None)

                    def safe_value(val):
                        if pd.isna(val): return None
                        if hasattr(val, "item"): return val.item()
                        if isinstance(val, pd.Timestamp): return val.to_pydatetime()
                        return val

                    df_unique = df.drop_duplicates(subset=["CMS_ID"], keep="first").reset_index(drop=True)

                    for _, row in df_unique.iterrows():
                        cursor.execute(
                            query,
                            (
                                "Report Generated", cli_name, cli_lobby,
                                safe_value(row.get("Date")), safe_value(row.get("CMS_ID")),
                                safe_value(row.get("Crew_Name")), safe_value(row.get("Train_No")),
                                safe_value(row.get("Loco_No")), "AI-Gen"
                            ),
                        )
                conn.commit()
    except Exception as e:
        st.error(f"Could not log action: {e}")


def gemini(df=None, selected_cms_id=None):
    # Gemini Pro API Key- AIzaSyAs8qhad-2bBi5_kjUw3Ccwx4NVtyZkZmk (DEE BL)
    # === 1. GROQ_API Setup === 👉 https://console.groq.com/ (tc312bct2.0@gmail.com)
    
    # If df and selected_cms_id are provided, skip file_uploader and use provided df
    if df is None:
        uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip()
            df.dropna(how='all', inplace=True)  # Drop blank rows
        else:
            return  # No file uploaded, exit function
    else:
        # If df is provided, filter by selected_cms_id if available
        if selected_cms_id is not None:
            df = df[df["CMS_ID"] == selected_cms_id]
        df.dropna(how='all', inplace=True)

    st.success(f"Loaded {len(df)} non-blank rows")
    # st.dataframe(df)
    df_unique = df.drop_duplicates(subset=["CMS_ID"], keep="first").reset_index(drop=True)

    # === Extract Core Metrics ===
    if "Date" in df.columns and "Time" in df.columns:
        df["DateTime"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str), errors="coerce")
        start_time = df["DateTime"].min()
        end_time = df["DateTime"].max()
        on_date = start_time.strftime('%d-%b-%Y')
        total_times = end_time - start_time
    else:
        st.error("Missing 'Date' or 'Time' columns.")
        st.stop()

    if "BFT_BPT" not in df.columns:
        st.warning("⚠️ 'BFT_BPT' column missing. BFT/BPT data will be N/A. Please upload a Fabricated Excel File.")

    # Helper: Get first available value or fallback
    def get_first_or(df, col, default="N/A"):
        return df[col].dropna().unique()[0] if col in df and not df[col].dropna().empty else default

    # Helper: Extract matching test data (BFT/BPT)
    def extract_value(df, keyword, col):
        match = df[df["BFT_BPT"].astype(str).str.contains(keyword, na=False)] if "BFT_BPT" in df else pd.DataFrame()
        return match[col].iloc[0] if not match.empty and col in match else "N/A"
        
    # Extract all required fields
    train_no = get_first_or(df, "Train_No")
    # distance = df["Distance"]
    loco_no = get_first_or(df, "Loco_No")
    cms_id = get_first_or(df, "CMS_ID")
    lp_name = get_first_or(df, "Crew_Name")
    designation = get_first_or(df, "Desig")
    cli_name = get_first_or(df, "Nom_CLI")
    run_no = get_first_or(df, "Run_No", "N/A")
    max_run_no = df["Run_No"].nunique() if "Run_No" in df.columns else "N/A"
    speed = df["Speed"]if "Speed" in df.columns else 0
    avg_speed = df["Speed"].mean() if "Speed" in df.columns else 0
    max_speed_by_lp = df.groupby("CMS_ID")["Speed"].max().get(cms_id, df["Speed"].max()) if "Speed" in df.columns and "CMS_ID" in df.columns else 0
    max_distance = df["Cum_Dist_LP"].max()/1000 if "Cum_Dist_LP" in df.columns else 0
    speeds_1000 = df[df["Pin_Point"].astype(str).str.contains("1000", na=False)]["Speed"].dropna().astype(int).tolist() if "Pin_Point" in df else []
    speeds_10 = df[df["Pin_Point"].astype(str).str.contains("10 Meters", na=False)]["Speed"].dropna().astype(int).tolist() if "Pin_Point" in df else []



    # Combine Date and Time into a single datetime column
    df["DateTime"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str), errors="coerce")
    if 'Speed' in df.columns:
        df["Speed_mps"] = df["Speed"] / 3.6
    else:
        df["Speed_mps"] = 0

    acceleration_df = pd.DataFrame()
    if "Run_No" in df.columns:
        df = df.sort_values(["Run_No", "DateTime"])
        def calculate_time_to_max_speed(group):
            group = group.reset_index(drop=True)
            max_speed = group["Speed_mps"].max()
            idx_max = group["Speed_mps"].idxmax()
            time_max_speed = group.loc[idx_max, "DateTime"]
            zero_speed_rows = group[group["Speed_mps"] == 0]
            
            if not zero_speed_rows.empty:
                time_zero_speed = zero_speed_rows.iloc[0]["DateTime"]
            else:
                time_zero_speed = group["DateTime"].min()
            time_diff_sec = (time_max_speed - time_zero_speed).total_seconds()
            acceleration = max_speed / time_diff_sec if time_diff_sec > 0 else 0

            return pd.Series({
                "Max_Speed_mps": max_speed,
                "Time_to_Max_Speed_s": time_diff_sec,
                "Acceleration_mps2": acceleration
            })
        acceleration_df = df.groupby("Run_No").apply(calculate_time_to_max_speed).reset_index()
    else:
        df = df.sort_values("DateTime")

    # MPS Maintained Speed Calculation....................................................................................
    df["Date_Time"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str), errors="coerce")

    # Get max speed
    max_speed = df["Speed"].max()

    # Define speed tolerance band (±5 km/h)
    lower_limit = max_speed - 3
    upper_limit = max_speed + 3

    # Filter rows where speed is within the ±5 km/h band
    high_speed_df = df[(df["Speed"] >= lower_limit) & (df["Speed"] <= upper_limit)].copy()

    # Sort by time to ensure proper sequence
    high_speed_df = high_speed_df.sort_values(["Date_Time"])

    # Compute total distance and time covered at near-max speed
    total_distance = high_speed_df["Distance"].max() - high_speed_df["Distance"].min() if not high_speed_df.empty else 0

    # Total time
    if not high_speed_df.empty:
        total_time = high_speed_df["Date_Time"].max() - high_speed_df["Date_Time"].min()
    else:
        total_time = pd.Timedelta(0)

    acceleration_text = acceleration_df.to_string(index=False) if not acceleration_df.empty else "N/A"

    # Dictionary for prompt filling
    variables_extracted = {
        "Date": on_date,
        "Start_Time": start_time.strftime("%d-%b-%Y %H:%M:%S"),
        "End_Time": end_time.strftime("%d-%b-%Y %H:%M:%S"),
        "Duration": str(total_times),
        "Train_No": train_no,
        "Loco_No": loco_no,
        "LP_Name": lp_name,
        "Designation": designation,
        "CMS_ID": cms_id,
        "CLI": cli_name,
        "Dead_Stops": max_run_no,
        "Max_Speed": round(max_speed_by_lp, 2),
        "Avg_Speed": round(avg_speed, 2),
        "Distance": round(max_distance, 2),
        "BFT_Start_Time": extract_value(df, "BFT", "Time"),
        "BFT_Start_Distance": extract_value(df, "BFT", "Cum_Dist_Run"),
        "BFT_Start_Speed": extract_value(df, "BFT", "Speed"),
        "BFT_End_Time": extract_value(df, "BFT_END", "Time"),
        "BFT_End_Distance": extract_value(df, "BFT_END", "Cum_Dist_Run"),
        "BFT_End_Speed": extract_value(df, "BFT_END", "Speed"),
        "BPT_Start_Time": extract_value(df, "BPT", "Time"),
        "BPT_Start_Distance": extract_value(df, "BPT", "Cum_Dist_Run"),
        "BPT_Start_Speed": extract_value(df, "BPT", "Speed"),
        "BPT_End_Time": extract_value(df, "BPT_END", "Time"),
        "BPT_End_Distance": extract_value(df, "BPT_END", "Cum_Dist_Run"),
        "BPT_End_Speed": extract_value(df, "BPT_END", "Speed"),
        "Braking_Speeds_1000": speeds_1000,
        "Braking_Speeds_10": speeds_10,
        "Acceleration_Data": acceleration_text,
    }
    
    # === Prompt Builder ===
    def build_structured_prompt(values: dict) -> str:
        speeds_1000_str = ", ".join(str(s) for s in values["Braking_Speeds_1000"])
        speeds_10_str = ", ".join(str(s) for s in values["Braking_Speeds_10"])

        return f"""
    ✅ Journey Summary: On Date **{values["Date"]}**,The journey commenced on **{values["Start_Time"]}** and concluded on **{values["End_Time"]}**, 
    spanning a total duration of **{values["Duration"]}** hours. The train operated under 
    Train Number **{values["Train_No"]}** and was driven by Loco Pilot **{values["LP_Name"]}**, holding the designation of **{values["Designation"]}**, 
    with CMS ID **{values["CMS_ID"]}**. The assigned locomotive was numbered **{values["Loco_No"]}**, 
    and the Nominated CLI for the LP is **{values["CLI"]}**. Throughout the run, 
    the train made **{values["Dead_Stops"]}** dead stops, attained a maximum speed of **{values["Max_Speed"]} km/h**, 
    and maintained an average speed of **{values["Avg_Speed"]} km/h**, over a total distance of **{values["Distance"]} kilometers** . 
    Show only this above details in paragraph format with ** values in bold not in table format. rest of the report in Summurized format.
            
    ✅ Brake Feel Test (BFT): Initiated at **{values["BFT_Start_Time"]}**, Distance: **{values["BFT_Start_Distance"]}**, Speed: **{values["BFT_Start_Speed"]}**. Ended at **{values["BFT_End_Time"]}**, Distance: **{values["BFT_End_Distance"]}**, Speed: **{values["BFT_End_Speed"]}**. Show in Summarized format with bullets and ** values in bold not in table format.

    ✅ Brake Power Test (BPT): Initiated at **{values["BPT_Start_Time"]}**, Distance: **{values["BPT_Start_Distance"]}**, Speed: **{values["BPT_Start_Speed"]}**. Ended at **{values["BPT_End_Time"]}**, Distance: **{values["BPT_End_Distance"]}**, Speed: **{values["BPT_End_Speed"]}**.

    ✅ Braking Pattern before 1000m of dead Stop: Speeds before halt: **{speeds_1000_str} kmph**. Show all Speeds like (24,30,50 & so on) not in table format in different run & find risky speed with logic, Use reduction of Speed up to 60% of max speed in that run logic to assess safety.

    ✅ Final Braking before 10m of dead Stop: Speeds before halt: **{speeds_10_str} kmph**. Safe stoppage is speed ≤ 10 kmph.

    ✅ Accelaration & Deaccelaration:  **{values["Acceleration_Data"]} meter per second square**.Show Acceleration Value for 
    each run with top speed and accelaration value in each run. and decide which run accelaration is aggressive and which is laggy. 
    Use logic of <0.05 m/s² as laggy and above that as aggressive.

    ✅ Maintained top Speed:  use **{max_speed} km/h**, Speed lag upto: {lower_limit} km/h" Total Distance at near-max speed: {total_distance:.2f} km".
    📝 NOTE: This paragraph has been generated using AI-based logic and automated data analysis. Please verify with Excel data before taking any operational decisions.
    
    """

# Button to Generate Summary -----------------------------------------------------------------------------------
    from pages.ai_engine import generate_ai_report
    with st.spinner("Preparing AI-Generated Insights..."):
        final_prompt = build_structured_prompt(variables_extracted)
        ai_text = generate_ai_report(final_prompt)
        st.markdown("## 📝 Summarized Insight")
        st.write(ai_text)
# # --- Add download button for response.text as PDF with Unicode support ---
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
# Define custom styles for header and body
        header_style = styles['Heading1']
        body_style = ParagraphStyle(
            name='BodyText',
            parent=styles['Normal'],
            fontSize=12,
            leading=14,  # Line spacing
            spaceAfter=12,
            fontName='Helvetica'
        )
# Build PDF content----------------------------------------------------------------------------
        content = []
        content.append(Paragraph("Summarized Insight", header_style))
        cleaned_text = ai_text.replace("*", "").replace('\u2264', '<=')
        paragraphs = cleaned_text.split('\n')
        
# Add each paragraph to the content-----------------------------------------------------------------------
        for para in paragraphs:
            content.append(Paragraph(para.strip(), body_style))
        content.append(Paragraph("Report Generated Using SPM Analysis App D&D by Western Railway, Mumbai Division @ BDTS1022", body_style))


# Generate PDF------------------------------------------------------------------------------------------
        doc.build(content)
        pdf_buffer.seek(0)
        st.download_button(
            label="📥 Download AI-Gen Report",
            data=pdf_buffer,
            file_name=f"AI Gen Report for {selected_cms_id} - Loco_{loco_no}.pdf",
            mime="application/pdf"
        )

    # If called from main() for PDF, return dummy PDF buffer and loco_no
    if selected_cms_id is not None:
        pdf_buffer = io.BytesIO(b"Dummy PDF content")
        return pdf_buffer, loco_no

def main():
    st.title("AI Powered Report Builder")

    # Hide default Streamlit sidebar buttons
    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚨 AI Powered SPM Report")
    report_file = st.sidebar.file_uploader("Upload Fabricated Excel Files only", type=["xlsx"], key="ai_report_file")
    # Home button to go to design.py
    if report_file:
        df = pd.read_excel(report_file, engine='openpyxl')
        df.columns = df.columns.str.strip()
        if "CMS_ID" not in df.columns:
            st.sidebar.error("Wrong File Uploaded")
            st.write("Columns found:", df.columns.tolist())
        else:
            selected_cms_id = st.sidebar.selectbox("Select CMS_ID", df["CMS_ID"].dropna().unique())
            st.info("👈 Please Select CMS ID & Click Button 'Generate Report' ")
            if st.sidebar.button("Generate Report"):
                result = gemini(df, selected_cms_id)
                if result is not None:
                    pdf_buffer, loco_no = result
                    # --- Get Train_No for logging ---
                    try:
                        train_no = df[df["CMS_ID"] == selected_cms_id]["Train_No"].iloc[0]
                    except Exception:
                        train_no = ""
                    # --- Log to Google Sheet ---
                    log_action(df[df["CMS_ID"] == selected_cms_id])
                    st.success("✅ Data Generated Successfully !!!!")

    if st.sidebar.button("🏠 Home", key="home_btn"):
        st.switch_page("pages/design.py")
    else:
        st.info("👈 Please upload a processed Excel file from the sidebar to generate a AI-Gen Report.")

if __name__ == "__main__":
    main()
