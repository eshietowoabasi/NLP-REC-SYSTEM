"""A SYNTHETIC multi-theme corpus for pipeline tests and the benchmark.

Sentences are generated from invented templates about three computing themes, plus a
"NUC core" text about classic core subjects. None of it is real corpus data.
"""

from __future__ import annotations

import random

THEMES: dict[str, dict[str, list[str]]] = {
    "cloud": {
        "subjects": [
            "The platform team",
            "Our DevOps engineers",
            "The cloud squad",
            "Site reliability staff",
        ],
        "verbs": ["deploy", "automate", "monitor", "scale", "secure"],
        "objects": [
            "Kubernetes clusters on AWS",
            "Docker containers with Terraform",
            "CI/CD pipelines in GitHub Actions",
            "cloud infrastructure on Microsoft Azure",
            "microservices behind Nginx",
        ],
    },
    "security": {
        "subjects": [
            "The security analysts",
            "Our SOC team",
            "Penetration testers",
            "The incident response unit",
        ],
        "verbs": ["investigate", "detect", "contain", "report", "assess"],
        "objects": [
            "threats using Splunk and SIEM rules",
            "vulnerabilities with Nmap and Burp Suite",
            "phishing incidents across the network",
            "risks under ISO 27001 controls",
            "malware found by Wireshark captures",
        ],
    },
    "data": {
        "subjects": [
            "The data scientists",
            "Our analytics team",
            "Machine learning engineers",
            "The AI group",
        ],
        "verbs": ["train", "evaluate", "deploy", "clean", "visualise"],
        "objects": [
            "machine learning models in Python",
            "datasets with Pandas and NumPy",
            "deep learning networks in PyTorch",
            "dashboards in Power BI",
            "natural language processing pipelines",
        ],
    },
}

NUC_CORE_TEXT = (
    "Synthetic core course outline. Students study introduction to computer science, discrete "
    "structures and computer programming. The course covers operating systems, data structures "
    "and algorithms, and database management. Learners study computer architecture and "
    "organisation. Topics include software engineering principles and systems analysis. "
    "Students learn compiler construction and formal languages. The programme covers computer "
    "networks, data communication and the internet. Numerical methods and operations research "
    "are studied in the later years. "
)


def sentence(theme: str, rng: random.Random) -> str:
    parts = THEMES[theme]
    return (
        f"{rng.choice(parts['subjects'])} {rng.choice(parts['verbs'])} "
        f"{rng.choice(parts['objects'])} every week."
    )


def document_text(theme: str, sentences: int, seed: int) -> str:
    """A synthetic document of ``sentences`` sentences on one theme."""
    rng = random.Random(seed)
    return " ".join(sentence(theme, rng) for _ in range(sentences))


def core_with_courses() -> str:
    """A synthetic NUC core laid out like CCMAS: course headers with units, then content.

    "CSC 309" is written from the security theme, so the security theme should be closest to it.
    "CSC 299" (SIWES) and "GST 111" repeat the security text too, but are excluded from the
    comparison by the default ``nuc_course_exclusions`` setting.
    """
    security = document_text("security", 10, seed=4242)
    return (
        "CSC 101: Introduction to Computer Science (3 Units C: LH 30; PH 45)\n"
        + NUC_CORE_TEXT * 2
        + "\n\nCSC 309: Computer Security Fundamentals (2 Units C: LH 15; PH 45)\n"
        + security
        + "\n\nCSC 402 - Numerical Methods (3 Units E: LH 45)\n"
        + NUC_CORE_TEXT
        + "\n\nCSC 299: SIWES I (3 Units C: PH 135)\n"
        + security
        + "\n\nGST 111: Communication in English (2 Units C: LH 15; PH 45)\n"
        + security
    )


def corpus(documents_per_theme: int = 3, sentences: int = 20) -> list[tuple[str, str]]:
    """``(theme, text)`` pairs: ``documents_per_theme`` documents for each theme."""
    return [
        (theme, document_text(theme, sentences, seed=index * 100 + number))
        for index, theme in enumerate(THEMES)
        for number in range(documents_per_theme)
    ]
