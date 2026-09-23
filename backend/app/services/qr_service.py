import io
import logging
import qrcode
import qrcode.image.svg

logger = logging.getLogger(__name__)


def generate_qr_png(url: str, box_size: int = 10, border: int = 4) -> bytes:
    """
    Generate an in-memory PNG QR code for a given URL.
    Returns raw bytes suitable for image/png HTTP response.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qr_svg(url: str, box_size: int = 10, border: int = 4) -> str:
    """
    Generate an in-memory SVG XML string for a given URL.
    Returns SVG markup suitable for image/svg+xml HTTP response.
    """
    factory = qrcode.image.svg.SvgPathImage
    svg_img = qrcode.make(
        url,
        image_factory=factory,
        box_size=box_size,
        border=border,
    )
    buffer = io.BytesIO()
    svg_img.save(buffer)
    return buffer.getvalue().decode("utf-8")
