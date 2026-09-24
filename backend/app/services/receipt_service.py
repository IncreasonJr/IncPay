import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


def generate_receipt_pdf(transaction: Dict[str, Any], seller: Dict[str, Any]) -> bytes:
    """
    Generate a professional customer payment receipt PDF in-memory.

    Content included:
    - IncPay branding + "Payment Receipt"
    - Business name (prominent)
    - Date and Paystack payment reference
    - Amount breakdown (Listed amount, visible D/2 customer discount, Total Paid)
    - Footer reassurance

    SECURITY CRITICAL:
    - Never includes platform_cut_amount or seller_payout_amount.
    - Does not expose internal seller credentials, bank accounts, or subaccount codes.
    """
    buffer = io.BytesIO()

    # Document setup: 0.5 inch margins for a clean, modern layout
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_style = ParagraphStyle(
        "IncPayBrand",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#111827"),
    )

    brand_sub = ParagraphStyle(
        "IncPaySub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6B7280"),
    )

    receipt_title = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=2,  # Right align
        textColor=colors.HexColor("#374151"),
    )

    receipt_status = ParagraphStyle(
        "ReceiptStatus",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor("#059669"),
    )

    merchant_header_label = ParagraphStyle(
        "MerchantLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6B7280"),
        textTransform="uppercase",
    )

    merchant_name_style = ParagraphStyle(
        "MerchantName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#111827"),
    )

    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#6B7280"),
    )

    meta_value_style = ParagraphStyle(
        "MetaValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1F2937"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#374151"),
    )

    table_row_label = ParagraphStyle(
        "TableRowLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#374151"),
    )

    table_row_val = ParagraphStyle(
        "TableRowVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor("#111827"),
    )

    discount_val_style = ParagraphStyle(
        "DiscountVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor("#059669"),
    )

    total_label_style = ParagraphStyle(
        "TotalLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#111827"),
    )

    total_value_style = ParagraphStyle(
        "TotalValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=2,
        textColor=colors.HexColor("#111827"),
    )

    footer_style = ParagraphStyle(
        "FooterStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        alignment=1,  # Center align
        textColor=colors.HexColor("#9CA3AF"),
    )

    story = []

    # 1. Header: Logo / Brand and Receipt Title
    header_table = Table(
        [
            [
                Paragraph("<b>IncPay</b>", brand_style),
                Paragraph("PAYMENT RECEIPT", receipt_title),
            ],
            [
                Paragraph("Payment-Bridge Platform", brand_sub),
                Paragraph("PAID & CONFIRMED", receipt_status),
            ],
        ],
        colWidths=[4.0 * inch, 3.5 * inch],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 14))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#E5E7EB"),
            spaceBefore=0,
            spaceAfter=14,
        )
    )

    # 2. Merchant Details
    business_name = (
        seller.get("business_name")
        or seller.get("name")
        or transaction.get("business_name")
        or "Merchant Partner"
    )

    story.append(Paragraph("Merchant Paid", merchant_header_label))
    story.append(Spacer(1, 2))
    story.append(Paragraph(business_name, merchant_name_style))
    story.append(Spacer(1, 16))

    # 3. Transaction Metadata Card
    reference = transaction.get("paystack_reference") or transaction.get("reference") or "—"
    created_at_val = transaction.get("created_at")
    if isinstance(created_at_val, datetime):
        formatted_date = created_at_val.strftime("%b %d, %Y • %H:%M UTC")
    elif isinstance(created_at_val, str) and created_at_val:
        try:
            dt = datetime.fromisoformat(created_at_val.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%b %d, %Y • %H:%M UTC")
        except Exception:
            formatted_date = created_at_val[:19].replace("T", " ")
    else:
        formatted_date = datetime.utcnow().strftime("%b %d, %Y")

    customer_email = transaction.get("customer_email") or "—"

    meta_data = [
        [
            Paragraph("Payment Reference:", meta_label_style),
            Paragraph(f"<font name='Helvetica-Bold'>{reference}</font>", meta_value_style),
        ],
        [
            Paragraph("Payment Date:", meta_label_style),
            Paragraph(formatted_date, meta_value_style),
        ],
        [
            Paragraph("Payment Channel:", meta_label_style),
            Paragraph("Paystack (Card / Mobile Money)", meta_value_style),
        ],
        [
            Paragraph("Customer Email:", meta_label_style),
            Paragraph(customer_email, meta_value_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[2.2 * inch, 5.3 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#E5E7EB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F3F4F6")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 20))

    # 4. Financial Calculations & Amount Breakdown
    try:
        listed_amt = float(transaction.get("listed_amount", 0.0))
        discount_amt = float(transaction.get("customer_discount_amount", 0.0))
        paid_amt = float(transaction.get("amount_paid", 0.0))
    except Exception:
        listed_amt = 0.0
        discount_amt = 0.0
        paid_amt = 0.0

    # Determine customer visible discount percentage (D/2)
    agreed_d = seller.get("agreed_discount")
    if agreed_d is not None:
        try:
            cust_pct = float(agreed_d) / 2.0
        except Exception:
            cust_pct = (discount_amt / listed_amt * 100.0) if listed_amt > 0 else 0.0
    elif listed_amt > 0 and discount_amt > 0:
        cust_pct = round((discount_amt / listed_amt) * 100.0, 1)
    else:
        cust_pct = 0.0

    breakdown_data = [
        [
            Paragraph("<b>Item / Description</b>", table_header_style),
            Paragraph("<b>Amount (GHS)</b>", table_row_val),
        ],
        [
            Paragraph("Listed Bill Amount", table_row_label),
            Paragraph(f"₵{listed_amt:,.2f}", table_row_val),
        ],
        [
            Paragraph(
                f"Instant Customer Discount ({cust_pct:.1f}%)",
                table_row_label,
            ),
            Paragraph(f"-₵{discount_amt:,.2f}", discount_val_style),
        ],
        [
            Paragraph("<b>Total Paid</b>", total_label_style),
            Paragraph(f"<b>₵{paid_amt:,.2f}</b>", total_value_style),
        ],
    ]

    breakdown_table = Table(breakdown_data, colWidths=[5.2 * inch, 2.3 * inch])
    breakdown_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 1), (-1, 2), 6),
                ("BOTTOMPADDING", (0, 1), (-1, 2), 6),
                ("LINEBELOW", (0, 2), (-1, 2), 1, colors.HexColor("#E5E7EB")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#F9FAFB")),
                ("TOPPADDING", (0, 3), (-1, 3), 10),
                ("BOTTOMPADDING", (0, 3), (-1, 3), 10),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#E5E7EB")),
            ]
        )
    )
    story.append(breakdown_table)
    story.append(Spacer(1, 30))

    # 5. Footer & Reassurance
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor("#E5E7EB"),
            spaceBefore=0,
            spaceAfter=14,
        )
    )
    story.append(
        Paragraph(
            "Thank you for your payment. This receipt was generated by IncPay.<br/>"
            "Official payment confirmation for merchant point-of-sale settlement.",
            footer_style,
        )
    )

    # Build PDF in memory
    doc.build(story)
    return buffer.getvalue()
