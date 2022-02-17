import datetime

from data.database.day_ohlc_data import DayOhlcData
from data.loader.database import DatabaseLoader


class DayDatabaseLoader(DatabaseLoader):
    def __init__(self, stock_id, is_etf=False,
                 logger_dir="database_loader", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(stock_id=stock_id, is_etf=is_etf,
                         logger_dir=logger_dir, logger_name=logger_name)

        self.day_data = DayOhlcData(stock_id=stock_id,
                                    logger_dir=self.logger_dir, logger_name=self.logger_name)

    def __getitem__(self, item):
        pass

    def __iter__(self):
        for ohlc in self.ohlcs:
            ohlc_data = f"{ohlc[0]}, {ohlc[1]}, {ohlc[2]}, {ohlc[3]}, {ohlc[4]}, {ohlc[5]}"
            yield ohlc_data

    def setLoggerLevel(self, level):
        pass

    def subscribe(self, ohlc_type, requests: list):
        pass

    def getRequestStockNumber(self, ohlc_type):
        pass

    def getRequestStocks(self, ohlc_type):
        pass

    def loadData(self, start_time: datetime.datetime = None, stop_time: datetime.datetime = None):
        super().loadData(start_time=start_time, stop_time=stop_time)
        self.ohlcs = self.day_data.selectTimeFliter(start_time=start_time,
                                                    end_time=stop_time,
                                                    sort_by="TIME")

    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        history = self.day_data.getHistoryData(start_time=start_time, end_time=end_time)

        return history

    def close(self):
        self.day_data.close(auto_commit=True)
