import datetime
from decimal import Decimal, ROUND_HALF_UP


class Kpi:
    def __init__(self, stock_id: str, date_time: datetime.datetime, buy_price: Decimal, return_kpi: Decimal,
                 trial_period: int = 30):
        self.stock_id = stock_id
        self.date_time = date_time
        self.buy_price = buy_price
        self.return_kpi = return_kpi

        # 嘗試期：股票剛買到可能還是負報酬，須給一段時間讓價格跑上去
        # TODO: 變成策略的可訓練參數，有些大器晚成型需要較長的時間醞釀漲幅
        self.trial_period = trial_period

        self.current = date_time
        self.current_price = Decimal("0.0")
        self.during_days = 0
        self.return_rate = Decimal("0.0")
        self.expect_return = Decimal("0.0")

    def __str__(self):
        description = f"Kpi({self.stock_id}, {self.date_time.date()} ~ {self.current.date()}, " \
                      f"during: {self.during_days} days, buy: {self.buy_price}, sell: {self.current_price}, " \
                      f"預期報酬率: {self.expect_return}, 實際報酬率: {self.return_rate})"

        return description

    __repr__ = __str__

    def updatePrice(self, current: datetime.datetime, price: Decimal):
        self.current = current
        self.during_days = (self.current - self.date_time).days
        self.current_price = price
        self.return_rate = (price / self.buy_price).quantize(Decimal('.0000'), ROUND_HALF_UP)

        # 持有天數下，預期報酬率
        self.expect_return = (self.return_kpi ** self.during_days).quantize(Decimal('.0000'), ROUND_HALF_UP)

        # 若持有天數已超過嘗試期，且報酬率不如預期
        return (self.during_days > self.trial_period) and (self.return_rate < self.expect_return)
