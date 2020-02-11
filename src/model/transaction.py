from db.connection import Connection
from .time import Time


class Transaction:
    def __init__(self, account_id, reference_number, trading_date, balance, description, created_at=None):
        self.account_id = account_id
        self.reference_number = reference_number
        self.trading_date = trading_date
        self.balance = balance
        self.description = description
        self.created_at = created_at
        self.connection = Connection()
        self.time = Time()

    def set_account_id(self, account_id):
        self.account_id = account_id

    def get_account_id(self):
        return self.account_id

    def set_reference_number(self, reference_number):
        self.reference_number = reference_number

    def get_reference_number(self):
        return str(self.reference_number)

    def set_trading_date(self, trading_date):
        self.trading_date = trading_date

    def get_trading_date(self):
        return self.trading_date

    def set_balance(self, balance):
        self.balance = balance

    def get_balance(self):
        return self.balance

    def set_description(self, description):
        self.description = description

    def get_description(self):
        return self.description

    def get_current_time(self):
        if self.created_at is None:
            return self.time.get_current_time()
        return self.created_at

    def save(self):
        connection = self.connection
        sql = "SELECT * FROM `transaction` where `reference_number`=%s and `account_id`=%s"
        transaction = connection.select(sql, (self.get_reference_number(), self.get_account_id()))
        if not transaction:
            # Create new transaction
            sql = "INSERT INTO `transaction` (`account_id`, `reference_number`, `trading_date`, `balance`, `description`,`created_at`) VALUES (%s, %s, %s, %s, %s,%s)"
            connection.query(sql, (
                self.get_account_id(), self.get_reference_number(), self.get_trading_date(), self.get_balance(),
                self.get_description(), self.get_current_time()))
            return 1
        return 0

    def get_status(self, reference_number):
        connection = self.connection
        sql = "SELECT `status` FROM `transaction` where `reference_number`=%s"
        transaction = connection.select(sql, reference_number)
        return transaction[0]
