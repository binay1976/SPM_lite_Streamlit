import pandas as pd
import streamlit as st
import mysql.connector
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from db_connection import get_connection, get_engine
import time
import logging



# Configure logging
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Exception Logs", page_icon="🚆", layout="wide")
st.title("🚆 Exceptions Fetch & Push to Database")

# ---------------------------- Get last processed ID ----------------------------
def get_last_processed_id():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(maindb_maxID) FROM exceptions_log")
        last_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return int(last_id or 0)
    except Exception as e:
        logger.error(f"Error getting last ID: {e}")
        st.error(f"Error getting last ID: {e}")
        return 0

   
# ---------------------------- Fetch maindb block ----------------------------
def fetch_maindb_batch(last_id):
    try:
        engine = get_engine()
        with engine.connect() as conn:
            seek_q = text("""
                SELECT CMS_ID, Loco_No, Train_No
                FROM maindb
                WHERE id > :last_id AND CMS_ID IS NOT NULL
                ORDER BY id ASC
                LIMIT 1
            """)
            res = conn.execute(seek_q, {"last_id": int(last_id)}).fetchone()
            if not res:
                return pd.DataFrame(), None

            cms_id, loco_no, train_no = res

            # Fetch the full group for this combination
            query = text("""
                SELECT id, Datetime, CMS_ID, Train_No, Loco_No, Speed, Crew_Name, Nom_CLI, Desig, uploaded_By, Train_Type, 
                       Cum_Dist_LP AS Distance, Over_Speed, Pin_Point,
                       BFT_BPT, Run_No
                FROM maindb 
                WHERE CMS_ID = :cms_id 
                  AND Loco_No = :loco_no 
                  AND Train_No = :train_no 
                ORDER BY id ASC
            """)
            df = pd.read_sql(
                query, conn, params={"cms_id": cms_id, "loco_no": loco_no, "train_no": train_no}
            )

        last_processed_id = int(df["id"].max())
        return df, last_processed_id

    except Exception as e:
        st.error(f"Error fetching batch: {e}")
        return pd.DataFrame(), last_id
    
    
# ---------------------------- Push exceptions ----------------------------
def push_exceptions(df, max_id):
    if df.empty:
        return 0
    engine = get_engine()
# Required columns --------------------------------------------------------------------
    cols = [
        "File_name", "created_at", "Datetime", "CMS_ID", "Train_No",
        "Loco_No", "Speed", "Distance", "Exception",
        "maindb_maxID", "Run_No"
    ]
# Prepare metadata ------------------------------------------------
    df["created_at"] = datetime.now(
        timezone(timedelta(hours=5, minutes=30))
    ).strftime("%Y-%m-%d %H:%M:%S")
    df["maindb_maxID"] = max_id
    df.rename(columns={"uploaded_By": "File_name"}, inplace=True)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols]
# Datetime normalize
    df["Datetime"] = (
        pd.to_datetime(df["Datetime"], errors="coerce")
        .dt.tz_localize(None)
        .dt.floor("s")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )
# String normalize
    for col in ["CMS_ID", "Train_No", "Exception"]:
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )
# Integer normalize
    for col in ["Loco_No", "Run_No"]:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            .astype(int)
        )
# 🔥 DROP DUPLICATES IN BATCH-----------------------------------------------------
    key_cols = ["Datetime", "CMS_ID", "Loco_No"]
    df = df.drop_duplicates(subset=key_cols)
    if df.empty:
        return 0

    # Convert all remaining NaN values to None for clean Database insertion
    df = df.where(pd.notnull(df), None)

# Safe insert with error handling-------------------------------------------------------
    try:
        with engine.begin() as conn:
            for _, row in df.iterrows():
                insert_stmt = text("""
                    INSERT IGNORE INTO exceptions_log
                    (File_name, created_at, Datetime, CMS_ID, Train_No,
                     Loco_No, Speed, Distance, Exception, maindb_maxID, Run_No)
                    VALUES
                    (:File_name, :created_at, :Datetime, :CMS_ID, :Train_No,
                     :Loco_No, :Speed, :Distance, :Exception, :maindb_maxID, :Run_No)
                """)
                conn.execute(insert_stmt, row.to_dict())

        return len(df)
    except Exception as e:
        logger.error(f"Insert failed: {e}")
        return 0
# ---------------------------- Exception rules ----------------------------
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

#  Get Dynamic Exceptions Rules------------------------------------------------------------------------------------
def get_rules():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            query = text("""
                SELECT id, head, speed, result
                FROM rules
                ORDER BY id ASC
            """)
            df = pd.read_sql(query, conn)
        if df.empty:
            st.error("Rules table is empty. Application cannot run without rules.")
            st.stop()
        return df
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()
rules_df = get_rules()

# Example of applying dynamic rules (this can be expanded based on actual rule structure)
def process_before_10m(df):
    if df.empty or "Pin_Point" not in df.columns or "Speed" not in df.columns:
        return pd.DataFrame()
    df["Speed"] = pd.to_numeric(df["Speed"], errors="coerce")

    # Convert rules dataframe to dictionary
    rules = {row["head"]: row for _, row in rules_df.iterrows()}
    very_risky_speed = int(rules["Before 10m >(Suspected Very Risky)"]["speed"])
    risky_speed = int(rules["Before 10m >(Suspected Risky)"]["speed"])

    results = []
    group_cols = ["CMS_ID", "Loco_No", "Train_No"]
    for keys, group in df.groupby(group_cols, dropna=False):
        subset = group[group["Pin_Point"] == "10 Meters"].copy()
        if subset.empty:
            continue
        subset["Exception"] = subset["Speed"].apply(
            lambda s: f"Before 10m >{very_risky_speed*2} (Too High Value)" if s > very_risky_speed * 2
            else (
                f"Before 10m >{very_risky_speed} (Suspected Very Risky)" if s > very_risky_speed
                else (
                    f"Before 10m >{risky_speed} (Suspected Risky)" if s > risky_speed
                    else ""
                )
            )
        )
        subset = subset[subset["Exception"] != ""]
        if not subset.empty:
            results.append(subset)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


def process_before_250m(df):
    if df.empty or "Pin_Point" not in df.columns or "Speed" not in df.columns:
        return pd.DataFrame()
    df["Speed"] = pd.to_numeric(df["Speed"], errors="coerce")

    # Convert rules dataframe to dictionary
    rules = {row["head"]: row for _, row in rules_df.iterrows()}
    very_risky_250 = int(rules["Before 250m >(Suspected Very Risky)"]["speed"])
    risky_250= int(rules["Before 250m >(Suspected Risky)"]["speed"])

    results = []
    group_cols = ["CMS_ID", "Loco_No", "Train_No"]
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


def process_data_errors(df):
    invalid = ["", "0", "0.0", "nan", "none", "<na>"]
    mask = (
        df["CMS_ID"].astype(str).str.lower().isin(invalid) | df["CMS_ID"].isna() |
        df["Loco_No"].astype(str).str.lower().isin(invalid) | df["Loco_No"].isna()
    )
    out = df[mask].copy()
    if out.empty:
        return pd.DataFrame()  # No invalid data
    out = (
        out.sort_values("id")
        .groupby(["CMS_ID", "Loco_No", "Train_No"], as_index=False)
        .first()
    )
    out["Exception"] = "Missing or 0 CMS_ID/Loco_No"
    return out

def process_id_change(df):
    if "BFT_BPT" not in df.columns: return pd.DataFrame()
    res = df[df["BFT_BPT"].astype(str).str.contains("ID Changed in Running", na=False)].copy()
    if res.empty: return pd.DataFrame()
    res["Exception"] = "ID Changed in Running"
    return res

#  This will use to Push MainDB Unique Records to Unique_MainDB -------------------------------------------------------------------------
def push_unique_block(df):
    if df.empty:
        return 0

    # Helper function to safely handle string conversion and Nulls/NaNs
    def clean_val(val, limit=None):
        if pd.isna(val) or val is None:
            return None
        s = str(val).strip()
        if s.lower() in ["nan", "none", "null", ""]:
            return None
        return s[:limit] if limit else s

    try:
        engine = get_engine()
        row = df.iloc[0]

        # Normalize Datetime
        dt = pd.to_datetime(row.get("Datetime"), errors="coerce")
        if pd.isna(dt):
            logger.error(f"Invalid Datetime for CMS_ID: {row.get('CMS_ID')}")
            return 0

        data = {
            "id": int(row.get("id")),
            "Datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "CMS_ID": clean_val(row.get("CMS_ID")),
            "Train_No": clean_val(row.get("Train_No")),
            "Loco_No": clean_val(row.get("Loco_No")),
            "Crew_Name": clean_val(row.get("Crew_Name"), 300),
            "Nom_CLI": clean_val(row.get("Nom_CLI"), 300),
            "Desig": clean_val(row.get("Desig"), 300),
            "uploaded_By": clean_val(row.get("uploaded_By"), 500),
            "Train_Type": clean_val(row.get("Train_Type"), 50),
        }

        query = text("""
        INSERT IGNORE INTO maindb_unique_2
        (id, Datetime, CMS_ID, Train_No, Loco_No,
         Crew_Name, Nom_CLI, Desig, uploaded_By, Train_Type)
        VALUES
        (:id, :Datetime, :CMS_ID, :Train_No, :Loco_No,
         :Crew_Name, :Nom_CLI, :Desig, :uploaded_By, :Train_Type)
        """)

        with engine.begin() as conn:
            result = conn.execute(query, data)
            return result.rowcount

    except Exception as e:
        logger.error(f"❌ Unique push error: {e}")
        return 0
# ---------------------------- Main ----------------------------
def run_processing():
    last_id = get_last_processed_id()
    st.info(f"Starting from ID: {last_id}")
    total_rows, total_excp = 0, 0

    while True:
        df, batch_end = fetch_maindb_batch(last_id)

        if df.empty or not batch_end:
            break
        st.divider()
        st.write(f"👉 Creating Block From id {df['id'].min()} to {batch_end}")

        file_name = df['uploaded_By'].iloc[0] if 'uploaded_By' in df.columns and not df.empty else "Unknown"
        st.write(f"Total Rows in Block for Below Crew: {len(df)} - File: {file_name}")

        unique_inserted = push_unique_block(df)

        # Collect all exception DataFrames
        frames = [
            process_overspeed(df), 
            process_before_10m(df),
            process_before_250m(df), 
            process_data_errors(df),
            process_id_change(df),
            process_bft_bpt(df)
        ]

        # Keep only valid DataFrames
        frames = [
            f for f in frames 
            if isinstance(f, pd.DataFrame) and not f.empty
        ]

        # Concatenate safely
        if frames:
            excp = (
                pd.concat(frames, ignore_index=True)
                .drop_duplicates(subset=["Datetime", "CMS_ID", "Loco_No"])
            )
        else:
            excp = pd.DataFrame()

        st.write("👉 Exceptions Found and Pushed:")
        if not excp.empty:
            for i, exc in enumerate(excp['Exception'].unique(), 1):
                st.write(f"{i}. ✅{exc}")
            pushed = push_exceptions(excp, batch_end)
            total_excp += pushed
        else:
            st.write("None")

        # Update counters
        last_id = int(batch_end)
        total_rows += len(df)

    st.success(
        f"✅ Done. Rows processed: {total_rows}, Exceptions pushed: {total_excp}"
    )


# ---------------------------- UI ----------------------------
if __name__ == "__main__":
    run_processing()
