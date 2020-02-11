from flask_restful import Resource, request
from db.connection import Connection


class TransactionsAccount(Resource):
    def __init__(self):
        self.connection = Connection()

    def get(self, account_number):
        result = []
        connection = self.connection
        sql = "SELECT `trading_date`,`reference_number`,`number`,`transaction`.`balance`,`description`,`status`,`created_at` FROM `transaction`"
        sql = sql + " INNER JOIN `account` ON transaction.account_id=account.id"
        sql = sql + " WHERE `number`=%s AND `status`=0 ORDER BY `created_at` DESC"
        args = [account_number]
        transactions = connection.query(sql, args).fetchall()
        for transaction in transactions:
            data = {
                'trading_date': str(transaction[0]),
                'reference_number': transaction[1],
                'account_number': transaction[2],
                'balance': float(transaction[3]),
                'description': transaction[4],
                'status': transaction[5],
                'created_at': str(transaction[6]),
            }
            result.append(data)
        return result
