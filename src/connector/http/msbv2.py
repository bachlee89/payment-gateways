import json
import sys
import requests
from lxml import html
from datetime import datetime
import time
import re

sys.path.append('../../')
from model.msb import MsbAccount
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
from converter.captcha import CaptchaResolver
from model.code import GenerateCode
from model.email import EmailTransport
import traceback
from model.history import History


class Msb:
    def __init__(self, name=None, session=None, proxy={}):
        self.session = session
        self.proxy = proxy
        self.config = Config()
        self.log = Log()
        self.captcha = CaptchaResolver()
        section_config = self.get_section_config(name)
        self.email_transport = EmailTransport()
        self.home_url = section_config['home_url']
        self.login_url = section_config['login_url']
        self.username = section_config['username']
        self.password = section_config['password']
        self.debug_mode = section_config['debug_mode']
        self.total_transactions = 0
        self.max_attempt_login = 10
        self.max_validate_captcha = 10
        self.login_failed = 0
        self.captcha_failed = 0
        self.history = History()
        self.code = GenerateCode()

    def is_debug(self):
        return self.debug_mode

    def get_section_config(self, name=None):
        if name is None:
            name = 'Msb'
        section_config = self.config.get_section_config(name)
        return section_config

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
                driver = selenium.get_chrome_driver(self.proxy)
                self.session.set_last_driver('Chrome')

            self.session.set_driver(driver)
            try:
                driver.get(login_url)
                # Get username input element
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="_userName"]'))
                )
                element.send_keys(username)

                # Get password input element
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="_passwordS"]'))
                )

                element.send_keys(password)

                captcha = self.get_captcha(driver)
                print(captcha)
                exit(111111)
                # Get captcha input element
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@name="_verifyCode"]'))
                )
                element.send_keys(captcha)

                # element.send_keys(Keys.RETURN)
                # Get submit button element
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//button[@id="loginBtn"]'))
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
                        current_date = self.history.get_current_update('techcombank')
                        from_date = driver.find_elements_by_xpath(
                            "//input[@id='fieldName:START.DATE']")[0]
                        from_date.send_keys(current_date, Keys.ENTER)
                        time.sleep(5)
                        to_date = driver.find_elements_by_xpath(
                            "//input[@id='fieldName:END.DATE']")[0]
                        to_date.send_keys(current_date)
                        time.sleep(5)
                        button = driver.find_elements_by_xpath(
                            '//a[@title="Xem giao dịch"]')[1]
                        button.click()
                        time.sleep(5)
                        button = driver.find_elements_by_xpath(
                            '//a[@title="Xem giao dịch"]')[1]
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

    def get_captcha(self, driver):
        img_data = driver.find_element_by_id('safecode').screenshot_as_png
        self.captcha.save_from_source(img_data)
        captcha_text = self.captcha.resolve(True)
        if re.match("^[a-zA-Z0-9]{4}$", captcha_text):
            return captcha_text
        return self.get_captcha(driver)
