"""
Job Scanner Bot - Matching Engine
===================================
Computes semantic similarity between resume and job descriptions
using sentence-transformers + cosine similarity.

First run downloads the model (~90MB). Subsequent runs use cache.
"""

import logging
import re
from html import unescape

import numpy as np
from sentence_transformers import SentenceTransformer

import config
from sources import JobPosting

logger = logging.getLogger("job_scanner.matcher")

# ─── Model Loading ──────────────────────────────────────────────────
# all-MiniLM-L6-v2 is fast, small, and good for semantic similarity
# For higher accuracy (slower): "all-mpnet-base-v2"
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
_resume_embedding = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading sentence-transformer model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_resume_embedding() -> np.ndarray:
    global _resume_embedding
    if _resume_embedding is None:
        model = _get_model()
        clean_resume = _clean_text(config.RESUME_TEXT)
        _resume_embedding = model.encode(clean_resume, normalize_embeddings=True)
    return _resume_embedding


def reload_resume():
    """Force re-encode resume (call after editing config.RESUME_TEXT)."""
    global _resume_embedding
    _resume_embedding = None
    _get_resume_embedding()


# ─── Text Cleaning ──────────────────────────────────────────────────
def _clean_text(text: str) -> str:
    """Strip HTML tags, decode entities, collapse whitespace."""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)        # strip HTML
    text = re.sub(r"&\w+;", " ", text)           # leftover entities
    text = re.sub(r"https?://\S+", "", text)     # URLs
    text = re.sub(r"\s+", " ", text).strip()     # collapse whitespace
    return text


# ─── Keyword Boost ──────────────────────────────────────────────────
def _keyword_boost(text: str) -> float:
    """Add a small bonus for each config.BOOST_KEYWORDS found in text."""
    text_lower = text.lower()
    matches = sum(1 for kw in config.BOOST_KEYWORDS if kw.lower() in text_lower)
    return matches * config.BOOST_WEIGHT


# ─── Core Matching ──────────────────────────────────────────────────


def _get_section_weights():
    """Get section weights from config, with defaults."""
    if hasattr(config, 'SECTION_WEIGHTS'):
        return config.SECTION_WEIGHTS
    return {}


def _split_resume_sections(text):
    """Split resume into sections based on role headers."""
    lines = text.strip().split(chr(10))  # Split by newline
    sections = {}
    current_section = 'General'

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Detect section headers: short lines without periods
        if len(line) < 50 and not line.endswith('.') and ':' not in line:
            headers = ['skills', 'certifications', 'engineer', 'developer',
                       'consultant', 'intern', 'experience', 'education']
            if any(kw in line.lower() for kw in headers):
                current_section = line
                continue
        if line.endswith(':') and len(line) < 30:
            current_section = line.rstrip(':')
            continue
        if current_section not in sections:
            sections[current_section] = []
        sections[current_section].append(line)

    return sections


def compute_similarity_weighted(job):
    """
    Weighted similarity: scores each resume section separately,
    then combines with section weights from config.

    score = sum(section_similarity * section_weight) / sum(weights)
    """
    model = _get_model()
    weights = _get_section_weights()
    default_w = getattr(config, 'DEFAULT_SECTION_WEIGHT', 1.0)

    # Get job text embedding
    job_text = '{} at {}. {}'.format(job.title, job.company, job.description)
    clean_job = _clean_text(job_text)
    if len(clean_job) < 20:
        return 0.0
    if len(clean_job) > 2000:
        clean_job = clean_job[:2000]
    job_emb = model.encode(clean_job, normalize_embeddings=True)

    # Split resume into sections and score each
    sections = _split_resume_sections(config.RESUME_TEXT)
    if not sections:
        # Fallback to original method
        return compute_similarity(job)

    weighted_sum = 0.0
    weight_total = 0.0

    for section_name, bullets in sections.items():
        section_text = ' '.join(bullets)
        if len(section_text) < 10:
            continue

        section_emb = model.encode(section_text, normalize_embeddings=True)
        sim = float(np.dot(job_emb, section_emb))

        # Look up weight for this section
        w = weights.get(section_name, default_w)
        weighted_sum += sim * w
        weight_total += w

    if weight_total == 0:
        return 0.0

    base_score = weighted_sum / weight_total

    # Add keyword boost
    boost = _keyword_boost(clean_job)
    return min(base_score + boost, 1.0)


def compute_similarity(job: JobPosting) -> float:
    """
    Compute match score between resume and a job posting.
    Returns float 0.0 - 1.0 (capped).
    
    Score = cosine_similarity(resume_emb, job_emb) + keyword_boost
    """
    model = _get_model()
    resume_emb = _get_resume_embedding()

    # Combine title + company + description for richer signal
    job_text = f"{job.title} at {job.company}. {job.description}"
    clean_job = _clean_text(job_text)

    if len(clean_job) < 20:
        return 0.0

    # Truncate very long descriptions (model max ~256 tokens optimal)
    if len(clean_job) > 2000:
        clean_job = clean_job[:2000]

    job_emb = model.encode(clean_job, normalize_embeddings=True)

    # Cosine similarity (already normalized, so dot product = cosine)
    cosine_sim = float(np.dot(resume_emb, job_emb))

    # Add keyword boost
    boost = _keyword_boost(clean_job)

    return min(cosine_sim + boost, 1.0)


def match_jobs(jobs: list[JobPosting]) -> list[tuple[JobPosting, float]]:
    """
    Score all jobs against resume and return those above threshold.
    Returns list of (job, score) sorted by score descending.
    """
    logger.info(f"Matching {len(jobs)} jobs against resume (threshold={config.SIMILARITY_THRESHOLD})...")

    matched = []
    for job in jobs:
        try:
            score = compute_similarity(job)
            if score >= config.SIMILARITY_THRESHOLD:
                matched.append((job, score))
        except Exception as e:
            logger.error(f"Matching error for '{job.title}': {e}")

    matched.sort(key=lambda x: x[1], reverse=True)
    logger.info(f"Found {len(matched)} jobs above {config.SIMILARITY_THRESHOLD:.0%} threshold")
    return matched


# ─── Diagnostics ────────────────────────────────────────────────────
def score_distribution(jobs: list[JobPosting], bins: int = 10) -> dict:
    """Get score distribution for tuning threshold. Useful for debugging."""
    scores = []
    for job in jobs:
        try:
            scores.append(compute_similarity(job))
        except:
            pass

    if not scores:
        return {"error": "no scores computed"}

    arr = np.array(scores)
    hist, edges = np.histogram(arr, bins=bins, range=(0, 1))

    return {
        "count": len(scores),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "std": float(arr.std()),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "histogram": {f"{edges[i]:.1f}-{edges[i+1]:.1f}": int(hist[i]) for i in range(bins)},
    }
