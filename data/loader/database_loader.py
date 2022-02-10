import datetime
import logging
from abc import ABCMeta, abstractmethod

import numpy as np

import utils.jikan as jikan
from data import StockCategory, parseOhlcData
from data.loader import DataLoader
from data.resource.ohlc_data import DayOhlcData, MinuteOhlcData
from utils import truncatedNormal, getValidPrices


class DatabaseLoader(DataLoader, metaclass=ABCMeta):
    def __init__(self, stock_id, is_etf=False,
                 logger_dir="database_loader", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(logger_dir=logger_dir, logger_name=logger_name)
        self.stock_id = stock_id
        self.is_etf = is_etf

        self.start_time = None
        self.end_time = None
        self.ohlcs = None

    @abstractmethod
    def __iter__(self):
        pass

    @staticmethod
    def createVolumns(volumn, size):
        """

        :param volumn: 加總數值
        :param size: 數值個數(包含數值為 0)
        :return:
        """
        volumn_matrix = np.zeros(shape=(volumn, size))
        # ex: 0 - 59
        indexs = np.random.randint(low=0, high=size - 1, size=volumn)
        volumn_matrix[np.arange(volumn), indexs] = 1.0
        volumns = volumn_matrix.sum(axis=0)

        return volumns

    @abstractmethod
    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        pass

    @abstractmethod
    def close(self):
        pass

    def getTimeRange(self):
        return self.end_time - self.start_time

    def loadData(self, start_time: datetime.datetime = None, stop_time: datetime.datetime = None):
        self.start_time = start_time

        if stop_time is None:
            self.end_time = datetime.date.today()
        else:
            self.end_time = stop_time

    # TODO: 透過呼叫 utils.getLastValidPrice / utils.getNextValidPrice 來取得下一筆 Tick 數據價格
    def generateTicks(self, stock_id: str, tick_time: datetime.datetime, size: int,
                      open_value: float, high_value: float, low_value: float, close_value: float, volumn: int):
        """
        數據傳入前，已排除 volumn = 0 的情形
        ex: XXX 15960 17010 20200707 132505 672535 33800 33950 33800 2505 1

        :param stock_id:
        :param tick_time:
        :param size:
        :param open_value:
        :param high_value:
        :param low_value:
        :param close_value:
        :param volumn:
        :return:
        """
        # 1 分 K 為過去 1 分鐘內 tick 的總和，因此 tick 會比 1 分 K 早一分鐘
        tick_time = tick_time - datetime.timedelta(minutes=1) + datetime.timedelta(seconds=1)
        tick_date = int(tick_time.strftime('%Y%m%d'))
        one_second = datetime.timedelta(seconds=1)

        prices, volumns = self.createTickValues(size=size,
                                                open_value=int(100 * open_value),
                                                high_value=int(100 * high_value),
                                                low_value=int(100 * low_value),
                                                close_value=int(100 * close_value),
                                                volumn=volumn,
                                                low_scale=0.8,
                                                high_scale=1.2)

        # print(f"#prices: {len(prices)}")
        # print(f"#volumns: {len(volumns)}")

        for i in range(size - 1):
            # 更新目前時間
            tick_hms = int(tick_time.strftime("%H%M%S"))
            tick_time += one_second

            # vol: volumn of tick
            vol = int(volumns[i])
            price = prices[i]

            yield 0, int(stock_id), 0, tick_date, tick_hms, 0, price, price, price, vol, 1

        # 更新目前時間
        tick_hms = int(tick_time.strftime("%H%M%S"))
        price = prices[size - 1]
        vol = int(volumns[size - 1])

        yield 0, int(stock_id), 0, tick_date, tick_hms, 0, price, price, price, vol, 1

    def createTickValues(self, size, open_value, high_value, low_value, close_value, volumn,
                         low_scale=0.8, high_scale=1.2):
        """
        價位由高到低，以 1, 2, 3, 4, 5 作為編號，依序為開高低收，有以下數種組合:
        3132, 3133, 3142, 3143, 3144, 3154
        3232, 3242, 3243, 3244, 3254
        3333, 3343, 3344, 3354

            h1
            h2      c2
        o3  h3  l3  c3
                l4  c4
                l5

        volumn: [組合類型]
        {1: [3333],
         2: [3232, 3344],
         3: [3132, 3144, 3242, 3354],
         4: [3142, 3154]}

        # volumn = 2
        # 3232: 開盤價即為最低價 & 收盤價即為最高價
        # 3344: 開盤價即為最高價 & 收盤價即為最低價

        # volumn = 3
        # 3132: 開盤價即為最低價
        # 3144: 收盤價即為最低價
        # 3242: 收盤價即為最高價
        # 3354: 開盤價即為最高價

        :param size:
        :param open_value:
        :param high_value:
        :param low_value:
        :param close_value:
        :param volumn:
        :param low_scale:
        :param high_scale:
        :return:
        """
        # self.logger.info(f"({open_value}, {high_value}, {low_value}, {close_value})")

        if volumn < 4:
            # volumns = [0, 1, 2, 0, 0, 4, ..., 0, 3]
            # indexs = [1, 2, 5, ..., n_data - 1]
            indexs = np.arange(0, size)
            np.random.shuffle(indexs)
            indexs = indexs[:volumn]

            volumns = np.zeros(size)
            volumns[indexs] = 1

            nonzero_prices = [open_value]

            if volumn == 3:
                # 3132, 3354
                if high_value == open_value or high_value == close_value:
                    nonzero_prices.append(low_value)

                # 3144, 3242 (low_value == open_value 或 low_value == close_value 或 其他)
                else:
                    nonzero_prices.append(high_value)

            if volumn >= 2:
                nonzero_prices.append(close_value)

            nonzero_prices = np.array(nonzero_prices)

        # volumn >= 4
        else:
            # volumns = [0, 1, 2, 0, 0, 4, ..., 0, 3]
            # indexs = [1, 2, 5, ..., n_data - 1]
            volumns = self.createVolumns(volumn=volumn - 1, size=size)

            # 確保最後一個 tick 有交易量
            volumns[-1] += 1
            indexs = np.where(volumns != 0)[0]

            n_price = len(indexs)

            # 確保第一筆和最後一筆為'開盤價'與'收盤價'
            base_price = np.linspace(open_value, close_value, num=n_price)
            truncated_normal = truncatedNormal(low=low_scale, high=high_scale, size=n_price)

            # '開盤價'與'收盤價'不會受到模擬波動影響
            truncated_normal[0] = 1
            truncated_normal[-1] = 1

            # 基本走向價格 搭配 波動模擬
            nonzero_prices = base_price * truncated_normal

            # 限制價格上下限
            nonzero_prices = np.clip(nonzero_prices, low_value, high_value)

            # 確保有最高、最低價
            argmax = np.argmax(nonzero_prices)
            nonzero_prices[argmax] = high_value
            argmin = np.argmin(nonzero_prices)
            nonzero_prices[argmin] = low_value

        prices = np.zeros_like(volumns)

        # 最後一個 tick 一定有交易量，因此最後一個價格一定會映射到最後一個 tick
        prices[indexs] = getValidPrices(nonzero_prices, is_etf=self.is_etf)

        return prices, volumns


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
            (date_time, open_value, high_value, low_value, close_value,
             volumn) = parseOhlcData(ohlc_data, is_minute_data=True, is_str_datetime=True)

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

    def loadData(self, start_time: datetime.datetime = None, stop_time: datetime.datetime = None):
        super().loadData(start_time=start_time, stop_time=stop_time)
        self.ohlcs = self.minute_data.selectTimeFliter(start_time=start_time,
                                                       end_time=stop_time,
                                                       sort_by="TIME")

    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        pass

    def close(self):
        pass


if __name__ == "__main__":
    class DatabaseLoaderTester:
        def __init__(self, logger_dir="test", logger_name="DatabaseLoaderTester"):
            self.logger_dir = logger_dir
            self.logger_name = logger_name

        @staticmethod
        def testMinuteDatabaseLoader():
            stock_id = "2527"
            is_etf = StockCategory.isEtf(stock_id)
            start_time = datetime.datetime(2021, 1, 18, 9, 3)
            end_time = datetime.datetime(2021, 1, 18, 9, 32)

            minute_loader = MinuteDatabaseLoader(stock_id=stock_id, is_etf=is_etf)
            minute_loader.setLoggerLevel(logging.DEBUG)
            minute_loader.loadData(start_time=start_time, stop_time=end_time)

            for idx, ohlc in enumerate(minute_loader):
                print(f"idx: {idx}, ohlc({stock_id}): {ohlc}")

        def testDayDatabaseLoader(self):
            stock_id = "2527"
            is_etf = StockCategory.isEtf(stock_id)
            start_time = datetime.datetime(2021, 3, 1, 9, 0)
            # end_time = datetime.datetime(2020, 6, 18, 12, 3)
            end_time = datetime.datetime.today()

            day_loader = DayDatabaseLoader(stock_id=stock_id, is_etf=is_etf,
                                           logger_dir=self.logger_dir, logger_name=self.logger_name)
            day_loader.loadData(start_time=start_time, stop_time=end_time)

            for idx, ohlc in enumerate(day_loader):
                print(f"idx: {idx}, ohlc: {ohlc}")


    tester = DatabaseLoaderTester()
    tester.testDayDatabaseLoader()
