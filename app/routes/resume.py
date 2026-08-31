"""
Generates an ATS-friendly PDF resume on-the-fly from portfolio_data.json.
Every request reads the JSON fresh — no caching.
"""
import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response
from fpdf import FPDF

router = APIRouter()

_DATA_PATH = Path(__file__).parent.parent.parent / "portfolio_data.json"

_BLUE = (37, 99, 235)
_GRAY = (107, 114, 128)
_BLACK = (17, 24, 39)

_FEATURED_PROJECTS = [
    "Syncly",
    "GlycanBench: integrated resource for working with glycans",
    (
        "Explainable Machine Learning-Based Approach to Developing "
        "Potent EGFR Inhibitors for Ovarian Cancer"
    ),
    "QSPR for Posaconazole SEDDS",
    (
        "Prediction of lignocellulosic components and fermentable sugars "
        "for bioethanol production by machine learning approach"
    ),
]

_SUMMARY = (
    "AI/ML Engineer and Full-Stack Developer specialising in agentic AI "
    "systems, WhatsApp automation, and explainable machine learning. M.Tech "
    "in Big Data Biology from SASTRA Deemed University (2025, 79.67%). "
    "Currently a Junior Software Developer at Ceiyone Tech Works (Zoho "
    "Partner), building AIORA - a multi-tenant WhatsApp business platform "
    "spanning a WhatsApp gateway (Oblion), booking and commerce backends, "
    "n8n-orchestrated AI conversation agents, and operator/customer "
    "dashboards - and mentoring 2 engineering interns on it. Also built "
    "production-grade platforms independently: Syncly (MERN + Socket.IO + "
    "AWS) and GlycanBench (glycoinformatics + MPNN). M.Tech thesis achieved "
    "98.47% accuracy in EGFR inhibitor classification for ovarian cancer "
    "using Gradient Boosting and SHAP."
)


def _load() -> dict:
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe(text) -> str:
    """Replace non-Latin-1 chars so core Helvetica font doesn't break."""
    return (
        str(text)
        .replace("–", "-")
        .replace("—", "--")
        .replace("‘", "'")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("•", "*")
        .replace("²", "2")
        .replace("³", "3")
        .replace("₂", "2")
        .replace("₁", "1")
        .replace("₀", "0")
        .replace("é", "e")
        .replace("è", "e")
        .replace("à", "a")
        .replace("ä", "a")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("\xa0", " ")
    )


class ResumePDF(FPDF):
    """FPDF subclass with resume-specific helpers."""

    def _lm(self) -> float:
        return self.l_margin

    def _ew(self) -> float:
        return self.epw

    def _accent_line(self, thickness: float = 0.4) -> None:
        self.set_draw_color(*_BLUE)
        self.set_line_width(thickness)
        y = self.get_y()
        self.line(self._lm(), y, self._lm() + self._ew(), y)

    def section(self, title: str) -> None:
        self.ln(5)
        self.set_font("Helvetica", style="B", size=10)
        self.set_text_color(*_BLUE)
        self.cell(0, 5, _safe(title), new_x="LMARGIN", new_y="NEXT")
        self._accent_line(0.4)
        self.set_text_color(*_BLACK)
        self.ln(2)

    def body(self, text: str, indent: float = 0) -> None:
        self.set_font("Helvetica", size=9)
        self.set_text_color(*_BLACK)
        self.set_x(self._lm() + indent)
        self.multi_cell(
            self._ew() - indent, 4.5, _safe(text),
            new_x="LMARGIN", new_y="NEXT"
        )

    def bold_line(self, text: str) -> None:
        self.set_font("Helvetica", style="B", size=10)
        self.set_text_color(*_BLACK)
        self.multi_cell(0, 5, _safe(text), new_x="LMARGIN", new_y="NEXT")

    def meta_line(self, text: str) -> None:
        self.set_font("Helvetica", style="I", size=9)
        self.set_text_color(*_GRAY)
        self.multi_cell(0, 4.5, _safe(text), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*_BLACK)

    def bullet(self, text: str) -> None:
        self.set_font("Helvetica", size=9)
        self.set_text_color(*_BLACK)
        self.set_x(self._lm() + 4)
        self.cell(5, 4.5, "-", new_x="RIGHT", new_y="TOP")
        self.multi_cell(
            self._ew() - 9, 4.5, _safe(text),
            new_x="LMARGIN", new_y="NEXT"
        )


def _header_section(pdf: ResumePDF, personal: dict) -> None:
    pdf.set_font("Helvetica", style="B", size=18)
    pdf.set_text_color(*_BLACK)
    pdf.cell(0, 9, _safe(personal["name"]), new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(*_GRAY)
    pdf.cell(
        0, 5,
        "AI/ML Engineer & Full-Stack Developer | Bioinformatics Researcher",
        new_x="LMARGIN", new_y="NEXT", align="C",
    )

    parts = [
        personal.get("email", ""),
        personal.get("linkedin", "").replace("https://", ""),
        personal.get("github", "").replace("https://", ""),
        personal.get("portfolio", "").replace("https://", ""),
    ]
    contact = " | ".join(x for x in parts if x)
    pdf.set_font("Helvetica", size=8)
    pdf.cell(0, 5, _safe(contact), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    pdf.set_draw_color(*_BLUE)
    pdf.set_line_width(0.8)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + pdf.epw, y)
    pdf.ln(1)


def _experience_section(pdf: ResumePDF, roles: list) -> None:
    pdf.section("WORK EXPERIENCE")
    for role in roles:
        pdf.bold_line(f"{role['role']} - {role['company']}")
        meta_parts = [role.get("type", ""), role.get("period", "")]
        if role.get("location"):
            meta_parts.append(role["location"])
        if role.get("supervisor"):
            meta_parts.append(f"Supervisor: {role['supervisor']}")
        pdf.meta_line(" | ".join(x for x in meta_parts if x))
        pdf.body(role.get("overview", ""))
        projs = role.get("projects", [])
        if projs:
            names = ", ".join(pr["name"] for pr in projs[:6])
            pdf.body(f"Key deliverables: {names}")
        for item in role.get("additional_responsibilities", []):
            pdf.bullet(item)
        pdf.ln(3)


def _education_section(pdf: ResumePDF, education: list) -> None:
    pdf.section("EDUCATION")
    for edu in education:
        pdf.bold_line(edu["degree"])
        meta = " | ".join(filter(None, [
            edu.get("institution", ""),
            edu.get("location", ""),
            edu.get("period", ""),
            f"Grade: {edu['grade']}" if edu.get("grade") else "",
        ]))
        pdf.meta_line(meta)
        if edu.get("focus"):
            pdf.body(f"Focus: {edu['focus']}")
        pdf.ln(2)


def _publications_section(pdf: ResumePDF, publications: list) -> None:
    pdf.section("PUBLICATIONS & RESEARCH")
    for pub in publications:
        pdf.bold_line(pub["title"])
        meta = " | ".join(filter(None, [
            pub.get("type", ""),
            pub.get("status", ""),
            pub.get("institution", ""),
            str(pub.get("year", "")),
        ]))
        pdf.meta_line(meta)
        abstract = pub.get("abstract", "")
        if abstract:
            pdf.body(abstract[:260] + ("..." if len(abstract) > 260 else ""))
        pdf.ln(2)


def _projects_section(pdf: ResumePDF, projects: dict) -> None:
    pdf.section("KEY PROJECTS")
    for name in _FEATURED_PROJECTS:
        proj = projects.get(name)
        if not proj:
            continue
        pdf.bold_line(name)
        if proj.get("subtitle"):
            pdf.meta_line(proj["subtitle"])
        desc = proj.get("description", "")
        pdf.body(desc[:290] + ("..." if len(desc) > 290 else ""))
        tech = ", ".join(proj.get("tech_stack", []))
        pdf.body(f"Stack: {tech}")
        links = []
        if proj.get("live_link"):
            links.append(f"Live: {proj['live_link']}")
        if proj.get("github"):
            links.append(f"GitHub: {proj['github']}")
        if proj.get("github_frontend"):
            links.append(f"GitHub (Frontend): {proj['github_frontend']}")
        if proj.get("github_backend"):
            links.append(f"GitHub (Backend): {proj['github_backend']}")
        if links:
            pdf.meta_line(" | ".join(links))
        pdf.ln(2)


def _skills_section(pdf: ResumePDF, skills: dict) -> None:
    pdf.section("TECHNICAL SKILLS")
    for category, skill_list in skills.items():
        label = f"{_safe(category)}: "
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.set_text_color(*_BLACK)
        pdf.set_x(pdf.l_margin)
        pdf.cell(pdf.get_string_width(label), 4.5, label, new_x="RIGHT", new_y="TOP")
        pdf.set_font("Helvetica", size=9)
        pdf.multi_cell(0, 4.5, _safe(", ".join(skill_list)), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _certs_section(pdf: ResumePDF, certifications: list) -> None:
    pdf.section("CERTIFICATIONS")
    for cert in certifications:
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.set_text_color(*_BLACK)
        pdf.cell(0, 4.5, _safe(cert["title"]), new_x="LMARGIN", new_y="NEXT")
        pdf.meta_line(f"{cert['issuer']} | Instructor: {cert['instructor']}")
    pdf.ln(2)


def _build(data: dict) -> bytes:
    pdf = ResumePDF(format="letter")
    pdf.set_margins(left=16.5, top=14, right=16.5)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    _header_section(pdf, data["personal"])

    pdf.section("PROFESSIONAL SUMMARY")
    pdf.body(_SUMMARY)

    _experience_section(pdf, data.get("work_experience", []))
    _education_section(pdf, data.get("education", []))
    _publications_section(pdf, data.get("publications", []))
    _projects_section(pdf, data.get("projects", {}))
    _skills_section(pdf, data.get("skills", {}))
    _certs_section(pdf, data.get("certifications", []))

    interests = data.get("research_interests", [])
    if interests:
        pdf.section("RESEARCH INTERESTS")
        pdf.body(", ".join(interests))

    return bytes(pdf.output())


@router.get("/api/resume")
async def generate_resume() -> Response:
    """Reads portfolio_data.json fresh and returns an ATS-friendly PDF."""
    data = _load()
    pdf_bytes = _build(data)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                'attachment; filename="Vigneshwaran_CJ_Resume.pdf"'
            ),
            "Cache-Control": "no-store",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
