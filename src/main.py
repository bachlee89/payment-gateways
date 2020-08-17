#!/usr/bin/env python3

from connector.http.vietcombank import Vietcombank
from connector.http.techcombank import Techcombank
from connector.http.vietcombank_enterprise import VietcombankEnterprise
from connector.http.klikbca_enterprise import KlikbcaEnterprise
from connector.http.msb import Msb
from model.config import Config
from model.log import Log
from model.thread.connector import ThreadConnector
from model.proxy import Proxy
from model.session import Session
from model.payment import Payment
import importlib
import sys


def run():
    payment = Payment()
    systemLog = Log()
    threads = []
    sessions = {}
    proxy = Proxy().random_proxy()
    payments = payment.get_payments()
    while 1:
        for p in payments:
            payment = payment.set_payment(p)
            name = payment.get_name()
            type = payment.get_type()
            if payment.get_status() == 0:
                continue
            connector_module = 'connector.http.' + name.lower()
            if type == 'enterprise':
                connector_module += '_enterprise'
            module = importlib.import_module(connector_module)
            class_ = getattr(module, name)
            sessions[name] = Session(proxy)
            connector = class_(payment, sessions[name], proxy)
            if sessions[name].is_changing_proxy() == 1:
                systemLog.log('Need to change ' + name + ' proxy!', 'debug')
                proxy = Proxy().random_proxy()
            thread_name = "Thread " + str(payment.get_id()) + " " + name + " " + type
            thread = ThreadConnector(thread_name.upper(), connector, 5)
            thread.start()
            threads.append(thread)
        for t in threads:
            t.join(60)


if __name__ == '__main__':
    run()
