from db.connection import Connection


class Account:
    def __init__(self, name, number, vendor, balance=None):
        self.name = name
        self.number = number
        self.vendor = vendor
        self.connection = Connection()
        self.balance = balance

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def set_number(self, number):
        self.number = number

    def get_number(self):
        return self.number

    def set_vendor(self, vendor):
        self.vendor = vendor

    def get_vendor(self):
        return self.vendor

    def set_balance(self, balance):
        self.balance = balance

    def get_balance(self):
        return self.balance

    def save(self):
        connection = self.connection
        sql = "SELECT * FROM `account` where `number`=%s"
        account = connection.select(sql, (self.get_number()))
        if not account:
            # Create new account
            sql = "INSERT INTO `account` (`number`, `name`,`vendor`) VALUES (%s, %s, %s)"
            connection.query(sql, (self.get_number(), self.get_name(), self.get_vendor()))

    def update_account(self):
        if self.get_account_id() is not None and self.get_balance() is not None:
            connection = self.connection
            sql = "UPDATE `account` set `balance`=%s, `name`=%s where `number`=%s"
            connection.query(sql, (self.get_balance(), self.get_name(), self.get_number()))
        else:
            self.save()

    def update_balance(self):
        connection = self.connection
        sql = "UPDATE `account` set `balance`=%s where `number`=%s"
        connection.query(sql, (self.get_balance(), self.get_number()))

    def get_account_id(self):
        connection = self.connection
        sql = "SELECT `id` FROM `account` where `number`=%s"
        account = connection.select(sql, (self.get_number()))
        if account is not None:
            return account[0]
        return None
