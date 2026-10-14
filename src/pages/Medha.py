import streamlit as st
import pandas as pd
import os,socket
import re
import io
import gspread
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="SPM App", page_icon="🚆", layout="wide")
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("🚫 🔐 You must login first.")
    st.header("🚫 🔐")
    st.switch_page("graph.py")
    st.stop()
st.markdown("""
    <script>
        window.scrollTo(0, 0);
    </script>
""", unsafe_allow_html=True)

def Medha(file):
    """
    Fabricate uploaded .txt file into an Excel file.
    """
    encodings_to_try = ['utf-8', 'latin-1', 'utf-16', 'windows-1252']
    df = None

    for encoding in encodings_to_try:
        try:
            df = pd.read_csv(file, delimiter='\t', encoding=encoding)
            break
        except Exception:
            continue

    if df is None:
        st.error("❌ Unable to read the uploaded text file with available encodings.")
        return None

    # Sample fabrication logic (modify as per your business rules)
    df.columns = df.columns.str.strip()
    df.dropna(how="all", inplace=True)
    # Define the new header names  .....................................................................................
    new_header_names = ['New Header 1']
    df.columns = new_header_names
    with st.spinner("Processing file... Please wait ⏳"):
        # Split the text in Column 1 using "|" delimiter
        split_values = df['New Header 1'].str.split("|", expand=True)
        df['Date'] = split_values[0]
        df['Time'] = split_values[1]
        df['Speed'] = split_values[2]
        df['Distance'] = split_values[3]
        df['Column 5'] = ''
        df['Column 6'] = ''
        df['Column 7'] = ''
        df['Column 8'] = ''
        df['Column 9'] = ''
        df['Column 10'] = ''
        df['Column 11'] = ''
        
        # Delete unnecessary columns
        columns_to_delete = ['Column 5', 'Column 6', 'Column 7', 'Column 8', 'Column 9', 'Column 10', 'Column 11']
        df.drop(columns=columns_to_delete, inplace=True)

        # Cut and paste Column 1 cell value to Column 5 if it contains "Driver"
        df.loc[df['Date'].str.contains('Driver', na=False), 'Column 5'] = df['Date']

        # Copy down cell value of Column 5 if Column 4 data is not null
        df['Column 5'] = df['Column 5'].ffill()

        # Delete the Entire row with garbage value (Condition applied "Where Col 3 is null")
        df = df.dropna(subset=['Speed'])
        df.reset_index(drop=True, inplace=True)

        # Delete Column 1 which is useless now
        df = df.drop("New Header 1", axis=1)
        
        # Split values in Column 5 using ":"
        split_values = df['Column 5'].str.split(":", expand=True)
        df['Column 6'] = split_values[0]
        df['Column 7'] = split_values[1]
        df['Column 8'] = split_values[2]
        df['Column 9'] = split_values[3]
        # Delete extra text from each row in Column 7, 8, 9 and Remove White Space Using ".str.strip()"
        df['CMS_ID'] = df['Column 7'].str.replace('Train No', '').str.strip()
        df['Train_No'] = df['Column 8'].str.replace('Locono', '').str.strip()
        df['Loco_No'] = df['Column 9'].str.replace(r'(?:Spd|Speed) Limit', '', regex=True).str.strip()
    # Function to clean and convert the text to time format ..........................................................................................
        def clean_and_convert_time(time_str):
            time_str = time_str.strip()
            match = re.match(r'^(\d+):(\d+):(\d+)$', time_str)
            if match:
                hour, minute, second = match.groups()
                return f"{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
            else:
                return None
# Apply the function to the 'Time' column and create a new column 'Formatted_Time' ..................................................................
        df['Time'] = df['Time'].apply(clean_and_convert_time)

# Stop Long term file Uploading--------------------------------------------------
        df_sample = df.head(50).copy()
        df_sample['DateTime'] = pd.to_datetime(
        df_sample['Date'] + ' ' + df_sample['Time'],
        format='%d/%m/%Y %H:%M:%S',
        errors='coerce')
        df_sample = df_sample.sort_values('DateTime')
        time_diffs = df_sample['DateTime'].diff().dt.total_seconds().dropna()
        median_diff = time_diffs.median()
        if median_diff > 5:
            st.error("Invalid File!!! Upload Only Short-term Raw Files")
            st.stop()
# Delete unnecessary columns-----------------------------------------------
        columns_to_delete = ['Column 5', 'Column 6', 'Column 7', 'Column 8', 'Column 9']
        df.drop(columns=columns_to_delete, inplace=True)
            
# Convert certain columns to numeric format .................................................................................................
        numeric_columns = ['Speed', 'Distance','Loco_No']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')

# Remove Gaps in CMS ID
        df['CMS_ID'] = df['CMS_ID'].str.replace(' ', '', regex=False)  

# Convert Date format .................................................................................................................
        try:
            df["Date"] = df["Date"].astype(str).str.strip().str.strip("'").str.strip()
            df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%y", errors="coerce")
            df["Date"] = df["Date"].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else '')
        except Exception as e:
            st.warning(f"⚠️ Failed to clean and convert date format: {e}")

# Cum_Dist_Run based on the Start & Stop ...................................................................................
        # Drop rows where 'Distance' is NaN
        df = df.dropna(subset=['Distance'])
        df['Cum_Dist_Run'] = df.groupby(df['Speed'].eq(0).cumsum())['Distance'].cumsum()

# Set ['Run_No'] ...................................................................................
        cms_change = (df['CMS_ID'] != df['CMS_ID'].shift()) | (df['Train_No'] != df['Train_No'].shift())
        distance_reset = df['Cum_Dist_Run'] < df['Cum_Dist_Run'].shift()
        group = cms_change.cumsum()
        df['Run_No'] = distance_reset.groupby(group).cumsum() + 1
       
# 'Cum_Dist_LP' ....................................................................
        df['Cum_Dist_Run'] = df.groupby(df['Speed'].eq(0).cumsum())['Distance'].cumsum()
        if {'Speed', 'CMS_ID', 'Distance'}.issubset(df.columns):
            df['Cum_Dist_LP'] = df.groupby(['CMS_ID', 'Train_No'])['Distance'].cumsum()

# 'Run_Sum'....................................................................
        df['Run_Sum'] = df.groupby(['Run_No','CMS_ID', 'Train_No'])['Distance'].transform('sum')

# Remove entire rows where 'CMS ID' contains 0........................................................................
        # df = df[df['CMS_ID'] != '0']

# Rev_Dist ........................................................................................
        df['Rev_Dist'] = df['Run_Sum'] - df['Cum_Dist_Run']

# Pin_Point with value  ........................................................."
        df['Pin_Point'] = ''
        for dist, label in [(10, '10 Meters'), (250, '250 Meters'), (500, '500 Meters'), (1000, '1000 Meters')]:
            idxs = (
                df.groupby(['Run_No', 'CMS_ID', 'Train_No'])['Rev_Dist']
                .apply(lambda x: (x - dist).abs().idxmin())
            )
            df.loc[idxs.values, 'Pin_Point'] = label

# Add BFT Column ......................................................................................................................
        if "BFT" not in df.columns: df["BFT"] = ""
        if "BFT_END" not in df.columns: df["BFT_END"] = ""

        # Clear any existing marks for a clean run
        df["BFT"] = ""
        df["BFT_END"] = ""

        for (cms_id, train_no), group in df.groupby(["CMS_ID", "Train_No"], sort=False):
            # Apply distance window
            g = group[group["Cum_Dist_LP"] < 10000]
            if g.empty:
                continue

            idxs = g.index.to_list()
            speeds = g["Speed"].to_list()

            bft_row_idx = None
            stopped = False

            # Phase 1: walk until either Reject (>17) or first BFT (15..17)
            for pos, ridx in enumerate(idxs):
                sp = speeds[pos]

                # Reject BEFORE BFT
                if bft_row_idx is None and sp > 17:
                    df.at[ridx, "BFT"] = "BFT Not Done"
                    stopped = True
                    break

                # First BFT trigger
                if bft_row_idx is None and 15 <= sp <= 17:
                    df.at[ridx, "BFT"] = "BFT"
                    bft_row_idx = ridx
                    bft_pos = pos
                    break  # switch to Phase 2

            if stopped or bft_row_idx is None:
                # Either rejected already, or no BFT found in window → nothing else to do
                continue

            # Phase 2: after BFT, scan forward for END (<10) or late Reject (>17)
            for pos2 in range(bft_pos + 1, len(idxs)):
                ridx2 = idxs[pos2]
                sp2 = speeds[pos2]

                # Late reject: >17 before reaching <10 → overwrite BFT with Not Done
                if sp2 > 17:
                    # remove earlier BFT mark
                    df.at[bft_row_idx, "BFT"] = ""
                    df.at[ridx2, "BFT"] = "BFT Not Done"
                    stopped = True
                    break

                # First <10 after BFT → BFT_END
                if sp2 < 10:
                    df.at[ridx2, "BFT_END"] = "BFT_END"
                    stopped = True
                    break

# Add BPT Column ====================================================================================
        s = df['Speed']
        is_potential_bpt = (
            (df['Cum_Dist_LP'] < 10000) &
            (s >= 40) & (s <= 70) &
            (s > s.shift(-1)) &      # Initial drop
            (s.shift(-1) >= s.shift(-2)) &
            (s.shift(-2) >= s.shift(-3)) &
            (s.shift(-3) >= s.shift(-4)) &
            (s.shift(-4) >= s.shift(-5)) &
            (s.shift(-5) >= s.shift(-6))
        )
        df['BPT'] = ''
        df.loc[is_potential_bpt.groupby([df['CMS_ID'], df['Train_No']]).idxmax(), 'BPT'] = 'BPT'

        df['Speed_shift'] = df['Speed'].shift(1)
        df.reset_index(drop=True, inplace=True)

        def get_bpt_end(df):
            df['BPT_END'] = ''
            for (cms_id, train_no), group in df.groupby(["CMS_ID", "Train_No"], sort=False):
                group = group.reset_index()
                bpt_idx = group[group['BPT'] == 'BPT'].index
                if not bpt_idx.empty:
                    bpt_idx = bpt_idx[0]
                    for i in range(bpt_idx + 1, len(group)):
                        if group.loc[i, 'Speed'] > group.loc[i, 'Speed_shift'] and 0 <= group.loc[i, 'Speed'] <= 40 and group.loc[i, 'Cum_Dist_LP'] < 10000:
                            end_idx = i - 1
                            if end_idx >= 0:
                                df.loc[group.loc[end_idx, 'index'], 'BPT_END'] = 'BPT_END'
                            break
            return df
        df = get_bpt_end(df)
        df.drop(columns=['Speed_shift'], inplace=True)

        def bft_bpt_concat(row):
            vals = [str(row[col]) for col in ['BFT', 'BPT', 'BFT_END', 'BPT_END'] if pd.notna(row[col]) and str(row[col]).strip() != '']
            return ' '.join(vals).strip()
        df['BFT_BPT'] = df.apply(bft_bpt_concat, axis=1)

# Create Over Speed/ Train Type Column ..........................................................................................................
        defined_mps = [130, 120, 110, 100, 90, 80, 75, 70, 60]
        if "Over_Speed" not in df.columns:
            df["Over_Speed"] = ""
        if "Train_Type" not in df.columns:
            df["Train_Type"] = ""

        # Mark "ID Changed in Running" once (safe if dtype issues in Speed)
        _speed_numeric_for_flag = pd.to_numeric(df["Speed"], errors="coerce")
        df["CMS_Changed"] = df["CMS_ID"].ne(df["CMS_ID"].shift())
        df.loc[df["CMS_Changed"] & (_speed_numeric_for_flag > 0), "BFT_BPT"] = "ID Changed in Running"
        df.drop(columns=["CMS_Changed"], inplace=True)

        for (cms_id, train_no), group in df.groupby(["CMS_ID", "Train_No"], sort=False):
            try:
                idx = group.index

# ---- Train_Type (always assign for the whole group) ----
                train_no = ""
                if "Train_No" in group.columns and len(group) > 0:
                    train_no = str(group["Train_No"].iloc[0]).strip()
                train_type = "Coaching" if (len(train_no) > 0 and train_no[0].isdigit()) else "Goods"
                df.loc[idx, "Train_Type"] = train_type

                # ---- Prepare numeric speeds for detection ----
                speed_num = pd.to_numeric(group["Speed"], errors="coerce")

                # If all speeds are NaN or group empty → no MPS / Over_Speed (but Train_Type already set)
                if speed_num.dropna().empty:
                    continue
                run_id = (speed_num.ne(speed_num.shift())).cumsum()
                # Length of each run, mapped back to rows
                run_len = run_id.map(run_id.value_counts())

                # Candidate rows where the run length >= 8
                candidates = speed_num[(run_len >= 8)]
                # Highest speed among those candidates (drop NaN first)
                max_speed_qualified = None
                candidates_non_nan = candidates.dropna()
                if not candidates_non_nan.empty:
                    max_speed_qualified = int(candidates_non_nan.max())

                # If no qualified max speed or below 56 → do not set MPS / Over_Speed
                if max_speed_qualified is None or max_speed_qualified < 56:
                    continue

                # ---- Map Max Speed → MPS per your exact bands ----
                if 126 <= max_speed_qualified <= 135:
                    mps = 130
                elif 116 <= max_speed_qualified <= 125:
                    mps = 120
                elif 106 <= max_speed_qualified <= 115:
                    mps = 110
                elif 96  <= max_speed_qualified <= 105:
                    mps = 100
                elif 86  <= max_speed_qualified <= 95:
                    mps = 90
                elif 76  <= max_speed_qualified <= 85:
                    mps = 80
                elif 66  <= max_speed_qualified <= 75:
                    mps = 70
                elif 56  <= max_speed_qualified <= 65:
                    mps = 60
                else:
                    mps = None  # below 56 already filtered; keep for completeness

                if mps is None:
                    continue

# ---- Over Speed marking: Speed > (MPS + 3) ----
                over_mask = speed_num > (mps + 3)
                if over_mask.any():
                    df.loc[idx[over_mask], "Over_Speed"] = f"MPS: {mps}, Over Speed"

            except Exception as e:
                # Never let a single CMS_ID failure stop Excel creation
                st.warning(f"⚠️ Skipped Over_Speed/Train_Type for CMS_ID '{cms_id}': {e}")
                continue
# # Adding a new column 'BFT_BPT' ............................................................................................................................
        df['BFT_BPT'] = df.apply(lambda row: 
            (str(row['BFT']) if pd.notna(row['BFT']) and row['BFT'] != '' else '') +
            (' ' + str(row['BPT']) if pd.notna(row['BPT']) and row['BPT'] != '' else '') +
            (' ' + str(row['BFT_END']) if pd.notna(row['BFT_END']) and row['BFT_END'] != '' else '') +
            (' ' + str(row['BPT_END']) if pd.notna(row['BPT_END']) and row['BPT_END'] != '' else ''),
            axis=1
            ).str.strip()

    # Adding a new column 'Crew Name' , 'CLI Name', 'Desig'............................................................................................................................
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



    # Create a New Sheet "Report" and Push Data to New Sheet .................................................................................................
        # Rearrange the Columns
        df = df[["Date", "Time", "Speed", "Distance", "CMS_ID", "Train_No", "Loco_No", "Crew_Name","Nom_CLI","Desig","BFT","BFT_END","BPT","BPT_END","BFT_BPT",
                    "Cum_Dist_Run","Cum_Dist_LP","Run_No","Run_Sum","Rev_Dist","Pin_Point"]]
        df_unique = df.drop_duplicates(subset=["CMS_ID", "Train_No"], keep="first").reset_index(drop=True)
        st.write("### Unique CMS_ID Entries Found:")
        st.write(df_unique)
        # st.info("Please Wait pushing Data to Server.........")
        st.info("Please Wait Creating Excel File.........")
        

    # Save to Excel using openpyxl (Streamlit web: download, PyQt: dialog)
        output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='DataBase')
    output.seek(0)

    # ✅ Push outside the writer
    st.write("May Download Excel from Sidebar")
    # import pages.exceptions_only as apd
    # apd.push_data(df)

    return output, len(df)

def main():
    st.title(":page_facing_up: Medha Text File Fabricator")
    st.info("Upload a Raw Medha .txt file to fabricate and download as Excel.") 
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {display: none;}
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
    # Making Side Bar
    gif_path = os.path.join(os.path.dirname(__file__), "Ver_3_2.ico")
    st.sidebar.image(gif_path, width=200)

    # Home button to go to design.py
    if st.sidebar.button("🏠 Back to Home", key="home_btn"):
        st.switch_page("pages/design.py")

    uploaded_file = st.file_uploader("Upload .txt File", type=["txt"])
    if uploaded_file:
        st.info("📄 File uploaded. Ready to process.")
        if st.button("Proceed"):
            result = Medha(uploaded_file)
            if result:
                excel_buffer, row_count = result
                st.sidebar.success(f"✅ Excel file generated with {row_count} rows!")
                df_download = pd.read_excel(excel_buffer, engine="openpyxl")
                if "Loco_No" in df_download.columns and not df_download["Loco_No"].isnull().all():
                    loco_no = str(df_download["Loco_No"].dropna().iloc[0])
                else:
                    loco_no = "Unknown"
                st.sidebar.download_button(
                    label="📥 Download Fabricated Excel",
                    data=excel_buffer,
                    file_name=f"Medha_{loco_no}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # st.dataframe(df_download)
                


if __name__ == "__main__":
    main()