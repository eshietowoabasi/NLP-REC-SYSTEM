"""Polite collector of job adverts for the NLP-RS corpus.

Sources: MyJobMag job pages (robots.txt obeyed, rate-limited) and, optionally, the Remotive
public API. Jobberman and LinkedIn are never scraped; manual copies go through
``corpus_collector.paste``. See README.md for the ethics and usage.
"""

__version__ = "1.0.0"
