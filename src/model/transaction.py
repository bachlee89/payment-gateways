from db.connection import Connection
from .time import Time
from .user import User
import uuid
import sys


class Transaction:
    def __init__(self, account_id, reference_number, trading_date, balance, description, created_at=None):
        self.account_id = account_id
        self.reference_number = reference_number
        self.trading_date = trading_date
        self.balance = balance
        self.description = description
        self.created_at = created_at
        self.connection = Connection()
        self.user = User()
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
        vendor = self.get_account_vendor(self, self.get_account_id)
        #if (vendor == 'Vietcombank')
        #    sql = "SELECT * FROM `transaction` where ((`trading_date`=%s and `balance`=%s and `description`=%s)) and `account_id`=%s"
        #else
        sql = "SELECT * FROM `transaction` where ((`reference_number`=%s) and (`trading_date`=%s and `balance`=%s and `description`=%s)) and `account_id`=%s"
        transaction = connection.select(sql, (self.get_reference_number(), self.get_trading_date(), self.get_balance(), self.get_description(), self.get_account_id()))
        if not transaction:
            codes = self.user.get_codes()
            user_code = None
            for code in codes:
                if code[0].lower() in self.get_description().lower():
                    user_code = str(code[0])
                    break
            # Create new transaction
            args = sys.argv
            project = None
            if len(args) > 1:
                project = str(args[1])
            if (project != 'financex'):
                unique_code = self.get_unique_string()
                sql = "INSERT INTO `transaction` (`trx_id`,`account_id`, `reference_number`, `trading_date`, `balance`, `description`,`code`,`created_at`) VALUES (%s, %s, %s, %s, %s, %s, %s,%s)"
                connection.query(sql, (
                    unique_code, self.get_account_id(), self.get_reference_number(), self.get_trading_date(),
                    self.get_balance(),
                    self.get_description(), user_code, self.get_current_time()))
            else:
                sql = "INSERT INTO `transaction` (`account_id`, `reference_number`, `trading_date`, `balance`, `description`,`code`,`created_at`) VALUES (%s, %s, %s, %s, %s,%s,%s)"
                connection.query(sql, (
                    self.get_account_id(), self.get_reference_number(), self.get_trading_date(), self.get_balance(),
                    self.get_description(), user_code, self.get_current_time()))
            return 1
        return 0

    def get_unique_string(self, string_length=10):
        random = str(uuid.uuid4())
        random = random.upper()
        random = random.replace("-", "")
        random_string = random[0:string_length]
        if self.check_unique(random_string) is not None:
            return self.get_unique_string()
        return random_string

    def check_unique(self, random_string):
        connection = self.connection
        sql = "SELECT `id` FROM `transaction` where `trx_id`=%s"
        transaction = connection.select(sql, random_string)
        return transaction

    def get_status(self, reference_number):
        connection = self.connection
        sql = "SELECT `status` FROM `transaction` where `reference_number`=%s"
        transaction = connection.select(sql, reference_number)
        return transaction[0]

    def get_account_vendor(self, account_id):
        connection = self.connection
        sql = "SELECT `vendor` FROM `account` where `number`=%s"
        vendor = connection.select(sql, account_id)
        return vendor[0]
