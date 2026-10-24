"""Get plain text out of uploaded files."""
import io
import os
import re

TEXT_EXT = {".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".xml", ".html", ".htm", ".tex", ".js", ".py", ".r", ".yaml", ".yml", ".log", ".bib"}
MAX_CHARS = 2_000_000


def is_text(name):
    return os.path.splitext(name)[1].lower() in TEXT_EXT


def extract_text(name, data):
    ext = os.path.splitext(name)[1].lower()
    try:
        if ext in TEXT_EXT:
            t = data.decode("utf-8", "replace")
            if ext in (".html", ".htm"):
                t = re.sub(r"<(script|style)[\s\S]*?</\1>|<[^>]+>", " ", t, flags=re.I)
        elif ext == ".pdf":
            from pypdf import PdfReader
            t = "\n\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        elif ext == ".docx":
            import docx
            lines = []
            for p in docx.Document(io.BytesIO(data)).paragraphs:
                style = p.style.name if p.style is not None else ""
                m = re.match(r"Heading (\d)", style)
                lines.append(("#" * int(m.group(1)) + " " + p.text) if m else p.text)
            t = "\n\n".join(lines)
        else:
            return ""
    except Exception:
        return ""
    return t[:MAX_CHARS]
