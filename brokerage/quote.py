import datetime
import logging
import math
from data.loader.multi_database_loader import MultiDatabaseLoader
from enums import OhlcType
from submodule.Xu3.utils import getLogger
from submodule.events import Event


class Quote:
    """ 報價系統
    接受報價訂閱，並廣播價格(有訂閱的策略才會接收到)
    """

    def __init__(self, logger_dir="brokerage", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__()
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)
        self.logger.setLevel(logging.DEBUG)

        self.loader = MultiDatabaseLoader(logger_dir=self.logger_dir,
                                          logger_name=self.logger_name)

        self.event = Event()

        # onDayOhlcNotify(stock_id, ohlc_data)
        self.onDayOhlcNotify = self.event.onDayOhlcNotify

        # onMinuteOhlcNotify(stock_id, ohlc_data)
        self.onMinuteOhlcNotify = self.event.onMinuteOhlcNotify

        self.onDayStart = self.event.onDayStart
        self.onDayEnd = self.event.onDayEnd

    def setLoggerLevel(self, level):
        self.logger.setLevel(level=level)
        self.loader.setLoggerLevel(level=level)

    def setDayOhlcNotifyListener(self, listener):
        self.onDayOhlcNotify += listener

    def setMinuteOhlcNotifyListener(self, listener):
        self.onMinuteOhlcNotify += listener

    def subscribe(self, ohlc_type: OhlcType, request_ohlcs: list):
        self.loader.subscribe(ohlc_type=ohlc_type, request_ohlcs=request_ohlcs)

    def dayStart(self, day: datetime.date):
        self.logger.info(f"Day {day} start.", extra=self.extra)
        # self.pause()
        self.onDayStart(day)

    def dayEnd(self, day: datetime.date):
        self.logger.info(f"Day {day} end.", extra=self.extra)
        # self.pause()
        self.onDayEnd(day)

    def run(self, start_time: datetime.datetime, end_time: datetime.datetime):
        n_day = (end_time - start_time).days
        self.logger.debug(f"#time: {n_day}", extra=self.extra)

        n_day_request = self.loader.getRequestStockNumber(OhlcType.Day)
        n_minute_request = self.loader.getRequestStockNumber(OhlcType.Minute)
        self.logger.debug(f"#day: {n_day_request}, #minute: {n_minute_request}", extra=self.extra)

        # n_request = (n_day_request + n_minute_request * 270) * n_day
        n_request = (n_day_request + n_minute_request * 500) * n_day
        self.logger.debug(f"#request: {n_request}, patch_days: {math.ceil(50000.0 / n_request)}", extra=self.extra)

        current_time = start_time

        # n_request = 25000 -> 一次取得 2 天的數據；n_request = 15000 -> 一次取得 3.33 天(無條件進位為 4 天)的數據
        # n_request ≧ 50000 -> 一次取得 1 天的數據
        time_delta = datetime.timedelta(days=math.floor(50000.0 / n_request))
        self.logger.debug(f"time_delta: {time_delta}", extra=self.extra)

        next_current = time_delta + datetime.timedelta(days=1)

        while current_time <= end_time:
            pause_time = min(current_time + time_delta, end_time)
            self.logger.info(f"start_time: {current_time}, end_time: {pause_time}", extra=self.extra)

            # 一次讀取部分數據
            # TODO: buildByDatas 數據產生器，提供 start_time 到 end_time 之間的數據
            self.loader.buildByDatas(start_time=current_time, end_time=pause_time)

            # TODO: 1989/06/04 start or end 都只會觸發一次，不因多支股票而重複被呼叫

            for day, day_datas in self.loader:
                self.dayStart(day=day.date())

                for day_data in day_datas:
                    stock_id, ohlc_data = day_data.formData()

                    if day_data.ohlc_type == OhlcType.Minute:
                        self.onMinuteOhlcNotify(stock_id, ohlc_data)

                    elif day_data.ohlc_type == OhlcType.Day:
                        self.onDayOhlcNotify(stock_id, ohlc_data)

                    self.logger.debug(f"stock_id: {stock_id}, ohlc_data: {ohlc_data}", extra=self.extra)

                self.dayEnd(day=day.date())

            current_time += next_current


if __name__ == "__main__":
    def onOhlcNotifyListener(stock_id, ohlc_data):
        print(f"[onOhlcNotifyListener] stock_id: {stock_id}, ohlc_data: {ohlc_data}")


    quote = Quote()
    quote.setLoggerLevel(level=logging.DEBUG)
    quote.setDayOhlcNotifyListener(listener=onOhlcNotifyListener)
    quote.onMinuteOhlcNotify(listener=onOhlcNotifyListener)
    request_ohlcs = []

    quote.subscribe(ohlc_type=OhlcType.Day, request_ohlcs=request_ohlcs)
    quote.subscribe(ohlc_type=OhlcType.Minute, request_ohlcs=request_ohlcs)
    quote.run(start_time=datetime.datetime(2021, 7, 1), end_time=datetime.datetime(2021, 7, 10))
