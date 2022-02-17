import datetime

import utils.jikan as jikan
from data.database.minute_ohlc_data import MinuteOhlcData
from data.loader.database import DatabaseLoader


class MinuteDatabaseLoader(DatabaseLoader):
    def __init__(self, stock_id, is_etf=False,
                 transaction_start=jikan.Hms(hour=9, minute=0), transaction_end=jikan.Hms(hour=13, minute=30),
                 logger_dir="database_loader", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(stock_id=stock_id, is_etf=is_etf,
                         logger_dir=logger_dir, logger_name=logger_name)

        self.minute_data = MinuteOhlcData(stock_id=stock_id)
        self.transaction_start = transaction_start
        self.transaction_end = transaction_end
        self.days = None
        self.ohlcs = None

    def __getitem__(self, item):
        pass

    def __iter__(self):
        # 依序取得 Ohlc 物件
        # ohlc example: ('2020/12/01 09:18', 29.35, 29.360001, 29.35, 29.35, 377)
        for ohlc in self.ohlcs:
            """
            <OnNotifyKLineData>
            新版輸出格式，1分鐘線。以逗號分開資料。
                  年/月/日,  時:分,    開盤價,     最高價,     最低價,    收盤價, 成交量
            例：2016/08/04, 09:01, 34.900002, 34.900002, 34.799999, 34.900002, 67

            新版輸出函式中所取回的價格已進行過小數點處理，且由 Solace K 線主機提供，例如 1101 價格為「36.500000」，
            則函式所傳回的價格同為「36.500000」，因此使用者所開發的程式必須另接手處理欲取小數點幾位數。
            ex: 2330 {2020/07/06 13:06, 335.500000, 336.000000, 335.500000, 335.500000, 77}

            [資料庫欄位格式]
            TIME: TEXT, OPEN: TEXT, HIGH: TEXT, LOW: TEXT, CLOSE: TEXT, VOL: INT

            :param stock_id: 上市股票(商品)代號。
            :param date_time: 年/月/日,  時:分 -> datetime.datetime
            :param open_value: 開盤價
            :param high_value: 最高價
            :param low_value: 最低價
            :param close_value: 收盤價
            :param volumn: 成交量
            """

            yield f"{ohlc[0]}, {ohlc[1]}, {ohlc[2]}, {ohlc[3]}, {ohlc[4]}, {ohlc[5]}"

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
        self.ohlcs = self.minute_data.selectTimeFliter(start_time=start_time,
                                                       end_time=stop_time,
                                                       sort_by="TIME")

    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        history = self.minute_data.getHistoryData(start_time=start_time, end_time=end_time)

        return history

    def close(self):
        self.minute_data.close(auto_commit=True)
