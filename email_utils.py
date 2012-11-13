__all__ = ["send_msg"]


import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# email config
from_email = "Lunch Robot <robot@wtfisforlunch.com>"


def _connect():
    email_username = os.environ.get("MAIL_USERNAME")
    email_password = os.environ.get("MAIL_PASSWORD")

    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(email_username, email_password)

    return s


def send_msg(email, text, subj):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subj
    msg["From"] = from_email
    msg["To"] = email
    msg.attach(MIMEText(text, "plain"))
    s = _connect()
    s.sendmail(msg["From"], msg["To"], msg.as_string())
    s.quit()
