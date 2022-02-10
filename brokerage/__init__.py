import datetime
import logging
from decimal import Decimal

from brokerage.order import Order
from brokerage.quote import Quote
from brokerage.reply import Reply
from enums import OhlcType
from submodule.Xu3.utils import getLogger


class Brokerage:
    # TODO: 報價、請求處理、回報(請求結果)
    def __init__(self, logger_dir="brokerage", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)
        self.logger_level = logging.DEBUG
        self.logger.setLevel(self.logger_level)

        self.order = Order(logger_dir=self.logger_dir, logger_name=self.logger_name)
        self.quote = Quote(logger_dir=self.logger_dir, logger_name=self.logger_name)
        self.reply = Reply(logger_dir=self.logger_dir, logger_name=self.logger_name)
        self.setListener()

    def setLoggerLevel(self, level: logging):
        self.logger_level = level
        self.logger.setLevel(level=level)
        self.quote.setLoggerLevel(level=level)
        self.order.setLoggerLevel(level=level)
        self.reply.setLoggerLevel(level=level)

    def setListener(self):
        self.order.onBought += self.reply.onBoughtListener
        self.order.onSold += self.reply.onSoldListener

        self.quote.onDayStart += self.reply.onDayStartListener
        self.quote.onDayEnd += self.reply.onDayEndListener
        self.quote.onOrderDayOhlcNotify += self.order.onOhlcNotifyListener
        self.quote.onOrderMinuteOhlcNotify += self.order.onOhlcNotifyListener

        # self.reply.onDayStartProcessed += self.onDayStartProcessedListener
        # self.reply.onDayEndProcessed += self.onDayEndProcessedListener

    # 提供給策略連結 Quote 的日線數據監聽器
    def setDayOhlcNotifyListener(self, listener):
        self.quote.onOrderDayOhlcNotify += listener

    # 提供給 RivalStrategy 連結 Quote 的分線數據監聽器
    def setMinuteOhlcNotifyListener(self, listener):
        self.quote.onOrderMinuteOhlcNotify += listener

    def subscribe(self, ohlc_type: OhlcType, request_ohlcs: list):
        # TODO: 回測系統的參數是策略，自動取出策略的 OhlcType 和相對應的股票代碼
        self.quote.subscribe(ohlc_type=ohlc_type, request_ohlcs=request_ohlcs)

    # 收到'購買'請求後的處理
    def buy(self, user: int, stock_id: str, guid: str, time: datetime.datetime, price: Decimal, volumn: int = 1):
        self.order.buy(user=user, guid=guid, stock_id=stock_id, time=time, price=price, volumn=volumn)

    def sell(self, user: int, stock_id: str, guid: str, time: datetime.datetime, price: Decimal, volumn: int = 1):
        self.order.sell(user=user, guid=guid, stock_id=stock_id, time=time, price=price, volumn=volumn)

    def run(self, start_time: datetime.datetime, end_time: datetime.datetime):
        # TODO: 執行 order , quote, reply 三個執行續
        # TODO: 時間的推進應考慮其他系統，而非自顧自地推進
        self.quote.run(start_time=start_time, end_time=end_time)


if __name__ == "__main__":
    from data import Inventory
    from time import sleep


    def onOhlcNotifyListener1(stock_id, ohlc_data):
        print(f"{datetime.datetime.now()} [QuoteTester] onOhlcNotifyListener1 | "
              f"stock_id: {stock_id}, ohlc_data: {ohlc_data}")
        sleep(0.1)


    def onOhlcNotifyListener2(stock_id, ohlc_data):
        print(f"{datetime.datetime.now()} [QuoteTester] onOhlcNotifyListener2 | "
              f"stock_id: {stock_id}, ohlc_data: {ohlc_data}")
        sleep(0.1)


    brokerage = Brokerage()
    brokerage.setLoggerLevel(level=logging.DEBUG)

    brokerage.setDayOhlcNotifyListener(listener=onOhlcNotifyListener1)
    brokerage.setDayOhlcNotifyListener(listener=onOhlcNotifyListener2)

    inv = Inventory()
    inventory = inv.getInventory()
    request_ohlcs = inventory[:3]

    brokerage.subscribe(ohlc_type=OhlcType.Day, request_ohlcs=request_ohlcs)
    brokerage.subscribe(ohlc_type=OhlcType.Minute, request_ohlcs=request_ohlcs)
    brokerage.run(start_time=datetime.datetime(2021, 7, 1), end_time=datetime.datetime(2021, 7, 10))
