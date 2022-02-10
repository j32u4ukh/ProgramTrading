import datetime
import functools
import logging

from data.resource import ResourceData


class DayOhlcData(ResourceData):
    def __init__(self, stock_id, latest_time=None, level: logging = logging.INFO,
                 logger_dir="resource_data", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        """

        :param stock_id:
        :param latest_time: 數據最久只取到這個時間點之後，那之前的數據則忽略
        :param logger_dir:
        :param logger_name:
        """
        super().__init__(db_name="stock_data", logger_dir=logger_dir, logger_name=logger_name)
        self.setLoggerLevel(level=level)

        self.stock_id = stock_id
        self.getDataTable()
        self.last_day = None
        today = datetime.datetime.today()
        latest_time = datetime.datetime(year=today.year, month=1, day=1) if latest_time is None else latest_time
        self.getLastTime(latest_time=latest_time)

        self.last_segement = datetime.datetime(1970, 1, 1)
        self.delta_segement = datetime.timedelta(days=20)

    def setLoggerLevel(self, level: logging):
        self.logger.setLevel(level)

    def getDataTable(self, table_name="", table_definition=""):
        table_name = f"DAY_{self.stock_id}"
        table_definition = """TIME   TEXT    PRIMARY KEY NOT NULL,
        OPEN    TEXT    NOT NULL,
        HIGH    TEXT    NOT NULL,
        LOW     TEXT    NOT NULL,
        CLOSE   TEXT    NOT NULL,
        VOL     INT     NOT NULL"""
        # 日線: bstrData: 2020/06/04, 28.670000, 28.750000, 28.549999, 28.670000, 22398
        super().getTable(table_name=table_name, table_definition=table_definition)

    def getLastTime(self, latest_time: datetime.datetime):
        """

        :param latest_time: 數據最久只取到這個時間點之後，那之前的數據則忽略
        :return:
        """

        def parseTime(str_time):
            return datetime.datetime.strptime(str_time, "%Y/%m/%d")

        self.last_day = self.getLastTimeCore(temp_time=self.last_day,
                                             latest_time=latest_time,
                                             time_column="TIME",
                                             parseTime=parseTime)

    def getDataInfo(self, is_minute_data: bool = False):
        super().getDataInfo(is_minute_data=False)

    # 日線: bstrData: 2020/06/04, 28.670000, 28.750000, 28.549999, 28.670000, 22398
    def addData(self, primary_column: str = "TIME", values: list = None, check_sequence=True):
        if len(values) == 0 or values is None:
            self.logger.debug("len(values) == 0 or values is None", extra=self.extra)
            return

        # 對 values 的日期進行排序，根據進行 value[0] 排序
        # 參考: https://stackoverflow.com/questions/3121979/
        # how-to-sort-a-list-tuple-of-lists-tuples-by-the-element-at-a-given-index
        values.sort(key=lambda value: value[0])

        # 輸入時間為字串，為進行時間上的比較，故須轉型為 datetime
        last_day = datetime.datetime.strptime(values[-1][0], "%Y/%m/%d")
        self.logger.debug(f"last_day in values: {last_day}", extra=self.extra)

        # 若 self.last_day 尚未初始化
        if self.last_day is None:
            self.last_day = last_day
        else:
            # 若加入的數據比最後一筆數據還舊，則直接不加入，因為我是由前往後新增，數據應該越來越新
            # 若加入的數據比較舊，表示應該是之前就加過的
            # check_sequence: 是否檢查時間順序，若不檢查則會由 super().add_ 判斷是否是已添加過的數據
            if (last_day < self.last_day) and check_sequence:
                self.logger.debug("新加入數據之時間，較資料庫中最近一筆來的晚，故不加入", extra=self.extra)
                return

        if last_day.date() == datetime.date.today():
            self.logger.info(values, extra=self.extra)

        super().add_(primary_column=primary_column, values=values)

    def displayDayData(self, columns: list = None,
                       sort_by: str = "TIME", sort_type="ASC",
                       limit: int = 20, offset: int = 0):
        result = super().select(table_name=self.table_name, columns=columns,
                                sort_by=sort_by, sort_type=sort_type,
                                limit=limit, offset=offset)
        for res in result:
            print(res)

    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        history = super().getHistoryData(start_time=start_time, end_time=end_time)

        return history


# 1分鐘線
class MinuteOhlcData(ResourceData):
    def __init__(self, stock_id, latest_time=None,
                 logger_dir="resource_data", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(db_name="stock_data", logger_dir=logger_dir, logger_name=logger_name)
        self.stock_id = stock_id
        self.getDataTable()
        self.last_minute = None
        today = datetime.datetime.today()
        latest_time = datetime.datetime(year=today.year, month=1, day=1) if latest_time is None else latest_time
        self.getLastTime(latest_time=latest_time)

    def setLoggerLevel(self, level: logging.INFO):
        self.logger.setLevel(level)

    def getDataTable(self, table_name="", table_definition=""):
        table_name = f"MINUTE_{self.stock_id}"
        table_definition = """TIME   TEXT    PRIMARY KEY NOT NULL,
        OPEN    TEXT    NOT NULL,
        HIGH    TEXT    NOT NULL,
        LOW     TEXT    NOT NULL,
        CLOSE   TEXT    NOT NULL,
        VOL     INT     NOT NULL"""
        # 1分鐘線: bstrData: 2020/05/07 13:02, 20.049999, 20.100000, 20.000000, 20.000000, 188
        super().getTable(table_name=table_name, table_definition=table_definition)

    def getLastTime(self, latest_time: datetime.datetime):
        def parseTime(str_time):
            return datetime.datetime.strptime(str_time, "%Y/%m/%d %H:%M")

        self.last_minute = self.getLastTimeCore(temp_time=self.last_minute,
                                                latest_time=latest_time,
                                                time_column="TIME",
                                                parseTime=parseTime)

    def getDataInfo(self, is_minute_data: bool = True):
        super().getDataInfo(is_minute_data=True)

    def addData(self, primary_column="TIME", values: list = None, check_sequence=True):
        if len(values) == 0 or values is None:
            self.logger.debug("len(values) == 0 or values is None", extra=self.extra)
            return

        # 對 values 的時間進行排序，根據進行 value[0] 排序
        values.sort(key=lambda value: value[0])

        # 輸入時間為字串，為進行時間上的比較，故須轉型為 datetime
        last_minute = datetime.datetime.strptime(values[-1][0], "%Y/%m/%d %H:%M")
        self.logger.debug(f"last_minute in values: {last_minute}", extra=self.extra)

        # 若 self.last_minute 尚未初始化
        if self.last_minute is None:
            self.last_minute = last_minute
        else:
            # 若加入的數據比最後一筆數據還舊，則直接不加入，因為我是由前往後新增，數據應該越來越新
            # 若加入的數據比較舊，表示應該是之前就加過的
            # check_sequence: 是否檢查時間順序，若不檢查則會由 super().add_ 判斷是否是已添加過的數據
            if (last_minute < self.last_minute) and check_sequence:
                # self.logger.info("新加入數據之時間，較資料庫中最近一筆來的晚，故不加入")
                return

        if last_minute.date() == datetime.date.today():
            self.logger.info(values, extra=self.extra)

        super().add_(primary_column="TIME", values=values)

    def displayMinuteData(self, columns: list = None,
                          sort_by: str = "TIME", sort_type="ASC",
                          limit: int = 20, offset: int = 0):
        result = super().select(table_name=self.table_name, columns=columns,
                                sort_by=sort_by, sort_type=sort_type,
                                limit=limit, offset=offset)

        for res in result:
            print(res)

    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        history = super().getHistoryData(start_time=start_time, end_time=end_time)

        return history


def sortOhlcDatas(ohlc_datas):
    """
    將 Ohlc Data 做排序，排序順序為: 時間(越早越前)
    ohlc_datas -> [stock_id, date, (time, open, high, low, close, volumn)]

    :param ohlc_datas: 所有請求
    :return:
    """

    def compareOhlcDatas(od1, od2):
        """
        sorted()也是一個高階函式，它可以接收一個比較函式來實現自定義排序，
        比較函式的定義是，傳入兩個待比較的元素 x, y，
        如果 x 應該排在 y 的前面，返回 -1，
        如果 x 應該排在 y 的後面，返回 1。
        如果 x 和 y 相等，返回 0。

        def customSort(x, y):
            if x > y:
                return -1
            if x < y:
                return 1
            return 0

        print(sorted([2,4,5,7,3], key=functools.cmp_to_key(customSort)))
        -> [7, 5, 4, 3, 2]

        :param od1: 請求 1
        :param od2: 請求 2
        :return:
        """
        # stock_id, (time, open, high, low, close, volumn) = ohlc_data
        _, date1, (time1, _, _, _, _, _) = od1
        _, date2, (time2, _, _, _, _, _) = od2

        if date1 < date2:
            return -1
        elif date1 > date2:
            return 1
        else:
            # time1 為日線數據，放後面
            if time1 == "":
                return 1

            # time1 為分線數據，放前面
            elif time2 == "":
                return -1

            # time1, time2 都是分線數據
            else:
                if time1 < time2:
                    return -1
                elif time1 > time2:
                    return 1
                else:
                    return 0

    # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
    return sorted(ohlc_datas, key=functools.cmp_to_key(compareOhlcDatas))


if __name__ == "__main__":

    class OhlcDataTester:
        @staticmethod
        def arbitraryTest():
            day_data = DayOhlcData(stock_id="3037")
            datas = day_data.selectTimeFliter(start_time=datetime.datetime(2021, 9, 28),
                                              end_time=datetime.datetime(2021, 10, 5))

            for data in datas:
                print(data)

        @staticmethod
        def checkOhlcDayData():
            day_data = DayOhlcData(stock_id="2812")
            # history = day_data.getHistoryData(end_time=datetime.datetime.today())
            #
            # for key, value in history.items():
            #     print(f"{key}: {value}")
            #
            #     if key == "volumns":
            #         avg_volumn = np.mean(value)
            #         print(f"avg_volumn: {avg_volumn}")

            # head = day_data.head(sort_by="TIME")
            tail = day_data.tail(sort_by="TIME")
            # head_list = list(head)
            tail_list = list(tail)
            # print(head_list)

            for data in tail_list:
                print(data)

            day_data.close()

        @staticmethod
        def testMinuteData(stock_id="2887"):
            minute_data = MinuteOhlcData(stock_id=stock_id)
            # minute_data.displayMinuteData(limit=30, sort_type="DESC")

            head = minute_data.head(sort_by="TIME")
            tail = minute_data.tail(sort_by="TIME")

            head_list = list(head)
            tail_list = list(tail)
            print("head_list\n", head_list)
            print("tail_list\n", tail_list)

            minute_data.close()

        @staticmethod
        def testFliterByTime(stock_id="2331"):
            data = DayOhlcData(stock_id=stock_id)
            print(data.head())
            start_time, end_time, delta_time = data.getTimeSection(is_minute_data=False)
            print(f"TimeSection: {start_time} ~ {end_time} | delta_time: {delta_time}")
            result = data.selectTimeFliter(start_time=datetime.datetime(2019, 12, 10, 9, 0),
                                           end_time=datetime.datetime(2019, 12, 20, 9, 0),
                                           sort_by="TIME")

            for res in result:
                print(res)

            data.close()


    # OhlcDataTester.arbitraryTest()
    # TODO: 重寫 9/28(含) 以後的數據，
    #  正確 ('2021/09/27', '11.55', '11.65', '11.50', '11.55', 6277),
    #  有誤 ('2021/09/28', ' 11.60', ' 11.65', ' 11.55', ' 11.60', 3953) 價格前不應有空格
    OhlcDataTester.checkOhlcDayData()
