from db.connection import Connection


class User:
    def __init__(self):
        self.connection = Connection()

    def get_codes(self):
        connection = self.connection
        sql = "SELECT `code` FROM `users` where `code` is not null"
        codes = connection.query(sql).fetchall()
        return codes
