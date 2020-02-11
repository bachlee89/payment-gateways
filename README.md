Usage:
1. Login to the server with Pem file, locate to the payment gateways folder:
cd /var/www/payment-gateways

2. Run following commands to start or start the services:
    - To start all payment service: ./bin/console start
    - To start a specific payment service: ./bin/console start {payment_name}
    Eg: ./bin/console start Klikbca
    - To stop all payment service: ./bin/console stop
    - To stop a specific payment service: ./bin/console stop {payment_name}
    Eg: ./bin/console stop Msb

3. Or use short commands:
    payment-gateways stop
    payment-gateways stop Msb
    payment-gateways start
    payment-gateways start Msb


