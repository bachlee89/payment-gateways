from flask_restful import Resource, reqparse
from db.connection import Connection

parser = reqparse.RequestParser()

parser.add_argument('status', type=str)


class App(Resource):
    def __init__(self):
        self.connection = Connection()

    def get(self):
        connection = self.connection
        sql = "SELECT `status` FROM `apps` where `platform`=%s"
        args = ["ios"]
        config = connection.query(sql, args).fetchall()
        ios = config[0]
        if ios[0] is 1:
            return True
        return False
