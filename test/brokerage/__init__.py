import datetime
import logging
from abc import ABCMeta, abstractmethod
from brokerage import Brokerage
from enums import OhlcType


class FakeStrategy(metaclass=ABCMeta):
    def __init__(self, stock_id, ohlc_type: OhlcType):
        self.stock_id = stock_id
        self.ohlc_type = ohlc_type

    @abstractmethod
    def onOhlcNotifyListener(self, stock_id, ohlc_data):
        pass


class FakeStrategy1(FakeStrategy):
    def __init__(self):
        super().__init__(stock_id="2812", ohlc_type=OhlcType.Day)

    def onOhlcNotifyListener(self, stock_id, ohlc_data):
        if stock_id == self.stock_id:
            print(f"[FakeStrategy1] onOhlcNotifyListener | stock_id: {self.stock_id}, ohlc_type: {self.ohlc_type}")


class FakeStrategy2(FakeStrategy):
    def __init__(self):
        super().__init__(stock_id="6005", ohlc_type=OhlcType.Day)

    def onOhlcNotifyListener(self, stock_id, ohlc_data):
        if stock_id == self.stock_id:
            print(f"[FakeStrategy1] onOhlcNotifyListener | stock_id: {self.stock_id}, ohlc_type: {self.ohlc_type}")


class FakeStrategy3(FakeStrategy):
    def __init__(self):
        super().__init__(stock_id="2812", ohlc_type=OhlcType.Minute)

    def onOhlcNotifyListener(self, stock_id, ohlc_data):
        if stock_id == self.stock_id:
            print(f"[FakeStrategy1] onOhlcNotifyListener | stock_id: {self.stock_id}, ohlc_type: {self.ohlc_type}")


class FakeStrategy4(FakeStrategy):
    def __init__(self):
        super().__init__(stock_id="6005", ohlc_type=OhlcType.Minute)

    def onOhlcNotifyListener(self, stock_id, ohlc_data):
        if stock_id == self.stock_id:
            print(f"[FakeStrategy1] onOhlcNotifyListener | stock_id: {self.stock_id}, ohlc_type: {self.ohlc_type}")


brokerage = Brokerage()
brokerage.setLoggerLevel(level=logging.DEBUG)

fss = [FakeStrategy1(),
       FakeStrategy2(),
       FakeStrategy3(),
       FakeStrategy4()]
day_request_ohlcs = []
minute_request_ohlcs = []

for fs in fss:
    if fs.ohlc_type == OhlcType.Day:
        day_request_ohlcs.append(fs.stock_id)
        brokerage.setDayOhlcNotifyListener(listener=fs.onOhlcNotifyListener)

    elif fs.ohlc_type == OhlcType.Minute:
        minute_request_ohlcs.append(fs.stock_id)
        brokerage.setMinuteOhlcNotifyListener(listener=fs.onOhlcNotifyListener)

brokerage.subscribe(ohlc_type=OhlcType.Day, request_ohlcs=day_request_ohlcs)
brokerage.subscribe(ohlc_type=OhlcType.Minute, request_ohlcs=minute_request_ohlcs)
brokerage.run(start_time=datetime.datetime(2021, 7, 1), end_time=datetime.datetime(2021, 7, 10))
