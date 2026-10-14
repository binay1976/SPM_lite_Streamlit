import streamlit as st
import plotly.express as px
import streamlit_authenticator as stauth
import plotly.io as pio
pio.renderers.default = "browser"
import plotly.graph_objects as go
import os,socket
import pandas as pd
from scipy.interpolate import make_interp_spline
# from st_aggrid import AgGrid, GridOptionsBuilder
from io import BytesIO
from reportlab.pdfgen import canvas
from PIL import Image
from datetime import timedelta
from reportlab.pdfgen import canvas
from PIL import Image
from datetime import timedelta
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from datetime import timedelta
import plotly.express as px
import plotly.io as pio
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
import tempfile
import logging 
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pytz
import streamlit.components.v1 as components
import socket




st.set_page_config(page_title="SPM App", page_icon="🚆", layout="wide")
# Session/authentication check
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("🚫 🔐 You must login first.")
    st.header("🚫 🔐")
    st.switch_page("graph.py")
    st.stop()

# Sidebar image
st.write(
    f"👤 Logged in as:- {st.session_state.get('user_name', '')} "
    f"(CLI/{st.session_state.get('user_lobby', '')} , Mob- {st.session_state.get('user_mobile', '')})"
)

gif_path = os.path.join(os.path.dirname(__file__), "Ver_3_2.ico")
if os.path.exists(gif_path):
    try:
        st.sidebar.image(gif_path, width=150)
    except Exception as e:
        st.sidebar.warning(f"Failed to load Ver_3_2.ico: {str(e)}")
else:
    st.sidebar.warning("Icon not found at the specified path.")



# function for Quick Report Button-2
def Quick_Report(df, cms_id):
    with st.spinner("Processing file... Please wait ⏳"):
        st.info("Inflatting Baloons, Please Wait PDF File is Generating.......")
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)  # <-- This will now work, as A4 is imported above
        width, height = A4

        # Step 1: Filter and Validate
        filtered_df = df[df["CMS_ID"] == cms_id].copy()
        if filtered_df.empty:
            st.error(f"No records found for CMS_ID: {cms_id}")
            return None
        else:
            st.write(f"Found {len(filtered_df)} records for CMS_ID: {cms_id}")

        # Step 2: Ensure Types
        try:
            filtered_df['Date'] = pd.to_datetime(filtered_df['Date'], format='%d/%m/%Y', errors='coerce')
            filtered_df['Time'] = pd.to_datetime(filtered_df['Time'], format='%H:%M:%S', errors='coerce').dt.time
            filtered_df['DateTime'] = pd.to_datetime(
                filtered_df['Date'].dt.strftime('%d/%m/%Y') + ' ' + filtered_df['Time'].astype(str),
                format='%d/%m/%Y %H:%M:%S',
                errors='coerce'
            )
            filtered_df = filtered_df.dropna(subset=['DateTime']).sort_values(by='DateTime')
        except Exception as e:
            st.error(f"Error in datetime processing: {e}")
            return None

        # Step 3: Extract metrics with safety checks
        try:
            train_no = filtered_df["Train_No"].min() if not filtered_df["Train_No"].isna().all() else "N/A"
            loco_no = filtered_df["Loco_No"].min() if not filtered_df["Loco_No"].isna().all() else "N/A"
            
            designation = (
                filtered_df["Desig"].dropna().iloc[0] if filtered_df["Desig"].notna().any() else ""
            )
            pilot_name = (
                filtered_df["Crew_Name"].dropna().unique()[0] if filtered_df["Crew_Name"].notna().any() else ""
            )
            nominated_cli = (
                filtered_df["Nom_CLI"].dropna().unique()[0] if filtered_df["Nom_CLI"].notna().any() else ""
            )

            total_km = round(filtered_df["Distance"].sum() / 1000, 3)
            top_speed = filtered_df["Speed"].max()
            total_halt = filtered_df["Run_No"].max()

            filtered_df["TimeDiff"] = filtered_df["DateTime"].diff().dt.total_seconds().fillna(0)
            running_time_sec = filtered_df.loc[filtered_df["Speed"] > 0, "TimeDiff"].sum()
            halt_time_sec = filtered_df.loc[filtered_df["Speed"] == 0, "TimeDiff"].sum()
            total_time_sec = running_time_sec + halt_time_sec

            running_time_str = str(timedelta(seconds=int(running_time_sec)))
            halt_time_str = str(timedelta(seconds=int(halt_time_sec)))
            avg_speed = round((total_km / total_time_sec) * 3600, 2) if total_time_sec > 0 else 0

            min_datetime = pd.to_datetime(filtered_df["DateTime"].min())
            max_datetime = pd.to_datetime(filtered_df["DateTime"].max())
            total_duration = max_datetime - min_datetime

            min_datetime_str = min_datetime.strftime("%d-%m-%Y %H:%M:%S")
            max_datetime_str = max_datetime.strftime("%d-%m-%Y %H:%M:%S")


        except Exception as e:
            st.error(f"Data extraction failed: {e}")
            return None

        # Step: Build PDF
        img_path = os.path.join(os.path.dirname(__file__), "Logo_HD_2.png")
        c.drawImage(img_path, x=-30, y=height - 130, width=270, height=140)

        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.HexColor("#9B069D"))
        c.drawString(170, height - 60, "Loco Pilot Driving Skill Analysis")
        c.setFont("Helvetica", 14)
        c.setFillColor(colors.HexColor("#062DB8"))
        c.drawString(250, height - 80, "Western Railway")
        c.line(40, height - 95, width - 40, height - 95)

        y = height - 120
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.HexColor("#A80609"))
        c.drawString(190, y, f"(Report For Crew CMS ID: {cms_id})")
        y -= 15
        c.drawString(100, y, f"Record Available For: {min_datetime_str} to {max_datetime_str}")
        y -= 10

        # Table data: [Sr, Head, "Details"]
        table_data = [
            ["Sr", "Head", "Details"],
            [1, "Loco Pilot Name", pilot_name],
            [2, "Designation", designation],
            [3, "CMS ID", cms_id],
            [4, "Nominated CLI", nominated_cli],
            [5, "Loco Number", loco_no],
            [6, "Train Number", train_no],
            [7, "Wheel Start Date & Time", min_datetime_str],
            [8, "Wheel Stop Date & Time", max_datetime_str],
            [9, "Total Distance Travelled", f"{total_km} KM"],
            [10, "Wheel Start to Stop Duration", f"{total_duration}"],
            [11, "Running Time", f"{running_time_str}"],
            [12, "Halt Time", f"{halt_time_str}"],
            [13, "Top Speed", f"{top_speed} Kmph"],
            [14, "Average Speed", f"{avg_speed} Kmph"],
            [15, "Dead Stopped", f"{total_halt} Times"],
            [16, "Train Load", ""],
            [17, "Guard Name", ""],
            [18, "BPC Details", ""],
        ]

        # Create table
        table = Table(table_data, colWidths=[30, 170, 280], rowHeights=[30] * len(table_data))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),   # Vertically center all cells
        ]))

        # Position the table lower so it doesn't overlap the header
        x = 50
        y = height - 720  # <-- Adjust this Y value to move table down
        table.wrapOn(c, width, height)
        table.drawOn(c, x, y)

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, f"Page 1")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

        # Signature
        c.setFont("Helvetica", 12)
        c.drawString(40, 80, f"Prepared By:- {st.session_state.get('user_name', '')} ")
        c.drawString(40, 65, f"(CLI/{st.session_state.get('user_lobby', '')} , Mob- {st.session_state.get('user_mobile', '')})")

# Page-2 For Exceptions---------------------------------------------------------------------------------------------------------------
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


        

# ==========================================================
# PAGE 2 — EXCEPTIONS REPORT
# ==========================================================

        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from xml.sax.saxutils import escape

        # Start Page 2
        c.showPage()

        width, height = A4

        left_margin = 40
        right_margin = 40
        bottom_margin = 40
        usable_width = width - left_margin - right_margin

        # Text styles
        title_style = ParagraphStyle(
            "ExceptionTitle",
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#9B069D"),
            alignment=TA_LEFT
        )

        header_style = ParagraphStyle(
            "ExceptionHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white
        )

        cell_style = ParagraphStyle(
            "ExceptionCell",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            wordWrap="CJK"
        )

        section_style = ParagraphStyle(
            "ExceptionSection",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#062DB8")
        )

        message_style = ParagraphStyle(
            "ExceptionMessage",
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#267326")
        )

        # ----------------------------------------------------------
        # PAGE HEADER
        # ----------------------------------------------------------

        def draw_exception_header():
            c.setFont("Helvetica-Bold", 16)
            c.drawString(left_margin, height - 45, "Exceptions Report")

            c.setStrokeColor(colors.grey)
            c.line(
                left_margin,
                height - 55,
                width - right_margin,
                height - 55
            )


        # ----------------------------------------------------------
        # PAGE FOOTER
        # ----------------------------------------------------------

        def draw_exception_footer():
            c.setFont("Helvetica-Oblique", 8)
            c.setFillColor(colors.grey)

            c.drawString(left_margin, 20, "Exceptions Report")

            c.drawRightString(
                width - right_margin,
                20,
                "Western Railway | SPM Analysis Tool"
            )


        # ----------------------------------------------------------
        # DRAW A TABLE AND CONTINUE ON NEW PAGES IF REQUIRED
        # ----------------------------------------------------------

        def draw_exception_table(title, data, columns, empty_message):
            nonlocal y

            # Section heading
            heading = Paragraph(escape(title), section_style)
            _, heading_height = heading.wrap(usable_width, height)

            if y - heading_height < bottom_margin:
                draw_exception_footer()
                c.showPage()
                draw_exception_header()
                y = height - 75

            heading.drawOn(c, left_margin, y - heading_height)
            y -= heading_height + 7

            # Display message if no exceptions exist
            if data.empty:
                message = Paragraph(escape(empty_message), message_style)
                _, message_height = message.wrap(usable_width, height)

                if y - message_height < bottom_margin:
                    draw_exception_footer()
                    c.showPage()
                    draw_exception_header()
                    y = height - 75

                message.drawOn(c, left_margin + 5, y - message_height)
                y -= message_height + 15
                return

            # Prepare table header
            table_data = [[
                Paragraph(escape(label), header_style)
                for _, label in columns
            ]]

            # Prepare exception records
            for _, row in data.iterrows():
                record = []

                for column, label in columns:
                    value = row.get(column, "")

                    if pd.isna(value):
                        value = ""

                    # Escape special characters for Paragraph
                    value = escape(str(value))

                    record.append(Paragraph(value, cell_style))

                table_data.append(record)

            # Calculate column widths
            col_count = len(columns)

            if col_count == 4:
                col_widths = [65, 75, 75, usable_width - 215]
            elif col_count == 7:
                col_widths = [48, 53, 53, 65, 55, 45, usable_width - 319]
            else:
                col_widths = [usable_width / col_count] * col_count

            # Build table
            table = Table(
                table_data,
                colWidths=col_widths,
                repeatRows=1,
                splitByRow=1
            )

            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0),
                colors.HexColor("#28487A")),

                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),

                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                ("FONTSIZE", (0, 0), (-1, -1), 8),

                ("VALIGN", (0, 0), (-1, -1), "TOP"),

                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),

                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F2F5FA")
                ]),
            ]))

            # Split and draw the table across pages
            remaining = table

            while remaining is not None:

                available_height = y - bottom_margin

                remaining.wrapOn(c, usable_width, available_height)

                parts = remaining.split(usable_width, available_height)

                if len(parts) >= 2:
                    current_table = parts[0]
                    remaining = parts[1]
                else:
                    # If the table fits completely, draw it.
                    _, total_height = remaining.wrapOn(
                        c, usable_width, available_height
                    )

                    if total_height <= available_height:
                        current_table = remaining
                        remaining = None
                    else:
                        # Avoid an infinite loop if a single row cannot split.
                        draw_exception_footer()
                        c.showPage()
                        draw_exception_header()
                        y = height - 75
                        continue

                _, table_height = current_table.wrapOn(
                    c, usable_width, height
                )

                current_table.drawOn(
                    c,
                    left_margin,
                    y - table_height
                )

                y -= table_height + 15

                if remaining is not None:
                    draw_exception_footer()
                    c.showPage()
                    draw_exception_header()
                    y = height - 75

            y -= 5


        # ----------------------------------------------------------
        # INITIALIZE PAGE POSITION
        # ----------------------------------------------------------

        draw_exception_header()
        y = height - 75


        # ----------------------------------------------------------
        # RUN EXISTING EXCEPTION DETECTION FUNCTIONS
        # ----------------------------------------------------------

        bft_bpt_df = process_bft_bpt(df)
        over_speed_df = process_overspeed(df)
        before_10m_df = process_before_10m(df)
        before_250m_df = process_before_250m(df)


        # ----------------------------------------------------------
        # 1. BFT / BPT EXCEPTIONS
        # ----------------------------------------------------------

        draw_exception_table(
            "1. BFT / BPT Exceptions",
            bft_bpt_df,
            [
                ("CMS_ID", "CMS ID"),
                ("Loco_No", "Loco No"),
                ("Train_No", "Train No"),
                ("Exception", "Exception"),
            ],
            "All OK - No BFT/BPT exceptions found."
        )


        # ----------------------------------------------------------
        # 2. OVER SPEED EXCEPTIONS
        # ----------------------------------------------------------

        draw_exception_table(
            "2. Over Speed Exceptions",
            over_speed_df,
            [
                ("CMS_ID", "CMS ID"),
                ("Loco_No", "Loco No"),
                ("Train_No", "Train No"),
                ("Date", "Date"),
                ("Time", "Time"),
                ("Speed", "Speed"),
                ("Exception", "Exception"),
            ],
            "All OK - No overspeeding found."
        )


        # ----------------------------------------------------------
        # 3. SPEED BEFORE 10 METERS
        # ----------------------------------------------------------

        draw_exception_table(
            "3. Suspected Risky Speed Before 10 Meters",
            before_10m_df,
            [
                ("CMS_ID", "CMS ID"),
                ("Loco_No", "Loco No"),
                ("Train_No", "Train No"),
                ("Date", "Date"),
                ("Time", "Time"),
                ("Speed", "Speed"),
                ("Exception", "Exception"),
            ],
            "All OK - No risky speed exceptions found before 10 m."
        )


        # ----------------------------------------------------------
        # 4. SPEED BEFORE 250 METERS
        # ----------------------------------------------------------

        draw_exception_table(
            "4. Suspected Risky Speed Before 250 Meters",
            before_250m_df,
            [
                ("CMS_ID", "CMS ID"),
                ("Loco_No", "Loco No"),
                ("Train_No", "Train No"),
                ("Date", "Date"),
                ("Time", "Time"),
                ("Speed", "Speed"),
                ("Exception", "Exception"),
            ],
            "All OK - No risky speed exceptions found before 250 m."
        )


        # ----------------------------------------------------------
        # FINAL PAGE FOOTER
        # ----------------------------------------------------------

        draw_exception_footer()

        # Continue with your existing PDF code.
        # Keep c.save() at the end of the complete report.






# Page-3: Speed Slab Wise Distance and Time-------------------------------------------------------------------------------------------
        c.showPage()  # Add new page......

        width, height = A4
        # Add title and image to PDF
        c.setFont("Helvetica-Bold", 1)
        Loco_No = filtered_df["Loco_No"].min() if not filtered_df["Loco_No"].empty else "N/A"
        c.drawCentredString(width / 2, height - 30, f"Speed Slab Report for CMS ID: {cms_id} & Loco No {Loco_No}")
        

        # Ensure 'Time' is datetime (full datetime, not just time)
        if not pd.api.types.is_datetime64_any_dtype(filtered_df["Time"]):
            filtered_df["Time"] = pd.to_datetime(filtered_df["Time"], format="%H:%M:%S", errors="coerce")

        filtered_df = filtered_df.dropna(subset=["DateTime"])
        filtered_df = filtered_df.sort_values(by="DateTime")

        filtered_df["TimeDiff"] = filtered_df["DateTime"].diff().fillna(pd.Timedelta(0))

        # Define speed slabs
        speed_slabs = [
            (1, 10), (11, 20), (21, 30), (31, 40), (41, 50),
            (51, 60), (61, 70), (71, 80), (81, 90), (91, 100),
            (101, 110), (111, 120), (121, 130), (131, 150)
        ]

        # Prepare data for table (header + rows)
        table_data = [
            ["Speed Slab (km/h)", "Total Distance (km)", "Total Time (HH:MM:SS)"]
        ]

        def strfdelta(tdelta):
            if pd.isna(tdelta):
                return " "
            total_seconds = tdelta.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            return f"{hours:02}:{minutes:02}:{seconds:02}"

        # Populate rows
        for start, end in speed_slabs:
            subset_df = filtered_df[(filtered_df['Speed'] >= start) & (filtered_df['Speed'] < end)]
            total_distance = subset_df["Distance"].sum() / 1000 if not subset_df.empty else 0
            total_time = subset_df["TimeDiff"].sum() if not subset_df.empty else pd.Timedelta(0)

            total_distance_str = f"{total_distance:.3f}" if total_distance > 0 else "- -"
            total_time_str = strfdelta(total_time) if total_time.total_seconds() > 0 else "- -"

            table_data.append([f"{start}-{end}", total_distance_str, total_time_str])

        # Create table
        col_widths = [130, 150, 170]
        row_heights = 25

        table = Table(table_data, colWidths=col_widths, rowHeights=row_heights)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
        ]))

        

        # Calculate Y position for table start (leaving some margin from title)
        x = 60
        y = height - 90 - (len(table_data) * row_heights)  # Adjust Y so table fits nicely below title

        table.wrapOn(c, width, height)
        table.drawOn(c, x, y)

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, f"Page 2")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

# Third page: Halt Bar Chart..................................................................................................
        c.showPage()  # Add new page
        c.setPageSize(landscape(A4))  # Change page size before starting new page
        width, height = landscape(A4)

        # Calculate max speed per Run_No and CMS_ID
        max_speed = filtered_df.groupby(['Run_No', 'CMS_ID'])['Speed'].max().reset_index()
        max_speed = max_speed[max_speed['CMS_ID'] == cms_id]

        # Sum speeds grouped by Run_No
        sum_max_speed = max_speed.groupby('Run_No')['Speed'].sum().reset_index()
        max_sum_max_speed_index = sum_max_speed['Speed'].idxmax() if not sum_max_speed.empty else -1

        # Create Plotly bar chart
        fig = px.bar(sum_max_speed, x="Run_No", y="Speed", text="Speed")

        # Color bars (brown for highest, light blue others)
        baar_colors = ['#05B7B7'] * len(sum_max_speed)
        if max_sum_max_speed_index >= 0:
            baar_colors[max_sum_max_speed_index] = '#854c03'
        fig.update_traces(marker_color=baar_colors)

        # Update layout
        fig.update_layout(
            title=f"Max. Speed of Each Stoppage (CMS_ID: {cms_id})",
            xaxis_title="Run Between each D/Stop & Start",
            yaxis_title="Speed",
        )
        fig.update_xaxes(type='category')


        # Save plot as a temp PNG file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            fig_path1 = tmp_file.name
            pio.write_image(fig, fig_path1, format="png", width=1200, height=600, scale=2)

        # Add title and image to PDF
        c.setFont("Helvetica-Bold", 12)
        Loco_No = filtered_df["Loco_No"].min() if not filtered_df["Loco_No"].empty else "N/A"
        c.drawCentredString(420, 560, f"Top Speed Between Each Halt (CMS ID: {cms_id} & Loco No {Loco_No})")

        # Insert image (adjust coordinates and size for landscape A4)
        c.drawImage(fig_path1, x=30, y=80, width=730, height=350)  # Adjust size as needed

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, f"Page 3")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

# Page-4: Speed Variation over Time...........................................................................................
        filtered_cms_df = filtered_df[filtered_df["CMS_ID"] == cms_id].copy()
        filtered_cms_df["Time"] = pd.to_datetime(filtered_cms_df["Time"]).dt.strftime('%H:%M:%S')
        filtered_cms_df = filtered_cms_df.sort_values(by="DateTime")
        
        # Find top speed before creating plot (needed for title & annotation)
        top_speed = filtered_cms_df["Speed"].max()
        top_speed_time = filtered_cms_df.loc[filtered_cms_df["Speed"] == top_speed, "Time"].iloc[0]
        
        # Create Plotly line chart........
        fig = px.line(
            filtered_cms_df,
            x="Time",
            y="Speed",
            title=f"Speed Variation over Time, Top Speed - {top_speed} Km/h",
            labels={"Time": "Time", "Speed": "Speed (km/h)"},
            color_discrete_sequence=["#3366CC"]
        )
        
        # Improve layout
        fig.update_layout(
            plot_bgcolor="white",
            xaxis=dict(
                showgrid=True,
                gridcolor="lightgray",
                title_font=dict(size=14),
                tickangle=90,
                type="category",
                showline=True,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="lightgray",
                title_font=dict(size=14),
                showline=True,
                type="linear",
                layer="below traces",
                zeroline=True,
                zerolinecolor="blue",
                zerolinewidth=1,
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12
            ),
            margin=dict(b=150)
        )
        
        # Add annotation for top speed
        fig.add_annotation(
            x=top_speed_time,
            y=top_speed,
            text="Top Speed",
            showarrow=True,
            arrowhead=4,
            arrowcolor="red",
            font=dict(color="black", size=12)
        )
        
    # Save plot as a temp PNG file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            fig_path3 = tmp_file.name
            pio.write_image(fig, fig_path3, format="png", width=1200, height=600, scale=2)

        c.showPage()  # Add new page
        c.setPageSize(landscape(A4))  # Change page size before starting new page
        width, height = landscape(A4)
        # Add title and image to PDF    
        c.setFont("Helvetica-Bold", 12)     
        Loco_No = filtered_df["Loco_No"].min() if not filtered_df["Loco_No"].empty else "N/A"
        c.drawCentredString(width / 2, height - 30, f"Report For CMS ID: {cms_id} & Loco No {Loco_No}")
        c.drawImage(fig_path3, x=20, y=height/4 - 150, width=width - 20, height=600, preserveAspectRatio=True)

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, f"Page 4")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

# page No-5: Speed Variation over Distance...................................................................................
        filtered_cms_df = filtered_df[filtered_df["CMS_ID"] == cms_id].copy()
        filtered_cms_df = filtered_cms_df.sort_values(by="Cum_Dist_LP")

        cum_dist_min = filtered_cms_df["Cum_Dist_LP"].min()
        cum_dist_max = filtered_cms_df["Cum_Dist_LP"].max()
        if pd.notna(cum_dist_min) and pd.notna(cum_dist_max):
            tick_step = max(1000, int((cum_dist_max - cum_dist_min) // 10) or 1)
            tick_values = list(range(int(cum_dist_min), int(cum_dist_max) + tick_step, tick_step))
        else:
            tick_values = []

        # Plotly figure
        fig = px.line(
            filtered_cms_df,
            x="Cum_Dist_LP",
            y="Speed",
            title=f"Speed Variation Over Distance, Top Speed:- {top_speed}",
            labels={"Cum_Dist_LP": "Distance (km)", "Speed": "Speed (km/h)"},
            color_discrete_sequence=["#D004B5"]
        )

        # Top speed annotation
        top_speed = filtered_cms_df["Speed"].max()
        if not pd.isna(top_speed):
            top_speed_dist = filtered_cms_df.loc[filtered_cms_df["Speed"] == top_speed, "Cum_Dist_LP"].median()
        else:
            top_speed_dist = 0

        fig.update_layout(
            plot_bgcolor="white",
            xaxis=dict(
                showgrid=True,
                gridcolor="lightgray",
                title_font=dict(size=14),
                tickangle=90,
                tickmode="array",
                tickvals=tick_values,
                type="linear",
                showline=True,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="lightgray",
                title_font=dict(size=14),
                showline=True,
                type="linear",
                layer="below traces",
                zeroline=True,
                zerolinecolor="blue",
                zerolinewidth=1,
            ),
            hoverlabel=dict(bgcolor="white", font_size=12),
            margin=dict(b=150)
        )

        fig.add_annotation(
            x=top_speed_dist,
            y=top_speed,
            text="Top Speed",
            showarrow=True,
            arrowhead=4,
            arrowcolor="red",
            font=dict(color="red", size=12)
        )  
        # Save plot as a temp PNG file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            fig_path2 = tmp_file.name
            pio.write_image(fig, fig_path2, format="png", width=1200, height=600, scale=2)

        # Add new landscape page
        c.showPage()
        c.setPageSize(landscape(A4))
        width, height = landscape(A4)

        # Add heading
        c.setFont("Helvetica-Bold", 12)
        loco_no = filtered_cms_df["Loco_No"].min()
        if pd.isna(loco_no):
            loco_no = "Unknown"

        c.drawCentredString(width / 2, height - 30, f"Report for CMS ID:- {cms_id} & Loco No:- {loco_no}")
        c.drawImage(fig_path2, x=20, y=height/4 - 150, width=width - 20, height=600, preserveAspectRatio=True)

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, f"Page 5")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

# Page-6 : Brake Feel & Brake Power Test Table.........................................................................................................................
        filtered_df["Time"] = pd.to_datetime(filtered_df["Time"], errors="coerce")
        loco_no = filtered_df.loc[filtered_df["CMS_ID"] == cms_id, "Loco_No"].min()
        if pd.isna(loco_no):
            loco_no = "Unknown"

        # Defensive: Only use BFT_END/BPT_END columns if they exist
        if "BFT_END" in filtered_df.columns:
            bft_end_filtered = filtered_df[filtered_df["BFT_END"] == "BFT_END"]
        else:
            bft_end_filtered = pd.DataFrame()

        if "BPT_END" in filtered_df.columns:
            bpt_end_filtered = filtered_df[filtered_df["BPT_END"] == "BPT_END"]
        else:
            bpt_end_filtered = pd.DataFrame()

        # BFT Data
        bft_filtered = filtered_df[filtered_df["BFT"] == "BFT"] if "BFT" in filtered_df.columns else pd.DataFrame()
        bft_time = bft_filtered["Time"].iloc[0].strftime('%H:%M:%S') if not bft_filtered.empty else "N/A"
        bft_dist = bft_filtered["Cum_Dist_LP"].iloc[0] if not bft_filtered.empty else "N/A"
        bft_speed = bft_filtered["Speed"].iloc[0] if not bft_filtered.empty else "N/A"

        bft_end_time = bft_end_filtered["Time"].iloc[0].strftime('%H:%M:%S') if not bft_end_filtered.empty else "N/A"
        bft_end_dist = bft_end_filtered["Cum_Dist_LP"].iloc[0] if not bft_end_filtered.empty else "N/A"
        bft_end_speed = bft_end_filtered["Speed"].iloc[0] if not bft_end_filtered.empty else "N/A"

        try:
            bft_total_dist = float(bft_end_dist) - float(bft_dist)
        except:
            bft_total_dist = "Improper BFT"

        # BPT Data
        bpt_filtered = filtered_df[filtered_df["BPT"] == "BPT"] if "BPT" in filtered_df.columns else pd.DataFrame()
        bpt_time = bpt_filtered["Time"].iloc[0].strftime('%H:%M:%S') if not bpt_filtered.empty else "N/A"
        bpt_dist = bpt_filtered["Cum_Dist_LP"].iloc[0] if not bpt_filtered.empty else "N/A"
        bpt_speed = bpt_filtered["Speed"].iloc[0] if not bpt_filtered.empty else "N/A"

        bpt_end_time = bpt_end_filtered["Time"].iloc[0].strftime('%H:%M:%S') if not bpt_end_filtered.empty else "N/A"
        bpt_end_dist = bpt_end_filtered["Cum_Dist_LP"].iloc[0] if not bpt_end_filtered.empty else "N/A"
        bpt_end_speed = bpt_end_filtered["Speed"].iloc[0] if not bpt_end_filtered.empty else "N/A"

        try:
            bpt_total_dist = float(bpt_end_dist) - float(bpt_dist)
        except:
            bpt_total_dist = "Improper BPT"

        # New landscape page
        c.showPage()
        c.setPageSize(landscape(A4))
        width, height = landscape(A4)

        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 30, f"Report for CMS ID: {cms_id} & Loco No: {loco_no}")

        c.setFont("Helvetica", 12)
        c.drawString(40, height - 70, "Brake Feel & Brake Power Test Conducted (Within 10 Km of First Section)")

        # Table data
        table_data = [
            ["Test Done", "Start Time", "End Time", "Start Distance", "End Distance", "Total Distance", "Start Speed", "End Speed"],
            ["BFT", str(bft_time), str(bft_end_time), str(bft_dist), str(bft_end_dist), str(bft_total_dist), str(bft_speed), str(bft_end_speed)],
            ["BPT", str(bpt_time), str(bpt_end_time), str(bpt_dist), str(bpt_end_dist), str(bpt_total_dist), str(bpt_speed), str(bpt_end_speed)]
        ]

        table = Table(table_data, colWidths=[92] * 8)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        # Draw the table (start ~150 units down)
        table.wrapOn(c, width, height)
        table.drawOn(c, x=30, y=height - 180)

        # Add note
        c.setFont("Helvetica-Bold", 10)
        c.drawString(30, height - 190, "Note: All Distances are Shown in Meters")
        regulation_lines = [
        "BPT BFT Rules & Regulations",
        "******************************************",
        "No. CSO/Safety/Safety Circular/163//74",
        "Zonal Safety Circular No. 03/2018",
        "Date: 05.06.2018",
        "Sub: Brake continuity test, Brake feel & Brake Power Tests.",
        "",
        "All concerned, are advised to perform the following test at appropriate stages to ensure Safety of the train:",
        "Brake Feel Test:",
        "1. Brake feel test to be done after start at the station/ Yard where the crew have taken over charge of the train.",
        "2. It should be performed on attaining the speed of about 20 kmph; Loco pilot shall reduce BP pressure by 0.5 to 0.8 kg/cm' through A9 valve and release after a pause.",
        "   The crew should feel the application of brakes and speed should reduce to about 15 kmph.",
        "",
        "Brake Power Test:",
        "1. Brake Power Test is to be done in the first block section or on the first opportunity.", 
        "2. When the train speed has reached 60 to 70 kmph in case of coaching train and 40 to 50 incase of goods Train.",
        "3. Loco pilot shall reduce the BP pressure by 1 Kg/Cm in Coaching Trains and loaded goods trains and 0.5 Kg/Cm in ease of empty Goods train through A9",
        "   and release after a  pause,",
        "4. The speed of the train should drop to 30 to 35 kmph in coaching train and 20 to 25 kmph in Goods Trains by the time BP pressure is Charged to 5 kg/cm2",
        "_____________",   

        "Chief Safety Officer",
        "P.V. Barapatre"
        ]

        y = 350
        c.setFont("Helvetica", 10)
        for line in regulation_lines:
            c.drawString(30, y, line)
            y -= 12  # line spacing

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, f"Page 6 ")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

    # BPT BFT Line Chart................................................................................................................
        data_base = filtered_df[filtered_df['Cum_Dist_LP'] < 10000]
        bft = data_base[data_base['BFT_BPT'] == "BFT"]
        bpt = data_base[data_base['BFT_BPT'] == "BPT"]

        # Create the line chart
        fig = px.line(
            data_base,
            x="Cum_Dist_LP",
            y="Speed",
            title="Brake Feel & Brake Power Test (First 10 KM)",
            labels={"Cum_Dist_LP": "Distance (mtr)", "Speed": "Speed (km/h)"},
            color_discrete_sequence=["#05B7B7"]
        )

        # Add annotations for BFT and BPT
        Dist_points = bft.index.tolist() + bpt.index.tolist()
        texts = ['BFT Done'] * len(bft) + ['BPT Done'] * len(bpt)

        for i, point in enumerate(Dist_points):
            if point in data_base.index:
                point_data = data_base.loc[point]
                fig.add_annotation(
                    x=point_data['Cum_Dist_LP'],
                    y=point_data['Speed'],
                    text=texts[i],
                    showarrow=True,
                    arrowhead=4,
                    arrowcolor="red",
                    font=dict(color="black", size=12)
                )

        # Tick configurations
        tick_step_x = 100
        tick_step_y = 5
        tick_values_x = list(range(
            int(filtered_df["Cum_Dist_LP"].min()),
            int(filtered_df["Cum_Dist_LP"].max()) + tick_step_x,
            tick_step_x
        ))
        tick_values_y = list(range(
            int(filtered_df["Speed"].min()),
            int(filtered_df["Speed"].max()) + tick_step_y,
            tick_step_y
        ))

        fig.update_layout(
            plot_bgcolor="white",
            xaxis=dict(
                showgrid=True,
                gridcolor="lightgray",
                title_font=dict(size=9),
                tickangle=90,
                tickmode="array",
                tickvals=tick_values_x,
                type="linear",
                tickfont=dict(size=8)  #
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="lightgray",
                title_font=dict(size=9),
                tickvals=tick_values_y,
                type="linear",
                zeroline=True,
                zerolinecolor="blue",
                zerolinewidth=1
            ),
            hoverlabel=dict(bgcolor="white", font_size=12),
            margin=dict(b=150)
        )

        # Save plot as a temp PNG file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            fig_path = tmp_file.name
            pio.write_image(fig, fig_path, format="png", width=1200, height=600, scale=2)

        # Add to PDF
        c.showPage()
        c.setPageSize(landscape(A4))
        width, height = landscape(A4)

        # Header
        c.setFont("Helvetica-Bold", 12)
        Loco_No = filtered_df["Loco_No"].min() if not filtered_df["Loco_No"].empty else "N/A"
        c.drawCentredString(width / 2, height - 30, f"Report For - CMS ID: {cms_id} & Loco No {Loco_No}")

        # Insert chart image
        c.drawImage(fig_path, x=20, y=height / 4 - 150, width=width - 40, height=600, preserveAspectRatio=True)

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, "Page 7")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

# Halt Table................................................................................................................
        c.showPage()
        c.setPageSize(landscape(A4))
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 30, f"From one Standstill to another Standstill Table for CMS ID: {cms_id}")
        c.setFont("Helvetica", 10)
        c.drawString(40, height - 50, "")# spacing
        c.drawString(40, height - 70, "Speed at Different Distance Points Before each Dead Stop (in KM/h)")   
        
        c.setFont("Helvetica-Bold", 10)
        col_widths = [40, 70, 70, 70, 90, 90, 90, 90, 90]
        headers = ["Run No", "Start Time", "End Time", "Distance (KM)", "Top Speed",
                "Before 1000m", "Before 500m", "Before 250m", "Before 10m"]
            
        x_start = 40
        y_start = height - 100
        row_height = 20
        
        # Draw headers
        x = x_start
        for i, header in enumerate(headers):
            c.setFillColor(colors.lightgrey)
            c.rect(x, y_start, col_widths[i], row_height, fill=True, stroke=False)
            c.setFillColor(colors.black)
            c.drawCentredString(x + col_widths[i]/2, y_start + 5, header)
            x += col_widths[i]
        
        c.setFont("Helvetica", 11)
        y = y_start - row_height
        run_numbers = sorted(filtered_df["Run_No"].unique())
        
        for run_no in run_numbers:
            run_data = filtered_df[filtered_df["Run_No"] == run_no].copy()
            if run_data.empty:
                continue
            
            start_time = run_data["Time"].min().strftime('%H:%M:%S') if not run_data.empty else "N/A"
            end_time = run_data["Time"].max().strftime('%H:%M:%S') if not run_data.empty else "N/A"
            distance = run_data["Distance"].sum() / 1000  # meters to km
            top_speed = round(run_data["Speed"].max(), 2) if not run_data.empty else "N/A"
            
            def get_speed_at_point(point):
                try:
                    point_data = run_data[run_data["Pin_Point"] == point]
                    return round(point_data["Speed"].iloc[0], 2) if not point_data.empty else "N/A"
                except Exception:
                    return "N/A"
            speed_1000m = get_speed_at_point("1000 Meters")
            speed_500m = get_speed_at_point("500 Meters")
            speed_250m = get_speed_at_point("250 Meters")
            speed_10m = get_speed_at_point("10 Meters")
            row_data = [
                str(run_no),
                start_time,
                end_time,
                f"{distance:.2f}",
                str(top_speed),
                str(speed_1000m),
                str(speed_500m),
                str(speed_250m),
                str(speed_10m)
            ]
            x = x_start
            for i, data in enumerate(row_data):
                c.drawCentredString(x + col_widths[i]/2, y + 5, data)
                x += col_widths[i]
            
            y -= row_height
            if y < 50:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 50

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(40, 20, "Page 8")
        c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")


# Breaking Pattern Chart as per Run Numbers..........................................................................................................................
        page_num = 10  # Starting page number

        braking_df = filtered_df[filtered_df["Rev_Dist"] < 1100].copy()
        valid_run_numbers = braking_df[braking_df["Run_Sum"] > 50]["Run_No"].unique()

        for run_no in valid_run_numbers:
            run_df = filtered_df[(filtered_df["Run_No"] == run_no) & (filtered_df["Rev_Dist"] < 1100)].copy()
            run_df = run_df.sort_values(by="Rev_Dist", ascending=False)
            top_speed = round(filtered_df[filtered_df["Run_No"] == run_no]["Speed"].max(), 2) if not run_df.empty else "N/A"

            annotation_data = {
                1000: run_df[run_df["Pin_Point"] == "1000 Meters"],
                500: run_df[run_df["Pin_Point"] == "500 Meters"],
                250: run_df[run_df["Pin_Point"] == "250 Meters"],
                10: run_df[run_df["Pin_Point"] == "10 Meters"]
            }

            Dist_points = []
            Speed_points = []
            text_values = []

            for distance, data in annotation_data.items():
                if not data.empty:
                    Dist_points.append(data["Rev_Dist"].min())
                    Speed_points.append(data["Speed"].min())
                    text_values.append(f"{distance} Meter<br>Speed: {data['Speed'].min()} kmph")

            fig = px.line(
                run_df,
                x="Rev_Dist",
                y="Speed",
                title=f"Braking Pattern Before 1000 meter of Halt - {run_no} (Max. Speed of Run: {top_speed} kmph)",
                labels={"Rev_Dist": "Distance (in Meter)", "Speed": "Speed (kmph)"},
                color_discrete_sequence=["#FF5733"]
            )
            fig.update_layout(
                plot_bgcolor="white",
                xaxis=dict(
                    showgrid=True,
                    gridcolor="lightgray",
                    title_font=dict(size=12),
                    tickangle=90,
                    type="linear",
                    autorange="reversed"
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="lightgray",
                    title_font=dict(size=12)
                ),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12
                ),
                margin=dict(b=150),
            )

            for i in range(len(Dist_points)):
                fig.add_annotation(
                    x=Dist_points[i],
                    y=Speed_points[i],
                    text=text_values[i],
                    showarrow=True,
                    arrowhead=5,
                    arrowcolor='red'
                )

            image_bytes = BytesIO()
            pio.write_image(fig, image_bytes, format="png", width=1200, height=600, scale=2)
            image_bytes.seek(0)
            img_reader = ImageReader(image_bytes)

            c.showPage()
            c.setPageSize(landscape(A4))
            width, height = landscape(A4)

            # Header
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(width / 2, height - 40, f"Braking Pattern of CMS ID: {cms_id} (Run No: {run_no})")

            # Draw chart image
            c.drawImage(img_reader, x=10, y=height/4 - 150, width=width - 20, height=600, preserveAspectRatio=True)

            # Footer with page number and fixed text
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(40, 20, f"Page {page_num}")
            c.drawRightString(width - 40, 20, "Western Railway, Mumbai Division @BDTS1022 | Generated by SPM Analysis Tool")

            page_num += 1
        c.save()
        buffer.seek(0)
        return buffer, loco_no



def main():
    # st.set_page_config(page_title="Quick Report", page_icon=":bar_chart:", layout="wide")
    st.title("Quick Report pdf Generator")

    # Hide default Streamlit sidebar buttons
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
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚨 Generate PDF Report")
    report_file = st.sidebar.file_uploader("Upload Fabricated Excel Files only", type=["xlsx"], key="quick_report_file")
    # Home button to go to design.py
    if st.sidebar.button("🏠 Back to Home", key="home_btn"):
        st.switch_page("pages/design.py")
    if report_file:
        df = pd.read_excel(report_file, engine='openpyxl')
        df.columns = df.columns.str.strip()
        if "CMS_ID" not in df.columns:
            st.sidebar.error("Wrong File Uploaded")
            st.write("Columns found:", df.columns.tolist())
        else:
            selected_cms_id = st.sidebar.selectbox("Select CMS_ID", df["CMS_ID"].dropna().unique())
            st.info("👈 Please Select CMS ID & Click Button 'Generate a Quick Report' ")
            if st.sidebar.button("Generate Report"):
                result = Quick_Report(df, selected_cms_id)
                if result is not None:
                    pdf_buffer, loco_no = result
                    # --- Log to Datbase ---
                    st.success("✅ PDF Generated Successfully!")
                    st.download_button(
                        label="📥 Download Quick Report",
                        data=pdf_buffer,
                        file_name=f"Quick Report for {selected_cms_id} - Loco_{loco_no}.pdf",
                        mime="application/pdf"
                    )
                    st.write("Download Quick Report PDF File first & Click to Edit the Downloaded PDF File online :- https://www.ilovepdf.com/edit-pdf")
                else:
                    st.error("❌ PDF Generation Failed. Please check the logs for details.")
    else:
        st.info("👈 Please upload a processed Excel file from the sidebar to generate a Quick Report.")

if __name__ == "__main__":
    main()
