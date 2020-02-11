import sys
from lxml import html
from datetime import datetime, timedelta
import time

sys.path.append('../../')
from model.klikbca import KlikbcaAccount
from model.transaction import Transaction
from model.config import Config
from model.log import Log
from model.code import GenerateCode
from model.email import EmailTransport
from helper.file import File


class KlikbcaEnterprise:
    def __init__(self, name=None, session=None, proxy={}):
        self.name = name
        self.session = session
        self.proxy = proxy
        self.config = Config()
        self.log = Log()
        self.code = GenerateCode()
        self.email_transport = EmailTransport()
        section_config = self.get_section_config(name)
        self.dashboard_url = section_config['dashboard_url']
        self.balance_url = section_config['balance_url']
        self.account_info_url = section_config['account_info_url']
        self.account_statement_url = section_config['account_statement_url']
        self.username = section_config['username']
        self.password = section_config['password']
        self.debug_mode = section_config['debug_mode']
        self.total_transactions = 0
        self.file = File()

    def get_section_config(self, name=None):
        if name is None:
            name = 'Klikbca'
        section_config = self.config.get_section_config(name)
        return section_config

    def is_logged(self):
        session_requests = self.session
        account_info_url = self.account_info_url
        tree = session_requests.get_tree()
        if tree is None:
            return 0
        try:
            result = session_requests.get(account_info_url)
            tree = html.fromstring(result.content)
            account_info_text = tree.xpath("//a[@href='menu_bar.htm']//b/text()")
            if "Account Information" in account_info_text:
                return 1
            return 0
        except:
            return 0

    def is_debug(self):
        return self.debug_mode

    def perform_login(self):
        dashboard_url = self.dashboard_url
        username = self.username
        password = self.password
        session_requests = self.session

        if self.is_logged() == 0:
            session_requests.set_tree(None)
            session_requests.init_session(self.proxy)
            session_requests.set_changing_proxy(1)
            payload = {
                'value(actions)': 'login',
                'value(user_id)': username,
                'value(user_ip)': self.proxy['ip'],
                'value(browser_info)': session_requests.get_user_agent(),
                'value(mobile)': 'false',
                'value(pswd)': password,
                'value(Submit)': 'LOGIN',
            }
            # Perform login
            try:
                login_post = session_requests.post(dashboard_url, payload)
                tree = html.fromstring(login_post.content)
                menu = tree.xpath("//frame[@name='menu']")
                if len(menu) > 0:
                    session_requests.set_tree(tree)
                    session_requests.set_changing_proxy(0)
            except:
                self.log.log(str(sys.exc_info()), 'debug')
                session_requests.set_changing_proxy(1)
        else:
            session_requests.set_changing_proxy(0)
            if self.debug_mode == 'true':
                self.log.log('Login ' + self.name + ' successfully by using old session', 'debug')
        tree = session_requests.get_tree()
        if tree is None:
            return 0
        self.update_transactions(session_requests)

    def update_transactions(self, session_requests):
        balance_url = self.balance_url
        account_statement_url = self.account_statement_url
        current_date = self.get_current_update().split('/')
        now = datetime.now()
        payload = {
            'value(D1)': 0,
            'value(r1)': 1,
            'value(startDt)': str(current_date[0]),
            'value(startMt)': str(current_date[1]),
            'value(startYr)': str(current_date[2]),
            'value(endDt)': str(now.day),
            'value(endMt)': str(now.month),
            'value(endYr)': str(now.year),
            'value(fDt)': '',
            'value(tDt)': '',
            'value(submit1)': 'View Account Statement',
        }
        statement_post = session_requests.post(account_statement_url, payload)

        tree = html.fromstring(statement_post.content)
        account_number = None
        account_name = None
        account_number_row = \
            tree.xpath("//table[@bordercolor='#f0f0f0'][@width='90%']//tr[@bgcolor='#e0e0e0']/td/font/text()")

        if len(account_number_row) > 0:
            account_number = account_number_row[2]

        account_name_row = \
            tree.xpath("//table[@bordercolor='#f0f0f0'][@width='90%']//tr[@bgcolor='#f0f0f0']/td/font/text()")
        if len(account_name_row) > 0:
            account_name = account_name_row[2]

        account = KlikbcaAccount(account_name, account_number)
        if account_number is not None and 'Period' not in account_number and 'Currency' not in account_name:
            balance_get = session_requests.post(balance_url, dict(referer=self.account_info_url))
            acc_tree = html.fromstring(balance_get.content)
            available_balance = acc_tree.xpath("//table[@width='590']//tr/td/div[@align='right']/font/text()")[0]
            available_balance = float(available_balance.strip().replace(',', ''))
            account.set_balance(available_balance)
            account.update_account()
        transactions = tree.xpath("//table[@bordercolor='#ffffff'][@width='100%']//tr")
        if len(transactions) > 0:
            del transactions[0]
        for row in transactions:
            columns = row.xpath("td")
            detail = []
            for column in columns:
                value = column.xpath("div/font")
                if len(value) > 0:
                    value = value[0]
                    value = value.text_content()
                    detail.append(value.strip())
            self.save_transaction(account, detail)
        self.set_current_update()
        self.log.update_log('Klikbca', self.username)
        self.log.log(str(self.total_transactions) + ' ' + self.name + ' transaction(s) created', 'message')

    def save_transaction(self, account, detail):
        now = datetime.now()
        year = str(now.year)
        if detail[0] == 'PEND':
            detail[0] = str(now.day) + '/' + str(now.month)
        trading_date = self.convert_trading_date(detail[0] + '/' + year)
        description = detail[1]
        account_id = account.get_account_id()
        if detail[4] == 'DB':
            balance = float('-' + detail[3].replace(',', ''))
        else:
            balance = float(detail[3].replace(',', ''))
        del detail[0]
        reference_number = self.code.generate_code('-'.join(detail))
        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d/%m/%Y')
        return date.strftime('%Y-%m-%d')

    def get_current_update(self):
        path = self.get_update_file()
        with open(path, 'r') as content_file:
            current_update = content_file.read()
        return current_update

    def set_current_update(self):
        path = self.get_update_file()
        current_date = time.strftime("%d/%m/%Y")
        date = datetime.strptime(current_date, "%d/%m/%Y")
        modified_date = date - timedelta(days=1)
        file = open(path, 'w')
        file.write(datetime.strftime(modified_date, "%d/%m/%Y"))
        file.close()

    def get_update_file(self):
        update_file = self.config.get_base_dir('tmp') + 'klikbca_enterprise_update.txt'
        return update_file
