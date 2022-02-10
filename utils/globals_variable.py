from decimal import Decimal

e_capital_discount = Decimal("0.65")

# 定存的(年化)報酬率
fixed_deposit_return_rate = Decimal("1.02")

# 大盤的(年化)報酬率
market_return_rate = Decimal("1.1")


def initialize():
    global e_capital_discount
    global fixed_deposit_return_rate, market_return_rate
