"""
Trovly - Hosted App
Run with: streamlit run app_hosted.py
"""

import streamlit as st
from auth import login_page, logout, get_user_data, save_user_data

st.set_page_config(
    page_title="Trovly",
    page_icon="mag",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
.main .block-container { padding-top: 2rem; max-width: 1200px; }
h1 { font-weight: 700 !important; letter-spacing: -0.02em !important; }
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460; border-radius: 12px; padding: 16px 20px;
}
div[data-testid="stMetric"] label { color: #8892b0 !important; font-size: 0.85rem !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #e6f1ff !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

username = login_page()

if username is None:
    st.stop()

user_data = get_user_data(username)

with st.sidebar:
    st.markdown("## Trovly")
    st.markdown("Logged in as **{}**".format(username))
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
            if jd_input and len(jd_input) > 30:
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
