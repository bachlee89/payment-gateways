from flask_restful import Resource, reqparse
from db.connection import Connection

parser = reqparse.RequestParser()
parser.add_argument('status', type=str)
parser.add_argument('reference_number', type=str)


class Transactions(Resource):
    def __init__(self):
        self.connection = Connection()

    def get(self):
        result = []
        connection = self.connection
        args = []
        sql = "SELECT `trading_date`,`reference_number`,`number`,`transaction`.`balance`,`description`,`status`,`created_at` FROM `transaction`"
        sql = sql + " INNER JOIN `account` ON transaction.account_id=account.id"
        sql = sql + " WHERE `status`=0 ORDER BY `created_at` DESC"
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

    def post(self):
        connection = self.connection
        args = parser.parse_args()
        status = str(args['status'])
        reference_number = str(args['reference_number'])
        sql = "UPDATE `transaction` set `status`=%s where `reference_number`=%s"
        args = [status, reference_number]
        update = connection.query(sql, args)
        result = {
            'message': str(update.rowcount) + " row(s) affected"
        }
        return result
