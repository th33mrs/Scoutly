"""
Trovly - Role Suggester
===========================
Analyzes your resume and suggests job roles you'd be a strong fit for.

Usage:
  python roles.py                  → Suggest roles from your resume
  python roles.py --top 20         → Show top 20 matches
  python roles.py --stretch        → Include stretch roles
  python roles.py --add-queries    → Auto-add top roles to SEARCH_QUERIES
"""

import argparse
import logging
import re
from html import unescape

import numpy as np
from sentence_transformers import SentenceTransformer

import config

logger = logging.getLogger("trovly.roles")

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


from role_database import EXPANDED_ROLES
ROLE_DATABASE = EXPANDED_ROLES
ROLE_DATABASE_OLD = [
    {"title": "DevOps Engineer", "category": "DevOps / Infrastructure",
     "description": "Design and maintain CI/CD pipelines, automate infrastructure provisioning with Terraform and Ansible, manage containerized deployments with Docker and Kubernetes, monitor production systems, implement infrastructure as code practices.",
     "key_skills": ["CI/CD", "Docker", "Kubernetes", "Terraform", "AWS", "Linux", "Jenkins", "GitHub Actions"]},
    {"title": "Site Reliability Engineer", "category": "DevOps / Infrastructure",
     "description": "Ensure system reliability and uptime, define SLOs and SLIs, build monitoring and alerting pipelines, perform incident response and root cause analysis, automate operational tasks with Python, manage cloud infrastructure at scale.",
     "key_skills": ["monitoring", "incident response", "Python", "Kubernetes", "AWS", "Terraform", "Prometheus", "Grafana"]},
    {"title": "Cloud Engineer", "category": "DevOps / Infrastructure",
     "description": "Design and implement cloud architecture on AWS, Azure, or GCP. Manage EC2, S3, RDS, ECS, EKS, Lambda, and networking services. Optimize cloud costs, implement security best practices, automate provisioning with Infrastructure as Code.",
     "key_skills": ["AWS", "Terraform", "CloudFormation", "EC2", "S3", "VPC", "IAM", "Lambda"]},
    {"title": "Platform Engineer", "category": "DevOps / Infrastructure",
     "description": "Build and maintain internal developer platforms, create self-service infrastructure tools, design deployment pipelines, manage Kubernetes clusters, improve developer experience through tooling and automation.",
     "key_skills": ["Kubernetes", "Docker", "CI/CD", "Python", "Terraform", "API design", "internal tooling"]},
    {"title": "Infrastructure Engineer", "category": "DevOps / Infrastructure",
     "description": "Manage and scale server infrastructure, automate provisioning, configure networking and load balancing, ensure high availability and disaster recovery, implement infrastructure as code.",
     "key_skills": ["Linux", "AWS", "Terraform", "Networking", "Load balancing", "DNS", "Ansible"]},
    {"title": "Cloud Security Engineer", "category": "Security",
     "description": "Implement cloud security controls, manage IAM policies and least-privilege access, conduct security assessments and vulnerability remediation, configure security groups and network ACLs.",
     "key_skills": ["IAM", "AWS", "security", "compliance", "vulnerability scanning", "encryption", "SIEM"]},
    {"title": "Security Operations Engineer", "category": "Security",
     "description": "Monitor security events using SIEM platforms like Splunk, investigate security incidents, build detection rules and alerting pipelines, perform threat hunting, maintain security tooling.",
     "key_skills": ["SIEM", "Splunk", "threat detection", "incident response", "Python", "security monitoring"]},
    {"title": "DevSecOps Engineer", "category": "Security",
     "description": "Integrate security practices into CI/CD pipelines, automate security scanning in deployment workflows, implement container security, manage secrets, enforce compliance in automated builds.",
     "key_skills": ["CI/CD", "security scanning", "Docker", "Kubernetes", "IAM", "SAST", "DAST", "secrets management"]},
    {"title": "SOC Analyst", "category": "Security",
     "description": "Monitor security dashboards and SIEM alerts, triage and investigate security events, document incidents, perform initial incident response, analyze log data for indicators of compromise.",
     "key_skills": ["SIEM", "Splunk", "log analysis", "incident response", "threat intelligence", "networking"]},
    {"title": "Detection Engineer", "category": "Security",
     "description": "Build and tune detection rules for security monitoring systems, create automated alerting workflows, develop threat models, analyze attack patterns, reduce false positives in SIEM platforms.",
     "key_skills": ["SIEM", "Splunk", "detection rules", "Python", "threat modeling", "log analysis"]},
    {"title": "Python Developer", "category": "Software Engineering",
     "description": "Build applications and services using Python, design APIs with Flask or FastAPI, write automated tests, work with databases like PostgreSQL and Redis, implement data processing pipelines.",
     "key_skills": ["Python", "Flask", "FastAPI", "PostgreSQL", "REST API", "testing", "Git"]},
    {"title": "Backend Engineer", "category": "Software Engineering",
     "description": "Design and build server-side applications, create RESTful APIs, manage databases and caching layers, implement authentication and authorization, optimize query performance.",
     "key_skills": ["Python", "Node.js", "PostgreSQL", "Redis", "REST API", "microservices", "Docker"]},
    {"title": "Software Engineer", "category": "Software Engineering",
     "description": "Design, develop, and maintain software applications. Write clean tested code, participate in code reviews, debug production issues, collaborate with cross-functional teams, follow agile methodologies.",
     "key_skills": ["Python", "JavaScript", "Git", "testing", "CI/CD", "databases", "agile"]},
    {"title": "Full Stack Engineer", "category": "Software Engineering",
     "description": "Build both frontend and backend components of web applications, create user interfaces with React or Vue, develop APIs with Node.js or Python, manage databases.",
     "key_skills": ["JavaScript", "Python", "React", "Node.js", "PostgreSQL", "HTML/CSS", "REST API"]},
    {"title": "Data Engineer", "category": "Data / ML",
     "description": "Build and maintain data pipelines, design ETL workflows, manage data warehouses, optimize database performance, work with Airflow, Spark, and SQL, ensure data quality.",
     "key_skills": ["Python", "SQL", "ETL", "data pipelines", "PostgreSQL", "Airflow", "Spark", "AWS"]},
    {"title": "Machine Learning Engineer", "category": "Data / ML",
     "description": "Deploy and maintain machine learning models in production, build ML pipelines, optimize model performance, work with TensorFlow and PyTorch, implement feature engineering.",
     "key_skills": ["Python", "machine learning", "TensorFlow", "PyTorch", "Docker", "AWS", "data pipelines"]},
    {"title": "MLOps Engineer", "category": "Data / ML",
     "description": "Bridge machine learning and operations. Build CI/CD pipelines for ML models, manage model versioning and deployment, monitor model performance, automate retraining workflows.",
     "key_skills": ["Python", "Docker", "Kubernetes", "CI/CD", "MLflow", "AWS", "monitoring"]},
    {"title": "Release Engineer", "category": "DevOps / Infrastructure",
     "description": "Manage software release processes, build and maintain CI/CD pipelines, coordinate deployments across environments, implement release automation, manage versioning and rollback.",
     "key_skills": ["CI/CD", "Git", "Jenkins", "GitHub Actions", "Docker", "scripting", "release management"]},
    {"title": "Systems Administrator", "category": "DevOps / Infrastructure",
     "description": "Manage and maintain server infrastructure, configure and troubleshoot Linux systems, automate routine tasks with scripting, manage user access, monitor system performance.",
     "key_skills": ["Linux", "Bash", "networking", "DNS", "monitoring", "automation", "security"]},
    {"title": "Production Engineer", "category": "DevOps / Infrastructure",
     "description": "Ensure production systems run reliably at scale. Debug and resolve production issues, automate operational processes, improve system performance, build tooling for engineering teams.",
     "key_skills": ["Python", "Linux", "monitoring", "automation", "debugging", "Kubernetes", "AWS"]},
    {"title": "Automation Engineer", "category": "DevOps / Infrastructure",
     "description": "Design and implement automation solutions for infrastructure, testing, and deployment. Build frameworks for repeatable processes, reduce manual operational work.",
     "key_skills": ["Python", "Bash", "Terraform", "Ansible", "CI/CD", "scripting", "API integration"]},
    {"title": "Cloud Architect", "category": "DevOps / Infrastructure",
     "description": "Design cloud infrastructure architecture, create migration strategies, establish best practices for cloud adoption, evaluate cloud services, design for scalability and cost optimization.",
     "key_skills": ["AWS", "architecture", "Terraform", "networking", "security", "cost optimization", "migration"]},
    {"title": "Developer Experience Engineer", "category": "DevOps / Infrastructure",
     "description": "Improve internal developer workflows and tooling, build self-service platforms, create documentation, optimize CI/CD pipelines, reduce friction in the development process.",
     "key_skills": ["CI/CD", "Python", "documentation", "API design", "developer tooling", "automation"]},
    {"title": "Solutions Engineer", "category": "Support / Operations",
     "description": "Bridge technical and business teams, design custom solutions for customers, conduct technical demos, support sales with architecture proposals, integrate products.",
     "key_skills": ["architecture", "API", "customer communication", "Python", "cloud", "integration"]},
    {"title": "Application Security Engineer", "category": "Security",
     "description": "Review application code for security vulnerabilities, implement secure coding practices, conduct penetration testing, integrate security testing into CI/CD.",
     "key_skills": ["security", "OWASP", "penetration testing", "CI/CD", "code review", "Python"]},
    {"title": "Vulnerability Management Engineer", "category": "Security",
     "description": "Identify and remediate security vulnerabilities across infrastructure and applications, manage vulnerability scanning tools, prioritize remediation efforts.",
     "key_skills": ["vulnerability scanning", "security", "NMAP", "remediation", "risk assessment", "SIEM"]},
    {"title": "Incident Response Engineer", "category": "Security",
     "description": "Lead response to security incidents, perform digital forensics, conduct root cause analysis, develop incident response playbooks, coordinate during security events.",
     "key_skills": ["incident response", "forensics", "SIEM", "Splunk", "log analysis", "security"]},
    {"title": "Penetration Tester", "category": "Security",
     "description": "Conduct authorized security testing against networks and applications, identify vulnerabilities, write detailed findings reports, use tools like Wireshark and NMAP.",
     "key_skills": ["penetration testing", "Wireshark", "NMAP", "networking", "security", "vulnerability assessment"]},
    {"title": "Observability Engineer", "category": "DevOps / Infrastructure",
     "description": "Design and implement monitoring, logging, and tracing systems. Build dashboards, configure alerting, instrument applications, manage Datadog, Prometheus, Grafana, CloudWatch.",
     "key_skills": ["monitoring", "Prometheus", "Grafana", "CloudWatch", "Datadog", "logging", "tracing"]},
    {"title": "GitOps Engineer", "category": "DevOps / Infrastructure",
     "description": "Implement GitOps workflows where Git is the single source of truth for infrastructure and deployments. Manage ArgoCD or Flux, automate reconciliation, ensure declarative infrastructure.",
     "key_skills": ["Git", "Kubernetes", "ArgoCD", "Terraform", "CI/CD", "infrastructure as code"]},
    {"title": "AI Engineer", "category": "Data / ML",
     "description": "Build AI-powered applications, integrate large language models, design prompt engineering workflows, deploy ML models as APIs, build RAG systems, optimize AI application performance.",
     "key_skills": ["Python", "LLMs", "API", "NLP", "Docker", "vector databases", "prompt engineering"]},
    {"title": "Database Administrator", "category": "Data / ML",
     "description": "Manage and optimize database systems, perform backups and recovery, tune query performance, manage replication and high availability, implement database security.",
     "key_skills": ["PostgreSQL", "MySQL", "Redis", "query optimization", "replication", "backups", "security"]},
    {"title": "QA Automation Engineer", "category": "Software Engineering",
     "description": "Design and implement automated test frameworks, write integration and end-to-end tests, integrate testing into CI/CD pipelines, improve test coverage and reliability.",
     "key_skills": ["testing", "automation", "Python", "CI/CD", "Selenium", "API testing"]},
    {"title": "Cloud Consultant", "category": "DevOps / Infrastructure",
     "description": "Advise organizations on cloud adoption and migration, design AWS or Azure architectures, optimize cloud spending, implement best practices, train teams on cloud technologies.",
     "key_skills": ["AWS", "architecture", "migration", "Terraform", "consulting", "cost optimization"]},
    {"title": "Data Platform Engineer", "category": "Data / ML",
     "description": "Build and maintain the infrastructure that data teams use. Manage data lakes, warehouses, and streaming systems. Ensure data availability, quality, and governance.",
     "key_skills": ["Python", "SQL", "AWS", "Kafka", "Spark", "Terraform", "data governance"]},
    {"title": "Compliance Engineer", "category": "Security",
     "description": "Implement and automate compliance controls, manage audit processes, ensure adherence to SOC2, HIPAA, or PCI-DSS, document security policies.",
     "key_skills": ["compliance", "security", "auditing", "IAM", "documentation", "policy"]},
    {"title": "Threat Intelligence Analyst", "category": "Security",
     "description": "Research and analyze cyber threats, track threat actor groups, produce intelligence reports, develop indicators of compromise, inform defensive strategies.",
     "key_skills": ["threat intelligence", "SIEM", "analysis", "security", "reporting", "indicators of compromise"]},
    {"title": "Network Engineer", "category": "DevOps / Infrastructure",
     "description": "Design and manage network infrastructure, configure firewalls and load balancers, troubleshoot connectivity issues, implement network security, manage VPNs.",
     "key_skills": ["networking", "firewalls", "load balancing", "VPN", "DNS", "TCP/IP", "AWS VPC"]},
]


def _clean_text(text):
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_resume_skills(resume_text):
    text_lower = resume_text.lower()
    all_skills = set()
    for role in ROLE_DATABASE:
        for skill in role["key_skills"]:
            if skill.lower() in text_lower:
                all_skills.add(skill)
    return sorted(all_skills)


def suggest_roles(resume_text=None, top_n=15, include_stretch=False):
    model = _get_model()
    if resume_text is None:
        resume_text = config.RESUME_TEXT
    clean_resume = _clean_text(resume_text)
    if len(clean_resume) < 50:
        return {"error": "Resume text too short to analyze"}

    resume_emb = model.encode(clean_resume, normalize_embeddings=True)
    role_texts = [r["description"] for r in ROLE_DATABASE]
    role_embs = model.encode(role_texts, normalize_embeddings=True)
    resume_skills = set(s.lower() for s in _extract_resume_skills(resume_text))

    results = []
    for i, role in enumerate(ROLE_DATABASE):
        sim = float(np.dot(resume_emb, role_embs[i]))
        role_skills = set(s.lower() for s in role["key_skills"])
        matching = role_skills & resume_skills
        missing = role_skills - resume_skills
        skill_coverage = len(matching) / len(role_skills) if role_skills else 0
        combined = (sim * 0.7) + (skill_coverage * 0.3)

        if combined >= 0.65:
            fit = "strong"
        elif combined >= 0.50:
            fit = "moderate"
        else:
            fit = "stretch"

        results.append({
            "title": role["title"], "category": role["category"],
            "score": round(combined, 4), "semantic_score": round(sim, 4),
            "skill_coverage": round(skill_coverage, 4), "fit": fit,
            "matching_skills": sorted(s.title() for s in matching),
            "missing_skills": sorted(s.title() for s in missing),
            "description": role["description"],
        })

    results.sort(key=lambda x: -x["score"])
    if not include_stretch:
        results = [r for r in results if r["fit"] in ("strong", "moderate")]
    return results[:top_n]


def print_suggestions(results):
    if isinstance(results, dict) and "error" in results:
        print(results["error"])
        return
    if not results:
        print("No matching roles found. Try --stretch to include stretch roles.")
        return

    print("\n" + "=" * 65)
    print("  TROVLY ROLE SUGGESTIONS")
    print("=" * 65)

    strong = [r for r in results if r["fit"] == "strong"]
    moderate = [r for r in results if r["fit"] == "moderate"]
    stretch = [r for r in results if r["fit"] == "stretch"]

    if strong:
        print("\n  STRONG FIT")
        print("  " + "-" * 63)
        for r in strong:
            print("    {:.0%}  {} [{}]".format(r["score"], r["title"], r["category"]))
            print("         Skills: {}".format(", ".join(r["matching_skills"][:6])))
            if r["missing_skills"]:
                print("         Gaps:   {}".format(", ".join(r["missing_skills"])))
            print()

    if moderate:
        print("\n  MODERATE FIT")
        print("  " + "-" * 63)
        for r in moderate:
            print("    {:.0%}  {} [{}]".format(r["score"], r["title"], r["category"]))
            print("         Skills: {}".format(", ".join(r["matching_skills"][:6])))
            if r["missing_skills"]:
                print("         Gaps:   {}".format(", ".join(r["missing_skills"])))
            print()

    if stretch:
        print("\n  STRETCH ROLES")
        print("  " + "-" * 63)
        for r in stretch:
            print("    {:.0%}  {} [{}]".format(r["score"], r["title"], r["category"]))
            if r["missing_skills"]:
                print("         Need:   {}".format(", ".join(r["missing_skills"])))
            print()

    resume_skills = _extract_resume_skills(config.RESUME_TEXT)
    print("\n  YOUR DETECTED SKILLS ({})".format(len(resume_skills)))
    print("  " + "-" * 63)
    print("    " + ", ".join(resume_skills))
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Trovly Role Suggester")
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--stretch", action="store_true")
    parser.add_argument("--add-queries", action="store_true")
    args = parser.parse_args()

    results = suggest_roles(top_n=args.top, include_stretch=args.stretch)
    print_suggestions(results)

    if args.add_queries and not isinstance(results, dict):
        existing = set(q.lower() for q in config.SEARCH_QUERIES)
        new_roles = [r["title"].lower() for r in results[:10] if r["title"].lower() not in existing]
        if new_roles:
            print("\nAdding {} new roles to SEARCH_QUERIES:".format(len(new_roles)))
            for role in new_roles:
                print("  + {}".format(role))
            with open("config.py", "r") as f:
                content = f.read()
            import re as re2
            match = re2.search(r"(SEARCH_QUERIES\s*=\s*\[.*?)(])", content, re2.DOTALL)
            if match:
                new_entries = ""
                for role in new_roles:
                    new_entries += '    "{}",\n'.format(role)
                content = content[:match.end(1)] + new_entries + content[match.start(2):]
                with open("config.py", "w") as f:
                    f.write(content)
                print("config.py updated.")


if __name__ == "__main__":
    main()
