"""Regenerate the sample packet PDFs used for manual smoke testing.

Run from the repo root:

    uv run python tests/fixtures/generate_samples.py

This produces three born-digital PDFs in this directory. Each page carries
enough text (well above `TEXT_CHAR_THRESHOLD=100`) that `input.detect_mode`
classifies them as "text" and the pipeline exercises the text path.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).parent


def _write_page(c: canvas.Canvas, header: str, body_lines: list[str]) -> None:
    """Write a single page with a large header and several body lines."""
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, header)
    c.setFont("Helvetica", 11)
    y = 680
    for line in body_lines:
        c.drawString(72, y, line)
        y -= 18
    c.showPage()


def build_multi_form_packet(path: Path) -> None:
    """8 pages, 3 documents - expected 3 segments: [0-1], [2-4], [5-7]."""
    c = canvas.Canvas(str(path), pagesize=letter)

    # Document 1: Invoice (2 pages)
    _write_page(
        c,
        "INVOICE #001",
        [
            "Acme Corporation - Invoice to Beta LLC",
            "Date: 2026-04-20   Due: 2026-05-20",
            "",
            "Line 1: Widgets (qty 10)            $1,200.00",
            "Line 2: Shipping & handling             $75.00",
            "Line 3: Installation service           $250.00",
            "",
            "Subtotal                             $1,525.00",
        ],
    )
    _write_page(
        c,
        "Invoice #001 - continued",
        [
            "Tax (8.25%)                           $125.81",
            "Total due                           $1,650.81",
            "",
            "Payment terms: Net 30",
            "Remit to: Acme Corp, 123 Industry Way",
            "Questions: billing@acme.example",
            "Thank you for your business.",
        ],
    )

    # Document 2: Purchase Order (3 pages)
    _write_page(
        c,
        "PURCHASE ORDER #P-47",
        [
            "Department of Procurement - PO #P-47",
            "Vendor: Acme Corporation",
            "Contract reference: C-2026-118",
            "",
            "Items requested:",
            "- 50 widgets, part #W-100",
            "- 10 support hours, skill tier 2",
            "- Shipping to warehouse 3",
        ],
    )
    _write_page(
        c,
        "PO #P-47 - Item detail",
        [
            "Full specification for W-100:",
            "  - Material: aluminum alloy 6061-T6",
            "  - Tolerance: +/- 0.05 mm",
            "  - Surface finish: anodized black",
            "",
            "Delivery window: 2026-05-01 to 2026-05-15",
            "Inspection required before acceptance.",
            "Contact: procurement@example.gov",
        ],
    )
    _write_page(
        c,
        "PO #P-47 - Terms",
        [
            "Payment terms: Net 45 from acceptance",
            "Liquidated damages: $50/day late after 2026-05-20",
            "Cancellation: 10-day written notice required",
            "",
            "Signatures:",
            "    Procurement Director ___________________",
            "    Vendor Representative  ___________________",
            "    Date                   ___________________",
        ],
    )

    # Document 3: Certificate of Delivery (3 pages)
    _write_page(
        c,
        "CERTIFICATE OF DELIVERY",
        [
            "Issued to: Department of Procurement",
            "Reference PO: P-47",
            "Delivery date: 2026-05-08",
            "",
            "This certifies that the items listed on the",
            "attached schedule have been delivered in good",
            "condition to warehouse 3, as per the terms of",
            "purchase order P-47 dated 2026-04-20.",
        ],
    )
    _write_page(
        c,
        "Certificate - Schedule",
        [
            "Items delivered:",
            "  50 x Widget W-100 (aluminum, anodized)",
            "  1  x Support voucher, 10 hours",
            "",
            "Serial numbers: SN-2026-0001 through SN-2026-0050",
            "Weight: 12.4 kg total",
            "Carrier: FastShip Express",
            "Tracking: FSE-99-82-001",
        ],
    )
    _write_page(
        c,
        "Certificate - Signatures",
        [
            "Received and inspected by:",
            "    Warehouse Manager _______________________",
            "    Date / Time        _______________________",
            "",
            "Witnessed by:",
            "    Inspector          _______________________",
            "    Inspector ID       _______________________",
            "",
            "Seal / stamp affixed below.",
        ],
    )

    c.save()


def build_double_letter(path: Path) -> None:
    """4 pages, 2 documents - expected 2 segments: [0-1], [2-3]."""
    c = canvas.Canvas(str(path), pagesize=letter)

    _write_page(
        c,
        "Letter from Alice Morales",
        [
            "Alice Morales",
            "14 Willow Lane, Rivertown",
            "April 20, 2026",
            "",
            "Dear Bob,",
            "",
            "I hope this letter finds you well. I wanted",
            "to follow up on the conversation we had at the",
            "conference last month about the new initiative.",
        ],
    )
    _write_page(
        c,
        "Letter from Alice - page 2",
        [
            "As I mentioned, the team is very excited about",
            "the opportunity and we'd love to coordinate a",
            "kickoff meeting within the next two weeks.",
            "",
            "Please let me know which dates work for you.",
            "",
            "Warm regards,",
            "Alice",
        ],
    )

    _write_page(
        c,
        "Letter from Charlie Diaz",
        [
            "Charlie Diaz",
            "Research and Development",
            "April 22, 2026",
            "",
            "Dear Dana,",
            "",
            "Thank you for reviewing the draft proposal.",
            "Your comments were very helpful and I've",
            "incorporated most of them into the revision.",
        ],
    )
    _write_page(
        c,
        "Letter from Charlie - page 2",
        [
            "One item I'd like to discuss further is the",
            "section on methodology. Would you be available",
            "for a short call next Tuesday afternoon?",
            "",
            "I'll send a calendar invite tomorrow morning.",
            "",
            "Best,",
            "Charlie",
        ],
    )

    c.save()


def build_single_report(path: Path) -> None:
    """3 pages, 1 document - expected 1 segment: [0-2] (no inner boundaries)."""
    c = canvas.Canvas(str(path), pagesize=letter)

    _write_page(
        c,
        "ANNUAL REPORT 2025",
        [
            "Rivertown Community Cooperative",
            "Fiscal year ending December 31, 2025",
            "",
            "This report summarizes the cooperative's activities,",
            "financial position, and outlook for the coming year.",
            "It is intended for members and the public record.",
            "Prepared by the board of directors.",
            "Published March 2026.",
        ],
    )
    _write_page(
        c,
        "Financial summary",
        [
            "Total revenue                        $1,820,400",
            "Total expenses                       $1,642,900",
            "Net surplus                            $177,500",
            "",
            "Cash on hand (year end)                $325,200",
            "Member equity                          $912,800",
            "",
            "Details by program are available in Appendix A.",
            "External audit performed by Smith & Partners LLP.",
        ],
    )
    _write_page(
        c,
        "Board and staff",
        [
            "Board of directors:",
            "  Chair: Ana Ribeiro",
            "  Vice chair: Miguel Tanaka",
            "  Treasurer: Priya Okafor",
            "",
            "Full-time staff: 14 (across 3 locations)",
            "Volunteers engaged: 127",
            "",
            "Annual meeting: May 18, 2026.",
        ],
    )

    c.save()


BUILDERS = {
    "multi_form_packet.pdf": build_multi_form_packet,
    "double_letter.pdf": build_double_letter,
    "single_report.pdf": build_single_report,
}


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in BUILDERS.items():
        out = FIXTURES_DIR / name
        builder(out)
        size_kb = out.stat().st_size / 1024
        print(f"  wrote {out.relative_to(FIXTURES_DIR.parent.parent)} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
