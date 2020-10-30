from .account import Account


class AcbAccount(Account):
    def __init__(self, name, number, payment_id):
        vendor = 'Acb'
        Account.__init__(self, name, number, vendor, payment_id)
