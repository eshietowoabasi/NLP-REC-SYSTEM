"""Curated Computing skill/tool/certification vocabulary for the spaCy EntityRuler (spec §8.3).

Each entry maps a canonical name to the surface forms matched case-insensitively.
Extend this list as the corpus grows; tests guard the tricky tokenisations.

Labels:
  SKILL - knowledge areas and practices (machine learning, penetration testing)
  TOOL  - languages, frameworks, platforms and products (Python, Kubernetes, AWS)
  CERT  - professional certifications (CISSP, CCNA)
"""

SKILLS = {
    "Artificial Intelligence": ["artificial intelligence", "AI"],
    "Machine Learning": ["machine learning", "ML"],
    "Deep Learning": ["deep learning", "neural networks", "neural network"],
    "Natural Language Processing": ["natural language processing", "NLP"],
    "Computer Vision": ["computer vision", "image recognition"],
    "Generative AI": ["generative AI", "large language models", "large language model", "LLMs", "LLM", "prompt engineering"],
    "MLOps": ["MLOps", "model deployment"],
    "Data Science": ["data science"],
    "Data Analysis": ["data analysis", "data analytics", "data analyst"],
    "Data Engineering": ["data engineering", "data pipelines", "data pipeline", "ETL", "ELT", "data warehousing", "data warehouse"],
    "Big Data": ["big data"],
    "Data Visualisation": ["data visualization", "data visualisation", "dashboards"],
    "Statistics": ["statistics", "statistical analysis", "statistical modelling", "statistical modeling"],
    "Database Management": ["database management", "database administration", "database design", "data modelling", "data modeling"],
    "Cybersecurity": ["cybersecurity", "cyber security", "information security", "infosec"],
    "Network Security": ["network security", "firewalls", "firewall", "intrusion detection", "IDS/IPS"],
    "Penetration Testing": ["penetration testing", "pen testing", "ethical hacking", "vulnerability assessment"],
    "Security Operations": ["security operations", "SOC", "incident response", "threat intelligence", "threat hunting", "SIEM"],
    "Digital Forensics": ["digital forensics", "computer forensics"],
    "Cryptography": ["cryptography", "encryption", "public key infrastructure", "PKI"],
    "Identity and Access Management": ["identity and access management", "IAM", "access control"],
    "Governance, Risk and Compliance": ["GRC", "risk management", "regulatory compliance", "compliance management", "data protection", "NDPR", "NDPA", "GDPR"],
    "Cloud Computing": ["cloud computing", "cloud infrastructure", "cloud services", "cloud architecture"],
    "Cloud Security": ["cloud security"],
    "DevOps": ["DevOps", "DevSecOps", "site reliability engineering", "SRE"],
    "CI/CD": ["CI/CD", "continuous integration", "continuous delivery", "continuous deployment"],
    "Infrastructure as Code": ["infrastructure as code", "IaC"],
    "Containerisation": ["containerization", "containerisation", "containers", "microservices"],
    "Networking": ["computer networking", "networking", "TCP/IP", "routing and switching", "network administration"],
    "Systems Administration": ["systems administration", "system administration", "sysadmin"],
    "Software Engineering": ["software engineering", "software development", "software design"],
    "Web Development": ["web development", "frontend development", "front-end development", "backend development", "back-end development", "full stack", "full-stack"],
    "Mobile Development": ["mobile development", "mobile app development", "android development", "iOS development"],
    "API Development": ["API development", "REST APIs", "RESTful APIs", "REST API", "RESTful", "GraphQL"],
    "Object-Oriented Programming": ["object-oriented programming", "object oriented programming", "OOP"],
    "Software Testing": ["software testing", "unit testing", "test automation", "quality assurance"],
    "Version Control": ["version control", "source control"],
    "Agile Methods": ["agile", "scrum", "kanban", "agile methodology"],
    "UI/UX Design": ["UI/UX design", "UI/UX", "user experience", "user interface design", "UX design", "UI design"],
    "Blockchain": ["blockchain", "smart contracts", "distributed ledger"],
    "Internet of Things": ["internet of things", "IoT", "embedded systems"],
    "Robotics": ["robotics", "robotic process automation", "RPA"],
    "Fintech": ["fintech", "digital payments", "mobile money"],
    "E-Government": ["e-government", "digital government", "digital public services"],
    "Digital Literacy": ["digital literacy", "digital skills"],
    "Technical Support": ["technical support", "IT support", "help desk", "helpdesk"],
    "Project Management": ["project management", "IT project management"],
    "Business Analysis": ["business analysis", "requirements analysis", "requirements engineering"],
    "Operating Systems": ["operating systems"],
    "Algorithms and Data Structures": ["algorithms", "data structures"],
}

TOOLS = {
    "Python": ["Python"], "Java": ["Java"], "JavaScript": ["JavaScript", "JS", "ES6"],
    "TypeScript": ["TypeScript"], "C++": ["C++"], "C#": ["C#"], "PHP": ["PHP"],
    "Kotlin": ["Kotlin"], "Swift": ["Swift"], "Dart": ["Dart"], "Rust": ["Rust"], "Ruby": ["Ruby"],
    "Go": ["Golang"], "R": ["RStudio"], "Scala": ["Scala"], "MATLAB": ["MATLAB"], "Bash": ["Bash", "shell scripting"],
    "SQL": ["SQL", "T-SQL", "PL/SQL"], "NoSQL": ["NoSQL"],
    "PostgreSQL": ["PostgreSQL", "Postgres"], "MySQL": ["MySQL"], "MongoDB": ["MongoDB"],
    "Oracle Database": ["Oracle Database", "Oracle DB"], "SQL Server": ["SQL Server", "MSSQL"], "Redis": ["Redis"],
    "HTML/CSS": ["HTML", "HTML5", "CSS", "CSS3"], "React": ["React", "React.js", "ReactJS"],
    "React Native": ["React Native"], "Angular": ["Angular"], "Vue.js": ["Vue", "Vue.js", "VueJS"],
    "Node.js": ["Node.js", "NodeJS", "Node"], "Express.js": ["Express.js", "ExpressJS"],
    "Django": ["Django"], "Flask": ["Flask"], "FastAPI": ["FastAPI"], "Spring Boot": ["Spring Boot", "Spring"],
    "Laravel": ["Laravel"], ".NET": [".NET", ".NET Core", "ASP.NET"], "Flutter": ["Flutter"],
    "Android": ["Android"], "Bootstrap": ["Bootstrap"], "Tailwind CSS": ["Tailwind", "Tailwind CSS"],
    "Git": ["Git"], "GitHub": ["GitHub"], "GitLab": ["GitLab"], "Jira": ["Jira"],
    "Docker": ["Docker"], "Kubernetes": ["Kubernetes", "K8s"], "Terraform": ["Terraform"], "Ansible": ["Ansible"],
    "Jenkins": ["Jenkins"], "Linux": ["Linux", "Ubuntu", "Red Hat", "RHEL"], "Windows Server": ["Windows Server"],
    "AWS": ["AWS", "Amazon Web Services", "EC2", "S3", "AWS Lambda"],
    "Microsoft Azure": ["Azure", "Microsoft Azure"], "Google Cloud": ["GCP", "Google Cloud", "Google Cloud Platform"],
    "TensorFlow": ["TensorFlow"], "PyTorch": ["PyTorch"], "scikit-learn": ["scikit-learn", "sklearn"],
    "Keras": ["Keras"], "Pandas": ["Pandas"], "NumPy": ["NumPy"], "Hugging Face": ["Hugging Face", "HuggingFace"],
    "Apache Spark": ["Apache Spark", "Spark", "PySpark"], "Hadoop": ["Hadoop"], "Kafka": ["Kafka", "Apache Kafka"],
    "Airflow": ["Airflow", "Apache Airflow"], "Power BI": ["Power BI", "PowerBI"], "Tableau": ["Tableau"],
    "Excel": ["Excel", "Microsoft Excel"], "Snowflake": ["Snowflake"],
    "Wireshark": ["Wireshark"], "Metasploit": ["Metasploit"], "Burp Suite": ["Burp Suite"], "Nmap": ["Nmap"],
    "Kali Linux": ["Kali Linux", "Kali"], "Splunk": ["Splunk"], "Cisco": ["Cisco IOS"],
    "Figma": ["Figma"], "Salesforce": ["Salesforce"], "SAP": ["SAP"],
}

CERTS = {
    "CISSP": ["CISSP"], "CISM": ["CISM"], "CISA": ["CISA"], "CEH": ["CEH", "Certified Ethical Hacker"],
    "OSCP": ["OSCP"], "CompTIA Security+": ["CompTIA Security+", "Security+"],
    "CompTIA Network+": ["CompTIA Network+", "Network+"], "CompTIA A+": ["CompTIA A+"],
    "CCNA": ["CCNA"], "CCNP": ["CCNP"],
    "AWS Certified": ["AWS Certified Solutions Architect", "AWS Certified Cloud Practitioner", "AWS Certified Developer", "AWS Certified"],
    "Azure Certification": ["AZ-900", "AZ-104", "Azure Fundamentals", "Azure Administrator"],
    "Google Cloud Certification": ["Google Cloud Certified", "Professional Cloud Architect"],
    "PMP": ["PMP"], "PRINCE2": ["PRINCE2"], "ITIL": ["ITIL"],
    "Certified Scrum Master": ["Certified ScrumMaster", "Certified Scrum Master", "CSM"],
    "CKA": ["CKA", "Certified Kubernetes Administrator"], "ISO 27001": ["ISO 27001", "ISO/IEC 27001"],
}

# Ambiguous names that need context: the verb "go", list items "(c)"/"(r)".
_LANG_CONTEXT = {"LOWER": {"IN": ["programming", "language", "developer", "developers", "programmer", "programmers"]}}
TOKEN_PATTERNS = [
    ("TOOL", name, [{"ORTH": name}, _LANG_CONTEXT]) for name in ("Go", "R", "C")
]
CONTEXT_ONLY = {"Go", "R", "C"}

# Single-word names matched with exact case: acronyms ("AI" but not "ai") and product
# names that are also ordinary English words ("Spark", "Swift", "Excel", "Node").
CASE_SENSITIVE_WORDS = {
    "Node", "Spring", "Swift", "Rust", "Ruby", "Dart", "Kali", "Spark", "Excel", "Angular",
    "React", "Vue", "Flask", "Git", "Bash", "Scala", "Java", "Tableau", "Snowflake",
    "Jenkins", "Android", "Bootstrap", "Airflow", "Kafka", "Python", "Oracle",
}


def _is_case_sensitive(form):
    return " " not in form and (form.isupper() or form in CASE_SENSITIVE_WORDS)


def build_patterns(tokenizer):
    """Return EntityRuler patterns; the canonical name is carried in the pattern ``id``.

    ``tokenizer`` is the pipeline's tokenizer, so case-sensitive forms that spaCy splits
    ("C#" -> "C", "#"; "CI/CD" -> "CI", "/", "CD") become matching token sequences.
    """
    patterns = []
    for vocabulary, label in ((SKILLS, "SKILL"), (TOOLS, "TOOL"), (CERTS, "CERT")):
        for canonical, forms in vocabulary.items():
            for form in forms:
                if _is_case_sensitive(form):
                    tokens = [{"ORTH": tok.text} for tok in tokenizer(form)]
                    patterns.append({"label": label, "pattern": tokens, "id": canonical})
                else:
                    patterns.append({"label": label, "pattern": form, "id": canonical})
    for label, canonical, tokens in TOKEN_PATTERNS:
        patterns.append({"label": label, "pattern": tokens, "id": canonical})
    return patterns
