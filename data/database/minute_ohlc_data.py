import datetime
import logging

from data.database.ohlc_data import OhlcDataBase


# 1分鐘線
class MinuteOhlcData(OhlcDataBase):
    def __init__(self, stock_id, folder="data", latest_time=None,
                 logger_dir="ohlc_data", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(db_name="stock_data", folder=folder, logger_dir=logger_dir, logger_name=logger_name)
        self.stock_id = stock_id
        self.getTable()
        self.last_minute = None
        today = datetime.datetime.today()
        latest_time = datetime.datetime(year=today.year, month=1, day=1) if latest_time is None else latest_time
        self.getLastTime(latest_time=latest_time)

    def setLoggerLevel(self, level: logging.INFO):
        self.logger.setLevel(level)

    def getTable(self, table_name="", table_definition=""):
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

        super().addData(primary_column="TIME", values=values)

    def getHistoryData(self, end_time: datetime.datetime, start_time: datetime.datetime = None):
        history = super().getHistoryData(start_time=start_time, end_time=end_time)

        return history


if __name__ == "__main__":

    class MinuteOhlcDataTester:
        def __init__(self, stock_id):
            self.minute_data = MinuteOhlcData(stock_id=stock_id)

        def __del__(self):
            self.minute_data.close()

        def display(self, columns: list = None, sort_by: str = "TIME", sort_type="ASC",
                    limit: int = 20, offset: int = 0):
            result = self.minute_data.select(columns=columns, sort_by=sort_by, sort_type=sort_type,
                                             limit=limit, offset=offset)

            for res in result:
                print(res)

        def checkMinuteOhlcData(self):
            head = self.minute_data.head(sort_by="TIME")
            tail = self.minute_data.tail(sort_by="TIME")

            head_list = list(head)
            tail_list = list(tail)
            print("head_list\n", head_list)
            print("tail_list\n", tail_list)
