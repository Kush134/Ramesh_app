import streamlit as st
import streamlit.components.v1 as components
import requests
from datetime import datetime

# Page configuration
st.set_page_config(page_title="DGCA Website Monitoring", layout="wide")

# Custom CSS Injection to mimic the exact desktop layout
st.markdown(
    """
    <style>
    /* Global Styles */
    :root {
        --dgca-blue: #073f88;
        --page-bg: #f8fafc;
        --border-color: #e2e8f0;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
    }
    
    .stApp {
        background-color: var(--page-bg);
    }
    
    /* Sidebar customization & edge-to-edge content */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #073f88 0%, #06387a 100%);
        min-width: 290px !important;
        padding-top: 0 !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0 !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #ffffff;
    }
    
    .sidebar-title {
        font-size: 26px;
        font-weight: 800;
        padding: 24px 20px 12px 20px;
        color: #ffffff;
        font-family: sans-serif;
    }
    
    .side-sep {
        height: 1px;
        background: rgba(255, 255, 255, 0.15);
        margin: 0 20px 20px 20px;
    }
    
    .nav-list {
        padding: 0 10px;
    }
    
    .nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 13px 20px;
        border-radius: 4px;
        margin: 6px 0;
        font-size: 14.5px;
        font-weight: 600;
        color: #d1d5db;
        opacity: 0.85;
        text-decoration: none;
        cursor: pointer;
    }
    
    .nav-item.active {
        background: rgba(255, 255, 255, 0.13);
        box-shadow: inset 4px 0 0 #3b82f6;
        color: #ffffff;
        opacity: 1;
    }
    
    .sidebar-spacer {
        height: 220px;
    }
    
    .user-card {
        padding: 20px 0;
        margin: 0 20px;
        text-align: center;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        color: #dbeafe;
    }
    
    .user-card .avatar {
        font-size: 32px;
        margin-bottom: 6px;
    }
    
    .user-card strong {
        display: block;
        font-size: 13.5px;
    }
    
    .user-card span {
        display: block;
        font-size: 12px;
        opacity: 0.75;
        margin-top: 2px;
    }
    
    /* Main Area padding adjustment */
    .main .block-container {
        padding-top: 0 !important;
        max-width: 1200px;
    }
    
    /* Top Bar Styling */
    .topbar {
        background: #ffffff;
        margin: 0 -3rem 24px -3rem;
        padding: 18px 32px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border-bottom: 1px solid #cbd5e1;
    }
    
    .topbar h1 {
        margin: 0;
        font-size: 24px;
        color: #0f172a;
        font-weight: 700;
    }
    
    .top-actions {
        display: flex;
        gap: 16px;
        align-items: center;
    }
    
    .bell {
        border: 1px solid #cbd5e1;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px;
        color: #f59e0b;
        background: #ffffff;
        font-size: 18px;
        cursor: pointer;
    }
    
    .logout {
        border: 1px solid #cbd5e1;
        color: #0f172a;
        font-weight: 700;
        border-radius: 4px;
        padding: 8px 18px;
        background: #ffffff;
        font-size: 14px;
        cursor: pointer;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Document Cards & Containers Customization */
    div[data-testid="stVerticalBlockBorderOnly"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        padding: 24px !important;
        margin-bottom: 24px !important;
    }
    
    .card-title {
        font-size: 18px;
        font-weight: 700;
        color: #073f88;
        margin-bottom: 8px;
    }
    
    .card-description {
        color: var(--text-secondary);
        font-size: 14px;
        margin-bottom: 0;
    }
    
    /* Control Buttons Styles override */
    .scraper-btn-wrapper div.stButton > button {
        background-color: #008f35 !important;
        color: white !important;
        border-color: #008f35 !important;
        font-weight: 700 !important;
        padding: 8px 20px !important;
        height: 40px !important;
        border-radius: 4px !important;
        font-size: 14px !important;
    }
    .scraper-btn-wrapper div.stButton > button:hover {
        background-color: #00772c !important;
        border-color: #00772c !important;
    }
    
    .schedule-btn-wrapper div.stButton > button {
        background-color: #003d8f !important;
        color: white !important;
        border-color: #003d8f !important;
        font-weight: 700 !important;
        padding: 8px 20px !important;
        height: 40px !important;
        border-radius: 4px !important;
        font-size: 14px !important;
    }
    .schedule-btn-wrapper div.stButton > button:hover {
        background-color: #002d6b !important;
        border-color: #002d6b !important;
    }
    
    .refresh-container {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        height: 100%;
    }
    
    .refresh-container div.stButton > button {
        background-color: transparent !important;
        color: #073f88 !important;
        border: none !important;
        font-size: 13.5px !important;
        font-weight: 600 !important;
        padding: 0 !important;
        margin: 0 !important;
        height: auto !important;
    }
    .refresh-container div.stButton > button:hover {
        background-color: transparent !important;
        color: #2563eb !important;
        text-decoration: underline !important;
    }
    
    /* Custom HTML Data Table */
    .documents-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 16px;
    }
    
    .documents-table th {
        background-color: #edf2f7;
        color: #1e293b;
        font-weight: 700;
        text-align: left;
        padding: 14px 16px;
        border-bottom: 2px solid #cbd5e1;
        font-size: 13.5px;
        text-transform: capitalize;
    }
    
    .documents-table td {
        padding: 14px 16px;
        border-bottom: 1px solid #e2e8f0;
        vertical-align: middle;
        color: #334155;
        font-size: 14px;
    }
    
    .documents-table tr:hover {
        background-color: #f8fafc;
    }
    
    .version-badge {
        background-color: #ffffff;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12.5px;
        border: 1px solid #cbd5e1;
        color: #475569;
        display: inline-block;
        white-space: nowrap;
    }
    
    /* Actions Buttons */
    .action-btn-view, .action-btn-dl {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background-color: transparent;
        color: #64748b !important;
        border: none;
        cursor: pointer;
        text-decoration: none;
        transition: all 0.2s;
    }
    
    .action-btn-view:hover, .action-btn-dl:hover {
        color: #0f172a !important;
        background-color: #f1f5f9;
        border-radius: 50%;
    }
    
    .action-btn-del {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        height: 34px;
        background-color: #ef4444;
        border-radius: 4px;
        color: #ffffff !important;
        text-decoration: none;
        box-shadow: 0 1px 3px rgba(239, 68, 68, 0.2);
        transition: all 0.2s;
    }
    
    .action-btn-del:hover {
        background-color: #dc2626;
        box-shadow: 0 2px 6px rgba(220, 38, 38, 0.35);
    }

    /* Document Comparison Styles */
    .metric-box {
        background: #ffffff;
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 14px 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,.04);
        text-align: center;
    }
    .metric-box strong {
        display: block;
        font-size: 22px;
        color: #0f172a;
        font-weight: 800;
    }
    .metric-box span {
        color: var(--text-secondary);
        font-size: 12.5px;
    }
    .summary-strip {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }
    .result-card {
        background: #ffffff;
        border: 1px solid var(--border-color);
        border-radius: 6px;
        margin-bottom: 16px;
        overflow: hidden;
        box-shadow: 0 1px 4px rgba(0,0,0,.04);
        border-left: 4px solid #cbd5e1;
    }
    .result-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 18px;
        border-bottom: 1px solid var(--border-color);
        font-weight: 700;
        color: var(--text-primary);
        font-size: 14.5px;
        background: #f8fafc;
    }
    .badge {
        color: #ffffff;
        border-radius: 4px;
        padding: 3px 8px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge.CHANGED   { background: #e67e22; }
    .badge.REMOVED   { background: #ef4444; }
    .badge.ADDED     { background: #10b981; }
    .badge.UNCHANGED { background: #64748b; }
    .result-body {
        margin: 16px 16px 8px 16px;
        padding: 16px;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        line-height: 1.7;
        font-size: 14px;
        color: var(--text-primary);
        white-space: pre-wrap;
    }
    .removed {
        color: #ef4444;
        text-decoration: line-through;
        background-color: #fef2f2;
        padding: 2px 4px;
        border-radius: 2px;
    }
    .added {
        color: #10b981;
        background-color: #ecfdf5;
        padding: 2px 4px;
        border-radius: 2px;
    }
    .final-version {
        margin: 8px 0 0 0;
        border-left: 3px solid #3b82f6;
        background: #eff6ff;
        padding: 12px 14px;
        line-height: 1.6;
        font-size: 13.5px;
        white-space: pre-wrap;
        color: #1e3a8a;
        border-radius: 0 4px 4px 0;
    }
    
    /* Collapsible Final Version Styles */
    details {
        margin: 0 16px 16px 16px;
    }
    details summary {
        cursor: pointer;
        color: #3b82f6;
        font-size: 13.5px;
        font-weight: 500;
        margin: 8px 0;
        outline: none;
        list-style: none; /* Hide default triangle */
        user-select: none;
    }
    details summary:hover {
        text-decoration: underline;
    }
    details summary::-webkit-details-marker {
        display: none;
    }
    details summary::marker {
        display: none;
    }
    details[open] summary::after {
        content: "Hide Final Version";
    }
    details:not([open]) summary::after {
        content: "Show Final Version";
    }
    .removed-card {
        border-left-color: #ef4444;
    }
    .removed-card .result-head {
        color: #b91c1c;
        background: #fef2f2;
    }
    .added-card {
        border-left-color: #10b981;
    }
    .added-card .result-head {
        color: #065f46;
        background: #ecfdf5;
    }
    .changed-card {
        border-left-color: #e67e22;
    }
    .changed-card .result-head {
        color: #c2410c;
        background: #fff7ed;
    }
    .score-row {
        padding: 8px 18px 0 18px;
    }
    .chunk-pill {
        font-size: 11px;
        color: var(--text-secondary);
        background: #f1f5f9;
        border-radius: 12px;
        padding: 2px 8px;
        margin-left: 8px;
        font-weight: 500;
        display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Helper function to format timestamp
def format_datetime(dt_str):
    if not dt_str:
        return ""
    try:
        if "T" in dt_str:
            dt_str = dt_str.replace("T", " ")
        if "." in dt_str:
            dt_str = dt_str.split(".")[0]
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour % 12
        if hour == 0:
            hour = 12
        am_pm = "PM" if dt.hour >= 12 else "AM"
        return f"{dt.month}/{dt.day}/{dt.year}, {hour}:{dt.minute:02d}:{dt.second:02d} {am_pm}"
    except Exception:
        return dt_str

# Check active page from query parameters
active_page = st.query_params.get("page", "website_monitoring")

# Sidebar Rendering
with st.sidebar:
    st.markdown('<div class="sidebar-title">DGCA Admin</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-sep"></div>', unsafe_allow_html=True)
    
    # Navigation Links with query parameters
    sidebar_class_monitoring = "nav-item active" if active_page == "website_monitoring" else "nav-item"
    sidebar_class_compare = "nav-item active" if active_page == "document_comparison" else "nav-item"
    
    st.markdown(
        f"""
        <div class="nav-list">
            <div class="nav-item" style="opacity: 0.4; cursor: not-allowed;">⚙️ <span>Dashboard Overview</span></div>
            <div class="nav-item" style="opacity: 0.4; cursor: not-allowed;">👥 <span>User Management</span></div>
            <a href="?page=website_monitoring" target="_self" style="text-decoration: none;">
                <div class="{sidebar_class_monitoring}">📈 <span>Website Monitoring</span></div>
            </a>
            <a href="?page=document_comparison" target="_self" style="text-decoration: none;">
                <div class="{sidebar_class_compare}">📄 <span>Document Comparison</span></div>
            </a>
            <div class="nav-item" style="opacity: 0.4; cursor: not-allowed;">🎯 <span>Impact Analysis</span></div>
            <div class="nav-item" style="opacity: 0.4; cursor: not-allowed;">⏱️ <span>SLA Tracking</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    
    # Bottom Profile Info
    st.markdown(
        """
        <div class="user-card">
            <div class="avatar">👤</div>
            <strong>rameshphatangare@gmail.com</strong>
            <span>Administrator</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Top Bar header rendering
title_text = "Website Monitoring" if active_page == "website_monitoring" else "Document Comparison"
st.markdown(
    f"""
    <div class="topbar">
        <h1>{title_text}</h1>
        <div class="top-actions">
            <div class="bell">🔔</div>
            <div class="logout">LOGOUT</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if active_page == "website_monitoring":
    # Intercept and process Scraper Action triggers via Query Params
    if st.query_params.get("action") == "run_scraper":
        st.query_params.clear()
        with st.spinner("Scraping DGCA website (this may take a few seconds)..."):
            try:
                res = requests.post("http://127.0.0.1:5000/crawl", timeout=360)
                if res.status_code == 200:
                    data = res.json()
                    st.success(data.get("message", "Scrape completed successfully!"))
                else:
                    st.error(f"Error executing scraper: {res.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend Flask API: {str(e)}")
    
    # CARD 1: Control Section
    with st.container(border=True):
        col_text, col_btn = st.columns([3.8, 1])
        with col_text:
            st.markdown('<div class="card-title">Control Section</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-description">Click the button to start the automated scraping process for DGCA CAR 145.</div>', unsafe_allow_html=True)
        with col_btn:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown('<div class="scraper-btn-wrapper">', unsafe_allow_html=True)
            if st.button("Start Scraper", use_container_width=True):
                st.query_params["action"] = "run_scraper"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Fetch active scheduler configuration from backend
    scheduler_settings = {"frequency": "Disabled", "is_active": 0, "last_run": None, "next_run": None}
    try:
        scheduler_res = requests.get("http://127.0.0.1:5000/api/scheduler", timeout=5)
        if scheduler_res.status_code == 200:
            scheduler_settings = scheduler_res.json()
    except Exception:
        pass
    
    db_frequency = scheduler_settings.get("frequency", "Disabled")
    frequency_options = ["Disabled", "Hourly", "Daily", "Weekly", "Monthly"]
    if db_frequency not in frequency_options:
        db_frequency = "Disabled"
    default_frequency_idx = frequency_options.index(db_frequency)
    
    # CARD 2: Monitoring Schedule
    with st.container(border=True):
        col_text, col_dropdown, col_btn = st.columns([2.5, 1.3, 1])
        with col_text:
            st.markdown('<div class="card-title">Monitoring Schedule</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-description">Set how often the system should automatically check for new versions on the DGCA website.</div>', unsafe_allow_html=True)
        with col_dropdown:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            selected_schedule = st.selectbox(
                "Select schedule",
                frequency_options,
                index=default_frequency_idx,
                label_visibility="collapsed"
            )
        with col_btn:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown('<div class="schedule-btn-wrapper">', unsafe_allow_html=True)
            if st.button("Save Schedule", use_container_width=True):
                try:
                    post_res = requests.post(
                        "http://127.0.0.1:5000/api/scheduler",
                        json={"frequency": selected_schedule},
                        timeout=5
                    )
                    if post_res.status_code == 200:
                        st.rerun()
                    else:
                        st.error(f"Error: {post_res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)
    
        # Render scheduler status details
        is_active = scheduler_settings.get("is_active", 0) == 1
        last_run_raw = scheduler_settings.get("last_run")
        next_run_raw = scheduler_settings.get("next_run")
        
        last_run_formatted = format_datetime(last_run_raw) if last_run_raw else "Never"
        next_run_formatted = format_datetime(next_run_raw) if next_run_raw else "Not scheduled"
        
        if last_run_raw and last_run_raw.startswith("Error"):
            status_html = last_run_formatted
        elif is_active:
            status_html = f"""
            <div style="background-color: #f0fdf4; padding: 14px 18px; border-radius: 6px; border: 1px solid #bbf7d0; margin-top: 15px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 13.5px; font-weight: 700; color: #14532d;">Scheduler Status</span>
                    <span style="background-color: #dcfce7; color: #15803d; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase;">Active</span>
                </div>
                <div style="font-size: 13px; color: #166534; line-height: 1.6;">
                    <div>📅 <strong>Last Crawl:</strong> {last_run_formatted}</div>
                    <div style="margin-top: 4px;">⏰ <strong>Next Scheduled:</strong> {next_run_formatted}</div>
                </div>
            </div>
            """
        else:
            status_html = f"""
            <div style="background-color: #f8fafc; padding: 14px 18px; border-radius: 6px; border: 1px solid #e2e8f0; margin-top: 15px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 13.5px; font-weight: 700; color: #475569;">Scheduler Status</span>
                    <span style="background-color: #f1f5f9; color: #475569; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase;">Inactive</span>
                </div>
                <div style="font-size: 13px; color: #475569;">
                    Scheduler is currently disabled. Live background updates are not running.
                </div>
            </div>
            """
        st.markdown(status_html, unsafe_allow_html=True)
    
    with st.container(border=True):
        col_text, col_btn = st.columns([3.8, 1])
        with col_text:
            st.markdown('<div class="card-title">Files Management</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-description">Recently retrieved files from DGCA website</div>', unsafe_allow_html=True)
        with col_btn:
            st.markdown('<div class="refresh-container">', unsafe_allow_html=True)
            if st.button("🔄 Refresh List", use_container_width=True):
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
        # Fetch fresh documents list from Flask API
        documents = []
        backend_online = True
        try:
            res = requests.get("http://127.0.0.1:5000/api/documents", timeout=10)
            if res.status_code == 200:
                documents = res.json()
            else:
                st.error(f"Backend API returned status code {res.status_code}")
        except Exception as e:
            backend_online = False
            st.error("Cannot connect to the Flask server. Please ensure flask_app.py is running on http://127.0.0.1:5000.")
    
        if backend_online:
            if not documents:
                st.info("No crawled records found in the database. Use the 'Start Scraper' button above to scrape them.")
            else:
                eye_svg   = '<svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 4 8 4s3.88.668 5.168 1.957A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12 8 12s-3.88-.668-5.168-1.957A13 13 0 0 1 1.172 8z"/><path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/></svg>'
                dl_svg    = '<svg xmlns="http://www.w3.org/2000/svg" width="17" height="17" fill="currentColor" viewBox="0 0 16 16"><path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5"/><path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708z"/></svg>'
                trash_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="white" viewBox="0 0 16 16"><path d="M2.5 1a1 1 0 0 0-1 1v1a1 1 0 0 0 1 1H3v9a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V4h.5a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H10a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1zm3 4a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-1 0v-7a.5.5 0 0 1 .5-.5M8 5a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-1 0v-7A.5.5 0 0 1 8 5m3 .5v7a.5.5 0 0 1-1 0v-7a.5.5 0 0 1 1 0"/></svg>'
    
                rows_html = ""
                for item in documents:
                    doc_id   = item.get("id")
                    title    = item.get("car_series_part", "").replace("\n", " ").strip()
                    ver      = item.get("issue_no_date", "").replace("\n", " ").strip()
                    status   = item.get("status", "Unchanged")
                    date_str = format_datetime(item.get("created_at"))
                    view_url = f"http://127.0.0.1:5000/api/documents/{doc_id}/view"
                    dl_url   = f"http://127.0.0.1:5000/api/documents/{doc_id}/download"
    
                    if status == "Updated":
                        status_badge = '<span style="background-color:#dcfce7;color:#15803d;padding:4px 8px;border-radius:4px;font-weight:600;font-size:12px;white-space:nowrap;">Updated</span>'
                    else:
                        status_badge = '<span style="background-color:#f1f5f9;color:#475569;padding:4px 8px;border-radius:4px;font-weight:600;font-size:12px;white-space:nowrap;">Unchanged</span>'
    
                    md_status = item.get("markdown_updated", 0)
                    md_url = f"http://127.0.0.1:5000/api/documents/{doc_id}/markdown"
                    
                    if md_status == 1:
                        md_badge = f'<a href="{md_url}" target="_blank" style="background-color:#eff6ff;color:#1d4ed8;padding:4px 8px;border-radius:4px;font-weight:600;font-size:12px;white-space:nowrap;text-decoration:none;border:1px solid #bfdbfe;">Ready 📝</a>'
                    elif md_status == -1:
                        md_badge = '<span style="background-color:#fef2f2;color:#b91c1c;padding:4px 8px;border-radius:4px;font-weight:600;font-size:12px;white-space:nowrap;border:1px solid #fecaca;">Failed ⚠️</span>'
                    elif status == "Updated" and (md_status == 0 or md_status is None):
                        md_badge = '<span style="background-color:#fffbeb;color:#b45309;padding:4px 8px;border-radius:4px;font-weight:600;font-size:12px;white-space:nowrap;border:1px solid #fde68a;">Processing ⏳</span>'
                    else:
                        md_badge = '<span style="color:#94a3b8;font-size:13px;">—</span>'
    
                    rows_html += (
                        f'<tr>'
                        f'<td style="font-weight:600;color:#475569;">{doc_id}</td>'
                        f'<td><a href="{view_url}" target="_blank" style="color:#0066cc;font-weight:700;text-decoration:none;">{title}</a></td>'
                        f'<td><span class="version-badge">{ver}</span></td>'
                        f'<td>{status_badge}</td>'
                        f'<td>{md_badge}</td>'
                        f'<td style="color:#475569;font-size:13.5px;">{date_str}</td>'
                        f'<td style="text-align:center;">'
                        f'  <div style="display:inline-flex;gap:12px;align-items:center;justify-content:center;width:100%;">'
                        f'    <a href="{view_url}" target="_blank" class="action-btn-view" title="View PDF">{eye_svg}</a>'
                        f'    <a href="{dl_url}" class="action-btn-dl" title="Download PDF">{dl_svg}</a>'
                        f'    <button class="action-btn-del" title="Delete record" onclick="deleteDoc({doc_id})">{trash_svg}</button>'
                        f'  </div>'
                        f'</td>'
                        f'</tr>'
                    )
    
                table_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                  body {{ margin: 0; padding: 0; font-family: sans-serif; background: transparent; }}
                  .documents-table {{ width: 100%; border-collapse: collapse; margin-top: 0; }}
                  .documents-table th {{
                      background-color: #edf2f7; color: #1e293b; font-weight: 700;
                      text-align: left; padding: 14px 16px; border-bottom: 2px solid #cbd5e1;
                      font-size: 13.5px; text-transform: capitalize;
                  }}
                  .documents-table td {{
                      padding: 14px 16px; border-bottom: 1px solid #e2e8f0;
                      vertical-align: middle; color: #334155; font-size: 14px;
                  }}
                  .documents-table tr:hover {{ background-color: #f8fafc; }}
                  .version-badge {{
                      background-color: #ffffff; padding: 4px 10px; border-radius: 4px;
                      font-weight: 600; font-size: 12.5px; border: 1px solid #cbd5e1;
                      color: #475569; display: inline-block; white-space: nowrap;
                  }}
                  .action-btn-view, .action-btn-dl {{
                      display: inline-flex; align-items: center; justify-content: center;
                      width: 32px; height: 32px; background-color: transparent;
                      color: #64748b; border: none; cursor: pointer;
                      text-decoration: none; transition: all 0.2s;
                  }}
                  .action-btn-view:hover, .action-btn-dl:hover {{
                      color: #0f172a; background-color: #f1f5f9; border-radius: 50%;
                  }}
                  .action-btn-del {{
                      display: inline-flex; align-items: center; justify-content: center;
                      width: 34px; height: 34px; background-color: #ef4444;
                      border-radius: 4px; color: #ffffff; border: none; cursor: pointer;
                      box-shadow: 0 1px 3px rgba(239,68,68,0.2); transition: all 0.2s;
                  }}
                  .action-btn-del:hover {{ background-color: #dc2626; box-shadow: 0 2px 6px rgba(220,38,38,0.35); }}
                </style>
                </head>
                <body>
                <table class="documents-table">
                  <thead>
                    <tr>
                      <th style="width:7%;">ID</th>
                      <th style="width:28%;">Title</th>
                      <th style="width:16%;">Version No</th>
                      <th style="width:11%;">Status</th>
                      <th style="width:12%;">Markdown</th>
                      <th style="width:14%;">Created Date</th>
                      <th style="width:12%;text-align:center;">Actions</th>
                    </tr>
                  </thead>
                  <tbody>{rows_html}</tbody>
                </table>
                <script>
                function deleteDoc(docId) {{
                    fetch('http://127.0.0.1:5000/api/documents/' + docId, {{ method: 'DELETE' }})
                        .then(function(res) {{
                            if (res.ok) {{
                                window.parent.location.reload();
                            }} else {{
                                alert('Delete failed. Status: ' + res.status);
                            }}
                        }})
                        .catch(function(err) {{
                            alert('Error connecting to server: ' + err);
                        }});
                }}
                </script>
                </body>
                </html>
                """
    
                table_height = 54 + len(documents) * 52 + 20
                components.html(table_html, height=table_height, scrolling=False)

else:
    # ============================================================
    # Document Comparison Page
    # ============================================================
    import html
    import re
    import difflib

    TOKEN_RE = re.compile(r"\s+|[\w]+(?:[-'][\w]+)*|[^\w\s]", re.UNICODE)
    
    def tokens(text: str) -> list[str]:
        return TOKEN_RE.findall(clean_text(text))

    def clean_text(value: str) -> str:
        value = value.replace("\u2013", "-").replace("\u2014", "-")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    def strip_leading_heading(text: str) -> str:
        text = text.strip()
        if text.startswith("#"):
            lines = text.split("\n")
            if lines:
                first_line = lines[0].strip()
                if re.match(r"^#+\s+", first_line):
                    return "\n".join(lines[1:]).strip()
        return text

    def diff_html(old_text: str, new_text: str) -> str:
        old_tok = tokens(old_text)
        new_tok = tokens(new_text)
        matcher = difflib.SequenceMatcher(None, old_tok, new_tok, autojunk=False)
        parts = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                parts.append(html.escape("".join(new_tok[j1:j2])))
            elif tag == "delete":
                parts.append(f'<span class="removed">{html.escape("".join(old_tok[i1:i2]))}</span>')
            elif tag == "insert":
                parts.append(f'<span class="added">{html.escape("".join(new_tok[j1:j2]))}</span>')
            elif tag == "replace":
                parts.append(f'<span class="removed">{html.escape("".join(old_tok[i1:i2]))}</span>')
                parts.append(f'<span class="added">{html.escape("".join(new_tok[j1:j2]))}</span>')
        return "".join(parts).replace("\n", "<br>")

    def score_bar(score: float) -> str:
        pct = int(score * 100)
        colour = "#10b981" if score >= 0.98 else ("#e67e22" if score >= 0.75 else "#ef4444")
        return (
            f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#64748b;margin-bottom:8px;">'
            f'<div style="flex:1;background:#e2e8f0;border-radius:4px;height:6px;max-width:130px;">'
            f'<div style="width:{pct}%;background:{colour};border-radius:4px;height:6px;"></div></div>'
            f'<span>sim: <strong>{score:.2f}</strong></span></div>'
        )

    # Fetch documents list from API
    documents = []
    backend_online = True
    try:
        res = requests.get("http://127.0.0.1:5000/api/documents", timeout=10)
        if res.status_code == 200:
            documents = res.json()
    except Exception:
        backend_online = False

    if not backend_online:
        st.error("Cannot connect to Flask server. Please run flask_app.py.")
    else:
        # Filter processed documents that have chunks
        eligible_docs = [d for d in documents if d.get("markdown_updated") == 1]
        
        if not eligible_docs:
            st.info("No documents are currently available for comparison. Crawled documents must have generated Markdown chunks. Run the scraper on the Website Monitoring tab to process files.")
        else:
            with st.container(border=True):
                st.markdown('<div class="card-title">Compare Revisions</div>', unsafe_allow_html=True)
                st.markdown('<div class="card-description">Select two crawled documents to compute their clause-level changes.</div>', unsafe_allow_html=True)
                
                eligible_labels = {
                    d["id"]: f"ID {d['id']}: {d.get('car_series_part', 'Unnamed').strip()} ({d.get('issue_no_date', '').strip()})"
                    for d in eligible_docs
                }
                
                keys = list(eligible_labels.keys())
                
                # Setup side-by-side selectors
                col_old, col_new = st.columns(2)
                with col_old:
                    old_id = st.selectbox(
                        "Old Revision",
                        options=keys,
                        format_func=lambda x: eligible_labels[x],
                        index=0
                    )
                with col_new:
                    new_id = st.selectbox(
                        "New Revision",
                        options=keys,
                        format_func=lambda x: eligible_labels[x],
                        index=min(1, len(keys) - 1)
                    )
                
                # Compare Button
                st.write("")
                compare_triggered = st.button("🔍 Compare Documents", type="primary")

            # We store the comparison result in session state to persist between user configuration tweaks
            comparison_key = f"comp_{old_id}_{new_id}"
            
            if compare_triggered:
                with st.spinner("Decoding database chunks and running semantic alignment..."):
                    try:
                        comp_res = requests.get(f"http://127.0.0.1:5000/api/documents/compare/{old_id}/{new_id}", timeout=60)
                        if comp_res.status_code == 200:
                            st.session_state[comparison_key] = comp_res.json()
                        else:
                            st.error(f"Comparison failed: {comp_res.text}")
                    except Exception as e:
                        st.error(f"Connection failure: {str(e)}")

            if comparison_key in st.session_state:
                rows = st.session_state[comparison_key]
                
                total = len(rows)
                unchanged = sum(1 for r in rows if r["status"] == "UNCHANGED")
                changed = sum(1 for r in rows if r["status"] == "CHANGED")
                added = sum(1 for r in rows if r["status"] == "ADDED")
                removed = sum(1 for r in rows if r["status"] == "REMOVED")

                # Metric Summary strip
                st.markdown(
                    f"""
                    <div class="summary-strip">
                        <div class="metric-box">
                            <strong>{total}</strong>
                            <span>Aligned Chunks</span>
                        </div>
                        <div class="metric-box" style="border-bottom: 3px solid #64748b;">
                            <strong>{unchanged}</strong>
                            <span>Unchanged</span>
                        </div>
                        <div class="metric-box" style="border-bottom: 3px solid #e67e22;">
                            <strong>{changed}</strong>
                            <span>Changed</span>
                        </div>
                        <div class="metric-box" style="border-bottom: 3px solid #10b981;">
                            <strong>{added}</strong>
                            <span>Added</span>
                        </div>
                        <div class="metric-box" style="border-bottom: 3px solid #ef4444;">
                            <strong>{removed}</strong>
                            <span>Removed</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Render dashboard options filter/ranges side bar or layout columns
                with st.container(border=True):
                    st.markdown('<div class="card-title">Filter Configurations</div>', unsafe_allow_html=True)
                    col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
                    
                    with col_f1:
                        c_from = st.number_input("From Clause Index", min_value=1, max_value=total, value=1)
                    with col_f2:
                        c_to = st.number_input("To Clause Index", min_value=1, max_value=total, value=min(20, total))
                    with col_f3:
                        selected_statuses = st.multiselect(
                            "Filter Statuses",
                            options=["UNCHANGED", "CHANGED", "ADDED", "REMOVED"],
                            default=["UNCHANGED","CHANGED", "ADDED", "REMOVED"]
                        )
                
                # Render results in range
                filtered_rows = [
                    r for r in rows 
                    if c_from <= r["index"] <= c_to and r["status"] in selected_statuses
                ]

                st.write("")
                st.subheader(f"Range-Based Semantic Diff (Showing Clauses {c_from} to {c_to})")

                if not filtered_rows:
                    st.info("No matching records found in this range with the selected status filter.")
                else:
                    for row in filtered_rows:
                        status = row["status"]
                        score = row["score"]
                        old_chunk_id = row["old_chunk_id"]
                        new_chunk_id = row["new_chunk_id"]
                        old_heading = row["old_heading"]
                        new_heading = row["new_heading"]
                        old_text = row["old_text"]
                        new_text = row["new_text"]
                        idx = row["index"]
                        
                        heading = new_heading or old_heading
                        if old_heading and new_heading and old_heading != new_heading:
                            heading = f"{old_heading}  →  {new_heading}"
                            
                        chunk_label = ""
                        
                        old_text_clean = strip_leading_heading(old_text)
                        new_text_clean = strip_leading_heading(new_text)

                        classes = ["result-card"]
                        if status == "REMOVED": 
                            classes.append("removed-card")
                            body = f'<span class="removed">{html.escape(old_text_clean).replace(chr(10), "<br>")}</span>'
                            final = ""
                        elif status == "ADDED":   
                            classes.append("added-card")
                            body = f'<span class="added">{html.escape(new_text_clean).replace(chr(10), "<br>")}</span>'
                            final = f'<div class="final-version">{html.escape(clean_text(new_text_clean)).replace(chr(10), "<br>")}</div>'
                        else:
                            classes.append("changed-card")
                            body = diff_html(old_text_clean, new_text_clean)
                            final = f'<div class="final-version">{html.escape(clean_text(new_text_clean)).replace(chr(10), "<br>")}</div>'
                            
                        if final:
                            final = (
                                f'<details>'
                                f'<summary></summary>'
                                f'{final}'
                                f'</details>'
                            )
                            
                        st.markdown(
                            f"""
                            <div class="{ ' '.join(classes) }">
                                <div class="result-head">
                                    <span>{idx}. {html.escape(heading)}{chunk_label}</span>
                                    <span class="badge {status}">{status}</span>
                                </div>
                                <div class="result-body">{body}</div>
                                {final}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

