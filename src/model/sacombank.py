from .account import Account


class SacombankAccount(Account):
    def __init__(self, name, number, payment_id):
        vendor = 'Sacombank'
        Account.__init__(self, name, number, vendor, payment_id)
