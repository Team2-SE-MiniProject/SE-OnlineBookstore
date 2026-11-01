from io import BytesIO
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def generate_invoice_pdf(order):
    """Generate a PDF invoice for an order and return its bytes."""
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="InvoiceTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1F4E79"),
        )
    )

    story = [
        Paragraph("ONLINE BOOKSTORE", styles["InvoiceTitle"]),
        Paragraph("ORDER INVOICE", styles["Heading2"]),
        Spacer(1, 8 * mm),
        Paragraph(f"<b>Order ID:</b> {order.pk}", styles["Normal"]),
        Paragraph(
            f"<b>Order Date:</b> {order.created_at.strftime('%d %b %Y, %H:%M')}",
            styles["Normal"],
        ),
        Paragraph(f"<b>Customer:</b> {order.user.username}", styles["Normal"]),
        Spacer(1, 8 * mm),
    ]

    rows = [["Book", "Quantity", "Unit Price (INR)", "Subtotal (INR)"]]
    subtotal = Decimal("0.00")

    for item in order.items.select_related("book").all():
        item_subtotal = item.unit_price * item.quantity
        subtotal += item_subtotal
        rows.append([
            Paragraph(str(item.book.title), styles["BodyText"]),
            str(item.quantity),
            f"{item.unit_price:.2f}",
            f"{item_subtotal:.2f}",
        ])

    discount = max(subtotal - order.total_amount, Decimal("0.00"))
    rows.extend([
        ["", "", "Subtotal", f"{subtotal:.2f}"],
        ["", "", "Discount", f"-{discount:.2f}"],
        ["", "", "Total", f"{order.total_amount:.2f}"],
    ])

    table = Table(
        rows,
        colWidths=[75 * mm, 25 * mm, 35 * mm, 35 * mm],
        repeatRows=1,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    story.extend([
        table,
        Spacer(1, 10 * mm),
        Paragraph("Thank you for shopping with Online Bookstore!", styles["Normal"]),
    ])

    document.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
