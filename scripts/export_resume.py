"""Export the ATS résumé (PDF, DOCX, TXT) to a folder without running the server.

Usage, from the backend repository root:
    python scripts/export_resume.py ../vigneshwarancj-portfolio-website

Writes resume.pdf, Vigneshwaran_CJ.docx, and resume.txt so the website's static
fallback downloads match what /api/resume serves.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("GROQ_API_KEY", "export-only")  # config import requires a value; no model is called

from app.routes.resume import render_docx, render_pdf  # noqa: E402
from app.services.resume_document import build_resume, render_text  # noqa: E402


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    target.mkdir(parents=True, exist_ok=True)
    document = build_resume()
    outputs = {
        "resume.pdf": render_pdf(document),
        "Vigneshwaran_CJ.docx": render_docx(document),
        "resume.txt": render_text(document).encode("utf-8"),
    }
    for name, content in outputs.items():
        (target / name).write_bytes(content)
        print(f"wrote {target / name} ({len(content):,} bytes)")


if __name__ == "__main__":
    main()
