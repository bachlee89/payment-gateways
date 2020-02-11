from flask import Flask
from flask_restful import Api
from api.transactions import Transactions
from api.app import App
from api.transactions_account import TransactionsAccount

app = Flask(__name__)
api = Api(app)
api.add_resource(Transactions, '/transactions')
api.add_resource(App, '/app')
api.add_resource(TransactionsAccount, '/transactions/<account_number>')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5002')
