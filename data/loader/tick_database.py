import datetime

import utils.jikan as jikan
from data import parseOhlcData
from data.database.minute_ohlc_data import MinuteOhlcData
from data.loader.database import DatabaseLoader


# TODO: 區分 OhlcType.Minute 和 OhlcType.Tick，不要混在一起
class TickDatabaseLoader(DatabaseLoader):
    def __init__(self, stock_id, is_etf=False,
                 transaction_start=jikan.Hms(hour=9, minute=0), transaction_end=jikan.Hms(hour=13, minute=30)):
        super().__init__(stock_id=stock_id, is_etf=is_etf, logger_name="TickDatabaseLoader")

        self.minute_data = MinuteOhlcData(stock_id=stock_id)
        self.transaction_start = transaction_start
        self.transaction_end = transaction_end
        self.days = None
        self.ohlcs = None

    def __getitem__(self, item):
        pass

    def __iter__(self):
        # size: tick 數據應有的數量(1 分鐘 60 個 tick)
        size = 60

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

            :param stock_id: 上市股票(商品)代號。
            :param date_time: 年/月/日,  時:分 -> datetime.datetime
            :param open_value: 開盤價
            :param high_value: 最高價
            :param low_value: 最低價
            :param close_value: 收盤價
            :param volumn: 成交量
            """
            ohlc_data = f"{ohlc[0]}, {ohlc[1]}, {ohlc[2]}, {ohlc[3]}, {ohlc[4]}, {ohlc[5]}"

            # self.logger.debug(f"ohlc_data: {ohlc_data}")
            date_time, open_value, high_value, low_value, close_value, volumn = parseOhlcData(ohlc_data)

            """
            ex: XXX 15960 17010 20200707 132505 672535 33800 33950 33800 2505 1

            :param market: 報價有異動的商品市場別。
            :param sys_stock_id: 系統自行定義的股票代碼。ex: 15960
            :param address: 表示資料的位址(Key)ex: 17010
            :param tick_date: 交易日期。(YYYYMMDD) ex: 20200707
            :param tick_hms: 時間1。(時：分：秒)  ex: 132505
            :param tick_millis_micros: 時間2。(‘毫秒"微秒)ex: 672535
            :param buy_price: 買價。ex: 33800
            :param sell_price: 賣價。ex: 33950
            :param deal_price: 成交價。ex: 33800
            :param deal_volumn: 成交量。ex: 2505
            :param is_simulate: 0: 一般揭示; 1: 試算揭示。ex: 1
            :return:
            """
            # volumn of ohlc
            volumn = int(volumn)

            # if volumn == 0:
            #     continue

            tick_time = datetime.datetime.strptime(date_time, "%Y/%m/%d %H:%M")
            # self.logger.debug(f"tick_time: {tick_time}")
            tick_generator = self.generateTicks(stock_id=self.stock_id,
                                                tick_time=tick_time,
                                                size=size,
                                                open_value=float(open_value),
                                                high_value=float(high_value),
                                                low_value=float(low_value),
                                                close_value=float(close_value),
                                                volumn=volumn)

            for i in range(size - 1):
                tick_data = next(tick_generator)

                yield tick_data, None

            # 取得最後一筆 tick 數據
            tick_data = next(tick_generator)

            yield tick_data, ohlc_data

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
        pass

    def close(self):
        pass
