import os
import sys
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

from graph import build_graph
from state import initial_state
from utils.document_parser import parse_uploaded_file, parse_text, parse_url
from utils.input_sanitizer import sanitize_input
from utils.pdf_exporter import resume_to_pdf, cover_letter_to_pdf
from utils.docx_exporter import resume_to_docx, cover_letter_to_docx

st.set_page_config(
    page_title="Job Application Copilot",
    page_icon="💼",
    layout="wide",
)

# ── Session state initialization ──────────────────────────────────────────────

if "step" not in st.session_state:
    st.session_state.step = "idle"   # idle | running | complete | error
if "result" not in st.session_state:
    st.session_state.result = None

# ── Sidebar: inputs ───────────────────────────────────────────────────────────

with st.sidebar:
    st.title("💼 Job Application Copilot")
    st.caption("Paste or upload your resume and job description to get started.")
    st.divider()

    st.subheader("Job Description")
    jd_method = st.radio(
        "jd_input_method",
        ["🔗 URL", "📄 Upload", "✏️ Paste"],
        horizontal=True,
        label_visibility="collapsed",
        key="jd_method",
    )

    jd_url, jd_file, jd_paste = "", None, ""
    if jd_method == "🔗 URL":
        jd_url = st.text_input(
            "Job posting URL",
            key="jd_url",
            placeholder="https://www.indeed.com/viewjob?jk=...",
            label_visibility="collapsed",
        )
    elif jd_method == "📄 Upload":
        jd_file = st.file_uploader(
            "Upload JD",
            type=["pdf", "docx", "txt"],
            key="jd_file",
            label_visibility="collapsed",
        )
    else:
        jd_paste = st.text_area(
            "Paste job description",
            height=150,
            key="jd_paste",
            label_visibility="collapsed",
            placeholder="Paste Job Description Here",
        )

    st.subheader("Your Resume")
    resume_method = st.radio(
        "resume_input_method",
        ["📄 Upload", "✏️ Paste"],
        horizontal=True,
        label_visibility="collapsed",
        key="resume_method",
    )

    resume_file, resume_paste = None, ""
    if resume_method == "📄 Upload":
        resume_file = st.file_uploader(
            "Upload Resume",
            type=["pdf", "docx", "txt"],
            key="resume_file",
            label_visibility="collapsed",
        )
    else:
        resume_paste = st.text_area(
            "Paste resume",
            height=150,
            key="resume_paste",
            label_visibility="collapsed",
            placeholder="Paste Resume Here",
        )

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
            for key in ("dl_resume_pdf", "dl_resume_docx", "dl_cover_pdf", "dl_cover_docx", "dl_interview_docx"):
                st.session_state.pop(key, None)
            st.rerun()

    st.divider()
    st.caption(
        "Powered by Claude Sonnet · Built with LangGraph + Streamlit\n\n"
        "Guardrails: fabrication detection, tone check, ATS keyword check."
    )

# ── Main content ──────────────────────────────────────────────────────────────

st.title("Job Application Copilot")

if st.session_state.step == "idle":
    st.info("Fill in your job description and resume in the sidebar, then click **Run Analysis**.")

# ── Run the graph (executes only on the button-click rerun) ───────────────────

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

    # ── Step labels and progress mapping ─────────────────────────────────────
    # 8 nodes, progress advances as each completes
    STEP_LABELS = [
        "Gap Analysis",
        "Resume Rewrite",
        "Fabrication Check",
        "Tone Check",
        "ATS Check",
        "LaTeX Generation",
        "Cover Letter",
        "Interview Questions",
    ]
    STEP_MAP = {
        "gap_analysis_complete":        0,
        "resume_rewritten":             1,
        "guardrail_fabrication_complete": 2,
        "guardrail_tone_complete":      3,
        "guardrail_ats_complete":       4,
        "latex_generated":              5,
        "cover_letter_drafted":         6,
        "complete":                     7,
    }

    progress_bar = st.progress(0, text="Starting analysis…")

    st.subheader("Gap Analysis")
    gap_container = st.empty()

    # st.subheader("Rewritten Resume")
    # resume_container = st.empty()

    # Single-element placeholder for all guardrail warnings
    warnings_placeholder = st.empty()

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

            # Progress bar
            idx = STEP_MAP.get(step, -1)
            if idx >= 0:
                pct = (idx + 1) / len(STEP_LABELS)
                progress_bar.progress(pct, text=f"Completed: {STEP_LABELS[idx]}")

            # Gap analysis
            if snapshot.get("gap_analysis"):
                gap_container.markdown(snapshot["gap_analysis"])

            # Guardrail warnings — write all as one element to avoid st.empty() issues
            warnings = snapshot.get("guardrail_warnings", [])
            if warnings:
                warnings_placeholder.warning("\n\n".join(warnings))

            if snapshot.get("cover_letter"):
                cover_container.markdown(snapshot["cover_letter"])

            if snapshot.get("interview_questions"):
                interview_container.markdown(snapshot["interview_questions"])

    except Exception as e:
        print(f"[app] graph stream error: {e}", file=sys.stderr)
        st.session_state.step = "error"
        st.error("Something went wrong. Please try again or reduce the size of your inputs.")
        st.stop()

    if final_state.get("error"):
        print(f"[app] node error: {final_state['error']}", file=sys.stderr)
        st.session_state.step = "error"
        progress_bar.empty()
        st.error("Analysis failed. Please try again.")
        st.stop()

    progress_bar.progress(1.0, text="Complete!")
    st.session_state.step = "complete"
    st.session_state.result = final_state
    # Force a clean rerun so the persistent results section renders correctly
    st.rerun()

# ── Persistent results (renders on every rerun after completion) ──────────────

if st.session_state.step == "complete" and st.session_state.result:
    result = st.session_state.result

    # ── Gap Analysis ──────────────────────────────────────────────────────────
    st.subheader("Gap Analysis")
    st.markdown(result.get("gap_analysis", ""))

    # Guardrail summary
    warnings = result.get("guardrail_warnings", [])
    fab = result.get("fabrication_result")
    tone = result.get("tone_result")
    ats = result.get("ats_result")

    st.markdown("**Guardrail checks**")
    gcol1, gcol2, gcol3 = st.columns(3)
    with gcol1:
        if fab:
            if fab["passed"]:
                st.success("Fabrication check passed")
            else:
                st.warning(f"Fabrication: {len(fab['issues'])} issue(s)")
    with gcol2:
        if tone:
            if tone["passed"]:
                st.success("Tone check passed")
            else:
                st.warning(f"Tone: {len(tone['issues'])} issue(s)")
    with gcol3:
        if ats:
            if ats["passed"]:
                st.success("ATS check passed")
            else:
                st.warning(f"ATS: {len(ats['issues'])} missing keyword(s)")

    if warnings:
        with st.expander(f"View {len(warnings)} guardrail warning(s)"):
            for w in warnings:
                st.warning(w)

    # ── Cover Letter ──────────────────────────────────────────────────────────
    st.subheader("Cover Letter")
    st.markdown(result.get("cover_letter", ""))

    # ── Interview Questions ───────────────────────────────────────────────────
    st.subheader("Interview Questions")
    st.markdown(result.get("interview_questions", ""))

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Downloads")

    # Lazily generate and cache all export formats on first render
    latex = result.get("latex_source", "")
    cover = result.get("cover_letter", "")
    resume_md = result.get("rewritten_resume", "")

    if "dl_resume_pdf" not in st.session_state:
        if latex:
            try:
                st.session_state.dl_resume_pdf = resume_to_pdf(latex)
            except Exception as e:
                st.session_state.dl_resume_pdf = None
                print(f"[app] resume PDF error: {e}", file=sys.stderr)
        else:
            st.session_state.dl_resume_pdf = None

    if "dl_resume_docx" not in st.session_state:
        try:
            # Drive from latex_source so DOCX mirrors the PDF exactly
            st.session_state.dl_resume_docx = resume_to_docx(latex) if latex else None
        except Exception as e:
            st.session_state.dl_resume_docx = None
            print(f"[app] resume DOCX error: {e}", file=sys.stderr)

    if "dl_cover_pdf" not in st.session_state:
        try:
            st.session_state.dl_cover_pdf = cover_letter_to_pdf(cover) if cover else None
        except Exception as e:
            st.session_state.dl_cover_pdf = None
            print(f"[app] cover PDF error: {e}", file=sys.stderr)

    if "dl_cover_docx" not in st.session_state:
        try:
            st.session_state.dl_cover_docx = cover_letter_to_docx(cover) if cover else None
        except Exception as e:
            st.session_state.dl_cover_docx = None
            print(f"[app] cover DOCX error: {e}", file=sys.stderr)

    if "dl_interview_docx" not in st.session_state:
        interview = result.get("interview_questions", "")
        try:
            st.session_state.dl_interview_docx = cover_letter_to_docx(interview) if interview else None
        except Exception as e:
            st.session_state.dl_interview_docx = None
            print(f"[app] interview DOCX error: {e}", file=sys.stderr)

    res_col, cl_col, int_col = st.columns(3)

    with res_col:
        st.markdown("**Resume**")
        if st.session_state.dl_resume_pdf:
            st.download_button(
                "Download PDF",
                data=st.session_state.dl_resume_pdf,
                file_name="tailored_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        if st.session_state.dl_resume_docx:
            st.download_button(
                "Download DOCX",
                data=st.session_state.dl_resume_docx,
                file_name="tailored_resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    with cl_col:
        st.markdown("**Cover Letter**")
        if st.session_state.dl_cover_pdf:
            st.download_button(
                "Download PDF",
                data=st.session_state.dl_cover_pdf,
                file_name="cover_letter.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        if st.session_state.dl_cover_docx:
            st.download_button(
                "Download DOCX",
                data=st.session_state.dl_cover_docx,
                file_name="cover_letter.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )

    with int_col:
        st.markdown("**Interview Prep**")
        if st.session_state.dl_interview_docx:
            st.download_button(
                "Download DOCX",
                data=st.session_state.dl_interview_docx,
                file_name="interview_questions.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
