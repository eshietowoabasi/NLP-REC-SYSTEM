"""Starter skill patterns for the spaCy EntityRuler (seeded by ``flask seed``).

Each entry is ``(label, canonical_name, patterns)``. A pattern is either a phrase (matched
case-insensitively) or a spaCy token pattern (list of token dicts) for short, ambiguous names
such as "Go", "R" or "C", which only count when followed by a word that confirms the meaning.
Admins can add, edit and deactivate patterns later.
"""

from __future__ import annotations

from typing import Any

Pattern = str | list[dict[str, Any]]


def _lang_token(name: str) -> list[dict[str, Any]]:
    """``<Name> programming|language|developer|...`` with exact casing for short names."""
    return [
        {"ORTH": name},
        {"LOWER": {"IN": ["programming", "language", "developer", "developers", "engineer"]}},
    ]


LANGUAGES: list[tuple[str, list[Pattern]]] = [
    ("Python", ["python"]),
    ("Java", ["java"]),
    ("JavaScript", ["javascript", "js", "ecmascript"]),
    ("TypeScript", ["typescript"]),
    ("C++", ["c++", "cpp"]),
    ("C#", ["c#", "c sharp"]),
    ("C", [_lang_token("C")]),
    ("Go", ["golang", _lang_token("Go")]),
    ("Rust", ["rust"]),
    ("Kotlin", ["kotlin"]),
    ("Swift", ["swift"]),
    ("PHP", ["php"]),
    ("Ruby", ["ruby"]),
    ("Scala", ["scala"]),
    ("R", [_lang_token("R"), "rstudio"]),
    ("SQL", ["sql", "t-sql", "pl/sql"]),
    ("Dart", ["dart"]),
    ("Bash", ["bash", "shell scripting"]),
    ("MATLAB", ["matlab"]),
    ("Solidity", ["solidity"]),
    ("HTML", ["html", "html5"]),
    ("CSS", ["css", "css3"]),
]

TOOLS: list[tuple[str, list[Pattern]]] = [
    # Web and mobile frameworks
    ("React", ["react", "react.js", "reactjs"]),
    ("Angular", ["angular"]),
    ("Vue.js", ["vue", "vue.js", "vuejs"]),
    ("Node.js", ["node.js", "nodejs"]),
    ("Express.js", ["express.js", "expressjs"]),
    ("Next.js", ["next.js", "nextjs"]),
    ("Django", ["django"]),
    ("Flask", ["flask"]),
    ("FastAPI", ["fastapi"]),
    ("Spring Boot", ["spring boot", "spring framework"]),
    ("Laravel", ["laravel"]),
    (".NET", [".net", "asp.net", ".net core"]),
    ("Ruby on Rails", ["ruby on rails", "rails"]),
    ("Flutter", ["flutter"]),
    ("React Native", ["react native"]),
    ("GraphQL", ["graphql"]),
    # Data and AI
    ("TensorFlow", ["tensorflow"]),
    ("PyTorch", ["pytorch"]),
    ("scikit-learn", ["scikit-learn", "sklearn"]),
    ("Pandas", ["pandas"]),
    ("NumPy", ["numpy"]),
    ("Keras", ["keras"]),
    ("Hugging Face", ["hugging face", "huggingface", "transformers library"]),
    ("LangChain", ["langchain"]),
    ("OpenCV", ["opencv"]),
    ("Apache Spark", ["apache spark", "spark", "pyspark"]),
    ("Hadoop", ["hadoop"]),
    ("Apache Kafka", ["kafka", "apache kafka"]),
    ("Apache Airflow", ["airflow", "apache airflow"]),
    ("Power BI", ["power bi", "powerbi"]),
    ("Tableau", ["tableau"]),
    ("Microsoft Excel", ["excel", "microsoft excel"]),
    ("Jupyter", ["jupyter", "jupyter notebook"]),
    # Cloud and DevOps
    ("AWS", ["aws", "amazon web services"]),
    ("Microsoft Azure", ["azure", "microsoft azure"]),
    ("Google Cloud Platform", ["gcp", "google cloud", "google cloud platform"]),
    ("Docker", ["docker"]),
    ("Kubernetes", ["kubernetes", "k8s"]),
    ("Terraform", ["terraform"]),
    ("Ansible", ["ansible"]),
    ("Jenkins", ["jenkins"]),
    ("GitHub Actions", ["github actions"]),
    ("GitLab CI", ["gitlab ci", "gitlab ci/cd"]),
    ("Git", ["git", "github", "gitlab"]),
    ("Linux", ["linux", "ubuntu", "red hat"]),
    ("Nginx", ["nginx"]),
    ("Prometheus", ["prometheus"]),
    ("Grafana", ["grafana"]),
    # Databases
    ("PostgreSQL", ["postgresql", "postgres"]),
    ("MySQL", ["mysql"]),
    ("MongoDB", ["mongodb", "mongo"]),
    ("Redis", ["redis"]),
    ("Oracle Database", ["oracle database", "oracle db"]),
    ("Microsoft SQL Server", ["sql server", "mssql"]),
    ("Firebase", ["firebase", "firestore"]),
    ("Elasticsearch", ["elasticsearch"]),
    ("Snowflake", ["snowflake"]),
    ("BigQuery", ["bigquery"]),
    # Security tools
    ("Wireshark", ["wireshark"]),
    ("Metasploit", ["metasploit"]),
    ("Burp Suite", ["burp suite", "burpsuite"]),
    ("Nmap", ["nmap"]),
    ("Splunk", ["splunk"]),
    ("Kali Linux", ["kali linux", "kali"]),
    # Collaboration and testing
    ("Jira", ["jira"]),
    ("Figma", ["figma"]),
    ("Postman", ["postman"]),
    ("Selenium", ["selenium"]),
    ("Cypress", ["cypress"]),
    # Payments / fintech platforms
    ("Paystack", ["paystack"]),
    ("Flutterwave", ["flutterwave"]),
    ("Interswitch", ["interswitch"]),
    ("Remita", ["remita"]),
    ("Stripe", ["stripe"]),
]

SKILLS: list[tuple[str, list[Pattern]]] = [
    ("Machine Learning", ["machine learning", "ml models"]),
    ("Deep Learning", ["deep learning", "neural networks"]),
    ("Natural Language Processing", ["natural language processing", "nlp"]),
    ("Computer Vision", ["computer vision", "image recognition"]),
    ("Artificial Intelligence", ["artificial intelligence"]),
    ("Generative AI", ["generative ai", "large language models", "llms", "prompt engineering"]),
    ("MLOps", ["mlops"]),
    ("Data Analysis", ["data analysis", "data analytics"]),
    ("Data Science", ["data science"]),
    ("Data Engineering", ["data engineering", "data pipelines", "etl"]),
    ("Data Visualisation", ["data visualization", "data visualisation"]),
    ("Big Data", ["big data"]),
    ("Statistics", ["statistics", "statistical analysis"]),
    ("Business Intelligence", ["business intelligence"]),
    ("Cloud Computing", ["cloud computing", "cloud infrastructure"]),
    ("DevOps", ["devops"]),
    ("CI/CD", ["ci/cd", "continuous integration", "continuous delivery", "continuous deployment"]),
    ("Microservices", ["microservices", "microservice architecture"]),
    ("API Development", ["rest api", "restful api", "restful apis", "api development", "grpc"]),
    ("Web Development", ["web development", "frontend development", "backend development"]),
    (
        "Mobile Development",
        ["mobile app development", "mobile development", "android development", "ios development"],
    ),
    (
        "Software Testing",
        ["software testing", "unit testing", "test automation", "quality assurance"],
    ),
    ("UI/UX Design", ["ui/ux", "user experience", "user interface design"]),
    ("Agile Methodologies", ["agile", "scrum", "kanban"]),
    ("Object-Oriented Programming", ["object-oriented programming", "oop"]),
    ("Data Structures and Algorithms", ["data structures", "algorithms"]),
    ("System Design", ["system design", "software architecture"]),
    (
        "Database Administration",
        ["database administration", "database design", "database management"],
    ),
    (
        "Networking",
        ["computer networking", "network administration", "tcp/ip", "routing and switching"],
    ),
    ("System Administration", ["system administration", "systems administration"]),
    ("Virtualisation", ["virtualization", "virtualisation", "vmware"]),
    ("Penetration Testing", ["penetration testing", "pen testing", "ethical hacking"]),
    ("Vulnerability Assessment", ["vulnerability assessment", "vulnerability management"]),
    ("Incident Response", ["incident response", "incident handling"]),
    ("Digital Forensics", ["digital forensics", "computer forensics"]),
    ("Threat Intelligence", ["threat intelligence", "threat hunting"]),
    ("Security Operations", ["security operations", "soc analyst", "siem"]),
    ("Cryptography", ["cryptography", "encryption"]),
    ("Identity and Access Management", ["identity and access management", "iam"]),
    ("Cloud Security", ["cloud security"]),
    ("Information Security", ["information security", "cybersecurity", "cyber security"]),
    ("Risk Management", ["risk management", "risk assessment"]),
    ("Data Protection Compliance", ["ndpr", "ndpa", "gdpr", "data protection"]),
    ("Blockchain", ["blockchain", "smart contracts", "web3"]),
    ("Internet of Things", ["internet of things", "iot"]),
    ("Embedded Systems", ["embedded systems", "microcontrollers"]),
    ("IT Support", ["it support", "technical support", "help desk", "troubleshooting"]),
    ("Project Management", ["project management"]),
    ("Payment Integration", ["payment integration", "payment gateway", "ussd", "mobile money"]),
    ("Version Control", ["version control"]),
]

CERTIFICATIONS: list[tuple[str, list[Pattern]]] = [
    ("AWS Certified Solutions Architect", ["aws certified solutions architect"]),
    ("AWS Certified Cloud Practitioner", ["aws certified cloud practitioner"]),
    ("Microsoft Azure Fundamentals", ["az-900", "azure fundamentals"]),
    ("Microsoft Azure Administrator", ["az-104", "azure administrator"]),
    ("Google Cloud Professional", ["google cloud professional", "professional cloud architect"]),
    ("CompTIA A+", ["comptia a+"]),
    ("CompTIA Network+", ["comptia network+", "network+"]),
    ("CompTIA Security+", ["comptia security+", "security+"]),
    ("CompTIA CySA+", ["cysa+"]),
    ("CompTIA PenTest+", ["pentest+"]),
    ("CISSP", ["cissp"]),
    ("CISM", ["cism"]),
    ("CISA", ["cisa"]),
    ("Certified Ethical Hacker", ["certified ethical hacker", "ceh"]),
    ("OSCP", ["oscp"]),
    ("CCNA", ["ccna"]),
    ("CCNP", ["ccnp"]),
    ("ITIL", ["itil"]),
    ("PMP", ["pmp"]),
    ("PRINCE2", ["prince2"]),
    ("Certified Scrum Master", ["certified scrum master", "csm", "psm"]),
    ("Oracle Certified Java Programmer", ["oracle certified java", "ocjp"]),
    ("Certified Kubernetes Administrator", ["certified kubernetes administrator", "cka"]),
    ("HashiCorp Terraform Associate", ["terraform associate"]),
    ("Google Data Analytics Certificate", ["google data analytics certificate"]),
    ("ISO 27001 Lead Implementer", ["iso 27001", "iso/iec 27001"]),
]

SKILL_PATTERN_GROUPS: dict[str, list[tuple[str, list[Pattern]]]] = {
    "LANGUAGE": LANGUAGES,
    "TOOL": TOOLS,
    "SKILL": SKILLS,
    "CERT": CERTIFICATIONS,
}


def iter_skill_patterns() -> list[tuple[str, str, Pattern]]:
    """Flatten the groups into ``(label, canonical_name, pattern)`` rows."""
    return [
        (label, canonical, pattern)
        for label, entries in SKILL_PATTERN_GROUPS.items()
        for canonical, patterns in entries
        for pattern in patterns
    ]
