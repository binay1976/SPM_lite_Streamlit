import streamlit as st
import os, socket

st.set_page_config(page_title="SPM App", page_icon="🚆", layout="wide")
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("🚫 🔐 You must login first.")
    st.header("🚫 🔐")
    st.switch_page("graph.py")
    st.stop()

# --- Custom CSS for Buttons and Links ---
st.markdown("""
<style>
/* General Streamlit Button Styling */
div.stButton > button {
    background-color: #BA028E !important;
    color: white !important;
    border: 1px solid #ddd !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    padding: 12px 24px !important;
    width: 250px !important;
    font-weight: bold !important;
    font-size: 16px !important;
    margin: 10px auto !important;
    display: block !important;
    transition: background-color 0.3s ease, color 0.3s ease !important;
}

/* General Button Hover */
div.stButton > button:hover {
    background-color: #0963B0 !important;
    color: white !important;
    border-color: orange !important;
}

/* Custom Link Styling */
.custom-link {
    display: block;
    width: 250px;
    box-sizing: border-box;
    text-align: center;
    padding: 12px 24px;
    margin: 30px auto;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    border: 1px solid #ddd;
    font-size: 16px;
    font-weight: bold;
    background-color: #CB0EED;
    color: white !important;
    text-decoration: none !important;
    border-radius: 10px;
    transition: background-color 0.3s ease, color 0.3s ease;
}

.custom-link:hover {
    background-color: #7a7a7a;
    color: white !important;
    text-decoration: none !important;
}

/* Hide Sidebar Navigation, Toolbar, Deploy Button and Footer */
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarNavSeparator"],
    [data-testid="stToolbar"],
    [data-testid="stDeployButton"],
    footer {
        display: none !important;
        visibility: hidden !important;
    }

/* Special Button: disabled key */
.st-key-disabled button {
    background-color: black !important;
    color: white !important;
    border: none !important;
}

/* Special Button Hover */
.st-key-disabled button:hover {
    background-color: #333333 !important;
    color: white !important;
    border: none !important;
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
def get_user_stats():
    try:
        with managed_connection() as conn:
            with conn.cursor() as cursor:
                # Total logins
                cursor.execute("SELECT COUNT(*) FROM users")
                users = cursor.fetchone()[0]

                # Excel Fabricated Count
                cursor.execute("SELECT COUNT(*) FROM action_logs WHERE event = 'Excel Fabricated' ")
                excel = cursor.fetchone()[0]

                # Report Generated Count
                cursor.execute("SELECT COUNT(*) FROM action_logs WHERE event = 'Report Generated' ")
                report = cursor.fetchone()[0]

                return users, excel, report
    except Exception as e:
        st.error(f"Could not fetch login stats: {e}")
        return 0, 0, 0

# Sidebar image
gif_path = os.path.join(os.path.dirname(__file__), "..", "Ver_3_2.ico")
if os.path.exists(gif_path):
    try:
        st.sidebar.image(gif_path, width=180)
    except Exception as e:
        st.sidebar.warning(f"Failed to load Ver_3_2.ico: {str(e)}")
else:
    st.sidebar.warning("Icon not found at the specified path.")

st.sidebar.markdown('-----')
st.write(f"👤Welcome {st.session_state.get('user_name', '')}/{st.session_state.get('user_id', '')}-{st.session_state.get('user_desig', '')}")
# === Logout button ===
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.switch_page("graph.py")
    st.sidebar.success("✅ Logged out successfully.")
    st.rerun()



col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<h4 style='font-size:22px; text-align:center;'>🧭 Raw File Processing</h4>", unsafe_allow_html=True)
    with st.container():
        if st.button("Medha (Raw txt)", key="medha_btn"):
            st.switch_page("pages/Medha.py")
        if st.button("Telpro (Raw pdf)", key="telpro_btn"):
            st.switch_page("pages/Telpro.py")
        if st.button("Laxven (Raw txt)", key="laxven_btn"):
            st.switch_page("pages/Laxven.py")
        if st.button("RTIS Analysis", key="rtis_btn"):
            st.switch_page("pages/RTIS_Raw.py")
        
with col2:
    # st.empty()
    st.markdown("<h4 style='font-size:22px; text-align:center;'>🚀 Reports</h4>", unsafe_allow_html=True)
    with st.container():
        if st.button("Quick Report with Excel", key="quick_report_btn"):
            st.switch_page("pages/Quick_Report.py")
        if st.button("Live View with Excel", key="live_view_btn"):
            st.switch_page("pages/Live_View.py")
        if st.button("AI-Gen Report", key="ai_gen_report_btn"):
            st.switch_page("pages/ai_Gemini.py")
        if st.button("Chat Genie Q&A", key="qa_btn"):
            st.switch_page("pages/Q&A.py")
        

          
with col3:
    st.markdown("<h4 style='font-size:22px; text-align:center;'>🌐 Data-Lake</h4>", unsafe_allow_html=True)
    with st.container():
        if st.button("MIS Dashboard", key="edash_btn"):
            st.switch_page("pages/dashboard.py") 
        if st.button("Crew & User Data", key="crew_btn"):
            st.switch_page("pages/crew_user_data.py")

# Footer............................................................................................................................   
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
        border-top: 5px solid #ddd;
        z-index: 80;
    }
    </style>

    <div class="custom-footer">
        SPM App Design & Development by Western Railway <br>
        &copy; 2023 ## BDTS1022. All rights reserved.
    </div>
""", unsafe_allow_html=True)

# Footer Cards............................................................................................................................ 
# Custom CSS with center alignment
st.markdown('-----')
st.markdown("""
    <style>
        .video-box {
            background-color: #F5F7F7;
            border-radius: 15px;
            padding: 20px;
            margin: 10px auto;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            width: 500px;   
            height: 320px; 
            text-align: center;
            display: flex;
            justify-content: center;
        }
        iframe {
                    border-radius: 16px;
                }
    </style>
""", unsafe_allow_html=True)


st.markdown(
    """
    <div style='text-align: center; font-size: 28px; font-weight: 600; margin-bottom: 20px;'>
        Spm App Tutorial YouTube Videos
    </div>
    """,
    unsafe_allow_html=True
)

# Layout with columns
col1, col2, col3, col4 = st.columns([1,1,1,1])

with col1:
# Video inside centered box
    st.markdown(f"""
        <div class="video-box">
            <iframe width="100%" height="280"
                title="SPM app Basic Tutorial" 
                src="https://www.youtube.com/embed/opZIAGlJd48"
                frameborder="0" allow="accelerometer; autoplay; clipboard-write; 
                encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        </div>
    """, unsafe_allow_html=True)
    

with col2:
# Video inside centered box
    st.markdown(f"""
        <div class="video-box">
            <iframe width="100%" height="280"
                title="SPM app Change Nomination" 
                src="https://www.youtube.com/embed/7DZhF4am1-A"
                frameborder="0" allow="accelerometer; autoplay; clipboard-write; 
                encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        </div>
    """, unsafe_allow_html=True)

with col3:
# Video inside centered box
    st.markdown(f"""
        <div class="video-box">
            <iframe width="100%" height="280" 
                title="SPM app Exception Report"
                src="https://www.youtube.com/embed/MFJiTsJH7CY"
                frameborder="0" allow="accelerometer; autoplay; clipboard-write; 
                encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        </div>
    """, unsafe_allow_html=True)

with col4:
# Video inside centered box
    st.markdown(f"""
        <div class="video-box">
            <iframe width="100%" height="280" 
                title="SPM app Exception Feedback"
                src="https://www.youtube.com/embed/wrOy9uUnD04"
                frameborder="0" allow="accelerometer; autoplay; clipboard-write; 
                encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        </div>
    """, unsafe_allow_html=True)