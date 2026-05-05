"""
Trovly - Hosted App
Run with: streamlit run app_hosted.py
"""

import streamlit as st
from auth import login_page, logout, get_user_data, save_user_data
from resume_parser import parse_resume_file
from usage_limits import (
    get_user_tier, can_scan, can_tailor,
    increment_scans, increment_tailors, get_usage_summary,
    get_tier_limits,
)

st.set_page_config(
    page_title="Trovly",
    page_icon="mag",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');

/* Brand variables */
:root {
    --gold-300: #fde047;
    --gold-500: #fbbf24;
    --amber-500: #f59e0b;
    --coral-500: #f97316;
    --pink-500: #ec4899;
    --night-900: #0d1117;
    --night-800: #161b22;
    --night-600: #2d2d44;
    --paper: #f8fafc;
    --paper-muted: #cbd5e1;
    --grad-sunset: linear-gradient(135deg, #fde047 0%, #fbbf24 30%, #f97316 65%, #ec4899 100%);
}

html, body, [class*="css"] { font-family: 'Outfit', sans-serif !important; }

.main .block-container {
    padding-top: 2rem;
    max-width: 1200px;
}

/* Headings */
h1, h2, h3 {
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: var(--paper) !important;
}

/* Gradient text for the brand name in main heading */
h1 {
    background: linear-gradient(135deg, #fde047 0%, #fbbf24 30%, #f97316 65%, #ec4899 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
}

/* Primary buttons - golden gradient with dark text */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #fde047 0%, #fbbf24 30%, #f97316 65%, #ec4899 100%) !important;
    color: #0d1117 !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(251, 191, 36, 0.25) !important;
    transition: transform 0.15s, box-shadow 0.2s !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(251, 191, 36, 0.4) !important;
}

/* Secondary buttons - outlined */
.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
    background: transparent !important;
    color: #f8fafc !important;
    border: 1.5px solid #cbd5e1 !important;
    font-weight: 500 !important;
}

.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {
    border-color: #fbbf24 !important;
    color: #fbbf24 !important;
}

/* Metric cards with golden accent border */
div[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #2d2d44;
    border-left: 3px solid #fbbf24;
    border-radius: 12px;
    padding: 16px 20px;
}

div[data-testid="stMetric"] label {
    color: #cbd5e1 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #f8fafc !important;
    font-weight: 700 !important;
}

/* Tabs - active tab has golden underline */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #2d2d44;
}

.stTabs [data-baseweb="tab"] {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
}

.stTabs [aria-selected="true"] {
    color: #fbbf24 !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, #fbbf24, #ec4899) !important;
    height: 3px !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: #161b22 !important;
    border-right: 1px solid #2d2d44;
}

section[data-testid="stSidebar"] .stMarkdown h2 {
    background: linear-gradient(135deg, #fbbf24 0%, #ec4899 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 28px !important;
}

/* Info/warning/error boxes */
div[data-testid="stAlert"] {
    border-radius: 10px;
    border-width: 1px;
}

/* Sliders - gold thumb */
.stSlider [role="slider"] {
    background: #fbbf24 !important;
    border-color: #fbbf24 !important;
}

/* Text inputs and text areas */
.stTextInput input, .stTextArea textarea {
    background: #161b22 !important;
    border: 1px solid #2d2d44 !important;
    color: #f8fafc !important;
    border-radius: 8px !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #fbbf24 !important;
    box-shadow: 0 0 0 1px #fbbf24 !important;
}

/* Expander headers */
.streamlit-expanderHeader {
    background: #161b22 !important;
    border: 1px solid #2d2d44 !important;
    border-radius: 10px !important;
    border-left: 3px solid #fbbf24 !important;
}

/* Login screen logo mark */
.trovly-mark {
    width: 64px;
    height: 64px;
    margin: 0 auto 16px;
    background: linear-gradient(135deg, #fde047 0%, #fbbf24 30%, #f97316 65%, #ec4899 100%);
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0d1117;
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    font-size: 36px;
    box-shadow: 0 8px 24px rgba(251, 191, 36, 0.3);
}

/* Apply links */
a[data-testid="stLink"] {
    color: #fbbf24 !important;
}
</style>
""", unsafe_allow_html=True)

username = login_page()

if username is None:
    st.stop()

user_data = get_user_data(username)

with st.sidebar:
    st.markdown("## Trovly")
    st.markdown("Logged in as **{}**".format(username))

    # Tier and usage display
    tier = get_user_tier(user_data)
    summary = get_usage_summary(username, tier)

    if tier == "free":
        st.markdown("**Tier:** Free")
        if summary["scans_remaining"] == 0:
            st.error("Scans: {} / {} (limit reached)".format(summary["scans_used"], summary["scans_limit"]))
        else:
            st.info("Scans: {} / {}".format(summary["scans_used"], summary["scans_limit"]))
        st.caption("Resume analyses: {} / {}".format(summary["tailors_used"], summary["tailors_limit"]))
        st.markdown("---")
        st.markdown("**Upgrade to Pro** for unlimited scans, more sources, and analytics.")
        st.button("Upgrade to Pro", disabled=True, help="Payment integration coming soon")
    else:
        st.success("Tier: {}".format(summary["tier_label"]))

    st.markdown("---")
    if st.button("Log out"):
        logout()
    st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Setup", "Scan", "Tailor"])

with tab1:
    st.markdown("### Your Profile")
    st.markdown("Paste your resume and set up your job search.")

    resume = st.text_area(
        "Resume",
        value=user_data.get("resume", ""),
        height=300,
        placeholder="Paste your full resume here...",
    )

    queries_str = st.text_area(
        "Job titles to search (one per line)",
        value="\n".join(user_data.get("queries", [])),
        height=150,
        placeholder="python developer\ndevops engineer\ncloud engineer",
    )

    col1, col2 = st.columns(2)
    with col1:
        threshold = st.slider(
            "Match threshold",
            0.3, 0.95,
            user_data.get("threshold", 0.55),
            0.05,
            format="%.0f%%",
        )
    with col2:
        remote_only = st.checkbox(
            "Remote only",
            value=user_data.get("remote_only", True),
        )

    if st.button("Save profile", type="primary"):
        queries_list = [q.strip() for q in queries_str.strip().split("\n") if q.strip()]
        save_user_data(username, {
            "resume": resume,
            "queries": queries_list,
            "threshold": threshold,
            "remote_only": remote_only,
        })
        st.success("Profile saved.")

with tab2:
    st.markdown("### Scan for Jobs")

    if not user_data.get("resume"):
        st.warning("Set up your profile first — paste your resume in the Setup tab.")
    else:
        st.markdown("**Resume loaded:** {} characters".format(len(user_data.get("resume", ""))))
        st.markdown("**Queries:** {}".format(", ".join(user_data.get("queries", []))))
        st.markdown("**Threshold:** {:.0%}".format(user_data.get("threshold", 0.55)))

        if st.button("Run scan now", type="primary"):
            allowed, msg = can_scan(username, tier)
            if not allowed:
                st.error(msg)
                st.stop()
            increment_scans(username)
            with st.spinner("Scanning job sources... this takes about 60 seconds."):
                try:
                    import config_cloud as config
                    config.RESUME_TEXT = user_data.get("resume", "")
                    config.SEARCH_QUERIES = user_data.get("queries", [])
                    config.SIMILARITY_THRESHOLD = user_data.get("threshold", 0.55)
                    config.REMOTE_ONLY = user_data.get("remote_only", True)

                    from sources import fetch_all_jobs
                    from matcher import match_jobs, reload_resume

                    reload_resume()
                    jobs = fetch_all_jobs()
                    st.info("Fetched {} jobs. Matching...".format(len(jobs)))

                    matched = match_jobs(jobs)

                    if matched:
                        st.success("Found {} matches.".format(len(matched)))
                        for job, score in matched:
                            with st.expander("{:.0%} — {} at {}".format(score, job.title, job.company)):
                                st.markdown("**Location:** {}".format(job.location or "Remote"))
                                if job.salary:
                                    st.markdown("**Salary:** {}".format(job.salary))
                                st.markdown("**Source:** {}".format(job.source))
                                st.link_button("Apply", job.url)
                    else:
                        st.warning("No matches above {:.0%}. Try lowering threshold in Setup.".format(
                            user_data.get("threshold", 0.55)))

                except Exception as e:
                    st.error("Scan failed: {}".format(e))

with tab3:
    st.markdown("### Resume Tailor")

    if not user_data.get("resume"):
        st.warning("Set up your profile first.")
    else:
        jd_input = st.text_area(
            "Paste a job description",
            height=250,
            placeholder="Paste the full job description here...",
        )

        if st.button("Analyze", type="primary"):
            allowed, msg = can_tailor(username, tier)
            if not allowed:
                st.error(msg)
                st.stop()
            if jd_input and len(jd_input) > 30:
                increment_tailors(username)
                with st.spinner("Analyzing..."):
                    try:
                        import config_cloud as config
                        config.RESUME_TEXT = user_data.get("resume", "")

                        from tailor import tailor_resume
                        from matcher import reload_resume
                        reload_resume()

                        result = tailor_resume(jd_input, verbose=False)

                        if "error" in result:
                            st.error(result["error"])
                        else:
                            total = result["total_bullets"]
                            strong_pct = len(result["strong_bullets"]) / total * 100 if total else 0

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Relevance", "{:.0f}%".format(strong_pct))
                            with col2:
                                st.metric("Keywords matched", result["jd_keywords_found"])
                            with col3:
                                st.metric("Skill gaps", result["jd_keywords_missing"])

                            if result["strong_bullets"]:
                                st.markdown("#### Strong matches")
                                for b in result["strong_bullets"]:
                                    st.markdown("**{:.0%}** — {}".format(b["relevance"], b["text"]))

                            if result["moderate_bullets"]:
                                st.markdown("#### Moderate matches")
                                for b in result["moderate_bullets"][:8]:
                                    st.markdown("**{:.0%}** — {}".format(b["relevance"], b["text"]))

                            if result["skill_gaps"]:
                                st.markdown("#### Skill gaps")
                                for gap in result["skill_gaps"]:
                                    st.markdown("- **{}**".format(gap))
                            else:
                                st.success("No skill gaps detected.")

                    except Exception as e:
                        st.error("Analysis failed: {}".format(e))
