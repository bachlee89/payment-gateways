import json
import sys
import requests
from lxml import html
from datetime import datetime
import time
import re
import os

sys.path.append('../../')
from model.acb import AcbAccount
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


class AcbEnterprise:
    def __init__(self, payment, session=None, proxy={}):
        self.session = session
        self.proxy = proxy
        self.config = Config()
        self.log = Log()
        self.username = payment.get_username()
        self.password = payment.get_password()
        acb = self.get_config()
        self.email_transport = EmailTransport()
        self.corp_url = acb['corp_url']
        self.captcha = CaptchaResolver()
        self.debug_mode = acb['debug_mode']
        self.total_transactions = 0
        self.history = History()
        self.code = GenerateCode()
        self.max_attempt_login = 20
        self.login_failed = 0
        self.session = session
        self.proxy = proxy
        self.payment = payment

    def get_config(self):
        config = self.config.get_section_config('AcbEnterprise')
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
                            (By.XPATH, "//a[contains(@href,'obk/login.jsp')]"))
                    )
                    online_banking.click()
                    time.sleep(5)
                    captcha = self.get_captcha(driver)
                    # Get username input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="UserName"]'))
                    )
                    element.send_keys(username, Keys.ARROW_DOWN)
                    # Get password input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="PassWord"]'))
                    )
                    driver.execute_script(
                        'arguments[0].style = ""; arguments[0].style.display = "block"; arguments[0].style.visibility = "visible";',
                        element)
                    element.send_keys(password)
                    # Get captcha input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="SecurityCode"]'))
                    )
                    driver.execute_script(
                        'arguments[0].style = ""; arguments[0].style.display = "block"; arguments[0].style.visibility = "visible";',
                        element)
                    element.send_keys(captcha)
                    time.sleep(2)
                    # Get submit button element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//a[@id="button-dangnhap"]'))
                    )
                    element.click()
                    time.sleep(3)
                    try:
                        # Update Account Information
                        WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located(
                                (By.XPATH, "//table[@id='table']//tr/td"))
                        )
                        account_info = driver.find_elements_by_xpath(
                            "//table[@id='table']//tr/td")
                        account_number = account_info[0].text.strip()
                        account_name = self.payment.get_username()
                        account_balance = float(
                            account_info[2].text.strip().replace(' ', '').replace('(VND)', '').replace('.', ''))
                        account = self.update_account(account_name, account_number, account_balance,
                                                      self.payment.get_id())
                    except:
                        driver.close()
                        return self.perform_login()

                    # click to transaction menu

                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[contains(@class,'acc_bold')]"))
                    )
                    element.click()
                    time.sleep(3)

                    view_link = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//input[contains(@onclick,'OutPrintByDate')]"))
                    )
                    view_link.click()
                    try:
                        window_after = driver.window_handles[1]
                        driver.switch_to_window(window_after)
                        WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located(
                                (By.XPATH, "//table[@id='table1']//tbody"))
                        )
                        transactions = driver.find_elements_by_xpath(
                            "//table[@id='table1']//tbody/tr[position() >= 0 and position() <= 10]")
                        for row in transactions:
                            columns = row.find_elements_by_xpath("td")
                            self.save_transaction(account, columns)
                        self.log.update_log('Acb', self.username)
                        self.log.log(
                            self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ": " + str(
                                self.total_transactions) + ' transaction(s) created', 'message')
                        self.session.set_changing_proxy(0)
                    except:
                        self.log.log(
                            self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ": " + "Cannot load transactions",
                            'error')
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        self.log.log(
                            self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ': ' + str(
                                sys.exc_info()), 'debug')
                        self.log.log(str(exc_type) + '-' + fname + '-' + str(exc_tb.tb_lineno), 'error')
                        self.session.set_changing_proxy(1)
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                self.log.log(
                    self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ': ' + str(
                        sys.exc_info()), 'debug')
                self.log.log(str(exc_type) + '-' + fname + '-' + str(exc_tb.tb_lineno), 'error')
                self.session.set_changing_proxy(1)
            driver.quit()
            self.history.set_current_update('acb_enterprise', "%d/%m/%Y")
            self.session.set_driver(None)

    def save_transaction(self, account, detail):
        if len(detail) < 4:
            return False
        trading_date = self.convert_trading_date(
            detail[0].text)
        reference_number = detail[1].text
        account_id = account.get_account_id()
        if detail[3].text.strip() is not '':
            balance = -float(
                detail[3].text.strip().replace('.', ''))
        else:
            balance = float(
                detail[4].text.strip().replace('.', ''))
        description = detail[2].text
        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def get_captcha(self, driver):
        img_data = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//img[@src='Captcha.jpg']"))
        )
        img_file = img_data.screenshot_as_png
        self.captcha.save_from_source(img_file, 'png')
        captcha_text = self.captcha.resolve(True)
        if re.match("^[a-zA-Z0-9]{5}$", captcha_text):
            return captcha_text
        driver.refresh()
        return self.get_captcha(driver)

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d-%m-%y')
        return date.strftime('%Y-%m-%d')

    def update_account(self, name, number, balance, payment_id):
        account = AcbAccount(name, number, payment_id)
        account.set_balance(balance)
        account.update_account()
        return account

    def is_debug(self):
        return self.debug_mode
