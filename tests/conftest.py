"""Shared fixtures + module loaders for the resume build scripts.

Two of the three modules under test have hyphenated filenames
(build-resume-docx.py, build-resume-pdf.py) so they can't be imported with a
plain `import`. They're loaded by file path via importlib. resume_blocks.py
imports normally once scripts/ is on sys.path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
RESUME_JSON = REPO / "public" / "resume.json"

# Make `import resume_blocks` work, and ensure the builders' internal
# `from resume_blocks import ...` resolves to this same module instance.
sys.path.insert(0, str(SCRIPTS))


def _load(mod_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(mod_name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def blocks_mod():
    import resume_blocks  # noqa: WPS433
    return resume_blocks


@pytest.fixture(scope="session")
def docx_mod():
    return _load("build_resume_docx", "build-resume-docx.py")


@pytest.fixture(scope="session")
def pdf_mod():
    return _load("build_resume_pdf", "build-resume-pdf.py")


@pytest.fixture(scope="session")
def real_data():
    """The actual canonical resume.json — exercises the real content path."""
    return json.loads(RESUME_JSON.read_text())


@pytest.fixture
def full_data():
    """Synthetic resume hitting every populated branch in build_blocks()."""
    return {
        "basics": {
            "name": "Test Person",
            "label": "Test Title",
            "location": {"city": "Sydney", "region": "NSW", "countryCode": "AU"},
            "profiles": [
                {"network": "LinkedIn", "url": "https://linkedin.com/in/test"},
                {"network": "GitHub", "url": "https://github.com/test"},
            ],
            "url": "https://example.com",
            "summary": "A summary.",
            "experienceLines": [{"years": "10+", "text": "doing things"}],
            "certifiedSummary": "Certified stuff",
            "subSummary": "Sub summary line.",
        },
        "skills": [
            {"name": "Architecture", "yearsExperience": 15},
            {"name": "Leadership"},  # no yearsExperience branch
        ],
        "highlights": [{"text": "Dict highlight"}, "String highlight"],
        "work": [
            {
                "name": "BigCorp",
                "position": "Architect",
                "startDate": "2020-03",
                "endDate": "2024-01",
                "location": "Sydney",
                "employmentType": "Contract",
                "context": "Context line.",
                "summary": "Role summary.",
                "clients": ["ClientA", "ClientB"],
                "highlights": [
                    {"text": "Metric highlight", "metric": "+30%"},
                    {"text": "Plain dict highlight"},
                    "String role highlight",
                ],
                "projects": [
                    {
                        "name": "Project X",
                        "role": "Lead",
                        "highlights": ["Proj highlight 1", "Proj highlight 2"],
                    },
                    {"name": "Project Y", "highlights": []},  # no role branch
                ],
                "softSkills": ["Comms"],
                "hardSkills": ["Python"],
                "agilePractices": ["Scrum"],
            },
            {"name": "MinimalCo"},  # position/dates/etc absent
            {
                "name": "OldCorp",
                "position": "Dev",
                "startDate": "2010",
                "endDate": "2012",
                "location": "Melbourne",
                "earlierCareer": True,
            },
            {
                "name": "OlderCorp",
                "position": "Junior",
                "startDate": "2008",
                "endDate": "2010",
                "earlierCareer": True,  # no location branch
            },
        ],
        "education": [
            {"institution": "Uni", "studyType": "BSc", "area": "CompSci", "endDate": "2008"},
            {"institution": "Bare Institution"},  # no details branch
        ],
        "certifications": [
            {"name": "Cert A", "issuer": "Issuer", "date": "2020"},
            {"name": "Cert B"},  # no meta branch
        ],
        "skillsByCategory": {
            "softSkills": [{"name": "Comms", "years": 10}],
            "technologies": [{"name": "Python", "years": 12}],
        },
        "directorships": [{"title": "Director", "startDate": "2018", "endDate": "2020"}],
        "memberships": ["ACS Member"],
        "sideProjects": [{"name": "Proj", "url": "https://p.example", "description": "desc"}],
        "personalAchievements": [
            {"text": "Marathon", "since": "2015", "url": "https://m.example"},
            {"text": "Award", "date": "2019"},
            {"text": "No date achievement"},
        ],
        "recruiterFAQ": {
            "availability": "Immediate",
            "visa": "Citizen",
            "rates": {"contract": "$X/day", "permanent": "$Y"},
            "location": {
                "based": "Sydney",
                "lookingIn": ["Sydney", "Remote"],
                "relocation": "no relocation",
                "travel": "yes",
            },
            "rolesPreferred": ["Architect", "Lead"],
            "rolesShortTerm": ["Consultant"],
            "holidays": "4 weeks",
            "perfectJob": "Building things.",
        },
        "references": [],
        "meta": {"version": "1.0.0", "lastModified": "2026-06-04"},
    }


@pytest.fixture
def min_data():
    """Minimal resume hitting the absent/empty branches in build_blocks()."""
    return {
        "basics": {
            "name": "Min Person",
            "label": "Min Title",
            "summary": "Only a summary.",
        },
        "work": [],
        "education": [],
        "certifications": [],
        "skillsByCategory": {},
        "meta": {"version": "0.1.0", "lastModified": "2026-01-01"},
    }
