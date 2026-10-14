from http.client import responses
import os
import streamlit as st
import pandas as pd
import re
from rapidfuzz import fuzz
import time

if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("🚫 🔐 You must login first.")
    st.header("🚫 🔐")
    st.switch_page("graph.py")
    st.stop()

st.set_page_config(page_title="SPM Chatbot", layout="wide")

# Hard-hide the sidebar completely
st.markdown("""
<style>

/* 🔥 Remove ALL Streamlit UI */
[data-testid="stSidebar"], #MainMenu, header, footer, [data-testid="stToolbar"], .stDeployButton {
    display: none !important;
}
/* 🔥 Full dark background */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #0e1117 !important;
    color: white !important;
}

/* 🔥 Proper padding (TOP 20px, LEFT/RIGHT 20px, BOTTOM 0) */
.block-container {
    padding: 20px 20px 0px 20px !important;
}

/* 🔥 Remove extra spacing */
[data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
}

/* 🔥 Labels */
label {
    color: #FCD50F !important;
}

/* 🔥 Placeholder text */
input::placeholder, textarea::placeholder {
    color: #999B9B !important;
            font-style: italic;
            font-size: 0.65em;
}

/* 🔥 Input box */
input, textarea {
    background-color: #262730 !important;
    color: white !important;
    border: 2px solid #696969 !important;
}

/* 🔥 Buttons */
button {
    background-color: #222222 !important;
    color: white !important;
    border-radius: 4px !important;
    border: 2px solid #262730 !important;
}

/* 🔥 File uploader */
div[data-testid="stFileUploader"] {
    color: lightgrey !important;
}

div[data-testid="stFileUploaderDropzone"] {
    background-color: lightgrey !important;
    color: #FCD50F !important;
}

/* Uploaded file box */
div[data-testid="stFileUploader"] section {
    background-color: #4B505A !important;
    color: white !important;
}

/* Uploaded file name */
div[data-testid="stFileUploader"] span {
    color: grey !important;
}

/* 🔥 Sidebar (if ever enabled) */
section[data-testid="stSidebar"] {
    background-color: #0e1117 !important;
}

</style>
""", unsafe_allow_html=True)

def typewriter_lines(text, speed=0.3):
    placeholder = st.empty()
    lines = text.split("\n")

    output = ""
    for line in lines:
        output += line + "  \n"   # 👈 VERY IMPORTANT (markdown line break)
        placeholder.markdown(output)
        time.sleep(speed)
# -----------------------------
# 🧠 INTENT DEFINITIONS
# -----------------------------
INTENTS = {
    "hi": ["hi", "hello", "hey", "start", "good morning", "good afternoon", "good evening"],
    "bft": ["bft", "brake feel test", "brake feel"],
    "bpt": ["bpt", "brake power test", "brake power"],
    "total_time": ["total time", "duty hrs", "duration", "time taken", "how long"],
    "total_distance": ["total distance", "total kms", "distance covered"],
    "crew_list": ["all crew", "crew list", "unique crew", "crew names", "cms id list", "total crew", "total lp", "all lp", "unique lp", "lp list"],
    "loco": ["loco", "loco no", "locomotive"],
    "train": ["train", "tr", "tr no",  "train no", "train number", "train details", "train detail", "train type", "goods", "passenger", "tr type"],
    "crew": ["crew", "lp info", "crew details", "crew info","lp", "loco pilot", "who is lp", "lp of", "lp name"],
    "trip": ["trip", "journey", "run", "trip details" , "trip detail"],
    "top_speed": ["top speed", "maximum speed", "mps", "max speed"],
    "start_time": ["start time", "departure time", "trip start"],
    "finish_time": ["finish time", "arrival time", "trip finish"],
    "braking": ["braking", "braking pattern", "10 meter", "250 meter","before 10 m", "before 250 m"],
    "overspeed": ["overspeed", "over speed", "over speeding", "overspeeding"],
    "unknown": ["unknown"]
}

# -----------------------------
# 🔍 INTENT DETECTION (FUZZY)
# -----------------------------
# def detect_intent(question):
#     q = question.lower()
#     best_match, best_score = None, 0

#     for intent, keywords in INTENTS.items():
#         for word in keywords:
#             score = fuzz.partial_ratio(q, word)
#             if score > best_score:
#                 best_score = score
#                 best_match = intent

#     return best_match if best_score > 70 else "unknown"

def detect_intent(question):
    q = question.lower()

    # Priority rules
       
    if "all crew" in q or "crew list" in q or "total crew" in q or "total lp" in q or "unique crew" in q or "crew names" in q or "cms id list" in q or "all crew" in q or "all lp" in q or "unique lp" in q or "lp list" in q:
        return "crew_list"
    
    if "lp" in q or "crew" in q or "crew name" in q or "loco pilot" in q or "who is lp" in q or "lp of" in q or "lp name" in q:
        return "crew"

    if "train" in q or "train no" in q or "train number" in q or "train details" in q or "train detail" in q or "train run" in q or "tr run" in q or "train type" in q or "goods" in q or "passenger" in q or "tr type" in q:
        return "train"

    if "loco" in q or "loco no" in q or "locomotive" in q:
        return "loco"
    
    if "overspeed" in q or "over speed" in q or "over speeding" in q or "over speeding" in q or "overspeeding" in q:
        return "overspeed"

    if "bft" in q:
        return "bft"

    if "bpt" in q:
        return "bpt"
    
    if "total time" in q or "duty hrs" in q or "duration" in q or "time taken" in q or "how long" in q:
        return "total_time"
    
    if "trip details" in q or "trip detail" in q or "journey" in q or "journey details" in q or "run detail" in q:
        return "trip"
    
    if "braking" in q or "10" in q or "10m" in q or "10 m" in q or "250" in q or "250 m" in q or "250m" in q or "speed at 10" in q or "speed at 250" in q or "before 10 m" in q or "before 250 m" in q:
        return "braking"

    # fallback
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if kw in q:
                return intent

    return "unknown"

# -----------------------------
# 🔎 PARAM EXTRACTION
# -----------------------------
def extract_cms_id(question):
    if not question:   # ✅ FIX
        return None
    import re
    q = question.upper()
    tokens = re.findall(r'\b[A-Z0-9]+\b', q)
    # Priority 1: Token with BOTH letters AND digits (like ADI2574, 1460UDN)
    for token in tokens:
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            return token
    # Priority 2: Pure numeric token (like 0)
    for token in tokens:
        if token.isdigit():
            return token
    return None

# -----------------------------
# ⚙️ RULE ENGINE
# -----------------------------
def ensure_datetime(df):
    df.columns = df.columns.str.strip()
    if 'Datetime' in df.columns:
        return pd.to_datetime(df['Datetime'], errors='coerce')
    elif 'Date' in df.columns and 'Time' in df.columns:
        return pd.to_datetime(
            df['Date'].astype(str) + ' ' + df['Time'].astype(str),
            errors='coerce'
        )
    for col in df.columns:
        if "date" in col.lower() and "time" in col.lower():
            return pd.to_datetime(df[col], errors='coerce')
    return None

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def handle_hi():
    response = """
    👋 Hello! I am your AI-powered SPM Ginie 🤖 !!!
        I can help you analyze Your Uploaded Excel file with SPM data quickly and accurately.  
        Just ask in simple language, and I will fetch insights from your uploaded Excel file.

        🔍 Here is what I can do:
        • Show trip details (duty time, distance, speed)
        • Provide BFT / BPT analysis
        • Analyze braking patterns (10m / 250m)
        • Fetch train, loco, and crew information
        • Calculate total time, top speed, average speed
        • Identify risky braking patterns

        💡 Try asking:
        • "Trip details of CMS ID ADI2574"
        • "BFT details of UDN1460"
        • "Braking pattern of ADI1270"
        • "Train number of CMS ID ADI2574"

        Lets get started! 🚀 I am Learning now...keep Asking
        
        🔥 Ask me about :: train details, Crew Details, BPT details, BFT Details, Duty hours, or braking patterns....
        🔥 Include CMS_ID for specific queries (e.g., 'Braking pattern of ADI1234')

        Developed by Binay Kumar | Mumbai Division |Western Railway | Version 3.2
    """
    return response.strip()


def handle_total_time(df, question):
    # 🔥 Auto-detect datetime
    if 'Datetime' in df.columns:
        df['Datetime'] = pd.to_datetime(df['Datetime'])
    elif 'Date' in df.columns and 'Time' in df.columns:
        df['Datetime'] = pd.to_datetime(
            df['Date'].astype(str) + ' ' + df['Time'].astype(str)
        )
    else:
        return "❌ No valid Date/Time column found"
    cms_id = extract_cms_id(question)
    if cms_id:
        temp = df[df['CMS_ID'].astype(str).str.upper() == cms_id]
        if temp.empty:
            return "No data found"
        return temp['Datetime'].max() - temp['Datetime'].min()
    result = df.groupby('CMS_ID')['Datetime'].agg(['min', 'max'])
    result['Total_Time'] = (result['max'] - result['min']).apply(format_timedelta)
    return result[['Total_Time']]


def handle_crew_list(df):
    all_lp = df[['CMS_ID', 'Crew_Name','Desig','Nom_CLI']].drop_duplicates().sort_values(by='CMS_ID')
    lp_counts = all_lp['CMS_ID'].drop_duplicates().count()
    response = f"""
        Total Crew Data Found :- {lp_counts}
        {all_lp.astype(str).apply(lambda row: " || ".join(row), axis=1).to_string(index=False)}

        🔥 Ask me about :: train details, Crew Details, BPT details, BFT Details, Duty hours, or braking patterns....
        🔥 Include CMS_ID for specific queries (e.g., 'Braking pattern of ADI1234')
    
        """
    return response.strip()

def handle_Loco(df, question=None):
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    if 'Loco_No' not in df.columns:
        return "❌ Loco_No column not found"
    val = df['Loco_No'].dropna().iloc[0]
    try:
        if float(val).is_integer():
            val = str(int(float(val)))
        else:
            val = str(val)
    except:
        val = str(val)
    return f"🚆 Loco No for CMS_ID {cms_id} → {val}"


def handle_train(df, question=None):
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    if 'Train_No' not in df.columns:
        return "❌ Train_No column not found"
    if 'Train_No' in df.columns:
        val_series = df['Train_No'].dropna()
        val = val_series.iloc[0] if not val_series.empty else "no info Available"
    else:
        val = "no info Available"

    # 🚄 Train Type
    if 'Train_Type' in df.columns:
        type_series = df['Train_Type'].dropna()
        type = type_series.iloc[0] if not type_series.empty else "Data Not Available"
    else:
        type = "Data Not Available"
    try:
        if float(val).is_integer():
            val = str(int(float(val)))
        else:
            val = str(val)
    except:
        val = str(val)
    return f"🚆 Train No for CMS_ID {cms_id} → {val} | Train Type → {type}"


def handle_crew(df, question):
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    if 'Crew_Name' not in df.columns:
        return "❌ Crew_Name column not found"
    val = df['Crew_Name'].drop_duplicates().iloc[0] if 'Crew_Name' in df.columns else "Not Found"
    desig = df['Desig'].drop_duplicates().iloc[0] if 'Desig' in df.columns else "Not Found"
    nom_cli = df['Nom_CLI'].drop_duplicates().iloc[0] if 'Nom_CLI' in df.columns else "Not Found"
    response = f"""
        Crew Name :- {val}
        CMS ID :- {cms_id}
        Designation :- {desig}
        Nominated CLI :- {nom_cli}

        🔥 Ask me about :: train details, Crew Details, BPT details, BFT Details, Duty hours, or braking patterns....
        🔥 Include CMS_ID for specific queries (e.g., 'Braking pattern of ADI1234')
    
        """
    return response.strip()

def handle_distance(df, question=None):
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    if 'Cum_Dist_LP' not in df.columns:
        return "❌ Distance column not found"
    distance = df['Cum_Dist_LP'].max()/1000 if pd.notna(df['Cum_Dist_LP'].max()) else "N/A"
    return f"📏 Total Distance covered by CMS_ID {cms_id} → {distance} KM"

def handle_duty_hours(df, question=None):
    df['Datetime'] = ensure_datetime(df)
    if df['Datetime'] is None:
        return "❌ No valid Date/Time column found"
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    start_time = df['Datetime'].min()
    end_time = df['Datetime'].max()
    duty_hours = end_time - start_time
    return f"⏱ Total Duty Hours for CMS_ID {cms_id} → {format_timedelta(duty_hours)}"        


def handle_top_speed(df, question=None):
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    df.columns = df.columns.str.strip()
    if 'Speed' not in df.columns:
        return "❌ Speed column not found"
    df['Speed'] = pd.to_numeric(df['Speed'], errors='coerce')
    max_speed = df['Speed'].max()
    if pd.isna(max_speed):
        return "❌ No valid speed data"
    train_no = df.loc[df['Speed'].idxmax(), 'Train_No'].astype(str) if 'Train_No' in df.columns else "Unknown Train"
    return f"🚀 Top Speed for CMS_ID {cms_id} || Train No: {train_no} → {int(max_speed)}"


def handle_start_time(df, question=None):
    df['Datetime'] = ensure_datetime(df)
    if df['Datetime'] is None:
        return "❌ No valid Date/Time column found"
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    start_time = df['Datetime'].min()
    response = f"""
    For CMS ID :- {cms_id}
    Train Departure Time :- {start_time}
    may ask for "trip details of CMS ID {cms_id}" to get complete info of train, duty hours, distance, speed and much more...
    """
    return response.strip()

def handle_finish_time(df, question=None):
    df['Datetime'] = ensure_datetime(df)
    if df['Datetime'] is None:
        return "❌ No valid Date/Time column found"
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    end_time = df['Datetime'].max()
    response = f"""
    For CMS ID :- {cms_id}
    Train Arrival Time :- {end_time}
    may ask for "trip details of CMS ID {cms_id}" to get complete info of train, duty hours, distance, speed and much more...
    """
    return response.strip()
   

def handle_bft(df, question=None):
    df['Datetime'] = ensure_datetime(df)
    if df['Datetime'] is None:
        return "❌ No valid Date/Time column found"
    # ✅ STEP 1: FILTER FIRST (ONLY ONCE)
    cms_id = None
    if question:
        cms_id = extract_cms_id(question)
        if cms_id:
            cms_id = cms_id.strip().upper()
            df_filtered = df[df['CMS_ID'] == cms_id]
            if df_filtered.empty:
                return f"❌ Alert:- CMS ID:{cms_id} Not Found, Please Ask for a Valid/Available CMS ID"
            df = df_filtered
    # ✅ STEP 2: BFT LOGIC ON FILTERED DATA ONLY
    bft_start = df[df['BFT_BPT'].astype(str).str.contains("BFT", case=False, na=False)]
    bft_end = df[df['BFT_BPT'].astype(str).str.contains("BFT_END", case=False, na=False)]
    if bft_start.empty:
        if cms_id:
            return f"❌ Failed:- BFT Not Done by CMS ID: {cms_id}"
    if bft_end.empty:
        return f"❌ Failed:- Improper BFT by CMS ID: {cms_id}"
    start_row = bft_start.iloc[0]
    end_row = bft_end.iloc[0]
    if end_row['Datetime'] < start_row['Datetime']:
        return "❌ Invalid BFT (End before Start)"
    # 🔥 Total Time
    time_diff = end_row['Datetime'] - start_row['Datetime']
    total_seconds = int(time_diff.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    total_time = f"{h:02}:{m:02}:{s:02}"
    # 🔥 Distance
    if 'Distance' in df.columns:
        try:
            distance = end_row['Distance'] - start_row['Distance']
            if distance < 0:
                distance = df.loc[start_row.name:end_row.name, 'Distance'].fillna(0).sum()
        except:
            distance = "N/A"
    else:
        distance = "N/A"

    # ✅ Output
    response = f"""
        🚆 Brake Feel Test (BFT) DETAILS
        For Crew → {start_row['CMS_ID']} | {start_row['Crew_Name']} | {start_row['Desig']} | CLI- {start_row['Nom_CLI']}
        Started at → {start_row['Datetime']} at Speed {start_row['Speed']} KMPH
        Finished at  → {end_row['Datetime']} at Speed {end_row['Speed']} KMPH

        ⏱ Total Time Taken : {total_time}
        📏 In Distance   : {distance} meter

        🔥 Ask me about :: train details, Crew Details, BPT details, BFT Details, Duty hours, or braking patterns....
        🔥 Include CMS_ID for specific queries (e.g., 'Braking pattern of ADI1234')
        """
    return response.strip()


def handle_bpt(df, question=None):
    df['Datetime'] = ensure_datetime(df)
    if df['Datetime'] is None:
        return "❌ No valid Date/Time column found"
    cms_id = None
    if question:
        cms_id = extract_cms_id(question)
        if cms_id:
            cms_id = cms_id.strip().upper()
            df_filtered = df[df['CMS_ID'] == cms_id]
            if df_filtered.empty:
                return f"❌ Alert:- CMS ID:{cms_id} Not Found, Please Ask for a Valid/Available CMS ID"
            df = df_filtered
    bpt_start = df[df['BFT_BPT'].astype(str).str.contains("BPT", case=False, na=False)]
    bpt_end = df[df['BFT_BPT'].astype(str).str.contains("BPT_END", case=False, na=False)]
    if bpt_start.empty:
        if cms_id:
            return f"❌ Failed:- BPT Not Done by CMS ID: {cms_id}"
    if bpt_end.empty:
        return f"❌ Failed:- Improper BPT by CMS ID: {cms_id}"
    start_row = bpt_start.iloc[0]
    end_row = bpt_end.iloc[0]
    if end_row['Datetime'] < start_row['Datetime']:
        return "❌ Invalid BPT (End before Start)"
    time_diff = end_row['Datetime'] - start_row['Datetime']
    total_seconds = int(time_diff.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    total_time = f"{h:02}:{m:02}:{s:02}"
    if 'Distance' in df.columns:
        try:
            distance = end_row['Distance'] - start_row['Distance']
            if distance < 0:
                distance = df.loc[start_row.name:end_row.name, 'Distance'].fillna(0).sum()
        except:
            distance = "N/A"
    else:
        distance = "N/A"
    response = f"""
            🚆 Brake Power Test (BPT) DETAILS
            For Crew → {start_row['CMS_ID']} | {start_row['Crew_Name']} | {start_row['Desig']} | CLI- {start_row['Nom_CLI']}
            Started at → {start_row['Datetime']} at Speed {start_row['Speed']} KMPH
            Finished at  → {end_row['Datetime']} at Speed {end_row['Speed']} KMPH

            ⏱ Total Time taken : {total_time}
            📏 In Distance   : {distance} meter

            🔥 Ask me about :: train details, Crew Details, BPT details, BFT Details, Duty hours, or braking patterns....
            🔥 Include CMS_ID for specific queries (e.g., 'Braking pattern of ADI1234')
            """
    return response.strip()


#  Get Run Summary (All-in-One)-------------------------------------------
def safe_first(df, col):
    if col in df.columns:
        series = df[col].dropna()
        if not series.empty:
            return str(series.iloc[0])
    return "-"


def handle_trip(df, question=None):
    df['Datetime'] = ensure_datetime(df)
    if df['Datetime'] is None:
        return "❌ No valid Date/Time column found"
    
    df['Datetime'] = pd.to_datetime(
    df['Date'].astype(str) + " " + df['Time'].astype(str),
    dayfirst=True,
    errors='coerce')

    df = df.sort_values(by='Datetime')
    df['time_diff'] = df['Datetime'].diff().dt.total_seconds() / 3600
    df['trip_id'] = (df['time_diff'] > 5).cumsum()

    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question)
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    crew_name = safe_first(df, 'Crew_Name')
    desig = safe_first(df, 'Desig')
    cli = safe_first(df, 'Nom_CLI')

    train = (
        df['Train_No']
        .dropna()
        .apply(lambda x: str(int(x)) if str(x).replace('.', '', 1).isdigit() else str(x))
        .unique()
        ) if 'Train_No' in df else []
    train_str = ", ".join(train) if len(train) > 0 else "-"
    loco = df['Loco_No'].dropna().astype(str).unique() if 'Loco_No' in df else []
    loco_str = ", ".join(loco) if len(loco) > 0 else "-"
    # tr_type = df['Train_Type'].dropna().astype(str).unique() if 'Train_Type' in df else []
    if 'Train_Type' in df.columns:
        type_series = df['Train_Type'].dropna()
        type = type_series.iloc[0] if not type_series.empty else "Data Not Available"
    else:
        type = "Data Not Available"
    tr_type = [type]
    tr_type_str = ", ".join(tr_type) if len(tr_type) > 0 else "-"
    start_time = df['Datetime'].min()
    end_time = df['Datetime'].max()
    total_seconds = int((end_time - start_time).total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    total_time = f"{h:02}:{m:02}:{s:02}"
    if 'Cum_Dist_LP' in df.columns:
        try:
            distance = df['Cum_Dist_LP'].max() / 1000 if pd.notna(df['Cum_Dist_LP'].max()) else "N/A"
        except:
            distance = "N/A"
    else:
        distance = "N/A"
    max_speed = df['Speed'].max() if 'Speed' in df.columns else "N/A"
    try:
        avg_speed = round(distance / (total_seconds / 3600), 2) if total_seconds > 0 else 0
    except:
        avg_speed = "N/A"
    bft_flag = "Yes" if df['BFT_BPT'].astype(str).str.contains("BFT", case=False, na=False).any() else "No"
    bpt_flag = "Yes" if df['BFT_BPT'].astype(str).str.contains("BPT", case=False, na=False).any() else "No"


    if 'Train_No' in df.columns:
        df['Train_No'] = df['Train_No'].astype(str).str.strip()
        grouped = df.groupby(['Train_No', 'trip_id'])
    else:
        grouped = [('Unknown', 0), df]

    responses = []
    for (train_no, trip_id), group in grouped:

        # --- Basic Info ---
        crew_name = safe_first(group, 'Crew_Name')
        desig = safe_first(group, 'Desig')
        cli = safe_first(group, 'Nom_CLI')

        loco = group['Loco_No'].dropna().astype(str).unique() if 'Loco_No' in group else []
        loco_str = ", ".join(loco) if len(loco) > 0 else "-"

        tr_type = group['Train_Type'].dropna().astype(str).unique() if 'Train_Type' in group else []
        tr_type_str = ", ".join(tr_type) if len(tr_type) > 0 else "-"

        # --- Time ---
        start_time = group['Datetime'].min()
        end_time = group['Datetime'].max()

        total_seconds = int((end_time - start_time).total_seconds())
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        total_time = f"{h:02}:{m:02}:{s:02}"

        # --- Distance ---
        if 'Cum_Dist_LP' in group.columns:
            try:
                distance = group['Cum_Dist_LP'].max() / 1000
            except:
                distance = "N/A"
        else:
            distance = "N/A"

        # --- Speed ---
        max_speed = group['Speed'].max() if 'Speed' in group.columns else "N/A"

        try:
            avg_speed = round(distance / (total_seconds / 3600), 2) if total_seconds > 0 else "N/A"
        except:
            avg_speed = "N/A"

        # --- Safety ---
        bft_flag = "Yes" if group['BFT_BPT'].astype(str).str.contains("BFT", case=False, na=False).any() else "No"
        bpt_flag = "Yes" if group['BFT_BPT'].astype(str).str.contains("BPT", case=False, na=False).any() else "No"

        # --- Clean Train No ---
        try:
            train_no_clean = str(int(float(train_no)))
        except:
            train_no_clean = str(train_no)

        trip_text = f"""
            🚆 TRIP DETAILS ({train_no_clean}) --------------------
            ⚡ Crew: {crew_name} / {desig} | CLI: {cli}
            🚄 Train Type: {tr_type_str} | Loco: {loco_str}
            🕒 Start: {start_time} | End: {end_time}
            🕒 Total Duty Hrs : {total_time}
            🚄 Total Distance Travelled : {distance} KM | Avg Speed: {avg_speed} | Top Speed: {max_speed}
            ⚡ Safety Checks:
                Brake feel Test (BFT): {bft_flag} | Brake Power Test (BPT): {bpt_flag}
            """
        responses.append(trip_text.strip())

    final_response = f"""
        🚆 CREW SUMMARY (CMS_ID: {cms_id})
        ----------------------------------

        """ + "\n\n".join(responses)

    return final_response.strip()


# Baraking patterns at 10 M & 250 M-------------------------------------
def handle_braking(df, question=None):
    # ✅ Normalize CMS_ID (important)
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    # ✅ Extract CMS_ID
    cms_id = extract_cms_id(question)
    crew_name = safe_first(df, 'Crew_Name')
    desig = safe_first(df, 'Desig')
    cli = safe_first(df, 'Nom_CLI')
    if not cms_id:
        return "❌ Please provide CMS_ID"
    df = df[df['CMS_ID'] == cms_id]
    if df.empty:
        return f"❌ No data found for CMS_ID {cms_id}"
    if 'Pin_Point' not in df.columns or 'Speed' not in df.columns:
        return "❌ Required columns Pin_Point / Speed not found"
    df['Pin_Point'] = df['Pin_Point'].astype(str).str.lower().str.strip()

    # 🔥 Extract Speeds (accurate matching)
    speed_10 = df[df['Pin_Point'].str.contains(r'\b10\b', regex=True, na=False)]['Speed'].dropna().tolist()
    speed_250 = df[df['Pin_Point'].str.contains(r'\b250\b', regex=True, na=False)]['Speed'].dropna().tolist()

    # 🔥 Risk Calculation Function
    def analyze_speed(speed_list, limit1, limit2):
        risky = 0
        very_risky = 0

        for s in speed_list:
            try:
                s = float(s)
                if s > limit2:
                    very_risky += 1
                elif s > limit1:
                    risky += 1
            except:
                continue

        return risky, very_risky
    # 🔥 Apply Rules
    risky_10, very_risky_10 = analyze_speed(speed_10, 7, 10)
    risky_250, very_risky_250 = analyze_speed(speed_250, 30, 35)
    # 🔥 Convert to string
    speed_10_str = ", ".join(map(str, speed_10)) if speed_10 else "No Data"
    speed_250_str = ", ".join(map(str, speed_250)) if speed_250 else "No Data"
    # 🔥 Summary Text
    summary_10 = f"({risky_10} Risky & {very_risky_10} ⚡ Very Risky)" if speed_10 else ""
    summary_250 = f"({risky_250} Risky & {very_risky_250} ⚡ Very Risky)" if speed_250 else ""

    # ✅ Final Output
    response = f"""
    🚆 BRAKING PATTERN OF (CMS_ID: {cms_id} | {crew_name} | {desig})

    10 Meter Before Halt  → {speed_10_str}
    ⚡ {summary_10}

    250 Meter Before Halt → {speed_250_str}
    ⚡ {summary_250}

    🔥 Ask me about :: train details, Crew Details, BPT details, BFT Details, Duty hours, or braking patterns....
    🔥 Include CMS_ID for specific queries (e.g., 'Braking pattern of ADI1234')
    """

    return response.strip()


def handle_overspeed(df, question=None):

    # ✅ Normalize columns
    df.columns = df.columns.str.strip()

    # ✅ Check column exists
    if 'Over_Speed' not in df.columns:
        return "❌ Over_Speed column not found"

    # ✅ Ensure Datetime exists
    df['Datetime'] = ensure_datetime(df)
    if df['Datetime'] is None:
        return "❌ No valid Date/Time column found"

    # ✅ Filter CMS_ID (if asked)
    df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
    cms_id = extract_cms_id(question) if question else None

    if cms_id:
        df = df[df['CMS_ID'] == cms_id]
        if df.empty:
            return f"❌ No data found for CMS_ID {cms_id}"

    # ✅ Filter Overspeed rows
    over_df = df[
        df['Over_Speed']
        .astype(str)
        .str.contains("overspeed", case=False, na=False)
    ]

    if over_df.empty:
        return "✅ No Overspeed events found"

    # ✅ Select required columns safely
    cols = []

    if 'Date' in df.columns:
        cols.append('Date')
    if 'Time' in df.columns:
        cols.append('Time')
    if 'Speed' in df.columns:
        cols.append('Speed')
    if 'Train_No' in df.columns:
        cols.append('Train_No')
    cols.append('Over_Speed')

    over_df = over_df[cols]

    # ✅ Format output
    formatted = over_df.astype(str).apply(lambda row: " || ".join(row), axis=1)

    response = f"""
🚨 OVERSPEED EVENTS DETECTED
----------------------------------
""" + "\n".join(formatted)

    return response.strip()


# -----------------------------
# 🤖 MAIN CHATBOT ENGINE
# -----------------------------
def chatbot(question, df):
    intent = detect_intent(question)

    if intent == "total_time":
        return handle_total_time(df, question)
    
    if intent == "hi":
        return handle_hi()
    
    elif intent == "start_time":
        return handle_start_time(df, question)
    
    elif intent == "finish_time":
        return handle_finish_time(df, question)
    
    elif intent == "top_speed":
        return handle_top_speed(df, question)
    
    elif intent == "duty_hours":
        return handle_duty_hours(df, question)
    
    elif intent == "overspeed":
        return handle_overspeed(df, question)
    
    elif intent == "total_distance":
        return handle_distance(df, question)
    
    elif intent == "bpt":
        return handle_bpt(df, question)

    elif intent == "crew_list":
        return handle_crew_list(df)

    elif intent == "loco":
        return handle_Loco(df,question)

    elif intent == "train":
        return handle_train(df,question)
    
    elif intent == "crew":
        return handle_crew(df,question)

    elif intent == "bft":
        return handle_bft(df, question)
    
    elif intent == "trip":
        return handle_trip(df, question)

    elif intent == "braking":
        return handle_braking(df, question)

    else:
        return "❓ Please Ask some Valid Questions !!!. Try: 'Trip details', 'crew list', 'BFT details'"

# -----------------------------
# 🚀 STREAMLIT UI
# -----------------------------
def format_response(result):
    if not isinstance(result, pd.DataFrame):
        return str(result)
    df = result.fillna("-")
    df = df.astype(str)
    # Calculate column widths
    col_widths = {}
    for col in df.columns:
        max_len = max(df[col].map(len).max(), len(col))
        col_widths[col] = max_len
    # Header
    header = " | ".join([col.ljust(col_widths[col]) for col in df.columns])
    separator = "-+-".join(["-" * col_widths[col] for col in df.columns])
    # Rows
    rows = []
    for _, row in df.iterrows():
        row_str = " | ".join([row[col].ljust(col_widths[col]) for col in df.columns])
        rows.append(row_str)
    return f"{header}\n{separator}\n" + "\n".join(rows)

col1, col2, col3= st.columns([2, 4, 2])
with col1:
    import os
    st.markdown(
    "<h1 style='text-align: center; color: #4B505A'>AI Powered <br> SPM Chatbot</h1>",
    unsafe_allow_html=True
    )
    logo_path = os.path.join(os.path.dirname(__file__), "AI_Logo.png")
    if os.path.exists(logo_path):
        try:
            st.image(logo_path, width=400)
        except Exception as e:
            st.warning(f"Failed to load AI_Logo.png: {str(e)}")
    col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
    with col_btn2:
        if st.button("🏠 Back to Home", key="home_btn"):
            st.switch_page("pages/design.py")

with col2:
    uploaded_file = st.file_uploader(
    "Upload Fabricated Excel File & Ask Questions in Natural Language",type=["xlsx"])
    if uploaded_file:
        @st.cache_data
        def load_data(file):
            return pd.read_excel(file, engine='openpyxl')
        try:
            df = load_data(uploaded_file)
            # ✅ Normalize column names
            df.columns = df.columns.str.strip()
            # ✅ Required columns
            required_cols = ["Date", "Time", "Speed", "Distance", "CMS_ID"]
            # 🔥 Check if required columns exist
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"❌ Invalid File Format!\nMissing Columns: {', '.join(missing_cols)}")
            else:
                st.write("✅ Excel Captured Successfully!")

        except Exception as e:
            st.error("❌ Unreadable or Corrupted Excel File Uploaded!")
        df = load_data(uploaded_file)
        df.columns = df.columns.str.strip()
        if 'CMS_ID' in df.columns:
            df['CMS_ID'] = df['CMS_ID'].astype(str).str.strip().str.upper()
        # st.dataframe(df.head())
        cms_ids = ', '.join(df['CMS_ID'].unique()[:20])
        st.markdown(
            f"""
            <p style="
                font-family: 'Courier New', Courier, monospace;
                font-size: 13px;
            ">
                ✅ Available CMS IDs are :- {cms_ids}
            </p>
            """,
            unsafe_allow_html=True
        )
        question = st.text_input("💬 Ask your question & press Enter", placeholder="Examples: 'Braking pattern of ADI1234', 'What is the total time of CMS ID UDN1460?', 'Show All crew', 'BFT details of ADI2574'")

        import time
        placeholder = st.empty()
        # ⚡ Step 1: Pre-Processing Animation
        messages = [
            "⚡ Fetching data from AI engine........",
            "🧠 Analyzing Logical Parameters..."
        ]
        for msg in messages:
            placeholder.markdown(f"""
            <div style="
                background-color:#262730;
                color:white;
                padding:10px 12px;
                border-radius:10px;
                margin:8px 0;
                font-family: 'Courier New', monospace;
                font-size: 0.85em;
            ">
                🤖 {msg}
            </div>
            """, unsafe_allow_html=True)
            time.sleep(2)   # ⏱ 2 sec gap between messages
        # 🧠 Step 2: Actual Processing (after animation)
        with st.spinner("Thinking..."):
            result = chatbot(question, df)
            response = format_response(result)
        # ✍️ Step 3: Typing Animation
        typed = ""
        for line in response.split("\n"):
            typed += line + "<br>"
            placeholder.markdown(f"""
            <div style="
                background-color:#262730;
                color:white;
                padding:10px 12px;
                border-radius:10px;
                margin:8px 0;
                max-width:100%;
                font-family: 'Courier New', monospace;
                font-size: 0.85em;
            ">
                🤖 {typed}
            </div>
            """, unsafe_allow_html=True)

            time.sleep(0.25)   # 👈 animation happens here

with col3:
    st.markdown(
    "<h2 style='text-align: center; color: #807D7C'>How to Ask?</h2>",
    unsafe_allow_html=True
    )
    st.markdown(
    """
    <ul style='color: #807D7C; font-family: Arial, sans-serif; font-size: 16px;'>
        <li>Use keywords like 'Trip Details', 'total time', 'crew list', 'BFT details', 'train info'</li>
        <li>Include CMS_ID for specific queries (e.g., 'Braking pattern of ADI1234')</li>
        <li>Ask about trip details, train details, Crew Details, BPT details,Duty hours, or braking patterns</li>
        <li>Example: 'What is the Trip details of ADI1234?'</li>
        <li>Example: 'What is the total time UDN1460?'</li>
        <li>Example: 'What is the total Traveltime of CMS ID UDN1460?'</li>
        <li>Example: 'Show All crew'</li>
        <li>Example: 'BFT or BPT details of ADI2574'</li>
    </ul>
    """,
    unsafe_allow_html=True
    )