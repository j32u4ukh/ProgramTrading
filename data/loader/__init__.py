import datetime
from abc import ABCMeta, abstractmethod

import numpy as np

from submodule.Xu3.utils import getLogger
from submodule.events import Event


class DataLoader(metaclass=ABCMeta):
    def __init__(self, logger_dir="data_loader", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

        self.start_time = None
        self.end_time = None
        self.n_data = 0
        self.event = Event()

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def loadData(self, start_time: datetime.datetime = None, end_time: datetime.datetime = None):
        pass

    def setLoggerLevel(self, level):
        self.logger.setLevel(level=level)


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
