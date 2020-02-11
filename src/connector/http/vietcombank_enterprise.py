import json
import sys
from lxml import html
from datetime import datetime
import time
import re

sys.path.append('../../')
from model.vietcombank import VietcombankAccount
from model.transaction import Transaction
from model.config import Config
from model.log import Log
from converter.captcha import CaptchaResolver
from model.email import EmailTransport


class VietcombankEnterprise:
    def __init__(self, name=None, session=None, proxy={}):
        self.config = Config()
        self.captcha = CaptchaResolver()
        self.log = Log()
        vietcombank = self.get_vietcombank_config(name)
        self.email_transport = EmailTransport()
        self.account_name = None
        self.home_url = vietcombank['home_url']
        self.login_url = vietcombank['login_url']
        self.dashboard_url = vietcombank['dashboard_url']
        self.username = vietcombank['username']
        self.password = vietcombank['password']
        self.debug_mode = vietcombank['debug_mode']
        self.total_transactions = 0
        self.max_attempt_login = 10
        self.max_validate_captcha = 20
        self.login_failed = 0
        self.captcha_failed = 0
        self.session = session
        self.proxy = proxy

    def is_logged(self):
        session_requests = self.session
        home_url = self.home_url
        tree = session_requests.get_tree()
        if tree is None:
            return 0
        try:
            left_menu = tree.xpath("//li[@class='hassub']/a/@href")
            list_account_url = home_url + left_menu[0]
            result = session_requests.get(list_account_url, dict(referer=list_account_url))
            tree = html.fromstring(result.content)
            tables = tree.xpath("//div[@id='pagecontents']/table//tr")
            if len(tables) > 0:
                return 1
            return 0
        except:
            return 0

    def is_debug(self):
        return self.debug_mode

    def perform_login(self):
        home_url = self.home_url
        login_url = self.login_url
        username = self.username
        password = self.password
        session_requests = self.session
        if self.is_logged() == 0:
            session_requests.init_session(self.proxy)
            session_requests.set_changing_proxy(1)
            # Get login csrf token
            result = session_requests.get(login_url)
            tree = html.fromstring(result.text)
            form_action = list(set(tree.xpath("//form[@id='LoginForm']/@action")))[0]
            form_action_url = home_url + form_action
            captcha_src = list(set(tree.xpath("//img[@id='captchaImage']/@src")))[0]
            captcha_guid1 = list(set(tree.xpath("//input[@name='captcha-guid1']/@value")))[0]
            img_data = session_requests.get(home_url + captcha_src).content
            self.captcha.save_from_source(img_data)
            captcha_text = self.captcha.resolve()
            captcha_text = captcha_text.replace(" ", "").upper()
            if self.validate_captcha(captcha_text) == 0:
                if self.captcha_failed < self.max_validate_captcha:
                    self.captcha_failed = self.captcha_failed + 1
                    return self.perform_login()
                else:
                    if self.debug_mode == 'true':
                        self.log.log('Can\'t validate captcha after ' + str(self.captcha_failed) + ' times', 'debug')
                    self.captcha_failed = 0
                    return 0
            self.captcha_failed = 0
            # Create payload
            payload = {
                "username": username,
                "pass": password,
                "captcha": captcha_text,
                "captcha-guid1": captcha_guid1,
                "source": ""
            }
            # Perform login
            login_post = session_requests.post(form_action_url, payload, dict(referer=login_url))
            # Scrape url
            tree = html.fromstring(login_post.content)
            error = tree.xpath("//div[@class='control mes_error']/span/text()")
            if error:
                self.login_failed = self.login_failed + 1
                if self.login_failed >= self.max_attempt_login:
                    if self.debug_mode == 'true':
                        self.log.log("Can not login with " + str(self.max_attempt_login) + " attempts", 'error')
                    return 0
                if self.debug_mode == 'true':
                    login_tree = html.fromstring(login_post.content)
                    error_message = login_tree.xpath("//div[@class='control mes_error']/span/text()")
                    self.log.log('Can\'t login. See details data bellow', 'debug')
                    self.log.log(json.dumps(payload), 'debug')
                    self.log.log(json.dumps(error_message), 'debug')
                return self.perform_login()
            if self.debug_mode == 'true':
                self.log.log(
                    'Login successfully after ' + str(self.login_failed + 1) + ' attempted. See detail bellow:',
                    'debug')
                self.log.log(json.dumps(payload), 'debug')
            self.login_failed = 0
            session_requests.set_changing_proxy(0)
            session_requests.set_tree(tree)
        else:
            session_requests.set_changing_proxy(0)
            if self.debug_mode == 'true':
                self.log.log('Login Vietcombank successfully by using old session', 'debug')
        tree = session_requests.get_tree()
        self.update_transactions(session_requests, tree)

    def get_vietcombank_config(self, name=None):
        if name is None:
            name = 'Vietcombank'
        vietcombank = self.config.get_section_config(name)
        return vietcombank

    def validate_captcha(self, captcha):
        if re.match("^[a-zA-Z0-9]{5}$", captcha):
            return 1
        return 0

    def update_transactions(self, session_requests, tree):
        home_url = self.home_url
        left_menu = tree.xpath("//li[@class='hassub']/a/@href")
        list_account_url = home_url + left_menu[0]
        result = session_requests.get(list_account_url, dict(referer=list_account_url))
        tree = html.fromstring(result.content)
        tables = tree.xpath("//div[@id='pagecontents']/table//tr")
        details = tables[0].xpath("//td/a/@href")
        # Process save transaction into database
        for i in range(len(details)):
            detail = details[i]
            detail_url = home_url + '/IBanking/Accounts/' + detail
            result = session_requests.get(detail_url, dict(referer=detail_url))
            tree = html.fromstring(result.content)
            account_info = tree.xpath("//table[@class='tbllisting hasborder']//tr/td[position()=2]/text()")
            account_name = account_info[0].strip()
            account_number = account_info[2].strip()
            account_balance = float(account_info[4].strip().replace(' VND', '').replace(',', ''))
            account = VietcombankAccount(account_name, account_number)
            account.set_balance(account_balance)
            account.update_account()
            form_action = tree.xpath("//form[@name='aspnetForm']/@action")[0]
            transaction_detail_url = home_url + '/IBanking/Accounts/' + form_action
            account_options = tree.xpath(
                "//select[@name='ctl00$Content$TransactionDetail$ListAccounts']//option")
            current_account_value = ''
            for option in account_options:
                if option.text_content() == account_number:
                    current_account_value = option.attrib['value']
                    break
            view_state = tree.xpath(
                "//input[@name='__VIEWSTATE']/@value")[0]
            view_state_generator = tree.xpath(
                "//input[@name='__VIEWSTATEGENERATOR']/@value")[0]
            view_state_encrypted = tree.xpath(
                "//input[@name='__VIEWSTATEENCRYPTED']/@value")[0]
            view_state_eventvalidation = tree.xpath(
                "//input[@name='__EVENTVALIDATION']/@value")[0]
            # Create payload
            payload = {
                "__VIEWSTATE": view_state,
                "__VIEWSTATEGENERATOR": view_state_generator,
                "__VIEWSTATEENCRYPTED": view_state_encrypted,
                "__EVENTVALIDATION": view_state_eventvalidation,
                "ctl00$Content$TransactionDetail$TxtFromDate": "",
                "ctl00$Content$TransactionDetail$TxtToDate": "",
                "ctl00$Content$TransactionDetail$ListAccounts": current_account_value,
                "ctl00$Content$TransactionDetail$TransByDate": "true",
                "ctl00$Content$TransactionDetail$ListMT940Type": "1"
            }
            self.save_transaction(account, session_requests, transaction_detail_url, payload)

        # Set processed date and log message
        self.set_current_update()
        self.log.update_log('Vietcombank', self.username)
        self.log.log(str(self.total_transactions) + ' Vietcombank transaction(s) created', 'message')

    def save_transaction(self, account, session_requests, url, payload):
        current_date = self.get_current_update()
        if len(current_date):
            payload["ctl00$Content$TransactionDetail$TxtFromDate"] = current_date
            payload["ctl00$Content$TransactionDetail$TxtToDate"] = time.strftime("%d/%m/%Y")
        trans_post = session_requests.post(url, payload, dict(referer=url))
        tree = html.fromstring(trans_post.content)
        transactions = tree.xpath(
            "//div[@id='ctl00_Content_TransactionDetail_Pn_TransDetailByDate']/table//tr[@valign='top']")
        total_transactions = 0
        for row in transactions:
            columns = row.xpath("td")
            detail = []
            for column in columns:
                value = column.text_content()
                detail.append(value.strip())
            account_id = account.get_account_id()
            trading_date = self.convert_trading_date(detail[0])
            reference_number = detail[1]
            if detail[3] == '':
                balance = float('-' + detail[2].replace(',', ''))
            else:
                balance = float(detail[3].replace(',', ''))
            description = detail[4]
            transaction = Transaction(account_id, reference_number, trading_date, balance, description)
            if transaction.save() == 1:
                total_transactions = total_transactions + 1
                self.email_transport.send_transaction_email(account, transaction)
        self.total_transactions = self.total_transactions + total_transactions

    def get_update_file(self):
        update_file = self.config.get_base_dir('tmp') + 'vietcombank_enterprise_update.txt'
        return update_file

    def get_current_update(self):
        path = self.get_update_file()
        with open(path, 'r') as content_file:
            current_update = content_file.read()
        return current_update

    def set_current_update(self):
        path = self.get_update_file()
        current_date = time.strftime("%d/%m/%Y")
        file = open(path, 'w')
        file.write(current_date)
        file.close()

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d/%m/%Y')
        return date.strftime('%Y-%m-%d')

    def split_array(self, arr, size):
        arrs = []
        while len(arr) > size:
            pice = arr[:size]
            arrs.append(pice)
            arr = arr[size:]
        arrs.append(arr)
        return arrs
