import datetime
import logging
from decimal import Decimal

from enums import BuySell
from submodule.Xu3.utils import getLogger
from submodule.events import Event


class Reply:
    """ 輔助系統
    協助用戶使用這個系統，比如連線成功通知、斷線通知、、、等，目前我的系統似乎還用不到。
    """

    def __init__(self, logger_dir="brokerage", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)
        self.logger.setLevel(logging.DEBUG)

        self.is_day_start_processed = False
        self.is_day_end_processed = False

        # region 事件
        self.event = Event()

        # 成功買入事件
        # onBought(user, stock_id, guid, time, price, volumn)
        self.onBought = self.event.onBought

        # 成功賣出事件
        # onSold(user, stock_id, guid, time, price, volumn)
        self.onSold = self.event.onSold

        # self.onDayStartProcessed = self.event.onDayStartProcessed
        # self.onDayEndProcessed = self.event.onDayEndProcessed

    def setLoggerLevel(self, level):
        self.logger.setLevel(level=level)

    def onDayStartListener(self, day: datetime.date):
        self.logger.info(f"day: {day}", extra=self.extra)
        # TODO: day start process
        # self.is_day_start_processed = True
        # self.is_day_end_processed = False
        # self.onDayStartProcessed(day)

    def loadInventory(self, bs: BuySell, users: list = None):
        pass

    def onDayEndListener(self, day: datetime.date):
        self.logger.info(f"day: {day}", extra=self.extra)
        # TODO: day end process
        # self.is_day_start_processed = False
        # self.is_day_end_processed = True
        # self.onDayEndProcessed(day)

    def saveInventory(self, user, inventory: list = None):
        pass

    def onBoughtListener(self, user: int, stock_id: str, guid: str, time: datetime.datetime, price: Decimal,
                         volumn: int = 1):
        pass

    def onSoldListener(self, user: int, stock_id: str, guid: str, time: datetime.datetime, price: Decimal,
                       volumn: int = 1):
        pass


if __name__ == "__main__":
    pass
