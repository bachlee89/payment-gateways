from babel.numbers import format_currency
from .time import Time
from .config import Config
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class EmailTransport:
    def __init__(self):
        self.time = Time()
        self.config = Config()
        self.email_config = self.config.get_section_config('Email')
        self.sender_email = self.email_config['sender_email']
        self.api_key = self.email_config['api_key']
        self.sale_emails = self.email_config['sale_emails']
        self.system_emails = self.email_config['system_emails']

    def send_transaction_email(self, account, transaction):
        subject = "[FinanceX Payment] You have a new transaction " + transaction.get_reference_number()
        sender = self.sender_email
        receiver = self.sale_emails
        if account.get_vendor() in ['Vietcombank', 'Maritimebank', 'Techcombank', 'Msb']:
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
        message = Mail(
            from_email=sender,
            to_emails=receiver,
            subject=subject,
            html_content=text)
        self.send(message)
        # Create secure connection with server and send email

    def send_error_transaction_email(self, account, transaction):
        subject = "[FinanceX Payment] Can not save a new transaction " + transaction.get_reference_number()
        sender = self.sender_email
        receiver = self.sale_emails
        if account.get_vendor() in ['Vietcombank', 'Maritimebank', 'Techcombank', 'Msb']:
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
        message = Mail(
            from_email=sender,
            to_emails=receiver,
            subject=subject,
            html_content=text)
        self.send(message)
        # Create secure connection with server and send email

    def send_notify(self, vendor, username):
        subject = "[FinanceX Payment] System Failure at" + self.time.get_current_time()
        sender = self.sender_email
        receiver = self.system_emails
        text = """\
        <html>
            <body>
            <p>We can not access <strong>{0}</strong> Bank with account <strong>{1}</strong> for about 1 hour. 
            Please check your <strong>system.log</strong> to see more detail. </p>
            </body>
        </html>
        """.format(vendor, username)

        message = Mail(
            from_email=sender,
            to_emails=receiver,
            subject=subject,
            html_content=text)
        self.send(message)

    def send(self, message):
        sg = SendGridAPIClient(self.api_key)
        sg.send(message)
