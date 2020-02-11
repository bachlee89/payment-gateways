import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from babel.numbers import format_currency
from .time import Time
from .config import Config


class EmailTransport:
    def __init__(self):
        self.time = Time()
        self.config = Config()
        self.email_config = self.config.get_section_config('Email')
        self.sender_email = self.email_config['sender_email']
        self.sender_pass = self.email_config['sender_pass']
        self.sale_emails = self.email_config['sale_emails']
        self.system_emails = self.email_config['system_emails']

    def send_transaction_email(self, account, transaction):
        message = MIMEMultipart()
        message["Subject"] = "[FinanceX Payment] You have a new transaction"
        message["From"] = self.sender_pass
        message["To"] = self.sale_emails.split(',')[0]
        if account.get_vendor() in ['Vietcombank', 'Maritimebank']:
            balance = format_currency(float(transaction.get_balance()), 'VND', locale='vi_VN')
        elif account.get_vendor() in ['Klikbca']:
            balance = format_currency(float(transaction.get_balance()), 'IDR', locale='vi_VN')
        else:
            balance = float(transaction.get_balance())
        description = transaction.get_description()
        trading_date = transaction.get_trading_date()
        if transaction.get_status(transaction.get_reference_number()) == 0:
            status = "Pending"
        else:
            status = "Completed"
        text = """\
        <html>
            <body>
                Account Number: <strong>{0}</strong><br/>
                Account Name: <strong>{1}</strong><br/>
                Vendor: <strong>{2}</strong><br/>
                Balance Changed: <strong>{3}</strong><br/>
                Description: <strong>{4}</strong><br/>
                Status: <strong>{5}</strong><br/>
                Trading Date: <strong>{6}</strong><br/>
            </body>
        </html>
        """.format(account.get_number(), account.get_name(), account.get_vendor(), balance, description, status,
                   trading_date)
        message.attach(MIMEText(text, "html"))
        self.send(self.sale_emails, message)
        # Create secure connection with server and send email

    def send_notify(self, vendor, username):
        message = MIMEMultipart()
        message["Subject"] = "[FinanceX Payment] System Failure"
        message["From"] = self.sender_pass
        message["To"] = self.system_emails.split(',')[0]
        text = """\
        <html>
            <body>
            <p>We can not access <strong>{0}</strong> Bank with account <strong>{1}</strong> for about 1 hour. 
            Please check your <strong>system.log</strong> to see more detail. </p>
            </body>
        </html>
        """.format(vendor, username)
        message.attach(MIMEText(text, "html"))
        self.send(self.system_emails, message)

    def send(self, receiver_emails, message):
        sender_email = self.sender_email
        password = self.sender_pass
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, receiver_emails.split(','), message.as_string()
            )
