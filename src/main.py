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
import sys


def run():
    config = Config()
    payment = Payment()
    systemLog = Log()
    sections = config.get_sections()
    threads = []
    created_bca_session = created_vcb_session = created_msb_session = created_tcb_session = {}
    klikbca_session = vietcombank_session = tcb_session = msb_session = None
    proxy = msb_proxy = tcb_proxy = Proxy().random_proxy()
    bca_proxy = Proxy().random_proxy('ID')
    while 1:
        for section in sections:
            section_config = config.get_section_config(section)

            if section.startswith('Vietcombank'):
                if payment.check_status(section_config['username']) == 0:
                    print('Payment Vietcombank is disabled')
                    continue
                if section not in created_vcb_session:
                    vietcombank_session = Session(proxy)
                    created_vcb_session[section] = vietcombank_session
                else:
                    vietcombank_session = created_vcb_session[section]

                if section_config['type'] == 'personal':
                    vietcombank = Vietcombank(section, vietcombank_session, proxy)
                    thread = ThreadConnector("Thread-Vietcombank-Personal", vietcombank, 15)
                    thread.start()
                    threads.append(thread)
                elif section_config['type'] == 'enterprise':
                    for x in range(0, 1):
                        vietcombank = VietcombankEnterprise(section, vietcombank_session, proxy)
                        thread = ThreadConnector("Thread-Vietcombank-Enterprise", vietcombank, 5)
                        thread.start()
                        threads.append(thread)
                else:
                    systemLog.log("Type " + type + " is not supported", 'error')

            if section.startswith('Klikbca'):
                if payment.check_status(section_config['username']) == 0:
                    print('Payment Klikbca is disabled')
                    continue
                if section not in created_bca_session:
                    klikbca_session = Session(bca_proxy)
                    created_bca_session[section] = klikbca_session
                else:
                    klikbca_session = created_bca_session[section]
                if section_config['type'] == 'enterprise':
                    klikbca = KlikbcaEnterprise(section, klikbca_session, bca_proxy)
                    thread = ThreadConnector("Thread-Klikbca-Enterprise", klikbca, 5)
                    thread.start()
                    threads.append(thread)

            if section.startswith('Msb'):
                if payment.check_status(section_config['username']) == 0:
                    print('Payment Msb is disabled')
                    continue
                if section not in created_msb_session:
                    msb_session = Session(msb_proxy)
                    created_msb_session[section] = msb_session
                else:
                    msb_session = created_msb_session[section]
                if section_config['type'] == 'personal':
                    msb = Msb(section, msb_session, {})
                    thread = ThreadConnector("Thread-Msb-personal", msb, 5)
                    thread.start()

            if section.startswith('Techcombank'):
                if payment.check_status(section_config['username']) == 0:
                    print('Payment Techcombank is disabled')
                    continue
                if section not in created_tcb_session:
                    tcb_session = Session(tcb_proxy)
                    created_tcb_session[section] = tcb_session
                else:
                    tcb_session = created_tcb_session[section]
                if section_config['type'] == 'personal':
                    tcb = Techcombank(section, tcb_session, {})
                    thread = ThreadConnector("Thread-Tcb-personal", tcb, 5)
                    thread.start()
                    threads.append(thread)

        if vietcombank_session is not None and vietcombank_session.is_changing_proxy() == 1:
            systemLog.log('Need to change Vcb proxy!', 'debug')
            proxy = Proxy().random_proxy()
        if msb_session is not None and msb_session.is_changing_proxy() == 1:
            systemLog.log('Need to change Msb proxy!', 'debug')
            msb_proxy = Proxy().random_proxy()

        if tcb_session is not None and tcb_session.is_changing_proxy() == 1:
            systemLog.log('Need to change Tcb proxy!', 'debug')
            # tcb_proxy = Proxy().random_proxy()

        if klikbca_session is not None and klikbca_session.is_changing_proxy() == 1:
            systemLog.log('Need to change Bca proxy!', 'debug')
            bca_proxy = Proxy().random_proxy()

        for t in threads:
            t.join(60)


if __name__ == '__main__':
    run()
