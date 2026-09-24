"""Synthetic job-market corpus with three clear themes for pipeline tests."""
import random

THEMES = {
    "cloud": [
        "The engineer will deploy containerised services with Docker and Kubernetes on AWS.",
        "Experience with Terraform and CI/CD pipelines for cloud infrastructure is required.",
        "You will automate infrastructure as code and monitor cloud workloads on Microsoft Azure.",
        "Our DevOps team maintains Linux servers and Jenkins build pipelines for deployment.",
    ],
    "security": [
        "The analyst will lead incident response and threat hunting in our security operations centre.",
        "Hands-on penetration testing with Burp Suite, Nmap and Metasploit is essential.",
        "Candidates holding CISSP or CompTIA Security+ certification are preferred.",
        "You will manage firewalls, SIEM alerts and vulnerability assessment across the network.",
    ],
    "data": [
        "The scientist will build machine learning models in Python with scikit-learn and PyTorch.",
        "Strong SQL skills and Power BI dashboards for data analysis are required.",
        "You will design data pipelines with Apache Spark and Airflow for reporting.",
        "Knowledge of statistics, deep learning and natural language processing is an advantage.",
    ],
}


CLIENTS = ["a Lagos fintech", "a bank in Uyo", "an Abuja agency", "a Port Harcourt energy firm",
           "a telecoms operator", "a state ministry", "a health start-up", "an e-commerce platform"]
TIMEFRAMES = ["from day one", "within six months", "on a hybrid basis", "as part of a small team",
              "under senior guidance", "on a two-year contract"]


def theme_text(theme, n=40, seed=0):
    """``n`` distinct sentences: a theme sentence plus a varied closing clause.

    Passages are de-duplicated before topic modelling, so the corpus must not just
    repeat the same few sentences.
    """
    rng = random.Random(f"{theme}-{seed}")
    sentences = set()
    while len(sentences) < n:
        base = rng.choice(THEMES[theme]).rstrip(".")
        sentences.add(f"{base} for {rng.choice(CLIENTS)} {rng.choice(TIMEFRAMES)}.")
    return "\n\n".join(sorted(sentences))
