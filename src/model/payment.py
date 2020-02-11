from db.connection import Connection


class Payment:
    def __init__(self, status=1):
        self.status = status
        self.connection = Connection()

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def set_username(self, username):
        self.username = username

    def get_username(self):
        return self.username

    def set_status(self, status):
        self.status = status

    def get_status(self):
        return self.status

    def save(self):
        connection = self.connection
        sql = "SELECT * FROM `payment` where `username`=%s"
        payment = connection.select(sql, (self.get_username()))
        if not payment:
            sql = "INSERT INTO `payment` (`name`,`username`,`status`) VALUES (%s, %s, %s)"
            connection.query(sql, (self.get_name(), self.get_username(), self.get_status()))

    def check_status(self, username):
        connection = self.connection
        sql = "SELECT `status` FROM `payment` where `username`=%s"
        payment = connection.select(sql, username)
        return payment[0]

    def update_status(self):
        connection = self.connection
        if self.get_name() is None:
            sql = "UPDATE `payment` set `status`=%s"
        else:
            sql = "UPDATE `payment` set `status`=%s where `name`=%s"
        connection.query(sql, (self.get_status(), self.get_name()))

    def clean(self):
        connection = self.connection
        sql = "DELETE FROM `payment`"
        connection.query(sql)
