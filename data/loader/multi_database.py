import datetime
import random
from collections import defaultdict

import dateutil.parser as time_parser

from data.container.ohlc_data import OhlcData
from data.database.day_ohlc_data import DayOhlcData
from data.loader import DataLoader
from enums import OhlcType


class MultiDatabaseLoader(DataLoader):
    # TODO: 應同時提供分線和日線數據
    def __init__(self, logger_dir="database_loader", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(logger_dir=logger_dir, logger_name=logger_name)
        self.stocks = []

        self.start_time = None
        self.end_time = None

        # 每次儲存一天內的數據，供外部遍歷呼叫
        self.day_ohlcs = None

        # TODO: ohlcs_dict 利用 OhlcType 作為 key，區分日線數據或分線數據，而非分別使用 self.day_ohlc 和 self.minute_ohlc
        self.day_ohlc = dict()
        self.minute_ohlc = dict()

    def __iter__(self):
        for day_ohlc in self.day_ohlcs:
            # 一次呼叫，回傳一天的數據
            yield day_ohlc

    def setLoggerLevel(self, level):
        self.logger.setLevel(level=level)

    def subscribe(self, ohlc_type: OhlcType, request_ohlcs: list):
        if ohlc_type == OhlcType.Day:
            for request_ohlc in request_ohlcs:
                if not self.day_ohlc.__contains__(request_ohlc):
                    self.day_ohlc[request_ohlc] = DayOhlcData(stock_id=request_ohlc,
                                                              logger_dir=self.logger_dir,
                                                              logger_name=self.logger_name)

        elif ohlc_type == OhlcType.Minute:
            for request_ohlc in request_ohlcs:
                if not self.minute_ohlc.__contains__(request_ohlc):
                    # self.minute_ohlc[request_ohlc] = MinuteOhlcData(stock_id=request_ohlc,
                    #                                                 logger_dir=self.logger_dir,
                    #                                                 logger_name=self.logger_name)

                    # NOTE: 暫時用 DayOhlcData 提供數據來測試程式邏輯
                    self.minute_ohlc[request_ohlc] = DayOhlcData(stock_id=request_ohlc,
                                                                 logger_dir=self.logger_dir,
                                                                 logger_name=self.logger_name)

    def getRequestStockNumber(self, ohlc_type: OhlcType):
        if ohlc_type == OhlcType.Day:
            return len(self.day_ohlc)

        elif ohlc_type == OhlcType.Minute:
            return len(self.minute_ohlc)

        else:
            return 0

    def getRequestStocks(self, ohlc_type: OhlcType):
        request_stocks = []

        if ohlc_type == OhlcType.Day:
            for stock_id in self.day_ohlc.keys():
                request_stocks.append(stock_id)

        elif ohlc_type == OhlcType.Minute:
            for stock_id in self.minute_ohlc.keys():
                request_stocks.append(stock_id)

        return request_stocks

    # def setTimeRange(self, start_time: datetime.datetime = None, end_time: datetime.datetime = None):
    #     if start_time is None:
    #         start_time = datetime.datetime.today() - datetime.timedelta(days=2000)
    #
    #     if end_time is None:
    #         end_time = datetime.datetime.today()
    #
    #     self.start_time = start_time
    #     self.end_time = end_time

    # TODO: 或許可在這裡額外添加 08:30/(13:25/13:30)/14:00 等時間戳，用以協助推動時間
    def loadData(self, start_time: datetime.datetime, end_time: datetime.datetime):
        self.day_ohlcs = []

        temp_minute_times = ["08:30", "09:00", "09:30", "10:30", "11:30", "12:30", "13:25", "13:30", "14:00"]

        # 以日期為 key，儲存同一天的數據
        day_map = defaultdict(list)

        # region Minute
        for stock_id, minute_ohlc in self.minute_ohlc.items():
            # [start_time, end_time] 開始和結束時間點都包含
            ohlcs = minute_ohlc.selectTimeFliter(start_time=start_time, end_time=end_time)

            for ohlc in ohlcs:
                date_time, o, h, l, c, v = ohlc

                # NOTE: 暫時測試用
                rand = random.randint(0, 4)
                date = date_time
                time = temp_minute_times[rand]

                # TODO: 實際接上 MinuteOhlcData 後，使用下方程式將
                # date, time = date_time.split(" ")
                # self.datas.append([stock_id, date_time[0], (date_time[1], o, h, l, c, v)])

                # 以日期為 key，儲存同一天的數據
                ohlc_data = OhlcData(stock_id=stock_id, ohlc_type=OhlcType.Minute, date=date, time=time,
                                     open_value=o, high_value=h, low_value=l, close_value=c, volumn=v)
                day_map[date].append(ohlc_data)
        # endregion

        # region Day
        for stock_id, day_ohlc in self.day_ohlc.items():
            ohlcs = day_ohlc.selectTimeFliter(start_time=start_time,
                                              end_time=end_time,
                                              sort_by="TIME")

            for ohlc in ohlcs:
                date, o, h, l, c, v = ohlc

                # 以日期為 key，儲存同一天的數據
                ohlc_data = OhlcData(stock_id=stock_id, ohlc_type=OhlcType.Day, date=date, time="",
                                     open_value=o, high_value=h, low_value=l, close_value=c, volumn=v)
                day_map[date].append(ohlc_data)
        # endregion

        days = list(day_map.keys())
        days.sort()
        self.logger.info(f"days: {days}", extra=self.extra)

        for date in days:
            # 將日線數據排到同一天的分線數據之後
            # stock_id, day, ("", o, h, l, c, v) = day_data
            day_datas = OhlcData.sorted(day_map[date])

            # day_ohlc = []
            #
            # # 將'同一天'的數據，存到 day_ohlc
            # for data in day_datas:
            #     # time(不包含 date，若為日線數據，則以 "" 呈現), o, h, l, c, v = ohlc
            #     stock_id, date, ohlc = data
            #
            #     if ohlc[0] == "":
            #         date_time = date
            #     else:
            #         date_time = " ".join([date, ohlc[0]])
            #
            #     ohlc_data = f"{date_time}, {ohlc[1]}, {ohlc[2]}, {ohlc[3]}, {ohlc[4]}, {ohlc[5]}"
            #     day_ohlc.append((stock_id, ohlc_data))

            self.day_ohlcs.append((time_parser.parse(date), day_datas))

    def close(self):
        for day_ohlc in self.day_ohlc.values():
            day_ohlc.close(auto_commit=True)

        for minute_ohlc in self.minute_ohlc.values():
            minute_ohlc.close(auto_commit=True)


if __name__ == "__main__":
    loader = MultiDatabaseLoader()
    loader.subscribe(ohlc_type=OhlcType.Day, request_ohlcs=["2812", "6005"])
    loader.subscribe(ohlc_type=OhlcType.Minute, request_ohlcs=["2812", "6005"])

    loader.loadData(start_time=datetime.datetime(2021, 8, 1, 7, 0, 0),
                    end_time=datetime.datetime(2021, 8, 10, 19, 0, 0))

    for data_time, datas in loader:
        print(f"Day start: {data_time.date()}")

        for data in datas:
            stock_id, ohlc_data = data.formData()
            print(f"({stock_id}) {data.ohlc_type} ohlc_data: {ohlc_data}")

        print(f"Day end: {data_time.date()}")
