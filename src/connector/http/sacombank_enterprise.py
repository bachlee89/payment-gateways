import json
import sys
import requests
from lxml import html
from datetime import datetime
import time
import re
import os
sys.path.append('../../')
from model.sacombank import SacombankAccount
from model.transaction import Transaction
from model.config import Config
from model.log import Log
from helper.file import File
from model.selenium import Selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import pickle
from model.code import GenerateCode
from model.email import EmailTransport
import traceback
from model.history import History
from converter.captcha import CaptchaResolver


class SacombankEnterprise:
    def __init__(self, payment, session=None, proxy={}):
        self.session = session
        self.proxy = proxy
        self.config = Config()
        self.log = Log()
        self.username = payment.get_username()
        self.password = payment.get_password()
        sacombank = self.get_config()
        self.email_transport = EmailTransport()
        self.corp_url = sacombank['corp_url']
        self.captcha = CaptchaResolver()
        self.debug_mode = sacombank['debug_mode']
        self.total_transactions = 0
        self.history = History()
        self.code = GenerateCode()
        self.max_attempt_login = 20
        self.login_failed = 0
        self.session = session
        self.proxy = proxy
        self.payment = payment

    def get_config(self):
        config = self.config.get_section_config('SacombankEnterprise')
        return config

    def perform_login(self):
        corp_url = self.corp_url
        # username = self.username
        password = self.password
        selenium = Selenium()
        if self.session.get_driver() is None:
            if self.session.get_last_driver() is None or self.session.get_last_driver() is 'Firefox':
                driver = selenium.get_firefox_driver(self.proxy)
                self.session.set_last_driver('Chrome')
            else:
                driver = selenium.get_firefox_driver(self.proxy)
                self.session.set_last_driver('Firefox')

            self.session.set_driver(driver)

            try:
                while True:
                    driver.get(corp_url)
                    online_banking = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[contains(@class,'btn-ebanking')]"))
                    )
                    online_banking.click()
                    time.sleep(5)
                    captcha = self.get_captcha(driver)
                    # Get username input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="AuthenticationFG.USER_PRINCIPAL"]'))
                    )
                    element.send_keys('14890491.STARLIGHT', Keys.ARROW_DOWN)
                    # Get captcha input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="AuthenticationFG.VERIFICATION_CODE"]'))
                    )
                    element.send_keys(captcha)
                    # element.send_keys(Keys.RETURN)
                    # Get submit button element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@id="STU_VALIDATE_CREDENTIALS"]'))
                    )
                    element.click()
                    time.sleep(5)
                    try:
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, '//span[@id="LoginHDisplay.Ra4.C1"]'))
                        )
                        element.click()
                    except:
                        driver.close()
                        return self.perform_login()
                    # Get password input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="AuthenticationFG.ACCESS_CODE"]'))
                    )
                    element.send_keys(password)
                    element.send_keys(Keys.RETURN)
                    time.sleep(5)
                    # Update Account Information
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//table[@id='HWListTable10072682']//tr/td"))
                    )
                    account_info = driver.find_elements_by_xpath(
                        "//table[@id='HWListTable10072682']//tr/td")
                    account_number = account_info[0].text.strip()
                    account_name = self.payment.get_username()
                    account_balance = float(
                        account_info[2].text.strip().replace('\n', '').replace('VND', '').replace('.', ''))
                    account = self.update_account(account_name, account_number, account_balance, self.payment.get_id())
                    # click to transaction menu
                    action_link = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//a[contains(@name,'HREF_Giao_dch')]"))
                    )
                    hover_action = ActionChains(driver).move_to_element(action_link)
                    hover_action.perform()
                    trans_link = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//a[contains(@id,'ID_IL_CTXNS_30')]"))
                    )
                    hover_trans = ActionChains(driver).move_to_element(trans_link)
                    hover_trans.perform()
                    all_trans = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//a[contains(@id,'Qun-l-giao-dch_Tt-c-giao-dch')]"))
                    )
                    all_trans.click()
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located(
                                (By.XPATH, "//table[@id='AllTransactionListingCorp']//tbody"))
                        )
                        transactions = driver.find_elements_by_xpath(
                            "//table[@id='AllTransactionListingCorp']//tbody[position() >= 0 and position() <= 10]")
                        for row in transactions:
                            columns = row.find_elements_by_xpath(".//tr/td")
                            self.save_transaction(account, columns, driver)
                        self.log.update_log('Sacombank', self.username)
                        self.log.log("Scb " + self.payment.get_type() + self.payment.get_username() + ": " + str(
                            self.total_transactions) + ' transaction(s) created', 'message')
                        self.session.set_changing_proxy(0)
                    except:
                        self.log.log(
                            self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ": " + "Cannot load transactions",
                            'error')
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self.log.log(str(exc_type) + '-' + fname + '-' + str(exc_tb.tb_lineno), 'error')
                        self.session.set_changing_proxy(1)
            except:
                exc_info = sys.exc_info()
                traceback.print_exception(*exc_info)
                self.log.log(
                    self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ': ' + str(
                        sys.exc_info()), 'debug')

            driver.close()
            self.history.set_current_update('sacombank_enterprise', "%d/%m/%Y")
            self.session.set_driver(None)

    def save_transaction(self, account, detail, driver):
        trading_date = self.convert_trading_date(
            detail[5].text)
        reference_number = detail[0].text
        account_id = account.get_account_id()
        balance = float(
            detail[8].text.strip().replace('\n', '').replace('VND', '').replace('.', ''))

        tran_type = detail[2].text
        if tran_type == 'Thanh toán' or type == 'Chuyển khoản':
            balance = -balance
        detail[0].click()
        time.sleep(5)
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[@id='PageConfigurationMaster_CVTXNW__1:HREF_ViewTxnDetailsFG.ENT_REMARKS']"))
        )
        description = driver.find_element_by_xpath(
            "//span[@id='PageConfigurationMaster_CVTXNW__1:HREF_ViewTxnDetailsFG.ENT_REMARKS']").text
        close_btn = driver.find_element_by_xpath(
            "//button[@id='closeIcon']")
        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        close_btn.click()
        time.sleep(5)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def get_captcha(self, driver):
        img_data = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//img[@id='IMAGECAPTCHA']"))
        )
        img_file = img_data.screenshot_as_png
        self.captcha.save_from_source(img_file, 'png')
        captcha_text = self.captcha.resolve(True)
        if re.match("^[0-9]{4}$", captcha_text):
            return captcha_text
        reload_captcha = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//img[@id='TEXTIMAGE']"))
        )
        reload_captcha.click()
        return self.get_captcha(driver)

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d-%m-%Y')
        return date.strftime('%Y-%m-%d')

    def update_account(self, name, number, balance, payment_id):
        account = SacombankAccount(name, number, payment_id)
        account.set_balance(balance)
        account.update_account()
        return account

    def is_debug(self):
        return self.debug_mode
