import re
import sys
from rank_bm25 import BM25Okapi
from state import AppState, GuardrailResult

# Minimal stopword set — avoids nltk dependency
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "this", "that", "these",
    "those", "we", "you", "they", "he", "she", "it", "i", "our", "your",
    "their", "its", "my", "as", "if", "not", "no", "all", "any", "both",
    "who", "which", "what", "when", "where", "how", "than", "then", "so",
    "up", "out", "about", "into", "over", "after", "also", "more", "other",
}

MISSING_THRESHOLD = 0.20  # flag if >20% of JD keywords are absent


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#.\-]{1,}\b', text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def ats_checker_node(state: AppState) -> dict:
    warnings = list(state.get("guardrail_warnings", []))

    if state.get("error") or not state.get("rewritten_resume"):
        return {}

    try:
        jd_tokens = _tokenize(state["job_description"])
        resume_tokens = _tokenize(state["rewritten_resume"])

        if not jd_tokens or not resume_tokens:
            result: GuardrailResult = {"passed": True, "issues": [], "severity": "warning"}
            return {"ats_result": result, "guardrail_warnings": warnings}

        # BM25 with single-document corpus (the resume)
        bm25 = BM25Okapi([resume_tokens])

        # Deduplicated JD keywords
        jd_keywords = list(dict.fromkeys(jd_tokens))

        missing = []
        for keyword in jd_keywords:
            scores = bm25.get_scores([keyword])
            if scores[0] == 0.0:
                missing.append(keyword)

        missing_ratio = len(missing) / len(jd_keywords) if jd_keywords else 0
        passed = missing_ratio <= MISSING_THRESHOLD

        # Surface only top missing keywords (up to 10) to avoid noise
        top_missing = missing[:10]

        result: GuardrailResult = {
            "passed": passed,
            "issues": top_missing,
            "severity": "warning",
        }

        if not passed:
            warnings.append(
                f"[ATS] {len(missing)} JD keywords not found in resume "
                f"({missing_ratio:.0%} missing). Top missing: {', '.join(top_missing)}"
            )

        return {"ats_result": result, "guardrail_warnings": warnings}

    except Exception as e:
        print(f"[ats_checker] error: {e}", file=sys.stderr)
        warnings.append("[ATS Check] Could not complete — treat output with caution.")
        result: GuardrailResult = {
            "passed": False,
            "issues": ["Guardrail check failed — treat output with caution."],
            "severity": "warning",
        }
        return {"ats_result": result, "guardrail_warnings": warnings}
