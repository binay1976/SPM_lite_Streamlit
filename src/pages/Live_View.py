import streamlit as st
import plotly.express as px
import plotly.io as pio
pio.renderers.default = "browser"
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader
import os, socket
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pytz
import numpy as np



st.set_page_config(page_title="SPM App", page_icon="🚆", layout="wide")
# Session/authentication check
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

# function for Live View Report Button-1............................................................................................
def Live_view(df, selected_cms_ids):
    filtered_df = df[df["CMS_ID"].isin(selected_cms_ids)].copy()  # <-- Add .copy() here to avoid SettingWithCopyWarning
    st.sidebar.info("Total Rows for this ID :  " + str(len(filtered_df)))
    
    st.markdown('<style>div.block-container{padding-top: 1rem;}</style>', unsafe_allow_html=True)
    page_option = st.sidebar.radio('Navigate',options=['Plot View','Statical View'])

    if page_option == 'Plot View':
        # st.header(":bar_chart: LP Driving Skill Analysis")
# Creating Top Cards..................................................................................................
        tr_no = (filtered_df["Train_No"].min())
        cms_id = (filtered_df["CMS_ID"].min())
        loco = (filtered_df["Loco_No"].min())
        end_time = (filtered_df["Time"].max())
        Dist_km = (filtered_df["Cum_Dist_LP"]/1000)
        speed = (filtered_df["Speed"].max())
        total_km = (filtered_df["Distance"].sum()/1000)
        drive_date = (filtered_df["Date"].min())
        start_time = (filtered_df["Time"].min())
        end_time = (filtered_df["Time"].max())
        speed = (filtered_df["Speed"].max())
        desig1 = filtered_df["Desig"].unique()
        desig= desig1[0]
        lp_name1 = filtered_df["Crew_Name"].unique()
        lp_name= f"{lp_name1[0]}-{desig1[0]}"
        cli_name1 = filtered_df["Nom_CLI"].unique()
        cli_name = cli_name1[0]
        # st.sidebar.success(f"Selected LP CMS ID : : {cms_id}", icon= "🚨")
        st.markdown('-----')
        col1,col2,col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">CMS ID- {cms_id}</h4>',
            unsafe_allow_html=True)
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Distance - {total_km} KM</h4>',
            unsafe_allow_html=True)
        with col2:
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Tr. No- {tr_no}</h4>',
            unsafe_allow_html=True)
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Date- {drive_date}</h4>',
            unsafe_allow_html=True)
        with col3:
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Loco_No.- {loco}</h4>',
            unsafe_allow_html=True)
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Start Time- {start_time}</h4>',
            unsafe_allow_html=True)
        with col4:
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Name- {lp_name}</h4>',
            unsafe_allow_html=True)
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">End Time- {end_time}</h4>',
                    unsafe_allow_html=True)
        with col5:
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Nom. CLI- {cli_name}</h4>',
            unsafe_allow_html=True)
            st.markdown(
            f'<h4 style="font-size: 18px; color: #053A8C;">Top Speed- {speed}</h4>',
            unsafe_allow_html=True)

# Show Exceptions of Data--------------------------------------------------------------------------------------------------
        def process_bft_bpt(df):
            if "BFT_BPT" not in df.columns or "CMS_ID" not in df.columns or df.empty:
                return pd.DataFrame()

            # 🔹 Skip processing only where CMS_ID is NULL
            df.dropna(subset=["CMS_ID"], inplace=True) # Drops rows with NULL CMS_ID
            df = df.copy() # Create a copy to avoid SettingWithCopyWarning
            if df.empty:
                return pd.DataFrame()

            # Normalize text to uppercase for consistent matching
            df["BFT_BPT"] = df["BFT_BPT"].astype(str).str.upper()

            # Combine all BFT_BPT texts per group
            text_joined = (
                df.groupby(["CMS_ID", "Loco_No", "Train_No"])["BFT_BPT"]
                .apply(lambda x: " ".join(x))
                .reset_index()
            )
            # Define conditions
            def detect_issue(txt):
                if "BFT NOT DONE" in txt:
                    return "Crossed BFT Limit"
                if "BFT" not in txt and "BFT_END" not in txt:
                    return "No BFT"
                if "BFT" in txt and "BFT_END" not in txt:
                    return "Improper BFT"
                if "BPT" not in txt and "BPT_END" not in txt:
                    return "No BPT"
                if "BPT" in txt and "BPT_END" not in txt:
                    return "Improper BPT"
                return ""

            # Apply detection
            text_joined["Exception"] = text_joined["BFT_BPT"].apply(detect_issue)
            text_joined = text_joined[text_joined["Exception"] != ""]

            # Merge exception with original df (keep first row only per group)
            merged = (
                df.merge(text_joined, on=["CMS_ID", "Loco_No", "Train_No"], how="inner")
                .groupby(["CMS_ID", "Loco_No", "Train_No"], as_index=False)
                .first()
            )
            return merged

        bft_bpt_df = process_bft_bpt(df)
        if not bft_bpt_df.empty:
            st.error("⚠️ BFT/BPT Exceptions Found!")

            for _, row in bft_bpt_df.iterrows():
                st.write(
                    f"CMS ID: {row['CMS_ID']} | "
                    f"Loco No: {row['Loco_No']} | "
                    f"Train No: {row['Train_No']} | "
                    f"Exception: {row['Exception']}"
                )
        else:
            st.success("✅ All OK — No BFT/BPT Exceptions Found.")

# Over Speed Detection & Exceptions-----------------------------------------------------------------------------------
        def process_overspeed(df):
            if "Over_Speed" not in df.columns: return pd.DataFrame()
            df["Speed"] = pd.to_numeric(df["Speed"], errors="coerce")
            df["is_overspeed"] = df["Over_Speed"].astype(str).str.contains("Over Speed", na=False)
            blocks = df[df["is_overspeed"]].copy()
            if blocks.empty: return pd.DataFrame()
            blocks["block"] = (blocks["is_overspeed"] != blocks["is_overspeed"].shift()).cumsum()
            idx = blocks.groupby("block")["Speed"].idxmax()
            res = blocks.loc[idx].copy()
            res["Exception"] = res["Over_Speed"]
            return res

        over_speed_df = process_overspeed(df)
        if not over_speed_df.empty:
            st.error("⚠️ Over Speed Exceptions Found!")

            for _, row in over_speed_df.iterrows():
                st.write(
                    f"CMS ID: {row['CMS_ID']} | "
                    f"Loco No: {row['Loco_No']} | "
                    f"Train No: {row['Train_No']} | "
                    f"Exception: {row['Exception']}"
                )
        else:
            st.success("✅ All OK — No Over Speeding Found.")
# Speed at 10M & 250M Exceptions ------------------------------------------------------------------------------------------
        def process_before_10m(df):
            if df.empty or "Pin_Point" not in df.columns or "Speed" not in df.columns:
                return pd.DataFrame()

            df["Speed"] = pd.to_numeric(df["Speed"], errors="coerce")

            very_risky_speed = 10
            risky_speed = 7

            results = []
            group_cols = ["CMS_ID", "Loco_No", "Train_No" , "Date", "Time", "Speed"]

            for keys, group in df.groupby(group_cols, dropna=False):
                subset = group[group["Pin_Point"] == "10 Meters"].copy()

                if subset.empty:
                    continue

                subset["Exception"] = subset["Speed"].apply(
                    lambda s: (
                        f"Before 10m >{very_risky_speed * 2} (Too High Value)"
                        if s > very_risky_speed * 2
                        else (
                            f"Before 10m >{very_risky_speed} (Suspected Very Risky)"
                            if s > very_risky_speed
                            else (
                                f"Before 10m >{risky_speed} (Suspected Risky)"
                                if s > risky_speed
                                else ""
                            )
                        )
                    )
                )

                subset = subset[subset["Exception"] != ""]

                if not subset.empty:
                    results.append(subset)

            return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

        before_10m_df = process_before_10m(df)
        if not before_10m_df.empty:
            st.error(f"⚠️ Before 10m, Total- {len(before_10m_df)} Suspected Risky Speed Exceptions Found!")

            for _, row in before_10m_df.iterrows():
                st.write(
                    f"CMS ID: {row['CMS_ID']} | "
                    f"Loco No: {row['Loco_No']} | "
                    f"Train No: {row['Train_No']} | "
                    f"Date: {row['Date']} | "
                    f"Time: {row['Time']} | "
                    f"Speed: {row['Speed']} | " 
                    f"Exception: {row['Exception']}"
                )
        else:
            st.success("✅ All OK — No 10M Before Over-Speeding Found.")


        def process_before_250m(df):
            if df.empty or "Pin_Point" not in df.columns or "Speed" not in df.columns:
                return pd.DataFrame()
            df["Speed"] = pd.to_numeric(df["Speed"], errors="coerce")

            # Convert rules dataframe to dictionary
            very_risky_250 = 35
            risky_250= 30

            results = []
            group_cols = ["CMS_ID", "Loco_No", "Train_No" , "Date", "Time", "Speed"]
            for keys, group in df.groupby(group_cols, dropna=False):
                subset = group[group["Pin_Point"] == "250 Meters"].copy()
                if subset.empty:
                    continue
                subset["Exception"] = subset["Speed"].apply(
                    lambda s: f"Before 250m >{very_risky_250*2} (Too High Value)" if s > very_risky_250 * 2
                    else (
                        f"Before 250m >{very_risky_250} (Suspected Very Risky)" if s > very_risky_250
                        else (
                            f"Before 250m >{risky_250} (Suspected Risky)" if s > risky_250
                            else ""
                        )
                    )
                )
                subset = subset[subset["Exception"] != ""]
                if not subset.empty:
                    results.append(subset)
            return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

        before_250m_df = process_before_250m(df)
        if not before_250m_df.empty:
            st.error(f"⚠️ Before 250m, Total- {len(before_250m_df)} Suspected Risky Speed Exceptions Found!")

            for _, row in before_250m_df.iterrows():
                st.write(
                    f"CMS ID: {row['CMS_ID']} | "
                    f"Loco No: {row['Loco_No']} | "
                    f"Train No: {row['Train_No']} | "
                    f"Date: {row['Date']} | "
                    f"Time: {row['Time']} | "
                    f"Speed: {row['Speed']} | "
                    f"Exception: {row['Exception']}"
                )
        else:
            st.success("✅ All OK — No 250M Before Over-Speeding Found.")

# Creating Side Bar Contents...............................................................................................
        st.markdown('----') # Creating Partition Line .....................................................................
        # Total Stop Count Text Line ...................................................................................................
        total_run = filtered_df['Run_No'].nunique()
        st.markdown(
        f'<h3 style="font-size: 18px; color: #c402c7;">Total {total_run} times Train Stopped by LP</h3>',
        unsafe_allow_html=True)

# BAR Graph for MAx Speed in Each Halt ............................................................................................
        max_speed = filtered_df.groupby(['Run_No', 'CMS_ID'])['Speed'].max().reset_index()
        max_speed_index = max_speed['Speed'].idxmax()
        fig = px.bar(max_speed, x="Run_No", y="Speed", text="Speed")
        bar_colors = ['#05B7B7'] * len(max_speed)
        bar_colors[max_speed_index] = '#854c03'
        fig.update_traces(marker_color=bar_colors)
        fig.update_layout(
            title="Top Speed Between Each Halt",
            xaxis_title="Halt Count",
            yaxis_title="Speed"
        )
        fig.update_xaxes(type='category')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('-------')

# Display the area chart within a specific Time And Speed ................................................................... 
        # X-Axis Change Dropdown
        mps = ['50','55','60','65','70','75','80','85','90','95','100','105','110','120','130']
        mps_filter = st.selectbox('Select MPS of Train:', mps)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=filtered_df["Time"],
            y=filtered_df["Speed"],
            mode='lines',
            fill='tozeroy',  # Set fill to 'tozeroy' for area chart
            line=dict(color='black', width=1),  # Reduced line thickness here
            fillcolor="#B0B9BD",
        ))
        fig.add_shape(
            type='line',
            x0=filtered_df["Time"].min(),  # Start x-coordinate of the line (time at the beginning)
            x1=filtered_df["Time"].max(),  # End x-coordinate of the line (time at the end)
            y0=mps_filter,  # y-coordinate of the line (speed of 60)
            y1=mps_filter,  # y-coordinate of the line (speed of 60)
            line=dict(color='red', dash='dash'),  # Customize the appearance of the line
        )
        fig.update_layout(
            title='Speed Variation over Time Line',
            xaxis=dict(title='Time'),
            yaxis=dict(title='Speed')
        )
        top_speed = filtered_df["Speed"].max()
        fig.add_annotation(y=top_speed, x=filtered_df.loc[filtered_df["Speed"] == top_speed, 'Time'].iloc[0],
                        text="Top Speed", showarrow=True, arrowhead=5, arrowcolor='Red')
        st.plotly_chart(fig, use_container_width=True)


# Area Chart Beteewn Distance & Speed .......................................................................................
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=filtered_df["Cum_Dist_LP"],
            y=filtered_df["Speed"],
            mode='lines',
            fill='tozeroy',  # Set fill to 'tozeroy' for area chart
            line=dict(color='black', width=1),
            fillcolor="#FBDE80",
        ))
        fig.add_shape(
            type='line',
            x0=filtered_df["Cum_Dist_LP"].min(),  # Start x-coordinate of the line (time at the beginning)
            x1=filtered_df["Cum_Dist_LP"].max(),  # End x-coordinate of the line (time at the end)
            y0=mps_filter,  # y-coordinate of the line (speed of 60)
            y1=mps_filter,  # y-coordinate of the line (speed of 60)
            line=dict(color='red', dash='dash'),  # Customize the appearance of the line
        )
        fig.update_layout(
            title='Speed Variation over Distance Travelled',
            xaxis=dict(title='Distance Travelled'),
            yaxis=dict(title='Speed')
        )
        top_speed = filtered_df["Speed"].max()
        fig.add_annotation(y=top_speed, x=filtered_df.loc[filtered_df["Speed"] == top_speed, 'Cum_Dist_LP'].iloc[0],
                        text="Top Speed", showarrow=True, arrowhead=5, arrowcolor='Red')
        st.plotly_chart(fig, use_container_width=True)
# BFT/BPT with Pointer........................................................................................................
        data_base = filtered_df.loc[filtered_df['Cum_Dist_LP'] < 5500]
        bft = data_base.loc[data_base['BFT_BPT'] == "BFT"]
        bpt = data_base.loc[data_base['BFT_BPT'] == "BPT"]

        Dist_points1 = []  # Specify the x-axis points where you want to display the values
        bft_points = bft.index.tolist()  # Get the indices of rows where BFT is present
        bpt_points = bpt.index.tolist()  # Get the indices of rows where BPT is present

        Dist_points1.extend(bft_points)  # Extend the Dist_points1 list with BFT indices
        Dist_points1.extend(bpt_points)  # Extend the Dist_points1 list with BPT indices

        text_values = ['BFT Done'] * len(bft_points) + ['BPT Done'] * len(bpt_points)
        fig = px.line(data_base, x="Time", y="Speed", color_discrete_sequence=["#05B7B7"])
        for i, tp in enumerate(Dist_points1):
            selected_data = data_base.loc[data_base.index == tp]
            if len(selected_data) > 0:
                fig.add_annotation(x=selected_data['Time'].iloc[0], y=selected_data['Speed'].iloc[0], text=text_values[i],
                                    showarrow=True, arrowhead=5, arrowcolor='red')
        fig.update_layout(
            title="Brake Feel & Brake Power Test (In First Section)",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Speed")
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
# Run Number Table ...............................................................................
        st.markdown('<h4 style="font-size: 18px; color: green;">Speed at Various Points Before 1000 Meters of Dead Stop</h4>', unsafe_allow_html=True)
        st.write("For optimal braking safety, the train's speed should be below 30 km/h before reaching the 250-meter, and it must reduce to below 8 km/h before the 10-meter of Dead Stop.")
        filtered_df2 = filtered_df[filtered_df['Pin_Point'].isin(["1000 Meters", "500 Meters", "250 Meters", "10 Meters"])]

        # Create pivot table as before
        pivot_table = pd.pivot_table(
            filtered_df2, values='Speed', index=['Run_No'], columns='Pin_Point'
        )
        pivot_table = pivot_table[['1000 Meters', '500 Meters', '250 Meters', '10 Meters']]
        pivot_table = pivot_table.fillna(0).astype(int)
        transposed = pivot_table.transpose().reset_index()
        transposed.columns.name = None  # Remove the column grouping label
        transposed = transposed.rename(columns={'index': 'Pin_Point'})
        transposed_limited = transposed.head(4)
        def color_cells(row):
            styles = [''] * len(row)  # default styles for the row

            if "10 Meters" in str(row.iloc[0]):
                for i, val in enumerate(row):
                    if i == 0:
                        continue  # skip first column
                    if isinstance(val, (int, float)):
                        if val > 8:
                            styles[i] = 'background-color: #F58F7A'
                        elif val > 6:
                            styles[i] = 'background-color: #DBC702'

            elif "250 Meters" in str(row.iloc[0]):
                for i, val in enumerate(row):
                    if i == 0:
                        continue  # skip first column
                    if isinstance(val, (int, float)) and val > 30:
                        styles[i] = 'background-color: #F58F7A'
            return styles
        styled = transposed_limited.style.apply(color_cells, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
 # Drop Down for Run Number to change Halting Speed  ...............................................................................................
        st.subheader("Train Deceleration Analysis (Braking Pattern)")
        # Step 1: Find Run_Nos where Speed at "10 Meters" is >= 10
        valid_run_nos = (
            filtered_df[(filtered_df["Pin_Point"] == "250 Meters") & (filtered_df["Speed"] >= 10)]
            ["Run_No"]
            .unique()
        )
        Run_Filter = st.selectbox('Select Run Number :', valid_run_nos)
        selection_run = filtered_df[filtered_df["Run_No"] == Run_Filter]

# Text For Pin Point Locations...................................................................................................
        mtr_1000 = selection_run.loc[selection_run['Pin_Point'] == "1000 Meters"]
        speed_1000 = (mtr_1000["Speed"].min())
        rev_dist_1000 = (mtr_1000["Rev_Dist"].min())

        mtr_500 = selection_run.loc[selection_run['Pin_Point'] == "500 Meters"]
        speed_500 = (mtr_500["Speed"].min())
        rev_dist_500 = (mtr_500["Rev_Dist"].min())

        mtr_250 = selection_run.loc[selection_run['Pin_Point'] == "250 Meters"]
        speed_250 = (mtr_250["Speed"].min())
        rev_dist_250 = (mtr_250["Rev_Dist"].min())

        mtr_10 = selection_run.loc[selection_run['Pin_Point'] == "10 Meters"]
        speed_10 = (mtr_10["Speed"].min())
        rev_dist_10 = (mtr_10["Rev_Dist"].min())


        col1,col2,col3, col4 = st.columns(4)
        with col1:
            st.markdown(
            f'<h5 style="font-size: 18px; color: #D30DF4 ;">Speed at 1000 meter:- {speed_1000}</h5>',
            unsafe_allow_html=True)
        with col2:
            st.markdown(
            f'<h5 style="font-size: 18px; color: #D30DF4 ;">At 500 meter:- {speed_500}</h5>',
            unsafe_allow_html=True)
        with col3:
            st.markdown(
            f'<h5 style="font-size: 18px; color: #D30DF4 ;">At 250 meter:- {speed_250}</h5>',
            unsafe_allow_html=True)
        with col4:
            st.markdown(
            f'<h5 style="font-size: 18px; color: #D30DF4 ;">At 10 meter:- {speed_10}</h5>',
            unsafe_allow_html=True)
# Train Deceleration Graph ........................................................................................................
        try:
            selection_run["DATETIME"] = pd.to_datetime(selection_run["Date"] + " " + selection_run["Time"].astype(str))
        except Exception as e:
            st.error(f"Error parsing DATE and TIME columns: {e}")
            st.stop()
        selection_run.sort_values("DATETIME", inplace=True)
        selection_run.reset_index(drop=True, inplace=True)
        marker_rows = selection_run[selection_run["Pin_Point"] == "1000 Meters"]
        if marker_rows.empty:
            st.error("Not Travelled '1000 Meters' from Last Stop")
            st.stop()
        start_idx = marker_rows.index[0]
        v_start_kmh = selection_run.loc[start_idx, "Speed"]
        v_start = v_start_kmh * 1000 / 3600  # Convert km/h to m/s
        t_start = selection_run.loc[start_idx, "DATETIME"]
        after_marker = selection_run.loc[start_idx:]
        stop_idx = after_marker["Speed"].idxmin()
        if stop_idx + 1 in selection_run.index:
            stop_row = selection_run.loc[stop_idx + 1]
        else:
            stop_row = selection_run.loc[stop_idx].copy()
            stop_row["DATETIME"] += pd.Timedelta(seconds=1)
            stop_row["Speed"] = 0.0

        t_end = stop_row["DATETIME"]
        v_end = stop_row["Speed"] * 1000 / 3600
        time_elapsed = (t_end - t_start).total_seconds()
        deceleration = (v_start - v_end) / time_elapsed if time_elapsed > 0 else None

        # Extract CMS_ID for display
        stop_point_idx = stop_idx - 1 if stop_idx > 0 else stop_idx
        cms_id = selection_run.loc[stop_point_idx, "CMS_ID"]

        # Display summary
        st.markdown('<h4 style="font-size: 18px; color: green;">Selected Run Details</h4>', unsafe_allow_html=True)
        st.markdown(f"""
        **📍 Speed Before 1000 meters:** {v_start:.2f} m/s ({v_start_kmh:.2f} km/h)  **⏰ Duration to Stop:** {time_elapsed:.0f} sec  **🕒 Start Time:** {t_start}  **🕔 End Time:** {t_end}
        """)
        graph_segment = selection_run.loc[start_idx:stop_idx].copy()
        graph_segment.loc[graph_segment["Speed"] == 0, "Rev_Dist"] = 0
        graph_segment["Rev_Dist"] = pd.to_numeric(graph_segment["Rev_Dist"], errors="coerce")
        graph_segment.sort_values("DATETIME", inplace=True)
        graph_segment.reset_index(drop=True, inplace=True)
        # --- Reference Deceleration Calculation ---
        u = v_start  # m/s
        s = 1000
        a = -(u**2) / (2 * s)
        # t_total = -u / a  # Removed unused variable

        # Print Reference Average Deceleration
        st.markdown(f"""
        **📍 Standard Deceleration:** {a:.4f} m/s²  **👨‍✈️ Actual Deceleration:** {deceleration:.4f} m/s²
        """)
# Time-based reference data..............................................................
        rev_dist_ref = np.linspace(1000, 0, 100)
        speed_rev_ref = np.sqrt(np.maximum(u**2 + 2 * a * (1000 - rev_dist_ref), 0))
        speed_rev_ref_kmph = speed_rev_ref * 3.6

        # Define important Rev_Dist markers (already created above)
        Dist_points = [rev_dist_1000, rev_dist_500, rev_dist_250, rev_dist_10]
        text_values = ['1000 M', '500 M', '250 M', '10 M']

# --- Graph 1: REV_DIST vs SPEED -------------------------------------------------------------------------
        graph_segment.loc[graph_segment["Speed"] == 0, "Rev_Dist"] = 0
        fig_dist = go.Figure()

        fig_dist.add_trace(go.Scatter(
            x=graph_segment["Rev_Dist"],
            y=graph_segment["Speed"],
            name="Real Train Speed",
            mode="lines",
            line=dict(color="green"),
            customdata=graph_segment["DATETIME"].dt.strftime("%d-%m-%y %H:%M:%S"),
            hovertemplate="Remaining_Dist: %{x:.0f} m<br>Speed: %{y:.0f} km/h<br>Time: %{customdata}<extra></extra>"
        ))
        # Add Ideal Deceleration line
        u = v_start  # m/s
        a = -(u**2) / (2 * 1000)
        s_vals = 1000 - rev_dist_ref
        t_ref_dist = (-u + np.sqrt(u**2 - 2*a*(-s_vals))) / a
        t_ref_dist = np.nan_to_num(t_ref_dist, nan=0, posinf=0, neginf=0)
        # Format as seconds from t_start, then format as string
        time_ref_dist = [
            (t_start + pd.Timedelta(seconds=float(t))).strftime("%d-%m-%y %H:%M:%S")
            for t in t_ref_dist
        ]

        fig_dist.add_trace(go.Scatter(
            x=rev_dist_ref,
            y=speed_rev_ref_kmph,
            name="Ideal Deceleration",
            line=dict(color="red", dash="dot", width=4),
            customdata=time_ref_dist,
            hovertemplate="<span style='color:red'>Remaining_Dist: %{x:.0f} m<br>Speed: %{y:.0f} km/h<br>Time: %{customdata}</span><extra></extra>"
        ))
        # Add Red Dotted Vertical Lines with Labels
        for i, tp in enumerate(Dist_points):
            fig_dist.add_vline(
                x=tp,
                line=dict(color="blue", width=2, dash="dot"),
                annotation_text=text_values[i],
                annotation_position="top",
                annotation_font=dict(color="Blue",size=12)
            )

        fig_dist.update_layout(
            title="Deceleration with Remaining Distance (with Ideal Deceleration)",
            xaxis_title="Remaining Distance (m)",
            yaxis_title="Speed (km/h)",
            legend=dict(x=0, y=1.1, orientation="h"),
            height=500,
            xaxis=dict(autorange='reversed')
        )

        st.plotly_chart(fig_dist, use_container_width=True)
 # --- Declaration List for Risky Points -----------------------------------------------------------------------------
        st.markdown("---")
        if st.checkbox("Show Detailed Excess Speeding While Stopping ✅ "):
            interp_std_speed = np.interp(
                graph_segment["Rev_Dist"].values,
                rev_dist_ref[::-1],
                speed_rev_ref_kmph[::-1]
            )
            # Condition: Actual Speed > Standard Speed by 10%
            mask = graph_segment["Speed"] > (interp_std_speed * 1.10)

            filtered_table = pd.DataFrame({
                "Distance (m)": graph_segment.loc[mask, "Rev_Dist"].round(2),
                "Actual Speed (km/h)": graph_segment.loc[mask, "Speed"].round(2),
                "Standard Speed (km/h)": interp_std_speed[mask].round(2),
                "Difference (km/h)": (graph_segment.loc[mask, "Speed"] - interp_std_speed[mask]).round(2)
            })
            risky_mask = (filtered_table["Difference (km/h)"] > (filtered_table["Standard Speed (km/h)"] * 0.10))
            risky_points = filtered_table[risky_mask]

            st.markdown(f'<h4 style="font-size: 18px; color: #D30DF4 ;">Points Where Actual Speed > 10% of Standard Speed</h4>',unsafe_allow_html=True)
            if not risky_points.empty:
                for idx, row in risky_points.iterrows():
                    st.markdown(
                        f"""
                        <div style='font-size:14px; line-height:1.2; margin-bottom:4px'>
                            📍<b>{row['Distance (m)']} m Before Stop</b>, 
                                |||| Actual Speed: <b>{row['Actual Speed (km/h)']} km/h</b>, 
                                |||| Standard Speed: <b>{row['Standard Speed (km/h)']} km/h</b>, 
                                |||| Overspeed : <b>{row['Difference (km/h)']} km/h</b>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.info("No risky points detected where speed exceeds standard by more than 10%.")

        st.markdown("---")
# All Run Graph after Distance < 1200 (With Average Line)
        pin_point_all = filtered_df[filtered_df['Rev_Dist'] < 1200]

        # Define important Rev_Dist markers
        Dist_points = [rev_dist_1000, rev_dist_500, rev_dist_250, rev_dist_10]
        text_values = ['1000 M', '500 M', '250 M', '10 M']

        # Multi-line graph (Run_No wise)
        fig = px.line(
            pin_point_all,
            x="Rev_Dist",
            y="Speed",
            color="Run_No",
            line_group="Run_No",
            markers=False,
            hover_data={
                "Rev_Dist": True,
                "Speed": True,
                "Run_No": True,
                "Time": True,
                "Rev_Dist": ":.0f"
            },
        )
        from scipy.signal import savgol_filter

        # Compute Min-Max Midpoint
        avg_base_df = pin_point_all.groupby('Rev_Dist').agg({'Speed': ['min', 'max']}).reset_index()
        avg_base_df.columns = ['Rev_Dist', 'Min_Speed', 'Max_Speed']
        avg_base_df['Mid_Speed'] = (avg_base_df['Min_Speed'] + avg_base_df['Max_Speed']) / 2

        # Sort by distance
        avg_base_df = avg_base_df.sort_values('Rev_Dist', ascending=False)

        # Apply Savitzky-Golay filter for smoothness
        avg_base_df['Smooth_Mid'] = savgol_filter(avg_base_df['Mid_Speed'], window_length=51, polyorder=3)

        # Plot
        fig.add_trace(
            go.Scatter(
                x=avg_base_df['Rev_Dist'],
                y=avg_base_df['Smooth_Mid'],
                mode='lines',
                name='Avg Speed',
                line=dict(color='black', width=3),
                hovertemplate='Distance: %{x}<br>Avg Speed: %{y:.2f} km/h'
            )
        )

        # ✅ Add Annotations
        fig.add_annotation(
            x=250, y=30,
            text="30 KMPH",
            showarrow=True,
            arrowhead=2,
            ax=40, ay=0,
            arrowsize=1,
            arrowcolor="red",
            font=dict(color="red", size=12),
            bgcolor="white",
            bordercolor="red",
        )
        fig.add_annotation(
            x=10, y=8,
            text="8 KMPH",
            showarrow=True,
            arrowhead=2,
            ax=40, ay=0,
            arrowsize=1,
            arrowcolor="red",
            font=dict(color="red", size=12),
            bgcolor="white",
            bordercolor="red",
        )

        # ✅ Add vertical markers
        for i, tp in enumerate(Dist_points):
            fig.add_vline(
                x=tp,
                line=dict(color="red", width=2, dash="dot"),
                annotation_text=text_values[i],
                annotation_position="top",
                annotation_font=dict(color="Blue", size=12)
            )

        # Layout styling
        fig.update_layout(
            title="Speed Variation Before 1000 Meters (All Runs) with Average Speed Line",
            xaxis=dict(title="Distance (In Meters)", autorange="reversed"),
            yaxis=dict(title="Speed (km/h)"),
            paper_bgcolor="#ffffff",
            legend=dict(title="Legend", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # Show in Streamlit
        st.plotly_chart(fig, use_container_width=True)
# Plot Line Chart Time VS Distance .................................................................................................
        fig = px.line(filtered_df, x="Time", y="Cum_Dist_LP" , color_discrete_sequence=["#05B7B7"])
        fig.update_layout(
        title="Distance Travelled over Time",
        xaxis_title="Distance in (meter)",
        yaxis_title="Speed"
        )
        st.plotly_chart(fig,use_container_width=True)


# Plot Micro Line Chart for Selected Time .................................................................................................
        st.markdown("---")
        st.markdown(f'<h4 style="font-size: 18px; color: green ;">Micro Drive Detail for Small Time Slot</h4>',unsafe_allow_html=True)


        selected_time = st.selectbox('Select Time', filtered_df['Time'])
        col1, col2 = st.columns([1,1])
        with col1:
            def plot_with_markers(data):
                fig2 = px.line(data, x='Time', y='Speed', markers=True, title='Speed VS Time')
                fig2.update_traces(marker=dict(size=8, color='orange', line=dict(width=1, color='DarkSlateGrey')))
                fig2.update_layout(xaxis=dict(title='Time', tickangle=90), yaxis=dict(title='Speed'))
                # Adding annotations for Speed values above the markers
                for i, row in data.iterrows():
                    fig2.add_annotation(x=row['Time'], y=row['Speed'], text=str(row['Speed']),
                                    showarrow=False, font=dict(color='blue', size=12), yshift=10)

                fig.update_layout(xaxis=dict(title='Time', tickangle=90), yaxis=dict(title='Speed'))
                return fig2

            # Find the index of the selected time
            index = filtered_df[filtered_df['Time'] == selected_time].index[0]-filtered_df['Time'].index[0]
            step = 10

            # Calculate the end index
            end_index = min(index + 200, len(filtered_df) - 1)

            # Generate the range of indices for the subset
            indices = list(range(index, end_index + 1, step))

            # Select the subset data
            subset_data = filtered_df.iloc[indices] 

            fig2 = plot_with_markers(subset_data)
            st.plotly_chart(fig2)

# Plot Line Chart for Selected Time .................................................................................................
        with col2:
            def plot_with_markers(data):
                fig3 = px.line(data, x='Cum_Dist_LP', y='Speed', markers=True, title='Speed VS Distance')
                fig3.update_traces(marker=dict(size=8, color='orange', line=dict(width=1, color='DarkSlateGrey')))
                fig3.update_layout(xaxis=dict(title='Time', tickangle=90), yaxis=dict(title='Speed'))
                # Adding annotations for Speed values above the markers
                for i, row in data.iterrows():
                    fig3.add_annotation(x=row['Cum_Dist_LP'], y=row['Speed'], text=str(row['Speed']),
                                    showarrow=False, font=dict(color='blue', size=12), yshift=10)

                fig3.update_layout(xaxis=dict(title='Distance', tickangle=90), yaxis=dict(title='Speed'))
                return fig3
            

            # Find the index of the selected time
            index = filtered_df[filtered_df['Time'] == selected_time].index[0]-filtered_df['Time'].index[0]
            step = 10

            # Calculate the end index
            end_index = min(index + 200, len(filtered_df) - 1)

            # Generate the range of indices for the subset
            indices = list(range(index, end_index + 1, step))

            # Select the subset data
            subset_data = filtered_df.iloc[indices] 
            fig3 = plot_with_markers(subset_data)
            st.plotly_chart(fig3)

# Speed Slab Table ..................................................................................................................
        st.markdown("---")
        # st.markdown(f'<h4 style="font-size: 18px; color: green ;">Speed Slab Wise Distance & Time</h4>',unsafe_allow_html=True)
        s1 = dict(selector='th', props=[('text-align', 'center')])
        s2 = dict(selector='td', props=[('text-align', 'center')])

        # st.header("Data statistical View (EDA)")
        eda = filtered_df[["Date","Time","Train_No","Loco_No","CMS_ID","Run_No","Speed","Rev_Dist","Pin_Point","BFT_BPT"]]
        date_value = pd.Timestamp(filtered_df["Date"].min())
        if pd.isnull(date_value) or date_value is pd.NaT:
            formatted_date = ""
        else:
            formatted_date = date_value.strftime("%d-%b-%Y")

    
        col1,col2 = st.columns([1,2])
        with col1:
            st.markdown(f'<h5 style="font-size: 18px; color: #D30DF4 ;">Speed Slab Wise Distance & Time</h5>',unsafe_allow_html=True)           

            # Avoid UserWarning by specifying a format for datetime conversion
            if not pd.api.types.is_datetime64_any_dtype(filtered_df["Time"]):
                filtered_df["Time"] = pd.to_datetime(filtered_df["Time"], format="%H:%M:%S", errors="coerce")

            # Sort the DataFrame by "Time" column (important for calculating time differences)
            filtered_df = filtered_df.sort_values(by="Time")

            filtered_df["TimeDiff"] = filtered_df["Time"].diff()

            # Define the speed slabs
            speed_slabs = [
                (1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 60), (61, 70), (71, 80), (81, 90), (91, 100), (101, 110), (111, 120), (121, 130), (131, 150)
            ]

            # Initialize lists to store the calculated values for each speed slab
            speed_slab_list = []
            distance_list = []
            time_list = []

            # Function to convert timedelta to "HH:MM:SS" format
            def strfdelta(timedelta):
                total_seconds = timedelta.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                seconds = int(total_seconds % 60)
                return f"{hours:02}:{minutes:02}:{seconds:02}"

            # Iterate through each speed slab and calculate the total distance and total time
            for start, end in speed_slabs:
                # Filter the DataFrame for the current speed slab
                slab_df = filtered_df[(filtered_df['Speed'] >= start) & (filtered_df['Speed'] < end)]

                # Check if the DataFrame is not empty for the current speed slab
                if not slab_df.empty:
                    # Calculate the total distance and total time for the current speed slab
                    total_distance = slab_df["Distance"].sum()
                    total_time_timedelta = slab_df["TimeDiff"].sum()

                    # Convert the total time timedelta to "HH:MM:SS" format using the strfdelta function
                    total_time_str = strfdelta(total_time_timedelta)

                    # Append the calculated values to the corresponding lists
                    speed_slab_list.append(f"{start}-{end}")
                    distance_list.append(total_distance)
                    time_list.append(total_time_str)

            # Create a new DataFrame with the calculated values
            result_df = pd.DataFrame({
                'Speed Slab': speed_slab_list,
                'Distance (in Mtr)': distance_list,
                'Time': time_list
            })
            table = result_df.style.set_table_styles([s1,s2]).hide(axis=0).to_html()     
            st.write(f'{table}', unsafe_allow_html=True)
            st.markdown("----")
        
        with col2:   
            st.markdown(f'<p style="font-size: 18px; color: #D30DF4;">Details of Specific Speed</p>',unsafe_allow_html=True) 
                       
            # Create a list from 1 to 140 for speed selection
            speed = [str(i) for i in range(1, 141)]
            speed_filter = st.selectbox('Select Speed of Train:', speed)
            
            # Create and display table for selected speed
            speed_val = int(speed_filter)
            # Defensive: Only select columns that exist in the DataFrame
            columns_to_show = [col for col in ["CMS_ID","Date", "Time", "Speed","Distance","Cum_Dist_LP","Run_No"] if col in filtered_df.columns]
            speed_table = filtered_df[filtered_df["Speed"] == speed_val][columns_to_show].copy()

            # Add total distance travelled at selected speed
            if "Distance" in speed_table.columns:
                total_distance = speed_table["Distance"].sum() if not speed_table.empty else 0
                st.markdown(f"Total Distance Travelled at Speed {speed_val} km/h:- {total_distance:.2f} meters")
            else:
                st.markdown(f"Total Distance Travelled at Speed {speed_val} km/h:- N/A (No 'Distance' column)")

            # Format Time column to HH:MM:SS if it's datetime
            if "Time" in speed_table.columns and pd.api.types.is_datetime64_any_dtype(speed_table["Time"]):
                speed_table["Time"] = speed_table["Time"].dt.strftime("%H:%M:%S")
            st.markdown("#### Table for Selected Speed")
            st.dataframe(speed_table.reset_index(drop=True), use_container_width=True)

# #=============================================================================================================================================================================
    elif page_option == 'Statical View':
            st.markdown(f'<h4 style="font-size: 18px; color: green ;">This Report has been Depriciated, Use Quick Report</h4>',unsafe_allow_html=True)
            st.header("🚫 🔐")



def main():
    st.title("Driving Technique Analysis || Interactive")

    # Hide menu and footer for authenticated users
    hide_menu_style= """
            <style>
            #main_menu {visibility:hidden;}
            footer {visibility:hidden;}
            </style>"""
    st.markdown(hide_menu_style,unsafe_allow_html=True)

    # Making Side Bar
    gif_path = os.path.join(os.path.dirname(__file__), "Ver_3_2.ico")
    st.sidebar.image(gif_path, width=200)

    # Button 1 – Live View
    st.sidebar.subheader("Live Visualization")
    live_file = st.sidebar.file_uploader("Upload Fabricated Excel Files only", type=["xlsx"], key="live_view_file")
    if live_file:
        df = pd.read_excel(live_file, engine='openpyxl')
        df.columns = df.columns.str.strip()
        st.info(" 🔔 Select CMS ID and Press 'Generate Live Report' Button to generate Live View Report")
        if "CMS_ID" not in df.columns:
            st.sidebar.error("The uploaded file must contain a 'CMS_ID' column.")
            st.write("Columns found:", df.columns.tolist())
        else:
            cms_ids = df["CMS_ID"].dropna().unique().tolist()
            selected_cms = st.sidebar.multiselect("🔍 Search CMS ID:", options=cms_ids)

            # Trigger Live_view automatically when CMS ID is selected
            if selected_cms:
                Live_view(df, selected_cms)
            else:
                st.sidebar.warning("Selected CMS_ID not found in the data.")

                
                
    # Home button to go to design.py
    if st.sidebar.button("🏠 Back to Home", key="home_btn"):
        st.switch_page("pages/design.py")

    
    # If no file is uploaded
    if not live_file :
        st.info("👈 Please Upload Processed File from Side Bar")
        st.markdown("<br>", unsafe_allow_html=True)
        gif_path = os.path.join(os.path.dirname(__file__), "SpeedView_2.gif")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.empty()
        with col2:
            st.image(gif_path, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<p style="font-size: 16px; color: #053A8C; text-align:center;">Design & Developed by- BDTS1022 <BR> Western Railway,<BR>Mumbai Division <BR> 2022</p>', unsafe_allow_html=True)
        with col3:
            st.empty()

if __name__ == "__main__":
    main()