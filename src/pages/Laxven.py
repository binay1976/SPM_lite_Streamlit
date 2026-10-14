import streamlit as st
import pandas as pd
import re
import os,socket
import io


st.set_page_config(page_title="SPM App", page_icon="🚆", layout="wide")
st.title(":pencil: Laxven Text File Convertor")
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("🚫 🔐 You must login first.")
    st.header("🚫 🔐")
    st.switch_page("graph.py")
    st.stop()


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
gif_path = os.path.join(os.path.dirname(__file__), "Ver_3_2.ico")
st.sidebar.image(gif_path, width=200)

# Home button to go to design.py
if st.sidebar.button("🏠 Back to Home", key="home_btn"):
    st.switch_page("pages/design.py")



# Use columns to split the page vertically: left for upload, right for form
col_upload, col_form = st.columns(2)

with col_upload:
    uploaded_file = st.file_uploader("Upload File with Data of Required LP portion Only. ", type=["txt", "xlsx", "xls"])
    st.success("Upload Laxvan .txt Files and Fill the Form then Click Submit Button to Get Excel File")
    if 'form_submitted' in st.session_state and not uploaded_file:
        st.warning("Please upload a Laxven file before submitting the form.")

# with col_form:
    with st.form("laxven_form"):
        cms_id = st.text_input("CMS ID")
        train_no = st.text_input("Train No")
        loco_no = st.text_input("Loco No")
        submitted = st.form_submit_button("Submit")
        # Show warnings for mandatory fields
        if submitted:
            if not cms_id.strip():
                st.warning("CMS ID is required.")
            if not train_no.strip():
                st.warning("Train No is required.")
            if not loco_no.strip():
                st.warning("Loco No is required.")
with st.spinner("Processing file... Please wait ⏳"):
# Only process if both form is submitted, file is uploaded, and all fields are filled
    if (
        submitted and uploaded_file
        and cms_id.strip() and train_no.strip() and loco_no.strip()
    ):
        st.success(f"Submitted! CMS ID: {cms_id}, Train No: {train_no}, Loco No: {loco_no}")

        st.info("Processing uploaded Laxven Raw file (.txt/.xlsx/.xls)...")
        encodings_to_try = ['utf-8', 'latin-1', 'utf-16', 'windows-1252']
        df = None

        if uploaded_file.name.endswith('.txt'):
            from io import StringIO
            # Read the raw bytes once; re-reading uploaded_file in the loop below would
            # return empty content on later attempts since the stream position is consumed.
            raw_content = uploaded_file.read().replace(b'\x00', b'')  # Remove NUL bytes
            for encoding in encodings_to_try:
                try:
                    text = raw_content.decode(encoding, errors='ignore')
                    lines = text.splitlines()
                    # The Laxven header actually spans two lines: a column-name line
                    # (Time/Distance/Speed/EventGn) followed by a units line (Km/Km-hr/---).
                    # The number of metadata lines before it varies between exports, so
                    # locate the column-name line dynamically instead of a fixed skiprows.
                    header_idx = None
                    for i, line in enumerate(lines[:15]):
                        cells = [c.strip().lower() for c in line.split('\t')]
                        if 'speed' in cells and ('distance' in cells or 'km' in cells):
                            header_idx = i
                            break
                    if header_idx is None:
                        header_idx = 5  # fallback to previous fixed behaviour

                    sliced_text = '\n'.join(lines[header_idx:])
                    # Skip the units line (row right after the header) if present
                    skip_units = [1] if header_idx + 1 < len(lines) else None
                    candidate_df = pd.read_csv(
                        StringIO(sliced_text),
                        delimiter='\t',
                        engine='python',
                        skiprows=skip_units,
                        skip_blank_lines=True
                    )
                    # Basic validation
                    if candidate_df.shape[0] > 1 and candidate_df.shape[1] >= 3:
                        df = candidate_df
                        break
                except Exception as e:
                    st.warning(f"Failed with encoding {encoding}: {e}")
            else:
                st.error("Could not read the file with any encoding.")
                st.stop()
        else:
            try:
                df = pd.read_excel(uploaded_file)
                st.success("Text File successfully read as Excel format.")
            except Exception as e:
                st.error(f"Failed to read Excel file: {e}")

        # --- Handle missing or unknown column names as in Tsi PYQT code ---
        # If 'Km' column not found, try to infer it from the first column
        if df is not None:
            # Normalize column names (header cells have stray leading/trailing whitespace)
            df.columns = [str(c).strip() for c in df.columns]
            if df.columns[0].lower() not in ['km']:
                # Try to rename the first column to 'Km' if it looks like distance
                first_col = df.columns[0]
                # Check if the first column contains mostly numbers (distance)
                if pd.api.types.is_numeric_dtype(df[first_col]) or df[first_col].astype(str).str.replace('.', '', 1).str.isdigit().mean() > 0.5:
                    df.rename(columns={first_col: 'Km'}, inplace=True)
                else:
                    # Try to find a column that looks like distance (e.g. Laxven's 'Distance' column holds Km readings)
                    for col in df.columns:
                        if col.lower() in ['km', 'distance', 'dist']:
                            df.rename(columns={col: 'Km'}, inplace=True)
                            break

        # Now proceed as before, but only if 'Km' column exists
        if df is not None and 'Km' in df.columns:
            df['Km'] = pd.to_numeric(df['Km'], errors='coerce')
            df['Distance'] = df['Km'].diff() * 1000
            df.loc[df.index[0], 'Distance'] = 0
            df['Distance'] = df['Distance'].round(2)
        else:
            cols = list(df.columns) if df is not None else []
            st.error(f"Could not find a 'Km' column in the uploaded file. Detected columns: {cols}. Please check your file format.")
            st.stop()

        # Step 3: Drop 'Km' and '---' columns if they exist
        columns_to_drop = ['Km', '---']
        df.drop(columns=[col for col in columns_to_drop if col in df.columns], inplace=True)

        try:
            first_col = df.columns[0]
            datetime_split = df[first_col].astype(str).str.strip().str.split(' ', n=1, expand=True)
            if datetime_split.shape[1] < 2:
                st.error(f"Could not split '{first_col}' into Date and Time. Sample values: {df[first_col].head(3).tolist()}")
                st.stop()
            # Drop the raw column before assigning Date/Time in case it was already named 'Time'
            df.drop(columns=[first_col], inplace=True)
            df['Date'] = datetime_split[0]
            df['Time'] = datetime_split[1]

        except Exception as e:
            st.error(f"Failed to split date and time: {e}")
            st.stop()

        # Adding new columns with blank data
        df['CMS_ID'] = [cms_id] * len(df)
        df['Loco_No'] = [loco_no] * len(df)
        df['Train_No'] = [train_no] * len(df)
        
        df.rename(columns={'Km/hr': 'Speed'}, inplace=True)
        # Rearrange columns as "Date, Time, Speed, Distance, Train_No"...........
        df = df[["Date", "Time", "Speed", "Distance", "CMS_ID", "Train_No", "Loco_No"]]

        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    # Convert certain columns to numeric format .................................................................................................
        numeric_columns = ['Speed', 'Distance', 'Loco_No']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')
        # Drop rows where "Speed" or "Distance" is NaN (non-numeric values)
        df = df.dropna(subset=["Speed", "Distance"])

    # Convert Date format .................................................................................................................
        try:
            df["Date"] = df["Date"].astype(str).str.strip().str.strip("'").str.strip()
            df["Date"] = pd.to_datetime(df["Date"], format="%d/%m/%y", errors="coerce")
            df["Date"] = df["Date"].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else '')
        except Exception as e:
            st.warning(f"⚠️ Failed to clean and convert date format: {e}")
            
    # Function to clean and convert the text to time format ..........................................................................................
        def clean_and_convert_time(time_str):
            time_str = time_str.strip()
            match = re.match(r'^(\d+):(\d+):(\d+)$', time_str)
            if match:
                hour, minute, second = match.groups()
                return f"{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}"
            else:
                return None
        df['Time'] = df['Time'].apply(clean_and_convert_time)

# Stop Long term file Uploading--------------------------------------------------
        # Check the average time interval in the first 20 rows to detect long-term files
        df_sample = df.head(20).copy()
        df_sample['Time'] = pd.to_datetime(df_sample['Time'], format='%H:%M:%S', errors='coerce')
        df_sample.dropna(subset=['Time'], inplace=True)
        
        time_diffs = df_sample['Time'].diff().dt.total_seconds().dropna()
        # Use median instead of mean to be robust against single large outliers
        median_diff = time_diffs.median() if not time_diffs.empty else 0

        if median_diff > 5: # If median interval is > 5s, it's likely a long-term file
            st.error("Invalid File!!! Upload Only Short-term Raw Files")
            st.stop()


    # Cumulate the value of 'Distance' based on the Start & Stop .................................................................................
        # Convert 'Distance' column to numeric, coercing errors to NaN
        df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
        df = df.dropna(subset=['Distance'])
        df['Cum_Dist_Run'] = df.groupby(df['Speed'].eq(0).cumsum())['Distance'].cumsum()

    # Create a new column 'Run_No' based on the conditions ...................................................................................
        df['Run_No'] = 1  
        cms_change = df['CMS_ID'] != df['CMS_ID'].shift()
        distance_reset = df['Cum_Dist_Run'] < df['Cum_Dist_Run'].shift()
        group = cms_change.cumsum()
        df['Run_No'] = distance_reset.groupby(group).cumsum() + 1

    # Cumulate the value of 'Distance' based on the Start & Stop .................................................................................
        df['Cum_Dist_Run'] = df.groupby(df['Speed'].eq(0).cumsum())['Distance'].cumsum()

    # Cumulate the value of 'Distance' based on the LP .................................................................................
        if {'Speed', 'CMS_ID', 'Distance'}.issubset(df.columns):
            df['Cum_Dist_LP'] = df.groupby('CMS_ID')['Distance'].cumsum()

    # Insert a new column 'Run_Sum' with the sum of 'Distance' per 'Run_No' ....................................................................
        df['Run_Sum'] = df.groupby(['Run_No','CMS_ID'])['Distance'].transform('sum')

    # Deduct values from 'Run_Sum' to 'Distance' column ........................................................................................
        df['Rev_Dist'] = df['Run_Sum'] - df['Cum_Dist_Run']

    # Create a new column 'Pin_Point' with value "10 Meters" for the rows closest to 10 in each 'Run_No' group .........................................................
        df['Pin_Point'] = ''
        for dist, label in [(10, '10 Meters'), (250, '250 Meters'), (500, '500 Meters'), (1000, '1000 Meters')]:
            idxs = (
                df.groupby(['Run_No', 'CMS_ID'])['Rev_Dist']
                .apply(lambda x: (x - dist).abs().idxmin())
            )
            df.loc[idxs.values, 'Pin_Point'] = label
    # Add BFT Column ......................................................................................................................
        if "BFT" not in df.columns: df["BFT"] = ""
        if "BFT_END" not in df.columns: df["BFT_END"] = ""

        # Clear any existing marks for a clean run
        df["BFT"] = ""
        df["BFT_END"] = ""

        for cms_id, group in df.groupby("CMS_ID", sort=False):
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
# BPT detection=======================================================================
        s = df['Speed']
        is_potential_bpt = (
            (df['Cum_Dist_LP'] < 10000) &
            (s >= 40) & (s <= 70) &
            (s > s.shift(-1)) &
            (s.shift(-1) >= s.shift(-2)) &
            (s.shift(-2) >= s.shift(-3)) &
            (s.shift(-3) >= s.shift(-4)) &
            (s.shift(-4) >= s.shift(-5)) &
            (s.shift(-5) >= s.shift(-6))
        )
        df['BPT'] = ''
        df.loc[is_potential_bpt.groupby(df['CMS_ID']).idxmax(), 'BPT'] = 'BPT'

        df['Speed_shift'] = df['Speed'].shift(1)
        df.reset_index(drop=True, inplace=True)

# BPT_END detection ===========================================================================
        def get_bpt_end(df):
            df['BPT_END'] = ''
            for cms_id, group in df.groupby('CMS_ID'):
                group = group.reset_index()
                bpt_idx = group[group['BPT'] == 'BPT'].index
                if not bpt_idx.empty:
                    bpt_idx = bpt_idx[0]
                    for i in range(bpt_idx + 1, len(group)):
                        if (group.loc[i, 'Speed'] > group.loc[i, 'Speed_shift'] and 
                            0 <= group.loc[i, 'Speed'] <= 40 and 
                            group.loc[i, 'Cum_Dist_LP'] < 10000):
                            end_idx = i - 1
                            if end_idx >= 0:
                                df.loc[group.loc[end_idx, 'index'], 'BPT_END'] = 'BPT_END'
                            break
            return df
        df = get_bpt_end(df)
        df.drop(columns=['Speed_shift'], inplace=True)

    # Adding a new column 'BFT_BPT' ............................................................................................................................
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

    # Rearrange the Columns
        df = df[["Date", "Time", "Speed", "Distance", "CMS_ID", "Train_No", "Loco_No", "Crew_Name","Nom_CLI","Desig","BFT","BFT_END","BPT","BPT_END","BFT_BPT",
                    "Cum_Dist_Run","Cum_Dist_LP","Run_No","Run_Sum","Rev_Dist","Pin_Point"]]
        
        df_unique = df.drop_duplicates(subset=["CMS_ID"], keep="first").reset_index(drop=True)
        st.write("### Unique CMS_ID Entries Found:")
        st.write(df_unique)
        st.success("Download Excel From Sidebar")

        # Save to Excel
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
            file_name=f"Laxvan_{df['Loco_No'].dropna().iloc[0] if 'Loco_No' in df.columns and not df['Loco_No'].isnull().all() else 'Unknown'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # st.dataframe(df)