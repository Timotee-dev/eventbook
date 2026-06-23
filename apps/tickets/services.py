"""
Generate QR code + branded PDF ticket after confirmed payment.
"""
import io, logging
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger('apps')

def make_ticket(booking):
    from .models import Ticket
    ticket, _ = Ticket.objects.get_or_create(booking=booking)
    if ticket.qr_image and ticket.pdf_file:
        return ticket

    verify_url = f'{settings.FRONTEND_URL}/verify-ticket/{ticket.number}/'

    # QR code
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(verify_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#0a0a0f', back_color='white')
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        ticket.qr_image.save(f'{ticket.number}.png', ContentFile(buf.getvalue()), save=False)
    except Exception as e:
        logger.error(f'QR generation failed: {e}')

    # PDF
    try:
        pdf_data = _build_pdf(ticket, booking, verify_url)
        ticket.pdf_file.save(f'{ticket.number}.pdf', ContentFile(pdf_data), save=False)
    except Exception as e:
        logger.error(f'PDF generation failed: {e}')

    ticket.save()
    return ticket


def _build_pdf(ticket, booking, verify_url):
    import io, qrcode
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.colors import HexColor, white
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    W, H = A5
    c = canvas.Canvas(buf, pagesize=A5)

    # Background
    c.setFillColor(HexColor('#0a0a0f'))
    c.rect(0, 0, W, H, fill=True, stroke=False)

    # Purple header bar
    c.setFillColor(HexColor('#7c3aed'))
    c.rect(0, H - 70, W, 70, fill=True, stroke=False)

    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(16, H - 30, settings.SITE_NAME)
    c.setFont('Helvetica', 10)
    c.drawString(16, H - 52, 'E-Ticket')

    event = booking.event
    y = H - 95
    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(16, y, event.title[:50])

    c.setFont('Helvetica', 9)
    c.setFillColor(HexColor('#c9c4d8'))
    for line in [
        f'📅 {event.start_datetime.strftime("%d %b %Y, %I:%M %p")}',
        f'📍 {event.venue_name}, {event.city}',
        f'🎟 Type: {booking.ticket_type.name if booking.ticket_type else "General"}',
        f'👤 Attendee: {booking.attendee_name}',
        f'🔢 Qty: {booking.quantity}',
        f'🆔 Booking: {booking.reference}',
        f'🎫 Ticket: {ticket.number}',
    ]:
        y -= 22
        c.drawString(16, y, line)

    # QR
    qr = qrcode.QRCode(box_size=5, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='black', back_color='white')
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, 'PNG')
    qr_buf.seek(0)
    c.drawImage(ImageReader(qr_buf), W - 110, 20, 90, 90)

    c.setFont('Helvetica-Oblique', 7)
    c.setFillColor(HexColor('#6b6480'))
    c.drawString(16, 16, 'Present this ticket at the entrance. Valid once only.')

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
