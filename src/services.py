#!/usr/bin/env python3

from model.config import Config
from model.payment import Payment
import sys


def setup(argv):
    config = Config()
    payment = Payment()
    payment.clean()
    sections = config.get_sections()
    for section in sections:
        section_config = config.get_section_config(section)
        if section.startswith('Vietcombank') \
                or section.startswith('Msb') \
                or section.startswith('Techcombank') \
                or section.startswith('Klikbca'):
            payment.set_name(section)
            payment.set_username(section_config['username'])
            payment.save()


def remove(argv):
    payment = Payment()
    payment.clean()


def status(argv):
    config = Config()
    payment = Payment()
    sections = config.get_sections()
    enabled_payments = []
    disabled_payments = []
    for section in sections:
        if section.startswith('Vietcombank') or section.startswith('Msb') or section.startswith('Klikbca'):
            section_config = config.get_section_config(section)
            status = payment.check_status(section_config['username'])
            if status == 0:
                disabled_payments.append(section)
            else:
                enabled_payments.append(section)
    print('List enabled payments:')
    for payment_str in enabled_payments:
        print(payment_str)
    print('List disabled payments:')
    for payment_str in disabled_payments:
        print(payment_str)


def payment(argv):
    name = argv[0]
    status = argv[1]
    payment = Payment()
    payment.set_name(name)
    payment.set_status(status)
    payment.update_status()


def run():
    argv = sys.argv
    command = argv[1]
    for i in range(0, 2):
        argv.remove(argv[0])
    switcher = {
        'setup': setup,
        'remove': remove,
        'payment': payment,
        'status': status
    }
    func = switcher.get(command, "nothing")
    if func is not "nothing":
        # Execute the function
        return func(argv)
    else:
        print('Incorrect command line!')


if __name__ == '__main__':
    run()
