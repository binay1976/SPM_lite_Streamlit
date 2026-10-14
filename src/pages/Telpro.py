import streamlit as st
import pandas as pd
import io
import pdfplumber
import warnings
import os,socket



st.set_page_config(page_title="SPM App", page_icon="🚆", layout="wide")
# Session/authentication check
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("🚫 🔐 You must login first.")
    st.header("🚫 🔐")
    st.switch_page("graph.py")
    st.stop()


def Telpro():
    st.title(":page_facing_up: Telpro PDF File Extractor")
    st.info("Upload a PDF file to extract tables and text into an Excel file.")

    # Hide default Streamlit sidebar buttons
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
    img_path = os.path.join(os.path.dirname(__file__), 'Ver_3_2.ico')
    st.sidebar.image(img_path, width=200)

    # Home button to go to design.py
    if st.sidebar.button("🏠 Back to Home", key="home_btn"):
        st.switch_page("pages/design.py")
    with st.spinner("Processing file... Please wait ⏳"):
        uploaded_pdf = st.file_uploader("Upload PDF File", type=["pdf"])
        if uploaded_pdf:
            if uploaded_pdf.size > 5_242_880:
                st.error("Uploaded file is larger, May Take 2-3 Minutes !!! Have Patient.")
            # Check file size (in bytes). 3.5 MB = 1_572_864 bytes
            if uploaded_pdf.size > 6_572_864:
                st.error("❌ Uploaded file is larger than 5 MB. Please upload a smaller file.")
                st.stop()
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            all_data = []
            with pdfplumber.open(uploaded_pdf) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        all_data.extend(table)
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            data = line.split()
                            all_data.append(data)
            if not all_data:
                st.warning("No data extracted from the PDF.")
                return
            pages = len(pdf.pages)
            st.success(f"{pages} PDF pages scanned")
            max_cols = max(len(row) for row in all_data)
            df = pd.DataFrame(all_data, columns=[f"Column_{i+1}" for i in range(max_cols)])

            df = df.fillna("")

# Combine row into single string and Create Status Column----------------------------------------------
            df["Row_Text"] = df.apply(lambda r: " ".join(r.astype(str)).strip(), axis=1)
            # Extract status values using regex
            df["Status"] = df["Row_Text"].str.extract(
                r"(RUN|STOP|START\s*\d+|POWER OFF|POWER ON|DRIVER ID CHANGED|TRAIN NO\. CHANGED)",
                expand=False
            )

# Rename First 4 Columns, if at least 5 columns exist
            if df.shape[1] >= 5:
                df.rename(columns={
                    "Column_1": "Date",
                    "Column_2": "Time",
                    "Column_3": "Distance",
                    "Column_4": "Speed"
                }, inplace=True)
# Reorder DataFrame Columns --------------------------------------------------------------
            column_order = [
            "Date", "Time", "Distance", "Speed", "Status"]
            df = df[column_order]    # Reorder DataFrame

# New column "data" for CMS_ID, Train_No & Loco No extraction------------------
            df.insert(df.columns.get_loc("Status") + 1, "data", "")

# Copy Column_1 data to 'data' for those rows who has Concatenated Value with Driver ID:-
            if not df.empty and "Date" in df and "data" in df:
                driver_rows = df["Date"].astype(str).str.contains("Driver ID:-", na=False, regex=True)
                df.loc[driver_rows, "data"] = df.loc[driver_rows, "Date"]
            if "data" not in df.columns:
                print("Error: data not found in extracted data.")
                return
            
# Extract Driver_ID, Train_No, Loco_No from the 'data' column============================================            
            import re
            def extract_driver_info(row):
                match = re.search(
                    r"Driver ID:-\s*([A-Za-z0-9 ]+)\s*Train No:-\s*([A-Za-z0-9 ]+)\s*Tr Load\(Ton\):-.*?Loco No:-\s*([A-Za-z0-9 ]+)\s*Wheel Dia",
                    str(row),
                    re.DOTALL)
                if match:
                    driver_id = match.group(1).replace(" ", "")
                    train_no = match.group(2).replace(" ", "")
                    loco_no = match.group(3).replace(" ", "")
                    return pd.Series([driver_id, train_no, loco_no])
                return pd.Series([None, None, None])
            df[["CMS_ID", "Train_No", "Loco_No"]] = df["data"].apply(extract_driver_info)

# Delete rows which don't contain "Driver" or "/20" in the 'Date' column----------------------------------
            if "Date" in df.columns:
                df = df[df["Date"].astype(str).str.contains("Driver|/20", na=False, regex=True)]
            
# Delete those rows where column Date == "Driver"----------------------------------------------------------
            if "Date" in df.columns:
                df = df[df["Date"].astype(str).str.strip() != "Driver"]

# Reorder DataFrame Columns with new Columns --------------------------------------------------------------
            column_order = [
            "Date", "Time", "Distance", "Speed","CMS_ID", "Train_No", "Loco_No", "Status"]
            df = df[column_order]    # Reorder DataFrame

# Filldown Logic for CMS_ID, Train_No & Loco_No based on Status Changes --------------------------------
            columns_to_fill = ["Train_No", "Loco_No", "CMS_ID"]
            change_rows = df.index[df["Status"].isin(["DRIVER ID CHANGED", "TRAIN NO. CHANGED"])].tolist()
            CHANGE_GAP_THRESHOLD = 10
            start_idx = 0
            last_change_row = None
            for change_row in change_rows:
                if last_change_row is not None and (change_row - last_change_row) < CHANGE_GAP_THRESHOLD:
                    continue
                df.loc[start_idx:change_row-1, columns_to_fill] = df.loc[start_idx:change_row-1, columns_to_fill].ffill()
                for col in columns_to_fill:
                    new_val_row = df.loc[change_row+1:, col].first_valid_index()
                    if new_val_row is not None:
                        new_val = df.loc[new_val_row, col]
                        df.loc[change_row:new_val_row, col] = new_val
                    else:
                        old_val = df.loc[change_row-1, col]
                        df.loc[change_row, col] = old_val

                start_idx = change_row + 1
                last_change_row = change_row
            df[columns_to_fill] = df[columns_to_fill].ffill()

#  Remove rows where Speed is empty, alphabetic, or mixed --------------------------------------------------------------
            df = df[df["Speed"].astype(str).str.match(r'^\d+(\.\d+)?$')]

# Trim white spaces from all string columns
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

# Convert certain columns to numeric format .................................................................................................
            numeric_columns = ['Speed', 'Distance', 'Loco_No']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')
            df = df.dropna(subset=["Speed", "Distance"])

# Remove Gaps in CMS ID-----------------------------
            df['CMS_ID'] = df['CMS_ID'].str.replace(' ', '', regex=False)  

# Function to clean and convert the text to time format ..........................................................................................
            def clean_and_convert_time(time_str):
                if not isinstance(time_str, str):
                    return None
                time_str = time_str.strip()
                match = re.match(r'^(\d{1,2}):(\d{1,2}):(\d{1,2})$', time_str)
                if match:
                    hour, minute, second = match.groups()
                    return f"{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
                return None
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
# Cum_Dist_Run based on the Start & Stop ...................................................................................
            df = df.dropna(subset=['Distance']) # Drop rows where 'Distance' is NaN
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
                idxs = (df.groupby(['Run_No', 'CMS_ID', 'Train_No'])['Rev_Dist'].apply(lambda x: (x - dist).abs().idxmin()))
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
            # Get the first index for each group where is_potential_bpt is True
            bpt_indices = is_potential_bpt[is_potential_bpt].groupby([df['CMS_ID'], df['Train_No']]).idxmax()
            if not bpt_indices.empty:
                df.loc[bpt_indices, 'BPT'] = 'BPT'
 
            df['Speed_shift'] = df['Speed'].shift(1)
            df.reset_index(drop=True, inplace=True)

# Add BPT_END Column ====================================================================================
            def get_bpt_end(df):
                df['BPT_END'] = ''
                for (cms_id, train_no), group in df.groupby(["CMS_ID", "Train_No"], sort=False):
                    group = group.reset_index()
                    bpt_idx = group[group['BPT'] == 'BPT'].index
                    if not bpt_idx.empty:
                        bpt_idx = bpt_idx[0]
                        for i in range(bpt_idx + 1, len(group)):
                            if pd.notna(group.loc[i, 'Speed']) and pd.notna(group.loc[i, 'Speed_shift']) and group.loc[i, 'Speed'] > group.loc[i, 'Speed_shift'] and 0 <= group.loc[i, 'Speed'] <= 40 and group.loc[i, 'Cum_Dist_LP'] < 10000:
                                end_idx = i - 1
                                if end_idx >= 0:
                                    df.loc[group.loc[end_idx, 'index'], 'BPT_END'] = 'BPT_END'
                                break
                return df
            df = get_bpt_end(df)
            df.drop(columns=['Speed_shift'], inplace=True)

# Add BFT_BPT Column ====================================================================================
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

# Map Crew Details -----------------------------------------------------------------------------------------
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
            
        # Final column selection===============================================================================
            df = df[["Date", "Time", "Speed", "Distance", "CMS_ID", "Train_No", "Loco_No", 
                    "Crew_Name", "Nom_CLI", "Desig", "BFT", "BFT_END", "BPT", "BPT_END", "BFT_BPT",
                    "Cum_Dist_Run", "Cum_Dist_LP", "Run_No", "Run_Sum", "Rev_Dist", "Pin_Point",
                    "Train_Type", "Over_Speed"]].copy()
            
            df_unique = df.drop_duplicates(subset=["CMS_ID","Train_No"], keep="first").reset_index(drop=True)
            st.write("### Unique CMS_ID Entries Found:")
            st.write(df_unique)
            st.info("Please Wait Creating Excel File.........")

# Remove illegal characters for Excel (openpyxl)-------------------------------------------------
            def remove_illegal_chars(val):
                if isinstance(val, str):
                    # Remove ASCII control characters except \t, \n, \r
                    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", val)
                return val
            df = df.map(remove_illegal_chars)

# Save to Excel-----------------------------------------------------------------------------------------
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='DataBase')
                log_action(df_unique)
                # import pages.auto_push_data as apd
                # apd.push_data(df)
            output.seek(0)
            st.sidebar.download_button(
                label="📥 Download Fabricated Excel",
                data=output,
                # file_name="test_telpro.xlsx",
                file_name=f"Telpro_{df['Loco_No'].dropna().iloc[0] if 'Loco_No' in df.columns and not df['Loco_No'].isnull().all() else 'Unknown'}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        # st.dataframe(df)

def main():
    Telpro()

if __name__ == "__main__":
    main()
