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
    body = " ".join(
        ["Provide professional nursing care."] * 100
    )

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
