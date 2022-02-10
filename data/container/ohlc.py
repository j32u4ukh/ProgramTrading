import copy
import datetime
from decimal import Decimal, ROUND_HALF_UP

import numpy as np

from submodule.events import Event


class OhlcContainer:
    def __init__(self, minutes=1, hours=0, days=0):
        self.minutes = minutes
        self.hours = hours
        self.days = days

        self.stop = None
        self.delta_time = datetime.timedelta(days=days, hours=hours, minutes=minutes)

        # region Structure of arrays (SoA) 每個陣列長度都相同
        # Ohlc 物件指針
        self.index = -1

        # Ohlc 物件開始時間
        self.start_datetime = []

        # Ohlc 物件結束時間
        self.stop_datetime = []

        # 開盤價
        self.open = []

        # 最高價
        self.high = []

        # 最低價
        self.low = []

        # 收盤價
        self.close = []

        # 交易量
        self.volumn = []
        # endregion

        self.event = Event()
        self.onOhlcFormed = self.event.onOhlcFormed

    def __repr__(self):
        ohlc = self.getOhlc(n_ohlc=self.__len__(), remove_raw_data=False)
        info = f"OhlcContainer(days={self.days}, hours={self.hours}, minutes={self.minutes})\n"
        info += str(ohlc)

        return info

    __str__ = __repr__

    def __len__(self):
        return len(self.open)

    # 新版輸出格式，1分鐘線。以逗號分開資料。字串。
    # (年/月/日, 時:分, 開盤價, 最高價, 最低價, 收盤價, 成交量)
    def addOhlc(self, date_time: datetime.datetime, open_value: Decimal, high_value: Decimal, low_value: Decimal,
                close_value: Decimal, volumn: int):
        """
        輸入 1 分 K，再根據事前設定的時間區隔，組成新的 Ohlc

        :param date_time: -> datetime.datetime
        :param open_value: -> float
        :param high_value: -> float
        :param low_value: -> float
        :param close_value: -> float
        :param volumn: -> int
        :return:
        """
        if self.stop is None:
            self.newOhlc(date_time, open_value, high_value, low_value, close_value)

        if date_time >= self.stop:
            # Ohlc 物件形成通知
            try:
                self.newOhlc(date_time, open_value, high_value, low_value, close_value)

                self.onOhlcFormed(date_time=self.stop_datetime[self.index],
                                  open_value=self.open[self.index],
                                  high_value=self.high[self.index],
                                  low_value=self.low[self.index],
                                  close_value=self.close[self.index],
                                  volumn=self.volumn[self.index])
            except IndexError:
                print(f"#stop_datetime: {len(self.stop_datetime)}, index: {self.index}")

        # print(f"[addOhlc] {date_time}, {open_value}, {high_value}, {low_value}, {close_value}, {volumn}")
        self.update(high_value, low_value, close_value, volumn)

    def addTick(self, date_time: datetime.datetime, price: Decimal, volumn: int):
        self.addOhlc(date_time, price, price, price, price, volumn)

    def newOhlc(self, date_time: datetime.datetime, open_value: Decimal, high_value: Decimal, low_value: Decimal,
                close_value: Decimal):
        self.index += 1

        start = datetime.datetime(year=date_time.year, month=date_time.month, day=date_time.day,
                                  hour=date_time.hour, minute=date_time.minute)
        self.stop = start + self.delta_time

        # Ohlc 物件開始時間
        self.start_datetime.append(start)

        # Ohlc 物件結束時間
        self.stop_datetime.append(self.stop)

        # 開盤價
        self.open.append(open_value)

        # 最高價
        self.high.append(high_value)

        # 最低價
        self.low.append(low_value)

        # 收盤價
        self.close.append(close_value)

        # 交易量
        self.volumn.append(0)

    def update(self, high_value: Decimal, low_value: Decimal, close_value: Decimal, volumn: int):
        self.high[self.index] = max(self.high[self.index], high_value)
        self.low[self.index] = min(self.low[self.index], low_value)
        self.close[self.index] = close_value
        self.volumn[self.index] += volumn

    def getOhlc(self, n_ohlc=5, remove_raw_data=True):
        """
        將 n_ohlc 個 Ohlc 數據合併成新的 Ohlc 數據

        :param n_ohlc: 由後(較新)往前(較舊)取多少筆數據
        :param remove_raw_data: 是否返回構成此新 Ohlc 數據的原始數據
        :return:
        """
        # Ohlc 物件開始時間
        start_datetime = self.start_datetime[-n_ohlc:]

        # Ohlc 物件結束時間
        stop_datetime = self.stop_datetime[-n_ohlc:]

        # 開盤價
        opens = self.open[-n_ohlc:]

        # 最高價
        highs = self.high[-n_ohlc:]

        # 最低價
        lows = self.low[-n_ohlc:]

        # 收盤價
        closes = self.close[-n_ohlc:]

        # 交易量
        volumns = self.volumn[-n_ohlc:]

        ohlc = Ohlc(minutes=self.minutes, hours=self.hours, days=self.days, remove_raw_data=remove_raw_data)

        if len(start_datetime) > 0:
            ohlc.loadData(start_datetime=start_datetime[0],
                          stop_datetime=stop_datetime[-1],
                          opens=opens,
                          highs=highs,
                          lows=lows,
                          closes=closes,
                          volumns=volumns)

        return ohlc

    def getLastValue(self, kind="close", n_ohlc=1):
        if self.__len__() == 0:
            date_kind = ["start", "stop"]

            if kind in date_kind:
                return datetime.datetime.today()
            else:
                return Decimal("0")
        else:
            if kind == "open":
                value = self.open[-n_ohlc:]
            elif kind == "high":
                value = self.high[-n_ohlc:]
            elif kind == "low":
                value = self.low[-n_ohlc:]
            elif kind == "volumn":
                value = self.volumn[-n_ohlc:]
            elif kind == "start":
                value = self.start_datetime[-n_ohlc:]
            elif kind == "stop":
                value = self.stop_datetime[-n_ohlc:]
            else:
                value = self.close[-n_ohlc:]

            if n_ohlc == 1:
                return value[0]
            else:
                return value

    def getSpread(self, n_ohlc=5):
        # 最高價
        high_value = np.max(self.high[-n_ohlc:])

        # 最低價
        low_value = np.min(self.low[-n_ohlc:])

        return high_value - low_value

    def reset(self):
        # Ohlc 物件指針
        self.index = -1

        self.stop = None

        # Ohlc 物件開始時間
        self.start_datetime = []

        # Ohlc 物件結束時間
        self.stop_datetime = []

        # 開盤價
        self.open = []

        # 最高價
        self.high = []

        # 最低價
        self.low = []

        # 收盤價
        self.close = []

        # 交易量
        self.volumn = []


class Ohlc:
    """
    目前最小單位為一分鐘，再透過組合這些數據，形成 5 分 K，小時 K 等數據。

    3. 新版輸出格式，1分鐘線。以逗號分開資料。 以字串回傳。
        (年/月/日, 時:分, 開盤價, 最高價, 最低價, 收盤價, 成交量)
    例："2016/08/04, 09:01, 34.900002, 34.900002, 34.799999, 34.900002, 67"
    """

    def __init__(self, minutes=1, hours=0, days=0, remove_raw_data=True):
        self.minutes = minutes
        self.hours = hours
        self.days = days
        self.timedelta = datetime.timedelta(minutes=self.minutes, hours=self.hours, days=self.days)
        self.remove_raw_data = remove_raw_data

        self.start_datetime = None
        self.stop_datetime = None

        # 數據儲存(原本為了拆分和組合不同時間區段的 Ohlc 而採用 DataFrame 儲存，但好像不是那麼必要，故改為儲存 4 個關鍵數值即可)
        # 開盤價
        self.open = None
        self.opens = []

        # 最高價
        self.high = None
        self.highs = []

        # 最低價
        self.low = None
        self.lows = []

        # 收盤價
        self.close = None
        self.closes = []

        # 交易量
        self.volumn = 0
        self.volumns = []

    def __len__(self):
        return len(self.opens)

    def __repr__(self):
        if self.open is not None:
            info = "Ohlc(open: {:.4f}, high: {:.4f}, low: {:.4f}, close: {:.4f}, volumn: {})".format(
                self.open, self.high, self.low, self.close, self.volumn)
            during = self.stop_datetime - self.start_datetime
            info += f"\n{self.start_datetime} ~ {self.stop_datetime}, during: {during}\n"

            if self.__len__() > 0:
                info += f"n_ohlc: {self.__len__()}"

            return info
        else:
            return "Ohlc(None)"

    __str__ = __repr__

    def __copy__(self):
        copy_instance = Ohlc(minutes=self.minutes, hours=self.hours, days=self.days,
                             remove_raw_data=self.remove_raw_data)
        copy_instance.start_datetime = self.start_datetime
        copy_instance.stop_datetime = self.stop_datetime
        copy_instance.open = self.open
        copy_instance.high = self.high
        copy_instance.low = self.low
        copy_instance.close = self.close
        copy_instance.volumn = self.volumn

        if not self.remove_raw_data:
            copy_instance.opens = copy.deepcopy(self.opens)
            copy_instance.highs = copy.deepcopy(self.highs)
            copy_instance.lows = copy.deepcopy(self.lows)
            copy_instance.closes = copy.deepcopy(self.closes)
            copy_instance.volumns = copy.deepcopy(self.volumns)
        return copy_instance

    def addOhlc(self, date_time: datetime.datetime, open_value: Decimal, high_value: Decimal, low_value: Decimal,
                close_value: Decimal, volumn: int):
        if self.open is None:
            self.open = open_value
            self.high = high_value
            self.low = low_value

            self.start_datetime = datetime.datetime(year=date_time.year, month=date_time.month, day=date_time.day,
                                                    hour=date_time.hour, minute=date_time.minute)
            self.stop_datetime = self.start_datetime + self.timedelta

        if date_time < self.stop_datetime:
            self.high = max(self.high, high_value)
            self.low = min(self.low, low_value)
            self.close = close_value
            self.volumn += volumn

            if not self.remove_raw_data:
                self.opens.append(open_value)
                self.highs.append(high_value)
                self.lows.append(low_value)
                self.closes.append(close_value)
                self.volumns.append(volumn)
        else:
            raise IndexError

    def addTick(self, date_time, price, volumn):
        self.addOhlc(date_time, price, price, price, price, volumn)

    def loadData(self, start_datetime, stop_datetime, opens, highs, lows, closes, volumns):
        self.start_datetime = start_datetime
        self.stop_datetime = stop_datetime

        # 不移除原始數據
        if not self.remove_raw_data:
            # 開盤價
            self.opens = opens

            # 最高價
            self.highs = highs

            # 最低價
            self.lows = lows

            # 收盤價
            self.closes = closes

            # 交易量
            self.volumns = volumns

        if len(opens) > 0:
            self.open = opens[0]
            self.high = np.max(highs)
            self.low = np.min(lows)
            self.close = closes[-1]
            self.volumn = np.sum(volumns)

    def getData(self):
        return self.start_datetime, self.stop_datetime, self.open, self.high, self.low, self.close, self.volumn

    def getDatas(self, kind="close"):
        if kind == "open":
            return copy.deepcopy(self.opens)
        elif kind == "high":
            return copy.deepcopy(self.highs)
        elif kind == "low":
            return copy.deepcopy(self.lows)
        elif kind == "volumn":
            return copy.deepcopy(self.volumns)
        else:
            return copy.deepcopy(self.closes)

    def getSpread(self):
        if self.high is not None:
            return self.high - self.low
        else:
            return Decimal("0")

    def getPriceDerivatives(self, kind):
        derivatives = []

        if kind == "open":
            prices = copy.deepcopy(self.opens)
        elif kind == "high":
            prices = copy.deepcopy(self.highs)
        elif kind == "low":
            prices = copy.deepcopy(self.lows)
        else:
            prices = copy.deepcopy(self.closes)

        n_price = len(prices)

        for i in range(1, n_price):
            derivatives.append(prices[i] - prices[i - 1])

        return derivatives

    def getDirection(self):
        # 計算變化率
        delta = ((self.close - self.open) / self.open).quantize(Decimal('.0000'), ROUND_HALF_UP)

        # 計算邊際變化率
        margin_delta = (delta / Decimal(str(len(self)))).quantize(Decimal('.0000'), ROUND_HALF_UP)

        return margin_delta, delta


if __name__ == "__main__":
    from data.container import ohlcGenerator


    class OhlcTester:
        @staticmethod
        def testTickOhlc():
            ohlc = Ohlc(minutes=1, remove_raw_data=False)

            datas = [(datetime.datetime(2020, 6, 4, 9, 5, 3), Decimal("30.5"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 5, 5), Decimal("29"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 5, 29), Decimal("28.7"), 1),
                     (datetime.datetime(2020, 6, 4, 9, 5, 35), Decimal("32.2"), 9),
                     (datetime.datetime(2020, 6, 4, 9, 5, 43), Decimal("30.5"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 5, 57), Decimal("29.5"), 3),

                     # 超過時間區段的數據 -> 順利 raise IndexError
                     # (datetime.datetime(2020, 6, 4, 9, 6, 57), 29.5, 3)
                     ]

            for data in datas:
                ohlc.addTick(*data)

            print(ohlc)
            print(ohlc.opens)
            print(ohlc.highs)
            print(ohlc.lows)
            print(ohlc.closes)
            print(ohlc.volumns)

        @staticmethod
        def testAddOhlc():
            ohlc = Ohlc(minutes=5, remove_raw_data=False)

            datas = [(datetime.datetime(2020, 6, 4, 9, 1, 3), Decimal("29"), Decimal("30.5"), Decimal("28.7"),
                      Decimal("28.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 2, 29), Decimal("28.7"), Decimal("32.2"), Decimal("28.7"),
                      Decimal("30.5"), 1),
                     (datetime.datetime(2020, 6, 4, 9, 3, 43), Decimal("30.5"), Decimal("30.5"), Decimal("29.5"),
                      Decimal("29.5"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 4, 57), Decimal("29.5"), Decimal("30.5"), Decimal("28.3"),
                      Decimal("29.3"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 5, 43), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 2),

                     # 超過時間區段的數據 -> 順利 raise IndexError
                     # (datetime.datetime(2020, 6, 4, 9, 6, 57), 29.5, 30.5, 29.3, 29.7, 3)
                     ]

            for data in datas:
                ohlc.addOhlc(*data)

            print(ohlc)
            print(ohlc.opens)
            print(ohlc.highs)
            print(ohlc.lows)
            print(ohlc.closes)
            print(ohlc.volumns)

        @staticmethod
        def testOhlcContainer():
            def onOhlcFormedListener(date_time, open_value, high_value, low_value, close_value, volumn):
                print(f"onOhlcFormedListener: ({date_time}, {open_value}, {high_value}, {low_value}, "
                      f"{close_value}, {volumn})")

            datas = [(datetime.datetime(2020, 6, 4, 9, 1, 3), Decimal("29"), Decimal("30.5"), Decimal("28.7"),
                      Decimal("28.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 2, 29), Decimal("28.7"), Decimal("32.2"), Decimal("28.7"),
                      Decimal("30.5"), 1),
                     (datetime.datetime(2020, 6, 4, 9, 3, 43), Decimal("30.5"), Decimal("30.5"), Decimal("29.5"),
                      Decimal("29.5"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 4, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.3"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 5, 43), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 6, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 7, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 3),
                     ]

            ohlc_container = OhlcContainer(minutes=2)
            ohlc_container.onOhlcFormed += onOhlcFormedListener

            for data in datas:
                ohlc_container.addOhlc(*data)

            print(ohlc_container.getLastValue(kind="close"))

        @staticmethod
        def testGetSpread():
            datas = [(datetime.datetime(2020, 6, 4, 9, 1, 3), Decimal("29"), Decimal("30.5"), Decimal("28.7"),
                      Decimal("28.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 2, 29), Decimal("28.7"), Decimal("32.2"), Decimal("28.7"),
                      Decimal("30.5"), 1),
                     (datetime.datetime(2020, 6, 4, 9, 3, 43), Decimal("30.5"), Decimal("30.5"), Decimal("29.5"),
                      Decimal("29.5"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 4, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.3"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 5, 43), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 6, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 7, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 3),
                     ]

            ohlc_container = OhlcContainer(minutes=1)

            for data in datas:
                ohlc_container.addOhlc(*data)

            n_ohlc = len(ohlc_container)
            print(f"n_ohlc: {n_ohlc}")
            print(ohlc_container)

            for i in range(3, n_ohlc):
                print(f"{i}, spread: {ohlc_container.getSpread(n_ohlc=i)}")

            print()
            ohlc = ohlc_container.getOhlc(n_ohlc=len(ohlc_container), remove_raw_data=False)
            print(ohlc.opens)
            print(ohlc.highs)
            print(ohlc.lows)
            print(ohlc.closes)
            print(ohlc.volumns)

        @staticmethod
        def testOhlcContainerWithGenerator():
            def onOhlcFormedListener(date_time: datetime.datetime, open_value: Decimal, high_value: Decimal,
                                     low_value: Decimal, close_value: Decimal, volumn: int):
                print(f"onOhlcFormedListener: ({date_time}, {open_value}, {high_value}, {low_value}, "
                      f"{close_value}, {volumn})")

            ohlc_container = OhlcContainer(minutes=2)
            ohlc_container.onOhlcFormed += onOhlcFormedListener

            og = ohlcGenerator(init_value=28, ohlc_time=datetime.datetime(year=1984, month=6, day=4),
                               offset=(1 / 1.05 + 0.01, 1.05))

            for i in range(10):
                data = next(og)
                ohlc_container.addOhlc(*data)

            print(ohlc_container)
            ohlc = ohlc_container.getOhlc(n_ohlc=len(ohlc_container), remove_raw_data=False)
            print(ohlc.opens)
            print(ohlc.highs)
            print(ohlc.lows)
            print(ohlc.closes)
            print(ohlc.volumns)


    OhlcTester.testOhlcContainer()
