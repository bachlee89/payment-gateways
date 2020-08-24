from .account import Account


class KlikbcaAccount(Account):
    def __init__(self, name, number, payment_id):
        vendor = 'Klikbca'
        Account.__init__(self, name, number, vendor, payment_id)
