from .account import Account


class KlikbcaAccount(Account):
    def __init__(self, name, number):
        vendor = 'Klikbca'
        Account.__init__(self, name, number, vendor)
