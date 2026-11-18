from app.services.harvesting.myjobmag import (
    parse_job_page,
    parse_listing,
    title_matches,
)


def test_title_matching_is_programme_driven():
    assert title_matches(
        "Registered Nurse",
        ["nurse", "midwife"],
    )

    assert title_matches(
        "Senior Accountant",
        ["accountant", "auditor"],
    )

    assert title_matches(
        "Mechanical Engineer",
        ["mechanical engineer"],
    )

    assert not title_matches(
        "Software Engineer",
        ["registered nurse"],
    )


def test_listing_parser_extracts_jobs():
    html = """
    <ul>
      <li class="job-info">
        <h2>
          <a href="/job/registered-nurse-example">
            Registered Nurse at Example Hospital
          </a>
        </h2>
      </li>
    </ul>
    """

    jobs = list(parse_listing(html))

    assert len(jobs) == 1

    assert jobs[0][1] == "Registered Nurse"

    assert jobs[0][2] == "Example Hospital"


def test_job_page_uses_jobposting_data():
    body = " ".join(["Provide professional nursing care."] * 100)

    html = f"""
    <html>
      <head>
        <script type="application/ld+json">
        {{
          "@type": "JobPosting",
          "title": "Registered Nurse",
          "datePosted": "2026-10-30",
          "hiringOrganization": {{
            "name": "Example Hospital"
          }},
          "jobLocation": {{
            "address": {{
              "addressLocality": "Uyo",
              "addressRegion": "Akwa Ibom"
            }}
          }},
          "description": "<p>{body}</p>"
        }}
        </script>
      </head>
    </html>
    """

    advert = parse_job_page(
        html,
        "https://www.myjobmag.com/job/example",
    )

    assert advert is not None

    assert advert.title == "Registered Nurse"

    assert advert.company == "Example Hospital"

    assert advert.location == "Uyo, Akwa Ibom"

    assert advert.date_posted == "2026-10-30"


# ----------------------------------------------------------------- collection (synthetic site)

BASE = "https://www.myjobmag.com"


def _listing(*jobs: tuple[str, str]) -> str:
    items = "".join(
        f'<li class="job-info"><h2><a href="/job/{slug}">{title}</a></h2></li>'
        for slug, title in jobs
    )
    return f"<ul>{items}</ul>"


def _advert(title: str) -> str:
    body = " ".join(["Synthetic duties of the role."] * 30)
    return (
        '<html><head><script type="application/ld+json">'
        f'{{"@type": "JobPosting", "title": "{title}", "description": "<p>{body}</p>"}}'
        "</script></head></html>"
    )


class FakeSite:
    """A synthetic MyJobMag: listing and advert pages by URL; anything else is a 404."""

    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str) -> str:
        self.requested.append(url)
        if url not in self.pages:
            raise LookupError(url)
        return self.pages[url]


def collect_from(site: FakeSite, monkeypatch, **kwargs):
    from app.services.harvesting import myjobmag

    monkeypatch.setattr(myjobmag, "MyJobMagClient", lambda: site)
    options = {"field_slugs": [], "target_count": 10, "pages_per_field": 2}
    return myjobmag.collect_jobs(**(options | kwargs))


def test_title_listings_come_first_and_fields_are_optional(monkeypatch):
    site = FakeSite(
        {
            f"{BASE}/jobs-by-title/nurse": _listing(
                ("n1", "Registered Nurse at Synthetic Clinic"),
                ("n2", "School Nurse at Synthetic College"),
            ),
            # No page 2 for nurse; no listing at all for "nurse educator".
            f"{BASE}/jobs-by-field/medical": _listing(
                ("d1", "Medical Doctor at Synthetic Hospital"),
                ("n1", "Registered Nurse at Synthetic Clinic"),
                ("m1", "Midwife at Synthetic Maternity"),
            ),
            f"{BASE}/job/n1": _advert("Registered Nurse"),
            f"{BASE}/job/n2": _advert("School Nurse"),
            f"{BASE}/job/m1": _advert("Midwife"),
        }
    )

    result = collect_from(
        site,
        monkeypatch,
        search_terms=["Nurse", "nurse educator", "midwife"],
        field_slugs=["medical"],
    )

    assert [a.title for a in result.adverts] == ["Registered Nurse", "School Nurse", "Midwife"]
    assert site.requested[:4] == [
        f"{BASE}/jobs-by-title/nurse",
        f"{BASE}/job/n1",
        f"{BASE}/job/n2",
        f"{BASE}/jobs-by-title/nurse/2",
    ]
    assert f"{BASE}/jobs-by-title/nurse-educator" in site.requested
    # The doctor is skipped by title and the repeated nurse advert is fetched only once.
    assert f"{BASE}/job/d1" not in site.requested
    assert site.requested.count(f"{BASE}/job/n1") == 1
    assert result.skipped >= 2

    only_titles = collect_from(
        FakeSite({f"{BASE}/jobs-by-title/midwife": _listing(("m1", "Midwife at X"))}),
        monkeypatch,
        search_terms=["midwife"],
    )
    assert only_titles.examined == 1


def test_collection_stops_at_the_target(monkeypatch):
    jobs = [(f"n{i}", f"Nurse {i} at Synthetic Clinic") for i in range(5)]
    pages = {f"{BASE}/jobs-by-title/nurse": _listing(*jobs)}
    pages |= {f"{BASE}/job/n{i}": _advert(f"Nurse {i}") for i in range(5)}
    site = FakeSite(pages)

    result = collect_from(site, monkeypatch, search_terms=["nurse"], target_count=2)

    assert len(result.adverts) == 2
    assert f"{BASE}/job/n2" not in site.requested


def test_listing_parser_reads_absolute_links_without_the_usual_layout():
    html = f'<div><a href="{BASE}/job/x"><img></a><a href="{BASE}/job/x">Nurse at Y</a></div>'

    assert list(parse_listing(html)) == [(f"{BASE}/job/x", "Nurse", "Y")]


def test_a_job_field_adds_adverts_with_other_titles_that_ask_for_the_skills(monkeypatch):
    """Synthetic: a field advert with an unlisted title is kept when it asks for two of the
    programme's skills, and dropped when it does not."""

    def advert_with(title: str, text: str) -> str:
        body = " ".join([text] * 20)
        return (
            '<html><head><script type="application/ld+json">'
            f'{{"@type": "JobPosting", "title": "{title}", "description": "<p>{body}</p>"}}'
            "</script></head></html>"
        )

    site = FakeSite(
        {
            f"{BASE}/jobs-by-title/software-developer": _listing(
                ("s1", "Software Developer at Synthetic Bank")
            ),
            f"{BASE}/jobs-by-field/information-technology": _listing(
                ("f1", "Platform Associate at Synthetic Telco"),
                ("f2", "Sales Associate at Synthetic Store"),
            ),
            f"{BASE}/job/s1": _advert("Software Developer"),
            f"{BASE}/job/f1": advert_with(
                "Platform Associate", "You will work with Python and SQL on cloud systems."
            ),
            f"{BASE}/job/f2": advert_with("Sales Associate", "You will sell phones in a store."),
        }
    )
    result = collect_from(
        site,
        monkeypatch,
        search_terms=["software developer"],
        field_slugs=["information-technology"],
        skill_names=["Python", "SQL", "Docker"],
    )
    assert [a.title for a in result.adverts] == ["Software Developer", "Platform Associate"]
