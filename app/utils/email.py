import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_receipt_email(to_email, order_details, total_cost):
    """
    Sends a receipt email using SMTP settings from environment variables (GoDaddy SMTP).
    :param to_email: Recipient's email address
    :param order_details: String or HTML with order summary
    :param total_cost: Total cost as string or number
    """
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = int(os.environ.get('MAIL_PORT', 587))
    mail_use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    if not all([mail_server, mail_port, mail_username, mail_password]):
        raise Exception('MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, and MAIL_PASSWORD must be set as environment variables.')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Your Plasma Table Order Receipt'
    msg['From'] = mail_username
    msg['To'] = to_email

    text = f"""
    Thank you for your order!

    Order Details:
    {order_details}

    Total: ${total_cost}
    """
    html = f"""
    <html><body>
    <h2>Thank you for your order!</h2>
    <p><strong>Order Details:</strong></p>
    <pre>{order_details}</pre>
    <p><strong>Total:</strong> ${total_cost}</p>
    </body></html>
    """
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    try:
        if mail_use_tls:
            server = smtplib.SMTP(mail_server, mail_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(mail_server, mail_port)
        server.login(mail_username, mail_password)
        server.sendmail(mail_username, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        raise Exception(f'Failed to send email: {e}')
