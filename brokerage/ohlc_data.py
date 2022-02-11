from abc import abstractmethod
from functools import total_ordering

from enums import OhlcType


@total_ordering
class OhlcData:
    """
    適用於 年/月/日/分 線數據，提供 MetaDataLoader 數據依據時間進行排序
    """

    def __init__(self, stock_id: str, ohlc_type: int, date: str, time: str,
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

    # region total_ordering: 使得可以只定義 __eq__ 和 __gt__ 就可進行完整的比較
    # https://python3-cookbook.readthedocs.io/zh_CN/latest/c08/p24_making_classes_support_comparison_operations.html
    def __eq__(self, other):
        return self.date == other.date and self.ohlc_type == other.ohlc_type

    def __gt__(self, other):
        # __gt__: 一般排序後會被放在後面
        if self.date > other.date:
            return True
        elif self.date < other.date:
            return False
        else:
            # 分/日/月/年 依序放後面
            # TODO: 考慮 月/年 線數據傳入的日期
            return self.ohlc_type > other.ohlc_type

    # endregion

    @abstractmethod
    def formData(self):
        ohlcv = f"{self.open_value}, {self.high_value}, {self.low_value}, {self.close_value}, {self.volumn}"

        if self.ohlc_type == OhlcType.Day:
            return self.stock_id, f"{self.date}, {ohlcv}"
        elif self.ohlc_type == OhlcType.Minute:
            return self.stock_id, f"{self.date} {self.time}, {ohlcv}"
