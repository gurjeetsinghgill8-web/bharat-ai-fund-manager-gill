import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# Load configuration
load_dotenv()

def send_momentum_newsletter(pdf_path, excel_path, run_date_str):
    """
    Sends the generated PDF and Excel reports to the recipients listed in .env
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    recipients_str = os.getenv("EMAIL_RECIPIENTS")

    if not smtp_user or not smtp_password or not recipients_str:
        print("SMTP Credentials not fully configured. Email newsletter skipped.")
        return False, "SMTP credentials missing or incomplete."

    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    if not recipients:
        return False, "No valid recipient email addresses found."

    try:
        # Create Message container
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"Bharat AI Fund Manager Gill - Weekly Report ({run_date_str})"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #1E2022;">
            <h2 style="color: #0B192C;">Bharat AI Fund Manager Gill</h2>
            <p>Dear Investor,</p>
            <p>Please find attached the weekly momentum ranking and breakout report for <b>{run_date_str}</b>.</p>
            <p>Our autonomous engine has processed the Nifty space and generated the following reports:
            <ul>
                <li><b>Weekly Rankings PDF:</b> Includes the top 15 ranked stocks, custom risk grades, and narrative analysis.</li>
                <li><b>Excel Sheet Ledger:</b> Contains complete ranked lists, breakout logs, sustained momentum flags, and the Red Alert Blacklist.</li>
            </ul>
            </p>
            <p><i>Note: This is an automated system output. Past performance is not indicative of future returns. Invest responsibly.</i></p>
            <br/>
            <p>Regards,<br/><b>Bharat AI System Team</b></p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        # Attach PDF
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(pdf_path)}",
                )
                msg.attach(part)
                
        # Attach Excel
        if os.path.exists(excel_path):
            with open(excel_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(excel_path)}",
                )
                msg.attach(part)

        # Connect and Send
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_string())
        server.quit()
        
        print("Newsletter email sent successfully.")
        return True, "Email sent successfully."
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False, str(e)
