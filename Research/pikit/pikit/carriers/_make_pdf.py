#!/usr/bin/env python3
"""Generate a clean PDF carrier file with metadata for pikit.

The PDF is minimal but valid — it has a visible page with text content and
metadata fields (Title, Author, Subject, Keywords) that can be tainted.
"""
import struct


def _pdf_string(s: str) -> bytes:
    """Encode a string as a PDF literal string."""
    escaped = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"({escaped})".encode("latin-1")


def make_pdf(
    title="Q3 Financial Report",
    author="Finance Team",
    subject="Quarterly Results",
    keywords="finance, q3, report",
    page_text="Q3 Financial Report\n\nRevenue $2.3M, Growth 20% YoY.",
    output_path=None,
) -> bytes:
    """Build a minimal valid PDF with the given metadata and page text."""
    objects = []

    # Object 1: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    # Object 2: Pages
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

    # Object 3: Page
    objects.append(
        b"<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> "
        b"/Contents 4 0 R >>"
    )

    # Object 4: Content stream (page text)
    lines = page_text.split("\n")
    content_ops = b"BT /F1 12 Tf 72 720 Td 14 TL "
    for i, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_ops += f"({escaped}) Tj ".encode("latin-1")
        if i < len(lines) - 1:
            content_ops += b"T* "
    content_ops += b"ET"
    objects.append(
        b"<< /Length "
        + str(len(content_ops)).encode()
        + b" >>\nstream\n"
        + content_ops
        + b"\nendstream"
    )

    # Object 5: Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Object 6: Info dictionary (metadata)
    info_parts = []
    info_parts.append(b"/Title " + _pdf_string(title))
    info_parts.append(b"/Author " + _pdf_string(author))
    info_parts.append(b"/Subject " + _pdf_string(subject))
    info_parts.append(b"/Keywords " + _pdf_string(keywords))
    objects.append(b"<< " + b" ".join(info_parts) + b" >>")

    # Assemble the PDF.
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects):
        offsets.append(len(pdf))
        obj_num = i + 1
        pdf += f"{obj_num} 0 obj\n".encode() + obj + b"\nendobj\n"

    # Cross-reference table.
    xref_offset = len(pdf)
    pdf += b"xref\n"
    pdf += f"0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()

    # Trailer.
    pdf += b"trailer\n"
    pdf += f"<< /Size {len(objects) + 1} /Root 1 0 R /Info 6 0 R >>\n".encode()
    pdf += b"startxref\n"
    pdf += f"{xref_offset}\n".encode()
    pdf += b"%%EOF\n"

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf)

    return pdf


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "report.pdf"
    make_pdf(output_path=path)
    print(f"Generated {path}")
