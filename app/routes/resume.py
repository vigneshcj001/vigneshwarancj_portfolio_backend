"""ATS-friendly résumé downloads (PDF, DOCX, plain text) from canonical Markdown."""

from __future__ import annotations

import io
import unicodedata
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response
from fpdf import FPDF

from app.limiter import limiter
from app.services.resume_document import ResumeDocument, build_resume, render_text

router = APIRouter()

FILE_STEM = "Vigneshwaran_CJ_Resume"
_INK = (17, 24, 39)
_MUTED = (75, 85, 99)
_RULE = (148, 163, 184)
_REPLACEMENTS = {
    "–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "•": "-",
    "→": "->", "×": "x", "…": "...", "\xa0": " ", "₂": "2", "₁": "1", "₀": "0",
}


def _latin1(text: str) -> str:
    """Core PDF fonts are Latin-1 only; transliterate instead of dropping text."""
    for source, target in _REPLACEMENTS.items():
        text = text.replace(source, target)
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        normalized = unicodedata.normalize("NFKD", text)
        return normalized.encode("latin-1", "ignore").decode("latin-1")


class _ResumePDF(FPDF):
    def write_block(self, kind: str, text: str, label: str = "") -> None:
        text = _latin1(text)
        if kind == "name":
            self.set_font("Helvetica", "B", 20)
            self.set_text_color(*_INK)
            self.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT", align="C")
        elif kind == "headline":
            self.set_font("Helvetica", "", 10.5)
            self.set_text_color(*_MUTED)
            self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT", align="C")
        elif kind == "contact":
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*_INK)
            self.multi_cell(0, 4.6, text, new_x="LMARGIN", new_y="NEXT", align="C")
        elif kind == "heading":
            self.ln(3.5)
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*_INK)
            self.cell(0, 6, text.upper(), new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*_RULE)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.l_margin + self.epw, self.get_y())
            self.ln(1.5)
        elif kind == "title":
            self.ln(1.2)
            self.set_font("Helvetica", "B", 10.5)
            self.set_text_color(*_INK)
            self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        elif kind == "meta":
            self.set_font("Helvetica", "I", 9.5)
            self.set_text_color(*_MUTED)
            self.multi_cell(0, 4.6, text, new_x="LMARGIN", new_y="NEXT")
        elif kind == "bullet":
            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*_INK)
            self.set_x(self.l_margin + 2)
            self.cell(4, 4.7, "-")
            self.multi_cell(self.epw - 6, 4.7, text, new_x="LMARGIN", new_y="NEXT")
        elif kind == "labeled":
            prefix = f"{_latin1(label)}: "
            self.set_text_color(*_INK)
            self.set_font("Helvetica", "B", 9.5)
            width = self.get_string_width(prefix) + 0.5
            self.cell(width, 4.7, prefix)
            self.set_font("Helvetica", "", 9.5)
            self.multi_cell(self.epw - width, 4.7, text, new_x="LMARGIN", new_y="NEXT")
        else:
            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*_INK)
            self.multi_cell(0, 4.7, text, new_x="LMARGIN", new_y="NEXT")


def render_pdf(doc: ResumeDocument) -> bytes:
    pdf = _ResumePDF(format="letter")
    pdf.set_margins(left=15, top=13, right=15)
    pdf.set_auto_page_break(auto=True, margin=13)
    # Document metadata is read by some parsers and shown in PDF viewers.
    pdf.set_title(_latin1(f"{doc.name} - Resume"))
    pdf.set_author(_latin1(doc.name))
    pdf.set_subject("Resume")
    pdf.set_keywords(_latin1(", ".join(doc.keywords)))
    pdf.set_creator("vigneshwarancj portfolio")
    pdf.add_page()
    for block in doc.blocks:
        pdf.write_block(block.kind, block.text, block.label)
    return bytes(pdf.output())


# ── DOCX ─────────────────────────────────────────────────────────────────────
# Hand-built Office Open XML keeps the dependency list small; Word, Google Docs,
# and ATS parsers all read this minimal package.
_W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _run(text: str, bold: bool = False, italic: bool = False, color: str | None = None, size: int | None = None) -> str:
    props = "".join([
        "<w:b/>" if bold else "",
        "<w:i/>" if italic else "",
        f'<w:color w:val="{color}"/>' if color else "",
        f'<w:sz w:val="{size}"/>' if size else "",
    ])
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _paragraph(runs: str, style: str | None = None, align: str | None = None, indent: bool = False, before: int = 0) -> str:
    props = "".join([
        f'<w:pStyle w:val="{style}"/>' if style else "",
        f'<w:spacing w:before="{before}" w:after="40"/>' if before else "",
        '<w:ind w:left="360" w:hanging="220"/>' if indent else "",
        f'<w:jc w:val="{align}"/>' if align else "",
    ])
    return f"<w:p><w:pPr>{props}</w:pPr>{runs}</w:p>"


def _docx_body(doc: ResumeDocument) -> str:
    parts = []
    for block in doc.blocks:
        if block.kind == "name":
            parts.append(_paragraph(_run(block.text, bold=True, size=40), align="center"))
        elif block.kind == "headline":
            parts.append(_paragraph(_run(block.text, color="4B5563", size=21), align="center"))
        elif block.kind == "contact":
            parts.append(_paragraph(_run(block.text, size=19), align="center"))
        elif block.kind == "heading":
            parts.append(_paragraph(_run(block.text.upper()), style="Heading1"))
        elif block.kind == "title":
            parts.append(_paragraph(_run(block.text, bold=True), before=100))
        elif block.kind == "meta":
            parts.append(_paragraph(_run(block.text, italic=True, color="4B5563")))
        elif block.kind == "bullet":
            # A literal tab inside <w:t> is not a tab in OOXML; use the <w:tab/> element.
            parts.append(_paragraph('<w:r><w:t xml:space="preserve">•</w:t><w:tab/></w:r>' + _run(block.text), indent=True))
        elif block.kind == "labeled":
            parts.append(_paragraph(_run(f"{block.label}: ", bold=True) + _run(block.text)))
        else:
            parts.append(_paragraph(_run(block.text)))
    section = (
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="792" w:right="864" w:bottom="792" w:left="864" w:header="0" w:footer="0" w:gutter="0"/></w:sectPr>'
    )
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {_W}><w:body>{"".join(parts)}{section}</w:body></w:document>'


_STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {_W}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="20"/><w:color w:val="111827"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="40" w:line="252" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="200" w:after="60"/><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="94A3B8"/></w:pBdr><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:b/><w:sz w:val="22"/></w:rPr></w:style>
</w:styles>"""

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _core(doc: ResumeDocument) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f"<dc:title>{escape(doc.name)} - Resume</dc:title><dc:creator>{escape(doc.name)}</dc:creator>"
        f"<cp:keywords>{escape(', '.join(doc.keywords))}</cp:keywords>"
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def render_docx(doc: ResumeDocument) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _CONTENT_TYPES)
        package.writestr("_rels/.rels", _ROOT_RELS)
        package.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        package.writestr("word/document.xml", _docx_body(doc))
        package.writestr("word/styles.xml", _STYLES)
        package.writestr("docProps/core.xml", _core(doc))
    return buffer.getvalue()


def _download(content: bytes, media_type: str, extension: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{FILE_STEM}.{extension}"',
            "Cache-Control": "no-store",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/api/resume")
@limiter.limit("20/minute")
async def resume_pdf(request: Request) -> Response:
    """Text-based, single-column PDF built from structured Markdown."""
    return _download(render_pdf(build_resume()), "application/pdf", "pdf")


@router.get("/api/resume.docx")
@limiter.limit("20/minute")
async def resume_docx(request: Request) -> Response:
    """Word version; many applicant tracking systems parse DOCX most reliably."""
    return _download(
        render_docx(build_resume()),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    )


@router.get("/api/resume.txt", response_class=PlainTextResponse)
@limiter.limit("20/minute")
async def resume_text(request: Request) -> PlainTextResponse:
    """Plain-text view: what a parser should extract from the PDF/DOCX."""
    return PlainTextResponse(render_text(build_resume()), headers={"Cache-Control": "no-store"})
