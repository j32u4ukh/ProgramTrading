import datetime
from abc import ABCMeta, abstractmethod
from decimal import Decimal, ROUND_HALF_UP

import numpy as np

from submodule.Xu3.database import DataBase


class OhlcDataBase(DataBase, metaclass=ABCMeta):
    def __init__(self, db_name="stock_data", folder="data",
                 logger_dir="ohlc_data", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(db_name=db_name, folder=folder, logger_dir=logger_dir, logger_name=logger_name)

    def __del__(self):
        super().__del__()

    @abstractmethod
    def setLoggerLevel(self, level):
        self.logger.setLevel(level=level)

    @abstractmethod
    def getTable(self, table_name, table_definition):
        super().getTable(table_name=table_name, table_definition=table_definition)

    @abstractmethod
    def getLastTime(self, latest_time: datetime.datetime):
        pass

    @abstractmethod
    def getDataInfo(self, is_minute_data: bool):
        head = self.head(table_name=self.table_name,
                         columns=["TIME", "OPEN"],
                         sort_by="TIME",
                         n_data=1)

        tail = self.tail(table_name=self.table_name,
                         columns=["TIME", "CLOSE"],
                         sort_by="TIME",
                         n_data=1)

        if is_minute_data:
            start_time = datetime.datetime.strptime(head[0][0], "%Y/%m/%d %H:%M")
            end_time = datetime.datetime.strptime(tail[0][0], "%Y/%m/%d %H:%M")

        else:
            start_time = datetime.datetime.strptime(head[0][0], "%Y/%m/%d")
            end_time = datetime.datetime.strptime(tail[0][0], "%Y/%m/%d")

        delta_year = Decimal(str((end_time - start_time) / datetime.timedelta(days=365)))
        open_value = Decimal(head[0][1]).quantize(Decimal('.00'), ROUND_HALF_UP)
        close_value = Decimal(tail[0][1]).quantize(Decimal('.00'), ROUND_HALF_UP)

        delta_price = close_value - open_value
        delta_rate = delta_price / open_value * Decimal("100.0")

        if delta_rate < 0:
            annual_rate_of_return = -np.power(abs(delta_rate), Decimal("1.0") / delta_year)
        else:
            annual_rate_of_return = np.power(delta_rate, Decimal("1.0") / delta_year)

        self.logger.info(f"資料長度: {delta_year}年，年報酬率: {delta_rate.quantize(Decimal('.0000'), ROUND_HALF_UP)}%, "
                         f"年均報酬率: {annual_rate_of_return.quantize(Decimal('.0000'), ROUND_HALF_UP)}%",
                         extra=self.extra)

    @abstractmethod
    def addData(self, primary_column: str, values: list = None, check_sequence=True):
        # super().add_(primary_column=primary_column, values=values)
        super().add(values=values, primary_column=primary_column)

    @abstractmethod
    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        results = self.selectTimeFliter(sort_by="TIME",
                                        sort_type="ASC",
                                        start_time=start_time,
                                        end_time=end_time)

        history_open = None
        history_high = Decimal("0")
        history_low = Decimal("1e5")
        close_value = Decimal("0")
        volumns = []

        for result in results:
            date_time, open_value, high_value, low_value, close_value, volumn = result

            if start_time is None:
                try:
                    start_time = datetime.datetime.strptime(date_time, "%Y/%m/%d")
                except ValueError:
                    start_time = datetime.datetime.strptime(date_time, "%Y/%m/%d %H:%M")

            if history_open is None:
                history_open = Decimal(open_value).quantize(Decimal('.00'), ROUND_HALF_UP)

            history_high = max(history_high, Decimal(high_value))
            history_low = min(history_low, Decimal(low_value))
            volumns.append(volumn)

        if history_open is None:
            history = None

        else:
            history_close = Decimal(close_value).quantize(Decimal('.00'), ROUND_HALF_UP)

            # 所選時間歷經多少年
            during_years = Decimal((end_time - start_time) / datetime.timedelta(days=1) / 365.25)

            # 平均年報酬率
            avg_annual_return = Decimal((history_close - history_open) / history_open / during_years)

            history = dict(open=history_open,
                           high=history_high.quantize(Decimal('.00'), ROUND_HALF_UP),
                           low=history_low.quantize(Decimal('.00'), ROUND_HALF_UP),
                           close=history_close,
                           volumns=volumns,
                           annual_return=avg_annual_return)

        return history

    def getLastTimeCore(self, temp_time, latest_time: datetime.datetime, time_column: str, parseTime=None):
        """
        取得資料庫中最新一筆的時間，並判斷與 latest_time 何者時間更新，返回較新的時間點

        :param temp_time:
        :param latest_time: 預計往回索取到此時間點的數據
        :param time_column:
        :param parseTime:
        :return: 資料庫中最新一筆的時間 or latest_time
        """
        # 檢查表格內是否有內容，不為空，才能取得上次最後一筆數據
        if not self.isTableEmpty(table_name=self.table_name):
            self.logger.debug("Table is not empty.", extra=self.extra)

            # 檢查 temp_time 是否初始化
            if temp_time is None:
                tail = self.tail(table_name=self.table_name,
                                 columns=[time_column],
                                 sort_by=time_column)
                temp_time = parseTime(tail[-1][0])
                self.logger.debug(f"Last time in database: {temp_time}", extra=self.extra)

            # latest_day: 最久只從這天開始記錄，之前資料庫最新一筆(last_day)比它舊也一樣，若比它新則直接使用 last_day
            if temp_time < latest_time:
                temp_time = latest_time
        else:
            temp_time = latest_time
            self.logger.info("Table is empty.", extra=self.extra)

        return temp_time

    def getTimeSection(self, is_minute_data: bool):
        head = self.head(table_name=self.table_name,
                         columns=["TIME"],
                         sort_by="TIME",
                         n_data=1)

        tail = self.tail(table_name=self.table_name,
                         columns=["TIME"],
                         sort_by="TIME",
                         n_data=1)

        if is_minute_data:
            start_time = datetime.datetime.strptime(head[0][0], "%Y/%m/%d %H:%M")
            end_time = datetime.datetime.strptime(tail[0][0], "%Y/%m/%d %H:%M")

        else:
            start_time = datetime.datetime.strptime(head[0][0], "%Y/%m/%d")
            end_time = datetime.datetime.strptime(tail[0][0], "%Y/%m/%d")

        delta_time = end_time - start_time

        return start_time, end_time, delta_time

    def selectTimeFliter(self, table_name: str = None, columns: list = None,
                         sort_by: str = None, sort_type="ASC", limit: int = None,
                         start_time: datetime.datetime = None, end_time: datetime.datetime = None):
        columns_name = self.formatColumns(columns=columns)

        if table_name is None:
            table_name = self.table_name

        sql = f"""SELECT {columns_name} from {table_name}"""

        if start_time is not None and end_time is not None:
            start_time -= datetime.timedelta(seconds=1)
            time_start = start_time.strftime("%Y/%m/%d %H:%M")
            time_end = end_time.strftime("%Y/%m/%d %H:%M")
            sql += f" WHERE '{time_start}' <= TIME AND TIME <= '{time_end}'"
        elif start_time is not None:
            start_time -= datetime.timedelta(seconds=1)
            time_start = start_time.strftime("%Y/%m/%d %H:%M")
            sql += f" WHERE '{time_start}' <= TIME"
        elif end_time is not None:
            time_end = end_time.strftime("%Y/%m/%d %H:%M")
            sql += f" WHERE TIME <= '{time_end}'"

        if sort_by is not None:
            sql += f" ORDER BY {sort_by} {sort_type}"

        if limit is not None:
            sql += f" LIMIT {limit}"

        self.logger.info(f"sql: {sql}", extra=self.extra)

        # result = (time, open, high, low, close, volumn)
        result = self.execute(sql)

        return result


if __name__ == "__main__":
    database = DataBase(db_name="stock_data")
    # database.deleteTable(table_name="STOCK_LIST")
    result = database.getAllTableName()
    print(result)
