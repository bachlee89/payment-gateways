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
import os


class VietcombankEnterprise:
    def __init__(self, payment, session=None, proxy={}):
        self.session = session
        self.proxy = proxy
        self.config = Config()
        self.log = Log()
        self.username = payment.get_username()
        self.password = payment.get_password()
        vietcombank = self.get_vietcombank_config()
        self.email_transport = EmailTransport()
        self.login_url = vietcombank['login_url']
        self.captcha = CaptchaResolver()
        self.debug_mode = vietcombank['debug_mode']
        self.total_transactions = 0
        self.history = History()
        self.code = GenerateCode()
        self.max_attempt_login = 5
        self.login_failed = 0
        self.session = session
        self.proxy = proxy
        self.payment = payment

    def get_vietcombank_config(self):
        vietcombank = self.config.get_section_config('VietcombankEnterprise')
        return vietcombank

    def perform_login(self):
        login_url = self.login_url
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
                if self.solve_captcha(driver) is False:
                    driver.close()
                    return False
                time.sleep(5)
                # Update account information
                try:
                    # driver.execute_script("window.scrollTo(0, 800);")
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//tbody[@id='dstkdd-tbody']"))
                    )
                    account_info = driver.find_elements_by_xpath(
                        "//tbody[@id='dstkdd-tbody']/tr/td")
                    account_name = self.payment.get_username()
                    account_number = account_info[0].text.strip()
                    account_balance = float(account_info[2].text.strip().replace(' VND', '').replace(',', ''))
                    account = self.update_account(account_name, account_number, account_balance, self.payment.get_id())
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[contains(@href,'/IbankingCorp/Accounts/TransactionDetail.aspx')]"))
                    )
                    reference_links = driver.find_elements_by_xpath(
                        "//a[contains(@href,'/IbankingCorp/Accounts/TransactionDetail.aspx')]")
                    reference_links[2].click()
                    view_link = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[contains(@id,'bdsdList-tab')]"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView();", view_link)
                    time.sleep(5)
                    view_link.click()
                    tran_by_date = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//a[contains(@id,'TransByDate')]"))
                    )
                    tran_by_date.click()
                    time.sleep(5)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//table[@id='tbTranHis']"))
                    )
                    trans_foot = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[@id='tbTranHis-footer']"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView();", trans_foot)
                    transactions = driver.find_elements_by_xpath(
                        "//table[@id='tbTranHis']//tbody/tr[position() >= 0 and position() <= 50]")
                    for row in transactions:
                        columns = row.find_elements_by_xpath("td")
                        self.save_transaction(account, columns)
                    self.log.update_log('Vietcombank', self.username)
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
                    self.log.log(str(exc_type) + '-' + fname + '-' + str(exc_tb.tb_lineno), 'error')
                    self.session.set_changing_proxy(1)


            except:
                exc_info = sys.exc_info()
                traceback.print_exception(*exc_info)
                self.log.log(
                    self.payment.get_name() + '-' + self.payment.get_type() + '-' + self.payment.get_username() + ': ' + str(
                        sys.exc_info()), 'debug')
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
                    ' ', '').replace('VND', ''))
        else:
            balance = float(
                detail[3].text.replace(',', '').replace(
                    ' ', '').replace('VND', ''))

        description = detail[4].text

        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def solve_captcha(self, driver):
        img_data = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//img[@id='ctl00_Content_Login_Captcha_Captcha']"))
        )
        img_file = img_data.screenshot_as_png
        self.captcha.save_from_source(img_file, 'png')
        captcha_text = self.captcha.resolve(True)
        if re.match("^[a-zA-Z0-9]{6}$", captcha_text):
            captcha = captcha_text
            username = self.username
            password = self.password
            # Get username input element
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@name="ctl00$Content$Login$TenTC"]'))
            )
            element.send_keys(username)
            # Get password input element
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@name="ctl00$Content$Login$MatKH"]'))
            )
            element.send_keys(password)
            # Get captcha input element
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@name="ctl00$Content$Login$ImgStr"]'))
            )
            element.send_keys(captcha)
            # element.send_keys(Keys.RETURN)
            # Get submit button element
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//input[@id="ctl00_Content_Login_LoginBtn"]'))
            )
            element.click()
            # click to account menu
            try:
                list_account = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH,
                         '//a[@id="ctl00_QuickNavigation_NaviRepeater_ctl01_NaviLink"]'))
                )
                time.sleep(5)
                list_account.click()
                self.login_failed = 0
                return True
            except:
                self.login_failed += 1
                if self.login_failed > self.max_attempt_login:
                    self.history.set_current_update('vietcombank_enterprise', "%d/%m/%Y")
                    self.session.set_driver(None)
                    return False
                driver.back()
                return self.solve_captcha(driver)
        driver.refresh()
        return self.solve_captcha(driver)

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%Y-%m-%d')
        return date.strftime('%Y-%m-%d')

    def update_account(self, name, number, balance, payment_id):
        account = VietcombankAccount(name, number, payment_id)
        account.set_balance(balance)
        account.update_account()
        return account

    def get_config(self, name=None):
        if name is None:
            name = 'Vietcombank'
        techcombank = self.config.get_section_config(name)
        return techcombank

    def is_debug(self):
        return self.debug_mode
