import sys
from lxml import html
from datetime import datetime
import re
from model.email import EmailTransport
import time

sys.path.append('../../')
from model.msb import MsbAccount
from model.transaction import Transaction
from model.config import Config
from model.log import Log
from model.code import GenerateCode
from converter.captcha import CaptchaResolver
from model.history import History
from helper.file import File


class Msb:
    def __init__(self, payment, session=None, proxy={}):
        self.payment = payment
        self.session = session
        self.proxy = proxy
        self.captcha = CaptchaResolver()
        self.config = Config()
        self.log = Log()
        self.history = History()
        self.code = GenerateCode()
        self.email_transport = EmailTransport()
        section_config = self.get_msb_config()
        self.username = payment.get_username()
        self.password = payment.get_password()
        self.home_url = section_config['home_url']
        self.login_url = section_config['login_url']
        self.account_list_url = section_config['account_list_url']
        self.account_info_url = section_config['account_info_url']
        self.debug_mode = section_config['debug_mode']
        self.total_transactions = 0
        self.max_attempt_login = 10
        self.max_validate_captcha = 10
        self.login_failed = 0
        self.captcha_failed = 0

    def get_msb_config(self):
        msb = self.config.get_section_config('Msb')
        return msb

    def is_logged_in(self):
        session_requests = self.session
        token = session_requests.get_token()
        if token is None:
            return 0
        try:
            account_list_url = self.account_list_url
            payload = {
                'acctType': "'CA','SA','LN'",
                'status': "'ACTV','DORM','MATU'",
                'tokenNo': token,
                'lang': "vi_VN",
            }
            list_post = session_requests.post(account_list_url, payload)
            response = list_post.json()
            if response['status'] == '200':
                return 1
            return 0
        except Exception as e:
            if self.debug_mode == 'true':
                self.log.log(str(e), 'debug')
            return 0

    def is_debug(self):
        return self.debug_mode

    def perform_login(self):
        home_url = self.home_url
        login_url = self.login_url
        username = self.username
        password = self.password
        session_requests = self.session

        if self.is_logged_in() == 0:
            session_requests.set_tree(None)
            session_requests.init_session(self.proxy)
            session_requests.set_changing_proxy(1)
            result = session_requests.get(login_url)
            tree = html.fromstring(result.text)
            window_location = tree.xpath("//script/text()")[0]
            window_location = self.replace_all(window_location,
                                               {"window.location.href = '": "", "';": ""})
            login_redirect_url = str(home_url + window_location.strip())
            result = session_requests.get(login_redirect_url, dict(referer=login_redirect_url))
            tree = html.fromstring(result.text)
            window_location = tree.xpath("//script/text()")[0]
            window_location = self.replace_all(window_location,
                                               {"window.location.href = '": "", "';": ""})
            real_login_redirect_url = str(home_url + window_location.strip())
            result = session_requests.get(real_login_redirect_url, dict(referer=login_redirect_url))
            tree = html.fromstring(result.content)
            dse_session_id = tree.xpath("//input[@name='dse_sessionId']/@value")[0]
            img_data = session_requests.get(home_url + '/IBSRetail/servlet/ImageServlet').content
            self.captcha.save_from_source(img_data)
            captcha_text = self.captcha.resolve(True)
            if self.validate_captcha(captcha_text) == 0:
                if self.captcha_failed < self.max_validate_captcha:
                    self.captcha_failed = self.captcha_failed + 1
                    return self.perform_login()
                else:
                    if self.debug_mode == 'true':
                        self.log.log('Can\'t validate captcha after ' + str(self.captcha_failed) + ' times', 'debug')
                    self.captcha_failed = 0
                    return 0
            payload = {
                'dse_sessionId': dse_session_id,
                'dse_applicationId': -1,
                'dse_pageId': 2,
                'dse_operationName': 'retailUserLoginProc',
                'dse_errorPage': 'index.jsp',
                'dse_processorState': 'initial',
                'dse_nextEventName': 'start',
                'orderId': '',
                '_userNameEncode': username,
                '_userName': username,
                '_password': password,
                '_verifyCode': captcha_text
            }
            # Perform login
            login_post = session_requests.post(login_url + '/Request', payload)
            tree = html.fromstring(login_post.text)
            window_location = tree.xpath("//script/text()")[0]
            window_location = self.replace_all(window_location,
                                               {"window.location.href = '": "", "';": ""})
            redirect_url = str(home_url + window_location.strip())
            result = session_requests.get(redirect_url)
            tree = html.fromstring(result.content)
            username = tree.xpath("//p[@class='username']/text()")
            if len(username) > 0:
                token = self.get_token_from_string(str(result.content))
                session_requests.set_token(token)
                session_requests.set_changing_proxy(0)
                self.login_failed = 0
            else:
                self.login_failed = self.login_failed + 1
                if self.login_failed >= self.max_attempt_login:
                    if self.debug_mode == 'true':
                        self.log.log(
                            "Can not login Msb with " + str(self.max_attempt_login) + " attempts",
                            'error')
                    return 0
                return self.perform_login()
        else:
            session_requests.set_changing_proxy(0)
            if self.debug_mode == 'true':
                self.log.log('Login Msb successfully by using old session', 'debug')
        token = session_requests.get_token()
        if token is None:
            return 0
        # with open('msb.html', 'w') as f:
        #     f.write(str(result.content))
        self.update_transactions(session_requests, token)

    def update_transactions(self, session_requests, token):
        account_list_url = self.account_list_url
        payload = {
            'acctType': "'CA','SA','LN'",
            'status': "'ACTV','DORM','MATU'",
            'tokenNo': token,
            'lang': "vi_VN",
        }
        list_post = session_requests.post(account_list_url, payload)
        try:
            response = list_post.json()
        except:
            response = {'status': 401}
        if response['status'] == '200':
            accounts = response['data']
            for account in accounts:
                account_name = account['acctName']
                account_number = account['acctNo']
                account_balance = account['availableBalance']
                msb_account = MsbAccount(account_name, account_number, self.payment.get_id())
                msb_account.set_balance(account_balance)
                msb_account.update_account()
                account_info_url = self.account_info_url
                current_date = self.history.get_current_update('maritimebank')
                payload = {
                    'acctNo': msb_account.get_number(),
                    'page': 1,
                    'tokenNo': token,
                    'lang': "vi_VN",
                    'fromDate': current_date.rstrip('\r\n'),
                    'toDate': time.strftime("%Y-%m-%d")
                }
                account_post = session_requests.post(account_info_url, payload)
                response = account_post.json()
                if response['status'] == '200':
                    histories = response['data']['history']
                    for history in histories:
                        self.save_transaction(msb_account, history)
        self.log.update_log('Maritimebank', self.username)
        self.history.set_current_update('maritimebank', "%Y-%m-%d")
        self.log.log(str(self.total_transactions) + ' Msb transaction(s) created', 'message')

    def save_transaction(self, account, history):
        trading_date = self.convert_trading_date(history['transferDate'])
        trading_time = history['transferTime']
        description = history['remark']
        if description is None:
            description = 'None'
        account_id = account.get_account_id()
        balance = float(history['amount'])
        if history['dcSign'] == 'D':
            balance = -balance
        reference_number = self.code.generate_code(
            description + history['transferDate'])
        created_at = trading_date + ' ' + trading_time
        transaction = Transaction(account_id, reference_number, trading_date, balance, description, created_at)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def replace_all(self, text, conditions):
        for i, j in conditions.items():
            text = text.replace(i, j)
        return text

    def validate_captcha(self, captcha):
        if re.match("^[a-zA-Z0-9]{4}$", captcha):
            return 1
        return 0

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d/%m/%Y')
        return date.strftime('%Y-%m-%d')

    def get_token_from_string(self, string):
        token = re.search("\'[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}", string)
        return token[0].replace("'", "")
