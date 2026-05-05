import pytest
from state import AppState


JOB_DESCRIPTION = """
Senior Python Engineer — Acme Corp

Requirements:
- 5+ years of Python experience
- Proficiency with FastAPI and Django
- Experience with PostgreSQL and Redis
- Familiarity with Docker and Kubernetes
- Strong understanding of REST APIs

Nice to have:
- Experience with GraphQL
- AWS or GCP cloud experience
"""

ORIGINAL_RESUME = """
Jane Doe
jane@example.com | github.com/janedoe

EXPERIENCE
Software Engineer — StartupXYZ (2020–present)
- Built REST APIs using Flask and Python, serving 50k daily requests
- Managed PostgreSQL databases with 10M+ rows
- Deployed services using Docker on AWS EC2

Junior Developer — WebAgency (2018–2020)
- Developed internal tools in Python
- Wrote SQL queries for reporting dashboards

SKILLS
Python, Flask, PostgreSQL, Docker, SQL, AWS, Git

EDUCATION
B.S. Computer Science — State University, 2018
"""

REWRITTEN_RESUME = """
Jane Doe
jane@example.com | github.com/janedoe

EXPERIENCE
Software Engineer — StartupXYZ (2020–present)
- Engineered REST APIs with Python, serving 50,000 daily active requests
- Managed PostgreSQL databases containing 10M+ records
- Containerized and deployed services via Docker on AWS EC2

Junior Developer — WebAgency (2018–2020)
- Developed Python-based internal tooling
- Created SQL reporting dashboards

SKILLS
Python, PostgreSQL, Docker, SQL, AWS, Git, REST APIs

EDUCATION
B.S. Computer Science — State University, 2018
"""

GAP_ANALYSIS = """
### Missing Required Skills
- FastAPI (Flask used instead)
- Redis
- Kubernetes

### Experience Level Gaps
- Role requires 5+ years; candidate shows ~6 years total.

### Missing Nice-to-Haves
- GraphQL
- GCP

### Strengths Match
- Strong Python background
- PostgreSQL experience
- Docker deployment
- AWS familiarity
- REST API development
"""


@pytest.fixture
def base_state() -> AppState:
    return AppState(
        job_description=JOB_DESCRIPTION,
        original_resume=ORIGINAL_RESUME,
        gap_analysis=GAP_ANALYSIS,
        rewritten_resume=REWRITTEN_RESUME,
        fabrication_result=None,
        tone_result=None,
        ats_result=None,
        cover_letter="",
        interview_questions="",
        guardrail_warnings=[],
        current_step="resume_rewritten",
        error=None,
    )


@pytest.fixture
def error_state() -> AppState:
    return AppState(
        job_description=JOB_DESCRIPTION,
        original_resume=ORIGINAL_RESUME,
        gap_analysis="",
        rewritten_resume="",
        fabrication_result=None,
        tone_result=None,
        ats_result=None,
        cover_letter="",
        interview_questions="",
        guardrail_warnings=[],
        current_step="start",
        error="Something went wrong.",
    )
