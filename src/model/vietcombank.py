from .account import Account


class VietcombankAccount(Account):
    def __init__(self, name, number):
        vendor = 'Vietcombank'
        Account.__init__(self, name, number, vendor)
