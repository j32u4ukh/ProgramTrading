import datetime
from abc import ABCMeta, abstractmethod


class DataLoader(metaclass=ABCMeta):
    """
    定義提供給報價系統(Quote)的數據類別，必須要提供的方法
    """

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def setLoggerLevel(self, level):
        pass

    @abstractmethod
    def subscribe(self, ohlc_type, requests: list):
        pass

    @abstractmethod
    def getRequestStockNumber(self, ohlc_type, requests: list):
        pass

    @abstractmethod
    def getRequestStocks(self, ohlc_type):
        pass

    @abstractmethod
    def loadData(self, start_time: datetime.datetime, end_time: datetime.datetime):
        # 載入指定時間區間內的數據，並根據時間進行排序
        pass

    @abstractmethod
    def close(self):
        # 關閉資料庫
        pass
