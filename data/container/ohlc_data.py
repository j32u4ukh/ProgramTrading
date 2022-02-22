import datetime
import functools
from abc import abstractmethod
from functools import total_ordering
import dateutil.parser as time_parser
from enums import OhlcType


class OhlcData:
    """
    適用於 年/月/日/分 線數據，提供 MetaDataLoader 數據依據時間進行排序
    """

    def __init__(self, stock_id: str, ohlc_type: OhlcType, date: str, time: str,
                 open_value: str, high_value: str, low_value: str, close_value: str, volumn: str):
        self.stock_id = stock_id
        self.ohlc_type = ohlc_type

        # TODO: 傳入參數合併為 date_time，再自行分割成 self.date 和 self.time
        self.date_time = ""
        self.date = date
        self.time = time

        self.open_value = open_value
        self.high_value = high_value
        self.low_value = low_value
        self.close_value = close_value
        self.volumn = volumn

    def __repr__(self):
        _, data = self.formData()

        return f"OhlcData({self.stock_id}, {self.ohlc_type} | {data})"

    __str__ = __repr__

    @staticmethod
    def sorted(ohlc_datas):
        def compareOhlcDatas(data1: OhlcData, data2: OhlcData):
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

            :param data1: 請求 1
            :param data2: 請求 2
            :return:
            """
            if data1.date > data2.date:
                return 1
            elif data1.date < data2.date:
                return -1

            # 分/日/月/年 依序放後面
            # TODO: 考慮 月/年 線數據傳入的日期
            if data1.ohlc_type.value > data2.ohlc_type.value:
                return 1
            elif data1.ohlc_type.value < data2.ohlc_type.value:
                return -1

            if data1.time > data2.time:
                return 1
            elif data1.time < data2.time:
                return -1
            else:
                return 0

        # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
        return sorted(ohlc_datas, key=functools.cmp_to_key(compareOhlcDatas))

    @abstractmethod
    def formData(self):
        ohlcv = f"{self.open_value}, {self.high_value}, {self.low_value}, {self.close_value}, {self.volumn}"

        if self.ohlc_type == OhlcType.Day:
            return self.stock_id, f"{self.date}, {ohlcv}"

        elif self.ohlc_type == OhlcType.Minute:
            return self.stock_id, f"{self.date} {self.time}, {ohlcv}"


if __name__ == "__main__":
    data0 = OhlcData(stock_id="2812", ohlc_type=OhlcType.Minute, date="2021/08/05", time="11:30",
                     open_value="11.95", high_value="12.00", low_value="11.90", close_value="12.00", volumn="3835")
    data1 = OhlcData(stock_id="6005", ohlc_type=OhlcType.Minute, date="2021/08/05", time="12:12",
                     open_value="15.90", high_value="16.00", low_value="15.80", close_value="15.85", volumn="2839")
    data2 = OhlcData(stock_id="9527", ohlc_type=OhlcType.Minute, date="2021/08/05", time="09:29",
                     open_value="15.90", high_value="16.00", low_value="15.80", close_value="15.85", volumn="2839")

    datas = [data0, data1, data2]
    datas = OhlcData.sorted(datas)

    for data in datas:
        print(data)

    # dt0 = datetime.datetime(2021, 8, 5, 11, 28)
    # dt1 = datetime.datetime(2021, 8, 5, 12, 0)
    # dt2 = datetime.datetime(2021, 8, 5, 11, 29)
    # dts = [dt0, dt1, dt2]
    # dts = sorted(dts)
    #
    # for dt in dts:
    #     print(dt)
