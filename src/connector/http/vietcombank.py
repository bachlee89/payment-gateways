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


class Vietcombank:
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
        self.max_attempt_login = 20
        self.login_failed = 0
        self.session = session
        self.proxy = proxy
        self.payment = payment

    def get_vietcombank_config(self):
        vietcombank = self.config.get_section_config('Vietcombank')
        return vietcombank

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
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="username"]'))
                )
                element.send_keys(username)
                # Get password input element
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="pass"]'))
                )
                element.send_keys(password)
                while True:
                    captcha = self.get_captcha(driver)
                    # Get captcha input element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//input[@name="captcha"]'))
                    )
                    element.send_keys(captcha)
                    # element.send_keys(Keys.RETURN)
                    # Get submit button element
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//button[@id="btnLogin"]'))
                    )
                    element.click()
                    time.sleep(5)
                    # click to account menu
                    try:
                        account_link = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.XPATH,
                                 "//a[contains(@class,'has-link-arrow tk')]//div[contains(@class,'item-link-arrow')]"))
                        )
                        account_link.click()
                        time.sleep(5)
                        self.login_failed = 0
                        break
                    except:
                        self.login_failed += 1
                        if self.login_failed > self.max_attempt_login:
                            driver.close()
                            self.history.set_current_update('vietcombank', "%d/%m/%Y")
                            self.session.set_driver(None)

                # Update account information
                try:
                    driver.execute_script("window.scrollTo(0, 800);")
                    time.sleep(5)
                    search_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             "//a[contains(@class,'ubtn ubg-primary ubtn-md ripple')]/span[contains(text(),'Tìm kiếm')]"))
                    )
                    search_button.click()
                    WebDriverWait(driver, 15).until(
                        EC.visibility_of_element_located(
                            (By.XPATH, "//form[@id='ChiTietTaiKhoan']"))
                    )
                    info = driver.find_element_by_xpath(
                        "//div[@class='list-info']")
                    number = info.find_element_by_xpath("//select/option").get_attribute('value')
                    name = info.find_elements_by_xpath(
                        "//div[contains(@class,'list-info-txt-main')]")[1].text
                    balance = float(info.find_elements_by_xpath(
                        "//div[contains(@class,'list-info-txt-main')]")[2].text.replace(
                        ',', '').replace(' VND', ''))
                    account = self.update_account(name, number, balance, self.payment.get_id())
                    transactions = driver.find_elements_by_xpath(
                        "//div[@id='toanbo']//div[contains(@class,'list-info-item')]")
                    for row in transactions:
                        columns = row.find_elements_by_xpath(".//div[contains(@class,'td-xs')]")
                        self.save_transaction(account, columns)
                    self.log.update_log('Vietcombank', self.username)
                    self.log.log(str(self.total_transactions) + ' Vcb transaction(s) created', 'message')
                    self.session.set_changing_proxy(0)
                except:
                    self.log.log("Vietcombank: Cannot load transactions", 'error')
                    self.log.log(str(sys.exc_info()), 'error')
                    self.session.set_changing_proxy(1)


            except:
                exc_info = sys.exc_info()
                traceback.print_exception(*exc_info)
                self.log.log(str(sys.exc_info()), 'debug')

            driver.close()
            self.history.set_current_update('vietcombank', "%d/%m/%Y")
            self.session.set_driver(None)

    def save_transaction(self, account, detail):
        trading_date = self.convert_trading_date(
            detail[0].find_element_by_xpath("div[contains(@class,'list-info-txt-sub')]").text)
        description = detail[0].find_element_by_xpath("div[contains(@class,'list-info-txt-main')]").text
        account_id = account.get_account_id()
        reference_number = detail[1].find_element_by_xpath("div[contains(@class,'list-info-txt-sub')]").text.replace(
            'Số tham chiếu: ', '')
        balance = float(
            detail[1].find_element_by_xpath("div[contains(@class,'list-info-txt-main')]").text.replace(',', '').replace(
                ' ', ''))
        transaction = Transaction(account_id, reference_number, trading_date, balance, description)
        print(reference_number)
        if transaction.save() == 1:
            self.total_transactions = self.total_transactions + 1
            self.email_transport.send_transaction_email(account, transaction)

    def get_captcha(self, driver):
        img_data = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'captcha')]//img"))
        )
        img_file = img_data.screenshot_as_png
        self.captcha.save_from_source(img_file, 'png')
        captcha_text = self.captcha.resolve(True)
        if re.match("^[a-zA-Z0-9]{5}$", captcha_text):
            return captcha_text

        ic_reload = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//img[contains(@src,'ic_reload')]"))
        )
        ic_reload.click()
        return self.get_captcha(driver)

    def convert_trading_date(self, trading_date):
        date = datetime.strptime(trading_date, '%d/%m/%Y')
        return date.strftime('%Y-%m-%d')

    def update_account(self, name, number, balance, payment_id):
        account = VietcombankAccount(name, number, payment_id)
        account.set_balance(balance)
        account.update_account()
        return account

    def get_config(self, name=None):
        if name is None:
            name = 'Vietcombank'
        vietcombank = self.config.get_section_config(name)
        return vietcombank

    def is_debug(self):
        return self.debug_mode
