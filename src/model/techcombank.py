from .account import Account


class TechcombankAccount(Account):
    def __init__(self, name, number):
        vendor = 'Techcombank'
        Account.__init__(self, name, number, vendor)
