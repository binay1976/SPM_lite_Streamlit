import streamlit as st
import os, socket
import base64
import logging
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.auth.exceptions import GoogleAuthError
from gspread.exceptions import GSpreadException
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)

st.set_page_config(page_title="SPM App", page_icon="🚆", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
     div.stButton > button {
        background-color: #0489aa !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        margin: 10px auto !important;
        display: block !important;
        transition: background-color 0.3s ease !important;
    }
    div.stButton > button:hover {
        background-color: orange !important;
        color: white !important;
    }

    [data-testid="stSidebar"], #MainMenu, footer, header, .stDeployButton {
        display: none !important;
    }
    /* Make inputs & buttons full width */
    .stTextInput, .stPassword, .stButton button {
        width: 100% !important;
    }
                    /* Add top margin */
    .block-container {
        padding-top: 250px !important;
    }

    /* Force responsive stacking for Streamlit columns */
    @media (max-width: 768px) {
        .stColumns {
            flex-direction: column !important;
        }
        .stColumn {
            width: 100% !important;
            margin-Top: 20px !important;
        }
    auto;
            flex: 1 1 100% !important;
            display: block !important;
        }
        /* Center the GIF */
        img {
            display: block;
            margin: 20 auto;
            max-width: 90% !important;
            height: auto;
        }
    }
    </style>
""", unsafe_allow_html=True)
# ------------------ LOGIN ------------------ #
sheet_url = "https://docs.google.com/spreadsheets/d/1e_3LQvEJrotZebyfuHRtL7klt2XmdBgxivVtE_qUA3k/edit?gid=0#gid=0"
# Google Sheets connection
def get_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Try to find the credentials file in the project root or src directory
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "gs_credentials.json"),
        os.path.join(os.path.dirname(__file__), "gs_credentials.json"),
        os.path.abspath("gs_credentials.json"),
    ]
    creds_path = None
    for path in possible_paths:
        if os.path.exists(path):
            creds_path = path
            break
    if creds_path is None:
        st.error("Google Service Account credentials file 'gs_credentials.json' not found. Please upload it to the project root or src directory.")
        raise FileNotFoundError("gs_credentials.json not found in expected locations.")
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1e_3LQvEJrotZebyfuHRtL7klt2XmdBgxivVtE_qUA3k/edit?gid=0#gid=0').worksheet('Users')
    return sheet

def authenticate_user(mobile, password):
    sheet = get_google_sheet()
    records = sheet.get_all_records()
    for user in records:
        if (
            str(user.get("Mobile", "")).strip() == str(mobile).strip()
            and str(user.get("Password", "")).strip() == str(password).strip()
            and str(user.get("Status", "")).strip().lower() == "active"
        ):
            return {
                "Name": user.get("Name", ""),
                "Lobby": user.get("Lobby", ""),
                "Mobile": user.get("Mobile", "")
            }
    return None

def authenticate_user(mobile, password):
    if not mobile.strip() or not password:
        return None

    credentials_path = os.path.join(os.path.dirname(__file__), "gs_credentials.json")
    worksheet = gspread.service_account(filename=credentials_path).open_by_url(sheet_url).sheet1
    rows = worksheet.get_all_values()
    if not rows:
        raise ValueError("The login spreadsheet is empty.")

    headers = {
        str(header).strip().casefold(): index
        for index, header in enumerate(rows[0])
    }
    if not {"mobile", "password"}.issubset(headers):
        raise ValueError("The login spreadsheet must contain mobile and password columns.")

    for row in rows[1:]:
        user = {
            header: row[index] if index < len(row) else ""
            for header, index in headers.items()
        }
        if (
            str(user.get("mobile", "")).strip() == mobile.strip()
            and str(user.get("password", "")) == password
        ):
            user["CLI_ID"] = user.get("cli_id", "")
            return user
    return None


def graph():
    # Example function
    pass

def main():
    st.markdown("""
    <style>
    .custom-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: #37568C;
        text-align: center;
        font-size: 36px;
        font-weight: bold;
        color: white;
        padding: 12px 0;
        border-bottom: 1px solid #ddd;
        z-index: 100;
    }
    /* Push page content below header */
    .block-container {
        padding-top: 80px !important;
    }
    </style>

    <div class="custom-header">
        ESMON Data Analysis App
    </div>
    """, unsafe_allow_html=True)
# Page UI Content Columns.................................................................................................................
    col1, col2 = st.columns([1,1], gap="large")
    with col1:
        gif_path = os.path.join(os.path.dirname(__file__), "Login_Page_Image.png")
        with open(gif_path, "rb") as f:
            gif_base64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <div style="margin-top: 90px; text-align: center;">
                <img src="data:image/gif;base64,{gif_base64}" style="width: 90%" />
            </div>
            """,
            unsafe_allow_html=True
        ) 
# -------------------- RIGHT SIDE (Forms with Blue BG) --------------------
    # Force scroll to top
    st.markdown("""<script>window.scrollTo(0, 0);</script>""", unsafe_allow_html=True)
    st.markdown("<div style='height:150px'></div>", unsafe_allow_html=True)
    # Reduced height spacer to ensure form isn't pushed under the footer
    st.markdown("<div style='height:50px'></div>", unsafe_allow_html=True)
    with col2:
        with st.container():
            st.title(" 🚆 Loco Pilot Driving Skill Analysis")
            if st.session_state.get("authenticated", False):
                try:
                    st.switch_page("pages/design.py")
                except Exception as e:
                    st.error(f"Error navigating to design page: {str(e)}")
            else:
                action = st.radio("Choose Action", ["Login"], horizontal=True,label_visibility="collapsed")

                if action == "Login":
                    st.subheader("Login")
                    # 👇 Show login stats as soon as page loads
                    mobile = st.text_input("Enter Mobile Number", max_chars=10, placeholder="Only 10 Digits of Registered Mobile Numbers")
                    password = st.text_input("Enter Password", type="password")
                    if st.button("Login"):
                        try:
                            user = authenticate_user(mobile, password)
                        except (
                            GSpreadException,
                            GoogleAuthError,
                            OSError,
                            RequestException,
                            ValueError,
                        ):
                            logger.exception("Could not validate login against the Google Sheet.")
                            st.error("Login validation is unavailable. Please try again later.")
                            user = None
                            sheet_error = True
                        else:
                            sheet_error = False

                        if user:
                            if str(user.get("status", "")).strip().lower() == "active":
                                st.success(f"Welcome, {user.get('name')}! Wait to Proceed")
                                st.session_state.authenticated = True
                                st.session_state.user_name = user.get("name", "")
                                st.session_state.user_lobby = user.get("lobby", "")
                                st.session_state.user_mobile = user.get("mobile", "")
                                st.session_state.user_desig = user.get("desig", "")
                                st.session_state.user_email = user.get("email", "")
                                st.session_state.user_id = user.get("CLI_ID", "")
                                st.switch_page("pages/design.py")
                            else:
                                st.warning("Your account is not activated yet.")
                        elif not sheet_error:
                            st.error("Invalid mobile or password.")
                
# Footer .........................................................................................................................
    st.markdown("""
    <style>
    .custom-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #28487A;
        text-align: center;
        font-size: 14px;
        color: white;
        padding: 8px 0;
        border-top: 1px solid #ddd;
        z-index: 100;
    }
    </style>

    <div class="custom-footer">
        SPM App Design & Development by Western Railway <br>
        &copy; 2023 ## BDTS1022. All rights reserved.
    </div>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
