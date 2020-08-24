from .account import Account


class TechcombankAccount(Account):
    def __init__(self, name, number, payment_id):
        vendor = 'Techcombank'
        Account.__init__(self, name, number, vendor, payment_id)
