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


class Techcombank:
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
                driver.get(login_url)
                # Get username input element
                element = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="signOnName"]'))
                )
                element.send_keys(username)
                # element.send_keys(Keys.RETURN)
                element = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="password"]'))
                )
                # Get password input element
                element.send_keys(password)
                # element.send_keys(Keys.RETURN)
                # Get submit button element
                element = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="btn_login"]'))
                )
                element.click()
                time.sleep(5)
                WebDriverWait(driver, 60).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//table[contains(@id,'datadisplay_AcctBalance')]"))
                )
                sub_accounts = driver.find_elements_by_xpath(
                    "//table[contains(@id,'datadisplay_AcctBalance')]//tr")
                for i in range(0, len(sub_accounts)):
                    WebDriverWait(driver, 60).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//table[contains(@id,'datadisplay_AcctBalance')]"))
                    )
                    WebDriverWait(driver, 60).until(
                        EC.visibility_of_element_located(
                            (By.XPATH,
                             "//table[contains(@id,'datadisplay_AcctBalance')]//a/img[contains(@src,'View.png')]"))
                    )
                    sub_account = driver.find_elements_by_xpath(
                        "//table[contains(@id,'datadisplay_AcctBalance')]//tr")[i]
                    search_btn = sub_account.find_element_by_xpath(".//a/img[contains(@src,'View.png')]")
                    search_btn.click()
                    # Update account information
                    try:
                        WebDriverWait(driver, 120).until(
                            EC.visibility_of_element_located(
                                (By.XPATH, "//table[@id='enqheader']//tr"))
                        )
                        info = driver.find_elements_by_xpath(
                            "//table[@id='enqheader']//tr")
                        number = info[2].find_elements_by_xpath("td")[1].text
                        try:
                            balance = float(info[2].find_elements_by_xpath("td")[3].text.replace(',', ''))
                        except:
                            balance = float(0)
                        name = info[3].find_elements_by_xpath("td")[1].text
                        account = self.update_account(name, number, balance, self.payment.get_id())
                        transactions = driver.find_elements_by_xpath(
                            "//table[starts-with(@id,'datadisplay_MainBody')]//tr")
                        count = 0
                        for row in transactions:
                            count += 1
                            # Get first 10 records
                            if count > 10:
                                break
                            columns = row.find_elements_by_xpath("td")
                            self.save_transaction(account, columns)
                        self.log.update_log('Techcombank', self.username)
                        self.log.log("Tcb " + self.payment.get_type() + self.payment.get_username() + ": " + str(
                            self.total_transactions) + ' transaction(s) created', 'message')
                        self.session.set_changing_proxy(0)
                    except:
                        self.log.log(
                            "Tcb " + self.payment.get_type() + self.payment.get_username() + ": " + "Cannot load transactions",
                            'error')
                        self.log.log(str(sys.exc_info()), 'error')
                        self.session.set_changing_proxy(1)
                    home_btn = driver.find_element_by_xpath(
                        '//a[@name="AI.QCK.HOME"]')
                    home_btn.click()
            except:
                exc_info = sys.exc_info()
                traceback.print_exception(*exc_info)
                self.log.log(str(sys.exc_info()), 'debug')

            driver.close()
            self.history.set_current_update('techcombank', "%d/%m/%Y")
            self.session.set_driver(None)

    def save_transaction(self, account, detail):
        trading_date = self.convert_trading_date(detail[0].text)
        if trading_date is None:
            return 0
        description = detail[1].text
        account_id = account.get_account_id()
        balance = float(detail[2].text.replace(',', ''))
        reference_number = self.convert_reference_number(description)
        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def convert_reference_number(self, description):
        description_array = description.split('/')
        reference_number = description_array[len(description_array) - 1].strip()
        return reference_number

    def convert_trading_date(self, trading_date):
        try:
            date = datetime.strptime(trading_date, '%d/%m/%Y')
            return date.strftime('%Y-%m-%d')
        except:
            return None

    def update_account(self, name, number, balance, payment_id):
        account = TechcombankAccount(name, number, payment_id)
        account.set_balance(balance)
        account.update_account()
        return account

    def get_techcombank_config(self):

        techcombank = self.config.get_section_config('Techcombank')
        return techcombank

    def is_debug(self):
        return self.debug_mode
