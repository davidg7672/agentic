import os
import sys
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from graph import build_graph
from state import initial_state
from utils.document_parser import parse_uploaded_file, parse_text, parse_url
from utils.input_sanitizer import sanitize_input

st.set_page_config(
    page_title="Job Application Copilot",
    page_icon="💼",
    layout="wide",
)

# ── Session state initialization ─────────────────────────────────────────────

if "step" not in st.session_state:
    st.session_state.step = "idle"  # idle | running | complete | error
if "result" not in st.session_state:
    st.session_state.result = None

# ── Sidebar: inputs ───────────────────────────────────────────────────────────

with st.sidebar:
    st.title("💼 Job Application Copilot")
    st.caption("Paste or upload your resume and job description to get started.")
    st.divider()

    st.subheader("Job Description")
    jd_url = st.text_input("Paste a job URL (Indeed, Glassdoor, etc.)", key="jd_url", placeholder="https://www.indeed.com/viewjob?jk=...")
    jd_file = st.file_uploader("…or upload (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], key="jd_file")
    jd_paste = st.text_area("…or paste the text", height=120, key="jd_paste")

    st.subheader("Your Resume")
    resume_file = st.file_uploader("Upload Resume (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], key="resume_file")
    resume_paste = st.text_area("…or paste it here", height=150, key="resume_paste")

    st.divider()

    run_button = st.button(
        "Run Analysis",
        type="primary",
        use_container_width=True,
        disabled=(st.session_state.step == "running"),
    )

    if st.session_state.step == "complete":
        if st.button("Start Over", use_container_width=True):
            st.session_state.step = "idle"
            st.session_state.result = None
            st.rerun()

    st.divider()
    st.caption(
        "Powered by Claude Sonnet · Built with LangGraph + Streamlit\n\n"
        "Guardrails: fabrication detection, tone check, ATS keyword check."
    )

# ── Main content area ─────────────────────────────────────────────────────────

st.title("Job Application Copilot")

if st.session_state.step == "idle":
    st.info("Fill in your job description and resume in the sidebar, then click **Run Analysis**.")

# ── Run the graph ─────────────────────────────────────────────────────────────

if run_button:
    # Resolve inputs: URL > file upload > paste
    jd_text = ""
    resume_text = ""

    if jd_url.strip():
        try:
            with st.spinner("Fetching job description from URL…"):
                jd_text = parse_url(jd_url.strip())
            st.success(f"Fetched {len(jd_text):,} characters from URL.")
        except ValueError as e:
            st.error(str(e))
            st.stop()
    elif jd_file:
        try:
            jd_text = parse_uploaded_file(jd_file)
        except ValueError as e:
            st.error(str(e))
            st.stop()
    elif jd_paste.strip():
        jd_text = parse_text(jd_paste)

    if resume_file:
        try:
            resume_text = parse_uploaded_file(resume_file)
        except ValueError as e:
            st.error(str(e))
            st.stop()
    elif resume_paste.strip():
        resume_text = parse_text(resume_paste)

    if not jd_text:
        st.error("Please provide a job description (upload or paste).")
        st.stop()
    if not resume_text:
        st.error("Please provide your resume (upload or paste).")
        st.stop()

    try:
        jd_text = sanitize_input(jd_text)
        resume_text = sanitize_input(resume_text)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    if len(resume_text) > 20_000:
        st.warning("Resume is very long — consider trimming it to reduce processing time and cost.")

    st.session_state.step = "running"
    st.session_state.result = None

    graph = build_graph()
    state = initial_state(jd_text, resume_text)

    # ── Progress bar and step containers ─────────────────────────────────────

    STEP_LABELS = [
        "Gap Analysis",
        "Resume Rewrite",
        "Fabrication Check",
        "Tone Check",
        "ATS Check",
        "Cover Letter",
        "Interview Questions",
    ]

    STEP_MAP = {
        "gap_analysis_complete": 1,
        "resume_rewritten": 2,
        "cover_letter_drafted": 5,
        "complete": 6,
    }

    progress_bar = st.progress(0, text="Starting analysis…")

    st.subheader("Gap Analysis")
    gap_container = st.empty()

    st.subheader("Rewritten Resume")
    resume_container = st.empty()
    warnings_container = st.empty()

    st.subheader("Cover Letter")
    cover_container = st.empty()

    st.subheader("Interview Questions")
    interview_container = st.empty()

    # ── Stream the graph ──────────────────────────────────────────────────────

    final_state = state
    try:
        for snapshot in graph.stream(state, stream_mode="values"):
            final_state = snapshot
            step = snapshot.get("current_step", "")

            # Update progress bar
            step_index = STEP_MAP.get(step, 0)
            progress_pct = step_index / (len(STEP_LABELS) - 1) if step_index else 0
            label = STEP_LABELS[step_index] if step_index < len(STEP_LABELS) else "Processing…"
            progress_bar.progress(progress_pct, text=f"Completed: {label}")

            # Render outputs as they arrive
            if snapshot.get("gap_analysis"):
                gap_container.markdown(snapshot["gap_analysis"])

            if snapshot.get("rewritten_resume"):
                resume_container.markdown(snapshot["rewritten_resume"])

            # Show guardrail warnings after resume is written
            warnings = snapshot.get("guardrail_warnings", [])
            if warnings:
                with warnings_container.container():
                    for w in warnings:
                        st.warning(w)

            if snapshot.get("cover_letter"):
                cover_container.markdown(snapshot["cover_letter"])

            if snapshot.get("interview_questions"):
                interview_container.markdown(snapshot["interview_questions"])

    except Exception as e:
        print(f"[app] graph stream error: {e}", file=sys.stderr)
        st.session_state.step = "error"
        st.error("Something went wrong. Please try again or reduce the size of your inputs.")
        st.stop()

    # Check for node-level errors
    if final_state.get("error"):
        print(f"[app] node error: {final_state['error']}", file=sys.stderr)
        st.session_state.step = "error"
        progress_bar.empty()
        st.error("Analysis failed. Please try again.")
        st.stop()

    progress_bar.progress(1.0, text="Complete!")
    st.session_state.step = "complete"
    st.session_state.result = final_state

# ── Show download buttons after completion ────────────────────────────────────

if st.session_state.step == "complete" and st.session_state.result:
    result = st.session_state.result
    st.divider()
    st.subheader("Downloads")
    col1, col2, col3 = st.columns(3)

    with col1:
        if result.get("rewritten_resume"):
            st.download_button(
                "Download Resume",
                data=result["rewritten_resume"],
                file_name="tailored_resume.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with col2:
        if result.get("cover_letter"):
            st.download_button(
                "Download Cover Letter",
                data=result["cover_letter"],
                file_name="cover_letter.txt",
                mime="text/plain",
                use_container_width=True,
            )

    with col3:
        if result.get("interview_questions"):
            st.download_button(
                "Download Interview Prep",
                data=result["interview_questions"],
                file_name="interview_questions.txt",
                mime="text/plain",
                use_container_width=True,
            )
