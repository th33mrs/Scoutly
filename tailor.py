"""
Job Scanner Bot - Resume Tailor
Usage:
  python tailor.py --jd "paste job description here"
  python tailor.py --export --jd "paste JD"
  python tailor.py SEARCH_TERM               → tailor for a tracked job
  python tailor.py --gaps SEARCH_TERM         → skill gaps only
"""

import argparse
import re
from html import unescape

import numpy as np
from sentence_transformers import SentenceTransformer

import config
from tracker import JobTracker

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _clean_text(text):
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&\w+;", " ", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_bullets(resume_text):
    lines = resume_text.strip().split("\n")
    bullets = []
    current_section = "General"
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(line) < 50 and not line.endswith(".") and ":" not in line:
            if any(kw in line.lower() for kw in ["skills", "certifications", "engineer", "developer",
                                                   "consultant", "intern", "experience", "education"]):
                current_section = line
                continue
        if line.endswith(":") and len(line) < 30:
            current_section = line.rstrip(":")
            continue
        bullets.append({"text": line, "section": current_section})
    return bullets


def _extract_keywords(text):
    tech_terms = set()
    text_lower = text.lower()
    known_keywords = [
        "python", "javascript", "typescript", "java", "go", "rust", "ruby", "c++", "c#",
        "react", "vue", "angular", "node.js", "django", "flask", "fastapi",
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
        "ci/cd", "jenkins", "github actions", "gitlab", "circleci",
        "postgresql", "mysql", "redis", "mongodb", "dynamodb", "elasticsearch",
        "linux", "nginx", "apache", "cloudflare",
        "rest", "graphql", "grpc", "microservices", "serverless",
        "machine learning", "deep learning", "nlp", "computer vision",
        "agile", "scrum", "kanban", "jira",
        "security", "siem", "splunk", "iam", "soc", "devsecops",
        "ecs", "eks", "ec2", "s3", "lambda", "cloudwatch", "cloudfront",
        "sqs", "sns", "rds", "alb", "vpc",
        "datadog", "prometheus", "grafana", "pagerduty",
        "git", "api", "sdk", "oauth", "saml",
        "data pipeline", "etl", "data warehouse", "snowflake", "databricks",
        "tableau", "power bi", "looker", "figma", "sketch",
        "communication", "leadership", "mentoring", "cross-functional",
    ]
    for kw in known_keywords:
        if kw.lower() in text_lower:
            tech_terms.add(kw)
    return tech_terms


def tailor_resume(job_description, verbose=True):
    model = _get_model()
    bullets = _extract_bullets(config.RESUME_TEXT)
    if not bullets:
        return {"error": "No resume bullets found"}

    jd_clean = _clean_text(job_description)
    if len(jd_clean) < 20:
        return {"error": "Job description too short"}

    jd_emb = model.encode(jd_clean, normalize_embeddings=True)
    bullet_texts = [b["text"] for b in bullets]
    bullet_embs = model.encode(bullet_texts, normalize_embeddings=True)

    scores = []
    for bullet, emb in zip(bullets, bullet_embs):
        sim = float(np.dot(jd_emb, emb))
        scores.append({"text": bullet["text"], "section": bullet["section"], "relevance": round(sim, 4)})
    scores.sort(key=lambda x: -x["relevance"])

    jd_keywords = _extract_keywords(jd_clean)
    resume_keywords = _extract_keywords(config.RESUME_TEXT)
    gaps = jd_keywords - resume_keywords
    matches = jd_keywords & resume_keywords

    strong = [s for s in scores if s["relevance"] >= 0.5]
    moderate = [s for s in scores if 0.3 <= s["relevance"] < 0.5]
    weak = [s for s in scores if s["relevance"] < 0.3]

    result = {
        "strong_bullets": strong, "moderate_bullets": moderate, "weak_bullets": weak,
        "skill_matches": sorted(matches), "skill_gaps": sorted(gaps),
        "total_bullets": len(scores),
        "jd_keywords_found": len(matches), "jd_keywords_missing": len(gaps),
    }
    if verbose:
        _print_tailoring(result)
    return result


def _print_tailoring(result):
    print("\n" + "=" * 65)
    print("  RESUME TAILORING ANALYSIS")
    print("=" * 65)

    print("\n  STRONG MATCHES (emphasize these)")
    print("  " + "-" * 63)
    if result["strong_bullets"]:
        for b in result["strong_bullets"][:10]:
            print("    {:.0%}  {}".format(b["relevance"], b["text"][:75]))
    else:
        print("    None — consider rewriting bullets to match the JD language")

    print("\n  MODERATE MATCHES (keep, consider rewording)")
    print("  " + "-" * 63)
    for b in result["moderate_bullets"][:8]:
        print("    {:.0%}  {}".format(b["relevance"], b["text"][:75]))

    print("\n  WEAK MATCHES (deprioritize or cut)")
    print("  " + "-" * 63)
    for b in result["weak_bullets"][:5]:
        print("    {:.0%}  {}".format(b["relevance"], b["text"][:75]))

    print("\n  SKILLS YOU MATCH")
    print("  " + "-" * 63)
    if result["skill_matches"]:
        print("    " + ", ".join(result["skill_matches"]))
    else:
        print("    None detected")

    print("\n  SKILL GAPS (in JD but missing from resume)")
    print("  " + "-" * 63)
    if result["skill_gaps"]:
        print("    " + ", ".join(result["skill_gaps"]))
        print("\n    TIP: Add these if you have any experience with them.")
    else:
        print("    None — your resume covers all detected keywords!")

    total = result["total_bullets"]
    strong_pct = len(result["strong_bullets"]) / total * 100 if total else 0
    print("\n  SUMMARY")
    print("  " + "-" * 63)
    print("    {} bullets analyzed".format(total))
    print("    {} strong | {} moderate | {} weak".format(
        len(result["strong_bullets"]), len(result["moderate_bullets"]), len(result["weak_bullets"])))
    print("    {:.0f}% of resume directly relevant".format(strong_pct))
    print("    {} / {} JD keywords matched".format(
        result["jd_keywords_found"], result["jd_keywords_found"] + result["jd_keywords_missing"]))
    print("=" * 65)


def export_tailored(job_description, filename="tailored_resume.txt"):
    model = _get_model()
    bullets = _extract_bullets(config.RESUME_TEXT)
    jd_clean = _clean_text(job_description)
    jd_emb = model.encode(jd_clean, normalize_embeddings=True)
    bullet_texts = [b["text"] for b in bullets]
    bullet_embs = model.encode(bullet_texts, normalize_embeddings=True)

    scored = []
    for bullet, emb in zip(bullets, bullet_embs):
        sim = float(np.dot(jd_emb, emb))
        scored.append((bullet, sim))
    scored.sort(key=lambda x: -x[1])

    sections = {}
    for bullet, score in scored:
        sec = bullet["section"]
        if sec not in sections:
            sections[sec] = []
        sections[sec].append((bullet["text"], score))
    section_order = sorted(sections.keys(), key=lambda s: -max(sc for _, sc in sections[s]))

    lines = ["TAILORED RESUME", "=" * 50, ""]
    for sec in section_order:
        lines.append(sec.upper())
        lines.append("-" * 40)
        for text, score in sections[sec]:
            marker = ">>>" if score >= 0.5 else "   "
            lines.append("{} {:.0%} | {}".format(marker, score, text))
        lines.append("")

    jd_keywords = _extract_keywords(jd_clean)
    resume_keywords = _extract_keywords(config.RESUME_TEXT)
    gaps = jd_keywords - resume_keywords
    if gaps:
        lines.append("SKILL GAPS TO ADDRESS")
        lines.append("-" * 40)
        lines.append(", ".join(sorted(gaps)))
        lines.append("")

    with open(filename, "w") as f:
        f.write("\n".join(lines))
    print("Tailored resume saved to {}".format(filename))


def main():
    parser = argparse.ArgumentParser(description="Resume Tailor")
    parser.add_argument("job", nargs="?", help="Search term for tracked job")
    parser.add_argument("--jd", type=str, help="Paste a job description directly")
    parser.add_argument("--gaps", action="store_true", help="Show skill gaps only")
    parser.add_argument("--export", action="store_true", help="Export tailored resume")
    args = parser.parse_args()

    if args.jd:
        if args.export:
            export_tailored(args.jd)
        else:
            tailor_resume(args.jd)
        return

    if args.job:
        tracker = JobTracker()
        results = tracker.search(args.job)
        if not results:
            print("No tracked job matching '{}'. Use --jd instead.".format(args.job))
            return
        job = results[0]
        print("Tailoring for: {} at {}".format(job["title"], job["company"]))
        try:
            import requests
            resp = requests.get(job["url"], timeout=15)
            jd_text = _clean_text(resp.text)
            if len(jd_text) < 50:
                print("Could not extract JD from URL. Use --jd and paste manually.")
                return
        except Exception as e:
            print("Could not fetch JD: {}. Use --jd and paste manually.".format(e))
            return

        if args.export:
            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", job["title"][:30]).lower()
            export_tailored(jd_text, "tailored_{}.txt".format(safe_name))
        elif args.gaps:
            result = tailor_resume(jd_text, verbose=False)
            print("\nSKILL GAPS for '{}':".format(job["title"]))
            if result["skill_gaps"]:
                for gap in result["skill_gaps"]:
                    print("  - {}".format(gap))
            else:
                print("  None — you match all detected keywords!")
        else:
            tailor_resume(jd_text)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
