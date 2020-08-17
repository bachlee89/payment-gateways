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
            if self.session.get_last_driver() is None or self.session.get_last_driver() is 'Chrome':
                driver = selenium.get_firefox_driver(self.proxy)
                self.session.set_last_driver('Firefox')
            else:
                driver = selenium.get_firefox_driver(self.proxy)
                self.session.set_last_driver('Firefox')

            self.session.set_driver(driver)

            try:
                driver.get(login_url)
                # Get username input element
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="signOnName"]'))
                )
                element.send_keys(username)
                # element.send_keys(Keys.RETURN)
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="password"]'))
                )
                # Get password input element
                element.send_keys(password)
                # element.send_keys(Keys.RETURN)
                # Get submit button element
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="btn_login"]'))
                )
                element.click()
                # click to account menu
                time.sleep(5)
                account_link = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, '//a[@name="AI.QCK.ACCOUNT"]'))
                )
                retry_account = 0

                while retry_account < 3:
                    try:
                        account_link.click()
                        # Click to view last 10 transactions
                        time.sleep(5)
                        # current_date = self.history.get_current_update('techcombank')
                        # from_date = driver.find_elements_by_xpath(
                        #     "//input[@id='fieldName:START.DATE']")[0]
                        # from_date.send_keys(current_date, Keys.ENTER)
                        # time.sleep(5)
                        # to_date = driver.find_elements_by_xpath(
                        #     "//input[@id='fieldName:END.DATE']")[0]
                        # to_date.send_keys(current_date)
                        # time.sleep(5)
                        # button = driver.find_elements_by_xpath(
                        #     '//a[@title="Xem giao dịch"]')[1]
                        # button.click()
                        # time.sleep(5)
                        button = driver.find_elements_by_xpath(
                            '//a[@title="Xem giao dịch"]')[0]
                        button.click()
                        break
                    except:
                        self.log.log("Techcombank: Re-click to account", 'debug')
                        self.log.log(str(sys.exc_info()), 'debug')
                        retry_account = retry_account + 1

                # Update account information
                try:
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//table[@id='enqheader']//tr[position()>1 and position()<4]"))
                    )
                    info = driver.find_elements_by_xpath(
                        "//table[@id='enqheader']//tr[position()>1 and position()<4]")
                    number = info[0].find_elements_by_xpath("td")[1].text
                    balance = float(info[0].find_elements_by_xpath("td")[3].text.replace(',', ''))
                    name = info[1].find_elements_by_xpath("td")[1].text
                    account = self.update_account(name, number, balance)
                    transactions = driver.find_elements_by_xpath(
                        "//table[starts-with(@id,'datadisplay_MainBody')]//tr")
                    for row in transactions:
                        columns = row.find_elements_by_xpath("td")
                        self.save_transaction(account, columns)
                    self.log.update_log('Techcombank', self.username)
                    self.log.log(str(self.total_transactions) + ' Tcb transaction(s) created', 'message')
                    self.session.set_changing_proxy(0)
                except:
                    self.log.log("Techcombank: Cannot load transactions", 'error')
                    self.log.log(str(sys.exc_info()), 'error')
                    self.session.set_changing_proxy(1)


            except:
                exc_info = sys.exc_info()
                traceback.print_exception(*exc_info)
                self.log.log(str(sys.exc_info()), 'debug')

            driver.close()
            self.history.set_current_update('techcombank', "%d/%m/%Y")
            self.session.set_driver(None)

    def save_transaction(self, account, detail):
        trading_date = self.convert_trading_date(detail[0].text)
        description = detail[1].text
        account_id = account.get_account_id()
        balance = float(detail[2].text.replace(',', ''))
        reference_number = self.code.generate_code(description)
        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d/%m/%Y')
        return date.strftime('%Y-%m-%d')

    def update_account(self, name, number, balance):
        account = TechcombankAccount(name, number)
        account.set_balance(balance)
        account.update_account()
        return account

    def get_techcombank_config(self):

        techcombank = self.config.get_section_config('Techcombank')
        return techcombank

    def is_debug(self):
        return self.debug_mode
