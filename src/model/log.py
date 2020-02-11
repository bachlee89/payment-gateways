from .config import Config
from .time import Time
from .email import EmailTransport
from db.connection import Connection
from datetime import datetime


class Log:
    def __init__(self):
        self.path = Config().get_base_dir('var') + 'log/'
        self.time = Time()
        self.email_transport = EmailTransport()
        self.connection = Connection()

    def log(self, message, type="message"):
        current_time = "[" + self.time.get_current_time() + "]"
        with open(self.path + 'system.log', 'a') as f:
            message = current_time + "[" + type + "]: " + message
            f.write(message + '\n')
            return 1

    def update_log(self, vendor, username):
        connection = self.connection
        sql = "SELECT * FROM `log` where `vendor`=%s and `username`=%s"
        log = connection.select(sql, (vendor, username))
        if not log:
            # Create new log
            sql = "INSERT INTO `log` (`vendor`, `username`, `created_at`, `updated_at`) VALUES (%s, %s, %s, %s)"
            connection.query(sql, (
                vendor, username, self.time.get_current_time(), self.time.get_current_time()))
        else:
            sql = "UPDATE `log` set `updated_at`=%s where `vendor`=%s and `username`=%s"
            connection.query(sql, (self.time.get_current_time(), vendor, username))

    def notify(self):
        connection = self.connection
        sql = "SELECT * FROM `log` a INNER JOIN `payment` b on a.`username`=b.`username` where status=1"
        logs = connection.select_all(sql, None)
        f = "%Y-%m-%d %H:%M:%S"
        current_time = datetime.strptime(self.time.get_current_time(), f)
        for log in logs:
            vendor = log[1]
            username = log[2]
            updated_at = log[4]
            time_diff = current_time - updated_at
            total_seconds = time_diff.total_seconds()
            if total_seconds > 3600:
                self.email_transport.send_notify(vendor, username)
