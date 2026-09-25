"""SYNTHETIC documents for benchmarking (invented text, not real corpus data).

Generates job-advert-like documents on several computing themes from sentence templates, with
enough variety that topic modelling finds distinct themes.
"""

from __future__ import annotations

import random

THEMES: dict[str, dict[str, list[str]]] = {
    "cloud": {
        "roles": [
            "platform engineers",
            "DevOps engineers",
            "site reliability engineers",
            "cloud architects",
        ],
        "tasks": [
            "deploy Kubernetes clusters on AWS",
            "automate infrastructure with Terraform",
            "build CI/CD pipelines in GitHub Actions",
            "manage Docker containers in production",
            "monitor services with Prometheus and Grafana",
            "design Microsoft Azure landing zones",
        ],
    },
    "security": {
        "roles": [
            "security analysts",
            "penetration testers",
            "SOC engineers",
            "incident responders",
        ],
        "tasks": [
            "investigate alerts in Splunk",
            "run vulnerability assessments with Nmap",
            "perform penetration testing with Burp Suite",
            "respond to phishing incidents",
            "apply ISO 27001 risk controls",
            "analyse network traffic in Wireshark",
        ],
    },
    "data": {
        "roles": [
            "data scientists",
            "machine learning engineers",
            "data analysts",
            "AI researchers",
        ],
        "tasks": [
            "train machine learning models in Python",
            "clean datasets with Pandas",
            "build deep learning networks in PyTorch",
            "publish dashboards in Power BI",
            "develop natural language processing pipelines",
            "evaluate models with scikit-learn",
        ],
    },
    "fintech": {
        "roles": [
            "payment engineers",
            "backend developers",
            "fintech product teams",
            "integration engineers",
        ],
        "tasks": [
            "integrate Paystack and Flutterwave payment gateways",
            "build USSD and mobile money services",
            "secure card transactions for Remita",
            "reconcile settlements with Interswitch",
            "design REST APIs in Node.js",
            "meet data protection rules under the NDPR",
        ],
    },
    "mobile": {
        "roles": [
            "mobile developers",
            "Flutter engineers",
            "Android developers",
            "UI/UX designers",
        ],
        "tasks": [
            "ship Flutter apps for Android and iOS",
            "design interfaces in Figma",
            "write Kotlin features for Android",
            "test apps with automated UI tests",
            "integrate Firebase authentication",
            "optimise React Native performance",
        ],
    },
}

CONNECTORS = [
    "Our {role} {task} every sprint.",
    "The successful team will {task} with other {role}.",
    "In this role, {role} {task} and document the results.",
    "We expect {role} to {task} while mentoring junior colleagues.",
    "Each quarter the {role} {task} for clients across West Africa.",
]

NUC_CORE_SENTENCES = [
    "Students are introduced to computer science and problem solving.",
    "The course covers discrete structures, logic and set theory.",
    "Learners study data structures, algorithms and their complexity.",
    "Operating systems topics include processes, memory and file systems.",
    "Database management covers the relational model and SQL.",
    "Computer architecture and organisation are studied in depth.",
    "Software engineering principles and systems analysis are taught.",
    "Compiler construction and formal languages form part of the core.",
    "Computer networks and data communication are covered.",
    "Numerical methods and operations research are introduced.",
]


def make_document(theme: str, words: int, seed: int) -> str:
    """A synthetic document of roughly ``words`` words on ``theme``."""
    rng = random.Random(seed)
    parts = THEMES[theme]
    sentences: list[str] = []
    count = 0
    while count < words:
        sentence = rng.choice(CONNECTORS).format(
            role=rng.choice(parts["roles"]), task=rng.choice(parts["tasks"])
        )
        sentences.append(sentence)
        count += len(sentence.split())
    # Paragraphs of 6 sentences, as in real adverts.
    return "\n\n".join(" ".join(sentences[i : i + 6]) for i in range(0, len(sentences), 6))


def make_corpus(documents: int = 20, words: int = 3000) -> list[tuple[str, str]]:
    """``(theme, text)`` pairs spread evenly across the themes."""
    themes = list(THEMES)
    return [
        (themes[i % len(themes)], make_document(themes[i % len(themes)], words, seed=i))
        for i in range(documents)
    ]


def make_nuc_core(words: int = 3000, seed: int = 7) -> str:
    rng = random.Random(seed)
    sentences, count = [], 0
    while count < words:
        sentence = rng.choice(NUC_CORE_SENTENCES)
        sentences.append(sentence)
        count += len(sentence.split())
    return "\n\n".join(" ".join(sentences[i : i + 6]) for i in range(0, len(sentences), 6))
