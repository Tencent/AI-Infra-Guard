"""PDF-metadata channel: hide the payload inside PDF metadata fields.

When a model reads a PDF — via text extraction, a retrieval pipeline, or
a summarisation tool — the document's metadata (Title, Author, Subject,
Keywords) is often included in the text stream. A payload planted in a
metadata field is invisible in the rendered page content yet present in
what the model processes.

**File mode**: :meth:`taint_file` uses :mod:`pypdf` to inject the payload
into a real PDF's ``/Info`` dictionary, producing a valid tainted ``.pdf``.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("pdf_metadata")
class PDFMetadataChannel(Channel):
    """Embed the payload in a PDF metadata field.

    The channel works on a plain-text representation of PDF metadata
    (``key: value`` lines, one per field). When the raw PDF bytes are not
    available — which is the common case in simulation — this text form
    is what the extraction pipeline would hand to the model.

    Parameters
    ----------
    field:
        The metadata field to inject into:
        * ``"title"`` — the ``Title`` field.
        * ``"author"`` — the ``Author`` field.
        * ``"subject"`` — the ``Subject`` field.
        * ``"keywords"`` — the ``Keywords`` field.
        * ``"custom"`` — a custom ``X-Comment`` field.
    """

    _FIELD_MAP = {
        "title": "Title",
        "author": "Author",
        "subject": "Subject",
        "keywords": "Keywords",
        "custom": "X-Comment",
    }

    def __init__(self, field: str = "title") -> None:
        if field not in self._FIELD_MAP:
            raise ValueError(
                "field must be 'title', 'author', 'subject', 'keywords', or 'custom'"
            )
        self.field = field

    def taint(self, data: str, payload: str) -> str:
        field_name = self._FIELD_MAP[self.field]
        lines = data.splitlines()
        injected = False
        out = []
        for line in lines:
            if not injected and line.strip().startswith(f"{field_name}:"):
                out.append(f"{field_name}: {payload}")
                injected = True
            else:
                out.append(line)
        if not injected:
            out.append(f"{field_name}: {payload}")
        return "\n".join(out)

    def taint_file(self, path: str, payload: str, output_path=None) -> str:
        """Inject the payload into a real PDF's metadata dictionary.

        Uses :mod:`pypdf` to read the PDF, overwrite the target metadata
        field with the payload, and write the tainted PDF.
        """
        import os

        from pypdf import PdfReader, PdfWriter

        field_name = "/{}".format(self._FIELD_MAP[self.field])

        reader = PdfReader(path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        # Copy existing metadata, then inject.
        meta = dict(reader.metadata) if reader.metadata else {}
        meta[field_name] = payload
        writer.add_metadata(meta)

        if output_path is None:
            base, ext = os.path.splitext(path)
            output_path = f"{base}.tainted{ext}"
        with open(output_path, "wb") as f:
            writer.write(f)
        return output_path

    def extract_file(self, path: str) -> str:
        """Return page text plus metadata as a model-facing PDF reader might.

        PDF files are binary, so the base text-file implementation cannot
        reliably expose an injected ``/Info`` value to the agent testbed.
        """
        from pypdf import PdfReader

        reader = PdfReader(path)
        metadata = reader.metadata or {}
        fields = []
        for key, value in metadata.items():
            if value is not None:
                # pypdf preserves a leading separator emitted by some attack
                # wordings (for example ``naive.inject("", task)``). Trim
                # it for the extracted, human/model-facing representation;
                # the original PDF metadata remains unchanged.
                fields.append(f"{str(key).lstrip('/')}: {str(value).strip()}")
        pages = [
            page.extract_text() or ""
            for page in reader.pages
        ]
        return "\n".join(fields + pages)
