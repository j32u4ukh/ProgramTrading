import datetime
from decimal import Decimal

import utils.globals_variable as gv
from data.inventory import Inventory
from order import OrderList
from submodule.Xu3.utils import getLogger
from submodule.events import Event


class TheWorld:
    def __init__(self, stock_id: str, order_list: OrderList,
                 logger_dir="strategy", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.stock_id = stock_id

        # 策略所管理的庫存
        self.order_list = order_list

        self.event = Event()
        self.onTheWorld = self.event.onTheWorld
        self.onRevise = self.event.onRevise

        # TODO: 歷史股利導入回測
        # 股利發放金額(現金股利)
        self.temp_revise = {
            # "2812": [(datetime.date(2021, 8, 31), Decimal("-0.45"))],
            # "5880": [(datetime.date(2021, 8, 11), Decimal("-0.85")),
            #          (datetime.date(2021, 9, 8), Decimal("-0.2"))],
            # "00850": [(datetime.date(2020, 11, 20), Decimal("-0.9"))],
            # "1305": [(datetime.date(2021, 9, 2), Decimal("-2.3"))],
            # "3711": [(datetime.date(2021, 9, 6), Decimal("-4.19"))],
            # "3048": [(datetime.date(2021, 9, 7), Decimal("-2.9"))],
            # "3037": [(datetime.date(2021, 8, 27), Decimal("-1.3929"))],
            # "9945": [(datetime.date(2021, 9, 23), Decimal("-4.0"))],
            # "2303": [(datetime.date(2021, 7, 22), Decimal("-1.6"))],

        }

        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

        self.logger.info(f"\n{self.order_list}", extra=self.extra)

        # 現實世界的庫存
        self.inventory = Inventory()

        # guid, date_time, stock_id, volumn, price
        # [['d156be39537f4e848e916154f325067d' '2021/3/24' '1310' 1000 '19.05']]
        # 載入實際交易數據的 時間、價格 等資訊，在相對應的時間用相對應的價格買入
        self.values = self.inventory.load(stock_id=self.stock_id)

        gv.initialize()
        self.discount = gv.e_capital_discount

    def onNextDayListener(self, date_time: datetime.date):
        for value in self.values:
            guid, buy_time, stock_id, volumn, price = value

            try:
                time = datetime.datetime.strptime(buy_time, "%Y-%m-%d")
            except ValueError:
                time = datetime.datetime.strptime(buy_time, "%Y/%m/%d")

            # 檢查是否為實際成交的那天
            if time.date() == date_time:
                self.onTheWorld(guid=guid, time=time, price=price, volumn=1)

            if self.temp_revise.__contains__(stock_id):
                revises = self.temp_revise[stock_id]

                for revise in revises:
                    revise_date, revise_value = revise

                    if date_time == revise_date:
                        self.onRevise(revise_date=revise_date, revise_value=revise_value)

    def getData(self):
        # guid, date_time, stock_id, volumn, price
        _, buy_time, _, _, price = self.values[0]

        try:
            time = datetime.datetime.strptime(buy_time, "%Y-%m-%d")
        except ValueError:
            time = datetime.datetime.strptime(buy_time, "%Y/%m/%d")

        # time, price
        return time, Decimal(price)


if __name__ == "__main__":
    def onTheWorldListener(guid: str, time: datetime.datetime, price: str, volumn: int):
        print(f"[TheWorld] onTheWorldListener | {guid}, {time}, {price}, {volumn}")


    # bb4ad84879904ae1b179fdb98494ca13,2021-05-31,2545,40.95,41.95
    stock_id = "2545"
    logger_dir = "strategy"
    logger_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    order_list = OrderList(stock_id=stock_id, logger_dir=logger_dir, logger_name=logger_name)
    the_world = TheWorld(stock_id=stock_id, order_list=order_list, logger_dir=logger_dir, logger_name=logger_name)
    the_world.onTheWorld += onTheWorldListener

    the_world.onNextDayListener(datetime.datetime(2021, 5, 31).date())
    the_world.onNextDayListener(datetime.datetime.today().date())
