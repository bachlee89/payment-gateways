from .account import Account


class MsbAccount(Account):
    def __init__(self, name, number, payment_id):
        vendor = 'Maritimebank'
        Account.__init__(self, name, number, vendor, payment_id)
