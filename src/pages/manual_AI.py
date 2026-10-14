import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import mysql.connector
import os
from db_connection import managed_connection

# ------------------ DB Credentials ------------------ #
# load_dotenv()
load_dotenv("/app/.env")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", 3307)

# ------------------ DB CONNECTION ------------------ #
# The get_connection function is no longer needed as we use the context manager.

# ------------------ Data to Action_log ------------------ #
def log_action(df):
    try:
        with managed_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                INSERT INTO action_logs
                (created_at, event, cli_name, cli_lobby, Date, cms_id, crew_name, train_no, loco_no, spm_make)
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
                                "Excel Fabricated",
                                cli_name,
                                cli_lobby,
                                safe_value(row.get("Date")),
                                safe_value(row.get("CMS_ID")),
                                safe_value(row.get("Crew_Name")),
                                safe_value(row.get("Train_No")),
                                safe_value(row.get("Loco_No")),
                                "PDF Report",
                            ),
                        )
                conn.commit()
    except Exception as e:
        st.error(f"Could not log action: {e}")


st.title("Driving Summary")

uploaded_file = st.file_uploader("📁 Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("🔍 Preview of Data", df.head())
    log_action(df)

    paragraph = []

    # ✅ Start & End Time
    if "Date" in df.columns and "Time" in df.columns:
        df["DateTime"] = pd.to_datetime(df["Date"].astype(str) + " " + df["Time"].astype(str), errors="coerce")
        start_time = df["DateTime"].min()
        end_time = df["DateTime"].max()
        on_date = start_time.strftime('%d-%b-%Y')
        drive_duration = f"The drive started from **{start_time.strftime('%d-%b-%Y %H:%M:%S')}** to **{end_time.strftime('%d-%b-%Y %H:%M:%S')}**"
        # Calculate total time
        total_time = end_time - start_time
        total_time_str = f", Total journey time: **{total_time}**"
    else:
        drive_duration = "Could not determine drive timing."
        total_time_str = ""

    # ✅ Total Distance from Cum_Dist_LP
    if "Cum_Dist_LP" in df.columns:
        max_distance = df["Cum_Dist_LP"].max()/1000
        distance_info = f" and covered a total distance of **{max_distance:,.2f} Kilometers**."
        drive_detail = f"🧠 Drive Details:-\n"
    else:
        distance_info = ""

    # paragraph.append(f"{drive_duration}{distance_info}")

    # ✅ Train Info
    try:
        train_no = df["Train_No"].dropna().unique()[0]
        loco_no = df["Loco_No"].dropna().unique()[0]
        cms_id = df["CMS_ID"].dropna().unique()[0]
        lp_name = df["Crew_Name"].dropna().unique()[0]
        designation = df["Desig"].dropna().unique()[0]
        cli_name = df["Nom_CLI"].dropna().unique()[0]
    except:
        train_no = loco_no = cms_id = lp_name = designation = cli_name = "N/A"

    # ✅ Number of Stops
    max_run_no = df["Run_No"].nunique() if "Run_No" in df.columns else "N/A"

    # ✅ Max & Avg Speed
    if "Speed" in df.columns:
        avg_speed = df["Speed"].mean()
        if "CMS_ID" in df.columns:
            max_speed_by_lp = df.groupby("CMS_ID")["Speed"].max().get(cms_id, df["Speed"].max())
        else:
            max_speed_by_lp = df["Speed"].max()
    else:
        avg_speed = max_speed_by_lp = "N/A"

    # ✅ Build main identity paragraph
    identity_line = (
        # f"On Date **{on_date}**, "
        f"Train Number **{train_no}** was driven by LP **{lp_name}**, "
        f"**{designation}**, CMS ID: **{cms_id}** with Locomotive Number **{loco_no}**. "
        f"His nominated CLI is **{cli_name}**.\n \n ✅ Drive Details:- "
        f"The loco pilot made **{max_run_no}** Dead stops during the trip. "
        f"He achieved a maximum speed of **{max_speed_by_lp:.2f} km/h**, "
        f"while the average speed of the train recorded **{avg_speed:.2f} km/h**."
        
    )
    paragraph.append(f"On Date **{on_date}**,")
    paragraph.append(drive_duration)
    paragraph.append(total_time_str)
    paragraph.append(identity_line)
    paragraph.append(distance_info)
    paragraph.append("\n \n")
    paragraph.append("✅ Brake feel & Brake Power Test Analysis:-")
    

    # 🔧 Add BFT Time detection
    bft_time_text = ""
    if "BFT_BPT" in df.columns and "Time" in df.columns:
        bft_rows = df[df["BFT_BPT"].astype(str).str.upper().str.contains("BFT", na=False)]
        if not bft_rows.empty:
            bft_time = bft_rows["Time"].iloc[0]
            bft_dist = bft_rows["Cum_Dist_Run"].iloc[0]
            bft_speed = bft_rows["Speed"].iloc[0]
            bft_time_text = f" Additionally,LP has conducted Brake Feel Test (BFT) at **{bft_time}** Hrs, at Distance of **{bft_dist} meters** from the starting point, BFT Initiated at the Speed **{bft_speed} KMPH**. "
        else:
            bft_time_text = "Brake Feel Test Not Carried out as Per Norms"
        paragraph.append(bft_time_text)

    bft_end_time_text = ""
    if "BFT_BPT" in df.columns and "Time" in df.columns:
        bft_end_rows = df[df["BFT_BPT"].astype(str).str.upper().str.contains("BFT_END", na=False)]
        if not bft_rows.empty:
            bft_end_time = bft_end_rows["Time"].iloc[0]
            bft_end_dist = bft_end_rows["Cum_Dist_Run"].iloc[0]
            bft_end_speed = bft_end_rows["Speed"].iloc[0]
            bft_end_time_text = f" And,BFT Finished at **{bft_end_time}** Hrs, at Distance of **{bft_end_dist} meters** from the starting point, LP Dropped Speed upto **{bft_end_speed} KMPH**, Proper functioning of the brake application system has been Varified."
        else:
            bft_end_time_text = "Brake Power Test Not Carried out as Per Norms"  
        paragraph.append(bft_end_time_text)
        paragraph.append("\n")
        paragraph.append("\n")
        
    
    # 🔧 Add BFT Time detection
    bpt_time_text = ""
    if "BFT_BPT" in df.columns and "Time" in df.columns:
        bft_rows = df[df["BFT_BPT"].astype(str).str.upper().str.contains("BPT", na=False)]
        if not bft_rows.empty:
            bpt_time = bft_rows["Time"].iloc[0]
            bpt_dist = bft_rows["Cum_Dist_Run"].iloc[0]
            bpt_speed = bft_rows["Speed"].iloc[0]
            bpt_time_text = f" Further,LP has conducted Brake Power Test (BPT) at **{bpt_time}** Hrs, at Distance of **{bpt_dist} meters** from the starting point, BPT Initiated at the Speed **{bpt_speed} KMPH**. "
        else:
            bpt_time_text = "Brake Power Test Not Carried out as Per Norms"
        paragraph.append(bpt_time_text)
        paragraph.append("\n")

    bft_end_time_text = ""
    if "BFT_BPT" in df.columns and "Time" in df.columns:
        bft_end_rows = df[df["BFT_BPT"].astype(str).str.upper().str.contains("BPT_END", na=False)]
        if not bft_rows.empty:
            bpt_end_time = bft_end_rows["Time"].iloc[0]
            bpt_end_dist = bft_end_rows["Cum_Dist_Run"].iloc[0]
            bpt_end_speed = bft_end_rows["Speed"].iloc[0]
            bpt_end_time_text = f" And,BPT Finished at **{bpt_end_time}** Hrs, at Distance of **{bpt_end_dist} meters** from the starting point, LP Dropped Speed upto **{bpt_end_speed} KMPH**, Proper efficiency of the brake application system has been Varified."
        else:
            bft_end_time_text = "Brake Power Test Not Carried out as Per Norms"
        paragraph.append(bpt_end_time_text)
        paragraph.append("\n")
        paragraph.append("\n")
        paragraph.append("✅ Braking Pattern Analysis:- ")
        paragraph.append("\n")
       


risk_lines = []
risky_runs = []  # ⬅️ Store risky cases for separate mention

if "Pin_Point" in df.columns and "Speed" in df.columns and "Run_No" in df.columns:
    # Filter where Pin_Point contains 1000
    pinpoint_1000_df = df[df["Pin_Point"].astype(str).str.contains("1000", na=False)]

    speeds_at_1000 = []

    for run_no in pinpoint_1000_df["Run_No"].unique():
        run_data = df[df["Run_No"] == run_no]
        max_speed = run_data["Speed"].max()

        speed_1000_row = pinpoint_1000_df[pinpoint_1000_df["Run_No"] == run_no]
        if not speed_1000_row.empty:
            speed_1000 = speed_1000_row["Speed"].iloc[0]
            speeds_at_1000.append(int(speed_1000))

            # Risk logic
            if speed_1000 > 0.6 * max_speed:
                risk_level = "Risky Approach"
                risky_runs.append(f"Run-{run_no} at **{int(speed_1000)} kmph**")
            else:
                risk_level = "Safe Approach"

            risk_lines.append(f"Run-{run_no}: **{int(speed_1000)} kmph** – {risk_level}")

    # Summary statement
    if speeds_at_1000:
        all_speeds_str = ", ".join(str(s) for s in speeds_at_1000)
        summary_line = (
            f"Speed at 1000 meter before Dead Stop was found **{all_speeds_str} kmph** "
            f"during different runs. Based on logic of **40% speed reduction** at 1000 meters "
            f"before halt, the following conclusions were drawn:"
        )
        paragraph.append("At Braking Distance (1000 Meters):- ")
        paragraph.append(summary_line)

        # Add each run's risk status
        for line in risk_lines:
            paragraph.append(line)

        # Highlight risky runs
        if risky_runs:
            risky_summary = "\n \n🚨 Risky Speed Detected before 1000 meter of Halt in: " + ", ".join(risky_runs)
            paragraph.append(risky_summary)
            paragraph.append("\n\n")


# 🚦 Analyze speed at "10 Meters" before halt
risk_lines10 = []
risky_runs10 = []

if "Pin_Point" in df.columns and "Speed" in df.columns and "Run_No" in df.columns:
    # Filter rows where Pin_Point contains "10 Meters"
    pinpoint_10_df = df[df["Pin_Point"].astype(str).str.contains("10 Meters", na=False)]

    speeds_at_10 = []

    for run_no10 in pinpoint_10_df["Run_No"].unique():
        run_data10 = df[df["Run_No"] == run_no10]
        max_speed10 = run_data10["Speed"].max()

        speed_10_row = pinpoint_10_df[pinpoint_10_df["Run_No"] == run_no10]
        if not speed_10_row.empty:
            speed_10 = speed_10_row["Speed"].iloc[0]
            speeds_at_10.append(int(speed_10))

            # Risk condition: Speed at 10m should be very low, ideally 0–10 kmph
            if speed_10 > 10:
                risk_level10 = "Risky Stoppage"
                risky_runs10.append(f"Run-{run_no10} at **{int(speed_10)} kmph**")
            else:
                risk_level10 = "Safe Stoppage"

            risk_lines10.append(f"Run-{run_no10}: **{int(speed_10)} kmph** – {risk_level10}")

    # 📄 Add to paragraph
    if speeds_at_10:
        all_speeds_10_str = ", ".join(str(s) for s in speeds_at_10)
        summary_line10 = (
            f"Speed at **10 meters** before Dead Stop was found to be **{all_speeds_10_str} kmph** "
            f"during different runs. Based on safe stopping logic (speed ≤ 10 kmph), the following were observed:"
        )
        paragraph.append("Final Braking Analysis (10 Meters):- ")
        paragraph.append(summary_line10)

        for line in risk_lines10:
            paragraph.append(line)

        if risky_runs10:
            risky_summary10 = "🚨 **Risky Final Approaches** detected in: " + ", ".join(risky_runs10)
            paragraph.append(risky_summary10)



    

    st.markdown("### 📝 Final Drive Observation")
    st.write(" ".join(paragraph))
    st.write("NOTE:- This paragraph has been generated using AI-based logic and automated data analysis. Please review the content and verify key insights with Excel file before taking any operational or official decisions.")