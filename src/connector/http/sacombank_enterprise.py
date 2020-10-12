import json
import sys
import requests
from lxml import html
from datetime import datetime
import time
import re

sys.path.append('../../')
from model.vietcombank import VietcombankAccount
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
        username = self.username
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
                    # Checkbox
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
                    time.sleep(60)
                    # click to account menu
                    try:
                        account_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.XPATH,
                                 "//a[contains(@href,'TransactionDetail')]"))
                        )
                        account_link.click()
                        self.login_failed = 0
                        break
                    except:
                        self.login_failed += 1
                        if self.login_failed > self.max_attempt_login:
                            driver.close()
                            self.history.set_current_update('vietcombank_enterprise', "%d/%m/%Y")
                            self.session.set_driver(None)

                # Update account information
                try:
                    # driver.execute_script("window.scrollTo(0, 800);")
                    time.sleep(5)
                    search_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             '//input[@id="ctl00_Content_TransactionDetail_TransByDate"]'))
                    )
                    search_button.click()
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//form[@id='aspnetForm']"))
                    )
                    account_info = driver.find_elements_by_xpath(
                        "//table[@class='tbllisting hasborder']//tr/td[position()=2]")
                    account_name = account_info[0].text.strip()
                    account_number = account_info[2].text.strip()
                    account_balance = float(account_info[4].text.strip().replace(' VND', '').replace(',', ''))
                    account = self.update_account(account_name, account_number, account_balance, self.payment.get_id())
                    transactions = driver.find_elements_by_xpath(
                        "//div[@id='ctl00_Content_TransactionDetail_Pn_TransDetailByDate']")
                    for row in transactions:
                        columns = row.find_elements_by_xpath(".//tr[@valign='top']/td")
                        self.save_transaction(account, columns)
                    self.log.update_log('Techcombank', self.username)
                    self.log.log("Vcb " + self.payment.get_type() + self.payment.get_username() + ": " + str(
                        self.total_transactions) + ' transaction(s) created', 'message')
                    self.session.set_changing_proxy(0)
                except:
                    self.log.log(
                        "Vcb " + self.payment.get_type() + self.payment.get_username() + ": " + "Cannot load transactions",
                        'error')
                    self.log.log(str(sys.exc_info()), 'error')
                    self.session.set_changing_proxy(1)


            except:
                exc_info = sys.exc_info()
                traceback.print_exception(*exc_info)
                self.log.log(str(sys.exc_info()), 'debug')

            driver.close()
            self.history.set_current_update('vietcombank_enterprise', "%d/%m/%Y")
            self.session.set_driver(None)

    def save_transaction(self, account, detail):
        trading_date = self.convert_trading_date(
            detail[0].text)
        reference_number = detail[1].text.replace(
            'Số tham chiếu: ', '')
        account_id = account.get_account_id()

        if detail[2].text is not '':
            balance = -float(
                detail[2].text.replace(',', '').replace(
                    ' ', ''))
        else:
            balance = float(
                detail[3].text.replace(',', '').replace(
                    ' ', ''))

        description = detail[4].text

        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
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
        date = datetime.strptime(trading_date, '%Y-%m-%d')
        return date.strftime('%Y-%m-%d')

    def update_account(self, name, number, balance, payment_id):
        account = VietcombankAccount(name, number, payment_id)
        account.set_balance(balance)
        account.update_account()
        return account

    def is_debug(self):
        return self.debug_mode
