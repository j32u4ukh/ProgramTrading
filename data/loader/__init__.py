import datetime
from abc import ABCMeta, abstractmethod

import numpy as np

from submodule.Xu3.utils import getLogger
from submodule.events import Event


class IDataLoader(metaclass=ABCMeta):
    """
    定義提供給報價系統(Quote)的數據類別，必須要提供的方法
    """

    def __init__(self, logger_dir="database_loader", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

    @abstractmethod
    def __iter__(self):
        raise NotImplementedError

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


class DataLoader(IDataLoader):
    def __init__(self, logger_dir="data_loader", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(logger_dir=logger_dir, logger_name=logger_name)

        self.start_time = None
        self.end_time = None
        self.n_data = 0
        self.event = Event()

    def __iter__(self):
        pass

    def setLoggerLevel(self, level):
        self.logger.setLevel(level=level)

    def subscribe(self, ohlc_type, requests: list):
        pass

    def getRequestStockNumber(self, ohlc_type, requests: list):
        pass

    def getRequestStocks(self, ohlc_type):
        pass

    def loadData(self, start_time: datetime.datetime, end_time: datetime.datetime):
        pass

    def close(self):
        pass


def getAverage(df, column_name, n_data=30):
    data = df[column_name].values
    average_array = []

    for i in range(len(data)):
        if i < n_data:
            average_array.append(np.mean(data[:i + 1]))
        else:
            average_array.append(np.mean(data[i - n_data: i]))

    return np.array(average_array)


if __name__ == "__main__":
    pass
