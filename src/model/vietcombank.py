from .account import Account


class VietcombankAccount(Account):
    def __init__(self, name, number, payment_id):
        vendor = 'Vietcombank'
        Account.__init__(self, name, number, vendor, payment_id)
