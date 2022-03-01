import datetime
import logging
from decimal import Decimal

from brokerage.order import Order
from brokerage.quote import Quote
from brokerage.reply import Reply
from enums import OhlcType
from submodule.Xu3.utils import getLogger


class ProgramTrading:
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

    def setLoggerLevel(self, level: logging):
        self.logger_level = level
        self.logger.setLevel(level=level)

    def onDayOhlcNotifyListener(self, stock_id, ohlc_data):
        print(f"[onDayOhlcNotifyListener] stock_id: {stock_id}, ohlc_data: {ohlc_data}")

    def onMinuteOhlcNotifyListener(self, stock_id, ohlc_data):
        print(f"[onMinuteOhlcNotifyListener] stock_id: {stock_id}, ohlc_data: {ohlc_data}")
