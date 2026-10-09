import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas

from app import config
from app.utils.validation import sanitize_filename


def get_certificate_path(certificate_id: str) -> Path:
    """Resolve and validate the destination path for a certificate PDF."""
    safe_id = sanitize_filename(certificate_id)
    target_path = (config.GENERATED_DIR / f"cert_{safe_id}.pdf").resolve()
    
    # Path traversal protection: ensure the target resides within GENERATED_DIR
    if not str(target_path).startswith(str(config.GENERATED_DIR.resolve())):
        raise ValueError("Invalid certificate path: Directory traversal detected")
        
    return target_path


def generate_certificate_pdf(
    certificate_id: str,
    recipient_name: str,
    course_name: str,
    completion_date: str,
    output_path: Path | None = None,
) -> Path:
    """
    Generate a professional landscape PDF certificate using ReportLab.
    
    Args:
        certificate_id: Unique UUID of the certificate
        recipient_name: Name of the recipient
        course_name: Course or event title
        completion_date: Formatted completion date (YYYY-MM-DD)
        output_path: Optional explicit output path (defaults to generated/ directory)
        
    Returns:
        Path: Absolute path to the generated PDF file
    """
    if output_path is None:
        output_path = get_certificate_path(certificate_id)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Dimensions for Letter Landscape: 792 pt wide, 612 pt high
    width, height = landscape(letter)

    c = canvas.Canvas(str(output_path), pagesize=landscape(letter), pageCompression=0)
    c.setTitle(f"Certificate of Completion - {recipient_name}")
    c.setAuthor("Bulk Certificate Generator")

    # 1. Background Fill (Subtle off-white / parchment tint)
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # 2. Elegant Double Borders
    # Outer Navy Blue Border
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setLineWidth(4)
    c.rect(28, 28, width - 56, height - 56, fill=0, stroke=1)

    # Inner Gold Border
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(1.5)
    c.rect(36, 36, width - 72, height - 72, fill=0, stroke=1)

    # Corner Decorative Squares
    corner_size = 12
    c.setFillColor(colors.HexColor("#D97706"))
    # Bottom-left, bottom-right, top-left, top-right
    c.rect(36, 36, corner_size, corner_size, fill=1, stroke=0)
    c.rect(width - 36 - corner_size, 36, corner_size, corner_size, fill=1, stroke=0)
    c.rect(36, height - 36 - corner_size, corner_size, corner_size, fill=1, stroke=0)
    c.rect(width - 36 - corner_size, height - 36 - corner_size, corner_size, corner_size, fill=1, stroke=0)

    # 3. Header & Institution Branding
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, height - 80, "ACADEMY OF PROFESSIONAL DEVELOPMENT")

    # Thin accent rule under header
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.line(width / 2 - 120, height - 88, width / 2 + 120, height - 88)

    # 4. Main Certificate Title
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 130, "CERTIFICATE OF COMPLETION")

    # 5. Presentation Subtitle
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 170, "THIS IS PROUDLY PRESENTED TO")

    # 6. Recipient Name (with dynamic font scaling for long names)
    max_text_width = width - 160
    name_font_size = 26
    while name_font_size > 14 and c.stringWidth(recipient_name, "Helvetica-Bold", name_font_size) > max_text_width:
        name_font_size -= 2

    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.setFont("Helvetica-Bold", name_font_size)
    c.drawCentredString(width / 2, height - 215, recipient_name)

    # Decorative Underline for Recipient Name
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(2)
    name_width = min(max(c.stringWidth(recipient_name, "Helvetica-Bold", name_font_size) + 40, 180), max_text_width)
    c.line(width / 2 - (name_width / 2), height - 225, width / 2 + (name_width / 2), height - 225)

    # 7. Achievement Statement
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(
        width / 2,
        height - 265,
        "for successfully fulfilling all curriculum requirements and standards for:",
    )

    # 8. Course / Event Name (with dynamic font scaling for long course titles)
    course_font_size = 18
    while course_font_size > 12 and c.stringWidth(f'"{course_name}"', "Helvetica-Bold", course_font_size) > max_text_width:
        course_font_size -= 1

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", course_font_size)
    c.drawCentredString(width / 2, height - 300, f'"{course_name}"')

    # 9. Verification Seal (Emblem in center bottom)
    seal_x = width / 2
    seal_y = height - 380

    # Outer circle
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setFillColor(colors.HexColor("#FEF3C7"))
    c.setLineWidth(2)
    c.circle(seal_x, seal_y, 34, fill=1, stroke=1)

    # Inner dashed ring
    c.setStrokeColor(colors.HexColor("#B45309"))
    c.setLineWidth(1)
    c.setDash(2, 2)
    c.circle(seal_x, seal_y, 28, fill=0, stroke=1)
    c.setDash()  # reset dash pattern

    # Seal text
    c.setFillColor(colors.HexColor("#B45309"))
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(seal_x, seal_y + 6, "OFFICIAL")
    c.drawCentredString(seal_x, seal_y - 6, "VERIFIED")
    c.setFont("Helvetica", 7)
    c.drawCentredString(seal_x, seal_y - 18, "SEAL")

    # 10. Signatures
    sig_line_y = 110
    text_y = sig_line_y - 14

    # Left Signature - Academic Director
    c.setStrokeColor(colors.HexColor("#475569"))
    c.setLineWidth(1)
    c.line(100, sig_line_y, 250, sig_line_y)

    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.setFont("Times-Italic", 16)
    c.drawCentredString(175, sig_line_y + 8, "Alexander Wright")

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(175, text_y, "Dr. Alexander Wright")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawCentredString(175, text_y - 12, "Academic Program Director")

    # Right Signature - Certification Officer
    c.setStrokeColor(colors.HexColor("#475569"))
    c.setLineWidth(1)
    c.line(width - 250, sig_line_y, width - 100, sig_line_y)

    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.setFont("Times-Italic", 16)
    c.drawCentredString(width - 175, sig_line_y + 8, "Sarah Jenkins")

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width - 175, text_y, "Sarah Jenkins")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawCentredString(width - 175, text_y - 12, "Director of Certification")

    # 11. Footer: Completion Date & Certificate ID
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawString(45, 48, f"Date of Completion: {completion_date}")
    c.drawRightString(width - 45, 48, f"Certificate ID: {certificate_id}")

    c.showPage()
    c.save()

    return output_path
