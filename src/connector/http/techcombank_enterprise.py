import json
import sys
import requests
from lxml import html
from datetime import datetime
import time
import re

sys.path.append('../../')
from model.techcombank import TechcombankAccount
from model.transaction import Transaction
from model.config import Config
from model.log import Log
from helper.file import File
from model.selenium import Selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pickle
from model.code import GenerateCode
from model.email import EmailTransport
import traceback
from model.history import History


class TechcombankEnterprise:
    def __init__(self, payment, session=None, proxy={}):
        self.session = session
        self.proxy = proxy
        self.payment = payment
        self.config = Config()
        self.log = Log()
        techcombank = self.get_techcombank_config()
        self.email_transport = EmailTransport()
        self.login_url = techcombank['login_url']
        self.username = payment.get_username()
        self.password = payment.get_password()
        self.debug_mode = techcombank['debug_mode']
        self.total_transactions = 0
        self.history = History()
        self.code = GenerateCode()
        self.max_attempt_login = 20
        self.login_failed = 0

    def perform_login(self):
        login_url = self.login_url
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
                while 1:
                    driver.get(login_url)
                    window_before = driver.window_handles[0]
                    # Get username input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="signOnName"]'))
                    )
                    element.send_keys(username)
                    time.sleep(2)
                    # element.send_keys(Keys.RETURN)
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="password"]'))
                    )
                    # Get password input element
                    element.send_keys(password)
                    time.sleep(2)
                    # element.send_keys(Keys.RETURN)
                    # Get submit button element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@type="submit"]'))
                    )
                    element.click()
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located(
                                (By.XPATH, "//div[contains(@id,'pane__FRAME')]"))
                        )
                        self.login_failed = 0
                        break
                    except:
                        self.login_failed += 1
                        if self.login_failed > self.max_attempt_login:
                            driver.close()
                            self.history.set_current_update('techcombank_enterprise', "%d/%m/%Y")
                            self.session.set_driver(None)

                # Update account information
                try:
                    search = WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//img[contains(@src,'drilldown/View.png')]"))
                    )
                    info = driver.find_elements_by_xpath(
                        "//table[contains(@id,'datadisplay_ACCOUNT')]//tr/td")
                    number = info[0].text.split('-')[0].strip()
                    name = info[1].text
                    balance = float(info[3].text.replace(',', ''))
                    account = self.update_account(name, number, balance, self.payment.get_id())
                    search.click()
                    window_after = driver.window_handles[1]
                    driver.switch_to_window(window_after)
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//table[contains(@id,'datadisplay_DATA')]"))
                    )
                    transactions = driver.find_elements_by_xpath(
                        "//table[contains(@id,'datadisplay_DATA')]//tr")
                    for row in transactions:
                        columns = row.find_elements_by_xpath("td")
                        self.save_transaction(account, columns)
                    self.log.update_log('Techcombank', self.username)
                    self.log.log(
                        self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ": " + str(
                            self.total_transactions) + ' transaction(s) created', 'message')
                    self.session.set_changing_proxy(0)
                except:
                    self.log.log(
                        self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ": " + "Cannot load transactions",
                        'error')
                    self.log.log(str(sys.exc_info()), 'error')
                    self.session.set_changing_proxy(1)

            except:
                exc_info = sys.exc_info()
                traceback.print_exception(*exc_info)
                self.log.log(str(sys.exc_info()), 'debug')
            driver.quit()
            self.history.set_current_update('techcombank_enterprise', "%d/%m/%Y")
            self.session.set_driver(None)

    def save_transaction(self, account, detail):
        trading_date = self.convert_trading_date(detail[0].text)
        reference_number = detail[1].text
        description = detail[3].text
        account_id = account.get_account_id()

        if detail[4].text is not '':
            balance = float(
                detail[4].text.replace(',', '').replace(
                    ' ', ''))
        else:
            balance = float(
                detail[5].text.replace(',', '').replace(
                    ' ', ''))
        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d/%m/%Y')
        return date.strftime('%Y-%m-%d')

    def update_account(self, name, number, balance, payment_id):
        account = TechcombankAccount(name, number, payment_id)
        account.set_balance(balance)
        account.update_account()
        return account

    def get_techcombank_config(self):

        techcombank = self.config.get_section_config('TechcombankEnterprise')
        return techcombank

    def is_debug(self):
        return self.debug_mode
