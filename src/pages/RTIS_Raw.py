import streamlit as st
import pandas as pd
import re
import os
import json
from datetime import datetime
import numpy as np
import plotly.express as px
import pydeck as pdk
import io


st.set_page_config(page_title="RTIS App", page_icon="🚆", layout="wide")
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("🚫 🔐 You must login first.")
    st.header("🚫 🔐")
    st.switch_page("graph.py")
    st.stop()
st.write(f"👤Welcome {st.session_state.get('user_name', '')}/{st.session_state.get('user_desig', '')}")
gif_path = os.path.join(os.path.dirname(__file__), "..", "RTIS Logo.png")
st.sidebar.image(gif_path, width=180)

if st.sidebar.button("Home"):
    st.switch_page("pages/design.py")

# --- Custom CSS for Buttons and Links ---
st.markdown("""
    <style>
    /* Button Styling */
    div.stButton > button {
        background-color: #0F0F0F !important;
        color: white !important;
        border: 1px solid #ddd !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        padding: 12px 24px !important;
        width: 250px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        margin: 10px auto !important;
        display: block !important;
        transition: background-color 0.3s ease !important;
    }
    div.stButton > button:hover {
        background-color: #B2F056 !important;
        color: white !important;
    }

    /* Link Styling */
    .custom-link {
        display: block;
        width: 250px;
        text-align: center;
        padding: 12px 24px;
        margin: 30px auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        border: 1px solid #ddd !important;
        font-size: 16px;
        font-weight: bold;
        background-color: #8d898e !important;
        color: white !important;
        text-decoration: none !important;
        border-radius: 10px;
        transition: background-color 0.3s ease;
    }
    .custom-link:hover {
        background-color: #7a7a7a !important;
        color: white !important;
        text-decoration: none !important;
    }

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

st.markdown("""
    <script>
        window.scrollTo(0, 0);
    </script>
""", unsafe_allow_html=True)


# Custom CSS
st.markdown("""
    <style>
        /* Move Streamlit header upward */
        .block-container {
            padding-top: 1rem;  /* default ~6rem, reduce to move up */
        }
    </style>
""", unsafe_allow_html=True)


# Function to convert and clean RTIS data=================================================
def convert_rtis(files):
    import pandas as pd

    df_list = []

    # files is a list -> read one by one
    for f in files:
        temp = pd.read_csv(f)
        df_list.append(temp)

    # merge into one df
    df = pd.concat(df_list, ignore_index=True)
    df.rename(columns={'Logging Time':'datetime'}, inplace=True)
    df.rename(columns={'last/cur stationCode':'StationCode'}, inplace=True)
    df.rename(columns={'distFromPrevLatLng':'Distance'}, inplace=True)

    df['datetime'] = df['datetime'].astype(str).str.strip()
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    df = df.dropna(subset=['datetime']) # Drop rows where datetime conversion failed

    df['Speed'] = pd.to_numeric(df['Speed'], errors='coerce').fillna(0).astype(int)
    # This keeps single zero-speed entries and the first entry of a consecutive sequence.
    mask_to_keep = (df['Speed'] != 0) | (df['Speed'].shift() != 0)
    df = df[mask_to_keep]

    df['Distance'] = df['Distance'].round(0).astype(int)
    df['Time'] = df['datetime'].dt.strftime('%H:%M:%S')
    df['Date'] = df['datetime'].dt.strftime('%d/%m/%Y')
    df = df[['datetime','Date','Time','Distance','Latitude','Longitude','Speed','StationCode']]
    df = df.dropna(subset=['Latitude','Longitude'])
    df = df.sort_values('datetime').reset_index(drop=True)

# Stop Long term file Uploading--------------------------------------------------
    df_sample = df.head(20).copy()
    df_sample['Time'] = pd.to_datetime(df_sample['Time'], format='%H:%M:%S', errors='coerce')
    df_sample.dropna(subset=['Time'], inplace=True)
    
    time_diffs = df_sample['Time'].diff().dt.total_seconds().dropna()
    # Use median instead of mean to be robust against single large outliers
    median_diff = time_diffs.median() if not time_diffs.empty else 0
    if median_diff > 5: # If median interval is > 5s, it's likely a long-term file
        st.error("Invalid File!!! Upload Only One Second Raw Files")
        st.stop()

    return df

# Upload RTIS Files and Show DataFrames ============================================================
st.title("RTIS Data Analysis (Per Second Raw Data)")
st.markdown("---")

rtis_df = None
st.subheader("Upload RTIS multiple CSV File")
rtis_files = st.file_uploader(
    "Don't Open or change CSV file before Uploading",
    type=['csv'],
    accept_multiple_files=True
)
# =====================================================================
# Show RTIS DataFrame with DateTime Filter 
# =====================================================================
if rtis_files:
    # Load the original, unfiltered dataframe
    rtis_df_original = convert_rtis(rtis_files)
    st.success("RTIS CSV File Loaded Successfully")
    # Condition: Only show datetimes where Speed is 0.
    stop_datetimes = rtis_df_original[rtis_df_original['Speed'] == 0]
    # Format the datetimes for the selectbox
    datetime_options = stop_datetimes['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S').unique().tolist()

    # Get unique station codes for dropdowns
    rtis_df = rtis_df_original.copy()
    station_codes = [''] + rtis_df['StationCode'].dropna().unique().tolist()


    col1, col2, Col3, Col4, col5 = st.columns(5)
    with col1:
        from_stn = st.selectbox("Duty Start Station", options=station_codes, index=0)
    with col2:
        to_stn = st.selectbox("Duty End Station", options=station_codes, index=0)
    with Col3:
        Loco_No = st.text_input("Loco No. (Mandatory)")
        if Loco_No == "":
            st.warning("Loco No is mandatory.")
            rtis_df['Loco_No'] = ''
        else:
            rtis_df['Loco_No'] = Loco_No.strip()
    with Col4:
        Train_No = st.text_input("Train No. (Mandatory)")
        if Train_No == "":
            st.warning("Train No is mandatory.")
            rtis_df['Train_No'] = ''
        else:
            rtis_df['Train_No'] = Train_No.strip()
    with col5:
        cms_id = st.text_input("Enter Crew CMS ID (Mandatory)")
        if cms_id == "":
            st.warning("Crew CMS ID is mandatory.")
            rtis_df['CMS_ID'] = ''
        else:
            rtis_df['CMS_ID'] = cms_id.strip()


    if from_stn and to_stn:
        try:
            from_idx = rtis_df.index[rtis_df['StationCode'] == from_stn][0]
            to_idx = rtis_df.index[rtis_df['StationCode'] == to_stn][0]
            if from_idx < to_idx:
                rtis_df = rtis_df.loc[from_idx:to_idx]
        except IndexError:
            st.warning("Selected station code not found for filtering. Showing full data.")

# Cumulative Distance Calculation ============================================================
    rtis_df['Cum_Dist_Train'] = rtis_df['Distance'].cumsum()

# Run Number Calculation ============================================================
    rtis_df['Run_No'] = (rtis_df['Speed'].shift(fill_value=1) == 0).cumsum()

# Cumulative Distance Run Calculation ============================================================
    rtis_df['Cum_Dist_Run'] = rtis_df.groupby('Run_No')['Distance'].cumsum()

# 'Cum_Dist_LP' ....................................................................
    rtis_df['Cum_Dist_Run'] = rtis_df.groupby(rtis_df['Speed'].eq(0).cumsum())['Distance'].cumsum()
    if {'Speed', 'CMS_ID', 'Distance'}.issubset(rtis_df.columns):
        rtis_df['Cum_Dist_LP'] = rtis_df.groupby(['CMS_ID', 'Train_No'])['Distance'].cumsum()

#  Run_Sum Column ============================================================
    rtis_df['Run_Sum'] = rtis_df.groupby(['Run_No'])['Distance'].transform('sum')

# Rev_Dist ........................................................................................
    rtis_df['Rev_Dist'] = rtis_df['Run_Sum'] - rtis_df['Cum_Dist_Run']

# Pin Point Calculation ============================================================
    rtis_df['Pin_Point'] = ''
    for dist, label in [(10, '10 Meters'), (250, '250 Meters'), (500, '500 Meters'), (1000, '1000 Meters')]:
        idxs = (
            rtis_df.groupby(['Run_No'])['Rev_Dist']
            .apply(lambda x: (x - dist).abs().idxmin())
        )
        rtis_df.loc[idxs.values, 'Pin_Point'] = label
# BFT Calculation ============================================================  
    if "BFT" not in rtis_df.columns:
        rtis_df["BFT"] = ""
    if "BFT_END" not in rtis_df.columns:
        rtis_df["BFT_END"] = ""

    # Clear existing marks
    rtis_df["BFT"] = ""
    rtis_df["BFT_END"] = ""

    # Filter within distance window < 10000
    df = rtis_df[rtis_df["Cum_Dist_Train"] < 10000]

    idxs = df.index.to_list()
    speeds = df["Speed"].to_list()

    bft_row_idx = None
    bft_pos = None
    stopped = False

    # -------------------------
    # Phase 1: Find first BFT or reject
    # -------------------------
    for pos, ridx in enumerate(idxs):
        sp = speeds[pos]

        # Reject BEFORE BFT
        if bft_row_idx is None and sp > 17:
            rtis_df.at[ridx, "BFT"] = "BFT Not Done"
            stopped = True
            break

        # First BFT trigger (15..17)
        if bft_row_idx is None and 15 <= sp <= 17:
            rtis_df.at[ridx, "BFT"] = "BFT"
            bft_row_idx = ridx
            bft_pos = pos
            break  # move to Phase 2

    if stopped or bft_row_idx is None:
        pass  # nothing more to do
    else:
        for pos2 in range(bft_pos + 1, len(idxs)):
            ridx2 = idxs[pos2]
            sp2 = speeds[pos2]

            # Late Reject after BFT but before <10
            if sp2 > 17:
                # remove earlier BFT
                rtis_df.at[bft_row_idx, "BFT"] = ""
                rtis_df.at[ridx2, "BFT"] = "BFT Not Done"
                break

            # BFT_END found (<10)
            if sp2 < 10:
                rtis_df.at[ridx2, "BFT_END"] = "BFT_END"
                break
# BPT Calculation ============================================================  
    df = rtis_df.copy()
    s = df['Speed']
    is_potential_bpt = (
        (df['Cum_Dist_Train'] < 10000) &
        (s >= 40) & (s <= 70) &
        (s > s.shift(-1)) &      # Initial drop
        (s.shift(-1) >= s.shift(-2)) &
        (s.shift(-2) >= s.shift(-3)) &
        (s.shift(-3) >= s.shift(-4)) &
        (s.shift(-4) >= s.shift(-5)) &
        (s.shift(-5) >= s.shift(-6))
    )
    rtis_df['BPT'] = ''
    if is_potential_bpt.any():
        first_bpt_index = is_potential_bpt.idxmax()
        rtis_df.loc[first_bpt_index, 'BPT'] = "BPT"
    rtis_df['Speed_shift'] = rtis_df['Speed'].shift(1)
    rtis_df['BPT_END'] = ''
    bpt_idx_list = rtis_df.index[rtis_df['BPT'] == 'BPT'].tolist()

    if bpt_idx_list:
        bpt_idx = bpt_idx_list[0]  # first BPT only

        # Scan forward from BPT+1 to find END
        for i in range(bpt_idx + 1, len(df)):
            if (
                rtis_df.loc[i, 'Speed'] > rtis_df.loc[i, 'Speed_shift'] and
                0 <= rtis_df.loc[i, 'Speed'] <= 40 and
                rtis_df.loc[i, 'Cum_Dist_Train'] < 10000
            ):
                end_idx = i - 1
                if end_idx >= 0:
                    rtis_df.loc[end_idx, 'BPT_END'] = "BPT_END"
                break
    rtis_df.drop(columns=['Speed_shift'], inplace=True)

# Adding a new column 'Crew Name','CLI Name', 'Desig'............................................................................................................................
    try:
            import os
            import gspread

            # CMS Google Spreadsheet
            cms_sheet_url = (
                "https://docs.google.com/spreadsheets/d/"
                "1iAY-h7udzOYpEDiSVK3rr6Ys-fE1D_V9QGlCFetHsGw/edit"
            )

            # Use the same credentials file as your working login
            credentials_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "gs_credentials.json"
            )

            if not os.path.exists(credentials_path):
                credentials_path = os.path.abspath("gs_credentials.json")

            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    "gs_credentials.json not found."
                )

            # Authenticate using the same method as your login code
            client = gspread.service_account(
                filename=credentials_path
            )

            # Open the CMS spreadsheet and worksheet
            worksheet = (
                client.open_by_url(cms_sheet_url)
                .worksheet("CMS_DATA")
            )

            # Read all rows
            rows = worksheet.get_all_values()

            if not rows:
                raise ValueError("CMS_DATA worksheet is empty.")

            # Build DataFrame using the first row as headers
            headers = [
                str(col).strip().upper()
                for col in rows[0]
            ]

            cms_df = pd.DataFrame(
                rows[1:],
                columns=headers
            )

            # Validate required columns
            required_columns = [
                "CREW_ID",
                "CREW_NAME",
                "DESIG",
                "CLI_NAME"
            ]

            missing = [
                col for col in required_columns
                if col not in cms_df.columns
            ]

            if missing:
                raise ValueError(
                    f"Missing columns in CMS_DATA: {missing}. "
                    f"Available columns: {list(cms_df.columns)}"
                )

            # Normalize IDs to strings
            cms_df["CREW_ID"] = (
                cms_df["CREW_ID"].astype(str).str.strip()
            )

            df["CMS_ID"] = (
                df["CMS_ID"].astype(str).str.strip()
            )

            # Remove blank IDs and duplicate crew records
            cms_df = cms_df[
                cms_df["CREW_ID"].ne("")
            ].copy()

            cms_df.drop_duplicates(
                subset=["CREW_ID"],
                keep="first",
                inplace=True
            )

            # Create lookup dictionaries
            crew_name_map = dict(
                zip(cms_df["CREW_ID"], cms_df["CREW_NAME"])
            )

            cli_name_map = dict(
                zip(cms_df["CREW_ID"], cms_df["CLI_NAME"])
            )

            desig_map = dict(
                zip(cms_df["CREW_ID"], cms_df["DESIG"])
            )

            # Map CMS data to the main DataFrame
            df["Crew_Name"] = df["CMS_ID"].map(crew_name_map)
            df["Nom_CLI"] = df["CMS_ID"].map(cli_name_map)
            df["Desig"] = df["CMS_ID"].map(desig_map)

            print(
                f"CMS Google Sheets loaded successfully: "
                f"{len(cms_df)} unique crew IDs"
            )

            del cms_df

        except Exception as e:
            print(f"Error loading CMS Data from Google Sheets: {e}")

            df["Crew_Name"] = None
            df["Nom_CLI"] = None
            df["Desig"] = None
# ==============================================================================
# Combine BFT / BPT Markers
# ==============================================================================
    def bft_bpt_concat(row):
        vals = [str(row[col]) for col in ['BFT', 'BPT', 'BFT_END', 'BPT_END']
                if pd.notna(row[col]) and str(row[col]).strip() != '']
        return ' '.join(vals).strip()

    rtis_df['BFT_BPT'] = rtis_df.apply(bft_bpt_concat, axis=1)


    # rtis_df2 = rtis_df[["Date", "Time", "Speed", "Distance","StationCode","BFT_BPT","Run_No"]]
    rtis_df2 = rtis_df[["Date", "Time", "Speed", "Distance", "CMS_ID", "Train_No", "Loco_No", "Crew_Name","Nom_CLI","Desig","BFT","BFT_END","BPT","BPT_END","BFT_BPT",
                        "Cum_Dist_Run","Cum_Dist_LP","Run_No","Run_Sum","Rev_Dist","Pin_Point","StationCode"]]
    # st.dataframe(rtis_df2, use_container_width=True)

    # Save to Excel using openpyxl (Streamlit web: download, PyQt: dialog)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        rtis_df2.to_excel(writer, index=False, sheet_name='DataBase')   # logging still inside
    output.seek(0)

    row_count = len(rtis_df)
    st.sidebar.success(f"✅ Excel file generated with {row_count} rows!")
    st.success(f"✅ Download Excel file from Sidebar!")
    rtis_df['Date'] = pd.to_datetime(rtis_df['Date'], errors='coerce')
    if pd.notna(rtis_df['Date'].iloc[0]):
        Date = rtis_df['Date'].iloc[0].strftime("%d-%m-%Y")
    else:
        Date = datetime.now().strftime("%d-%m-%Y")

    file_name = f"RTIS_{Date}.xlsx"    # as per your request
    st.sidebar.download_button(
        label="📥 Download RTIS Fabricated Excel",
        data=output,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    
# Plot Line Graph for BFT/BPT with Pointer........................................................................................................
    data_base = rtis_df.loc[rtis_df['Cum_Dist_Train'] < 5500]
    bft = data_base.loc[data_base['BFT_BPT'] == "BFT"]
    bpt = data_base.loc[data_base['BFT_BPT'] == "BPT"]

    Dist_points1 = []  # Specify the x-axis points where you want to display the values
    bft_points = bft.index.tolist()  # Get the indices of rows where BFT is present
    bpt_points = bpt.index.tolist()  # Get the indices of rows where BPT is present

    Dist_points1.extend(bft_points)  # Extend the Dist_points1 list with BFT indices
    Dist_points1.extend(bpt_points)  # Extend the Dist_points1 list with BPT indices

    text_values = ['BFT Done'] * len(bft_points) + ['BPT Done'] * len(bpt_points)
    fig_bft_bpt = px.line(data_base, x="Time", y="Speed", color_discrete_sequence=["#2FF7F7"])
    for i, tp in enumerate(Dist_points1):
        selected_data = data_base.loc[data_base.index == tp]
        if len(selected_data) > 0:
            fig_bft_bpt.add_annotation(x=selected_data['Time'].iloc[0], y=selected_data['Speed'].iloc[0], text=text_values[i],
                                showarrow=True, arrowhead=5, arrowcolor='red')
    fig_bft_bpt.update_layout(
        title="Brake Feel & Brake Power Test (In First Section)",
        xaxis=dict(title="Time"),
        yaxis=dict(title="Speed")
    )
    st.plotly_chart(fig_bft_bpt, use_container_width=True)
    st.markdown("---")

 

# Plot RTIS Speed VS Time+Station Code using Plotly ===============================================================
if rtis_df is not None and not rtis_df.empty:
    import plotly.graph_objects as go

    rtis_df['x_label'] = rtis_df['datetime'].dt.strftime('%H:%M:%S') + " (" + rtis_df['StationCode'].astype(str) + ")"
    fig_speed_time = go.Figure()
    fig_speed_time.add_trace(go.Scatter(
        x=rtis_df['x_label'],
        y=rtis_df['Speed'],
        line=dict(color='orange', width=2),
        mode='lines',
        name='RTIS Speed',
        hovertemplate=
        '<b span style="color:green">RTIS Data</b><br>'+
        'Date=%{customdata[0]}<br>'+
        'Time=%{customdata[3]}<br>'+
        'Stncode=%{customdata[2]}<br>'+
        'RTIS_Speed=<span style="color:green">%{y}<br>'+
        '<extra></extra>',
        customdata=rtis_df[['Date', 'Speed', 'StationCode','Time']].values
    ))

    title_str = "RTIS Time+Station Code VS Speed"
    if from_stn and to_stn:
        title_str += f" between {from_stn} to {to_stn}"

    fig_speed_time.update_layout(
        # title=(f"RTIS Time+Station Code VS Speed between {from_stn[0]} to {to_stn[0]}"),
        title=title_str,
        xaxis_title='Time (Station)',
        yaxis_title='Speed (km/h)',
        hovermode='x'
    )
    st.plotly_chart(fig_speed_time, use_container_width=True)


# Plot RTIS Distance VS Time+Station Code using Plotly ===============================================================
if rtis_df is not None and not rtis_df.empty:
    import plotly.graph_objects as go

    rtis_df['x_label'] = (
    (rtis_df['Cum_Dist_Train'] / 1000).map(lambda x: f"{x:.1f}")
    + " (" + rtis_df['StationCode'].astype(str) + ")"
    )

    fig_dist_time = go.Figure()
    fig_dist_time.add_trace(go.Scatter(
        x=rtis_df['x_label'],
        y=rtis_df['Speed'],
        mode='lines',
        name='RTIS Distance',
        hovertemplate=
        '<b span style="color:green">RTIS Data</b><br>'+
        'Date=%{customdata[0]}<br>'+
        'Time=%{customdata[3]}<br>'+
        'Stncode=%{customdata[2]}<br>'+
        'Train Speed=<span style="color:green">%{y}<br>'+
        '<extra></extra>',
        customdata=rtis_df[['Date', 'Speed', 'StationCode','Time']].values
    ))

    title_str = "Distance+Station Code VS Speed"
    if from_stn and to_stn:
        title_str += f" between {from_stn} to {to_stn}"

    fig_dist_time.update_layout(
        # title=(f"RTIS Time+Station Code VS Speed between {from_stn[0]} to {to_stn[0]}"),
        title=title_str,
        xaxis_title='Distance+Station Code',
        yaxis_title='Speed (km/h)',
        hovermode='x'
    )
    st.plotly_chart(fig_dist_time, use_container_width=True)

# Convert all Graphs into a landscape PDF with a header on each page ===============================================================
    st.markdown("---")
    st.subheader("Download All Graphs as PDF")

    def build_graphs_pdf(figures, titles):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader

        crew_name = rtis_df['Crew_Name'].dropna().iloc[0] if 'Crew_Name' in rtis_df.columns and not rtis_df['Crew_Name'].dropna().empty else ''
        route_str = f"{from_stn} to {to_stn}" if from_stn and to_stn else "Full Route"

        pdf_buffer = io.BytesIO()
        page_size = landscape(A4)
        page_w, page_h = page_size
        c = canvas.Canvas(pdf_buffer, pagesize=page_size)

        for fig_obj, fig_title in zip(figures, titles):
            # --- Header details on top of each page ---
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(page_w / 2, page_h - 1.2 * cm, "RTIS Data Analysis Report")

            c.setFont("Helvetica", 10)
            details_line1 = f"Train No: {Train_No or '-'}     Loco No: {Loco_No or '-'}     LP Name: {crew_name or '-'}     CMS ID: {cms_id or '-'}"
            details_line2 = f"Route: {route_str}     Date: {Date}"
            c.drawCentredString(page_w / 2, page_h - 1.9 * cm, details_line1)
            c.drawCentredString(page_w / 2, page_h - 2.4 * cm, details_line2)

            c.line(1 * cm, page_h - 2.7 * cm, page_w - 1 * cm, page_h - 2.7 * cm)

            # --- Graph image (top-anchored, right below the header line) ---
            # Extra bottom margin so x-axis labels/title aren't cut off in the exported PNG
            fig_obj.update_layout(margin=dict(b=150))
            img_bytes = fig_obj.to_image(format="png", width=1920, height=800, scale=2)
            img = ImageReader(io.BytesIO(img_bytes))
            img_w = page_w - 2 * cm
            img_top = page_h - 2.8 * cm
            img_h = img_top - 1 * cm
            c.drawImage(img, 1 * cm, 1 * cm, width=img_w, height=img_h, preserveAspectRatio=True, anchor='n')

            c.showPage()

        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer

    try:
        pdf_data = build_graphs_pdf(
            [fig_speed_time, fig_dist_time, fig_bft_bpt],
            ["RTIS Time+Station Code VS Speed", "Distance+Station Code VS Speed", "Brake Feel & Brake Power Test"]
        )
        pdf_file_name = f"RTIS_Graphs_{Date}.pdf"
        st.download_button(
            label="📥 Download All Graphs as PDF",
            data=pdf_data,
            file_name=pdf_file_name,
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Could not generate PDF: {e}")
