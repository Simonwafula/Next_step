#!/usr/bin/env python3
"""Generate a simple .docx from the assignment markdown without external deps."""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT_MD = ROOT / "assignment_draft.md"
OUTPUT_DOCX = ROOT / "assignment_draft.docx"


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
</w:styles>
"""


def xml_escape(text: str) -> str:
    return html.escape(text, quote=False)


def inline_runs(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    runs: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            value = xml_escape(part[1:-1])
            runs.append(
                f"<w:r><w:rPr><w:rFonts w:ascii=\"Courier New\" w:hAnsi=\"Courier New\"/>"
                f"</w:rPr><w:t xml:space=\"preserve\">{value}</w:t></w:r>"
            )
        else:
            value = xml_escape(part)
            runs.append(f"<w:r><w:t xml:space=\"preserve\">{value}</w:t></w:r>")
    return "".join(runs) or "<w:r><w:t></w:t></w:r>"


def paragraph(text: str, style: str | None = None) -> str:
    ppr = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    return f"<w:p>{ppr}{inline_runs(text)}</w:p>"


def bullet(text: str) -> str:
    return paragraph(f"- {text}")


def numbered(text: str) -> str:
    return paragraph(text)


def markdown_to_document_xml(markdown_text: str) -> str:
    body: list[str] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            body.append("<w:p/>")
            continue
        if line.startswith("# "):
            body.append(paragraph(line[2:], "Heading1"))
        elif line.startswith("## "):
            body.append(paragraph(line[3:], "Heading2"))
        elif re.match(r"^\d+\.\s+", line):
            body.append(numbered(line))
        elif line.startswith("- "):
            body.append(bullet(line[2:]))
        else:
            body.append(paragraph(line))
    sect = (
        "<w:sectPr>"
        "<w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" "
        "w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
        "</w:sectPr>"
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        f"<w:body>{''.join(body)}{sect}</w:body></w:document>"
    )


def main() -> None:
    markdown_text = INPUT_MD.read_text(encoding="utf-8")
    document_xml = markdown_to_document_xml(markdown_text)

    with zipfile.ZipFile(OUTPUT_DOCX, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/styles.xml", STYLES)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)

    print(OUTPUT_DOCX)


if __name__ == "__main__":
    main()
