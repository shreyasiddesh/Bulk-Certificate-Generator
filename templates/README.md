# Certificate Templates & Styling

This directory contains resources and design specifications for certificate generation.

## Default Predefined Template: `Executive Landscape`

The system uses a predefined ReportLab programmatic template implemented in [`app/services/certificate_service.py`](../app/services/certificate_service.py).

### Layout Specifications:
- **Dimensions**: US Letter Landscape (11 x 8.5 inches / 792 x 612 pt)
- **Palette**:
  - Primary Navy Blue: `#0F172A` / `#1E3A8A`
  - Accent Amber Gold: `#D97706` / `#B45309`
  - Background: Crisp Warm White `#F8FAFC`
  - Muted Slate: `#475569` / `#64748B`
- **Typography**:
  - Issuer Title: Helvetica-Bold 10pt
  - Header: Helvetica-Bold 28pt
  - Subtitle: Helvetica 12pt
  - Recipient Name: Helvetica-Bold 26pt (with gold underline accent)
  - Course Name: Helvetica-Bold 18pt
  - Signatures: Times-Italic 16pt (Script simulation)
- **Security & Integrity Elements**:
  - Verification Seal: Dual concentric rings with "OFFICIAL VERIFIED SEAL" badge
  - Certificate ID: Unique UUID tracking string
  - Formal Signature Lines: Academic Director and Director of Certification
