import calendar
import datetime
import time
from functools import total_ordering

from dateutil.parser import parse

"""
datetime
struct_date: 還包含"一周的第幾日"、"一年的第幾日"、、、等，應可額外添加是否為交易日等資訊
date
time
timestamp: start from 1970/01/01
stamp: start from now to end of program
---
format(str->time; time->str)
"""

# TODO: @total_ordering 用於簡化物件比較規則的訂定


class JiKan:
    def __init__(self):
        self.current = nowDatetime()

    @staticmethod
    def pdToDatetime(timestamp):
        """
        將 pandas 的時間格式 timestamp 轉換成 Python 內建的時間格式。

        df = pd.DataFrame({"a": ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"],
                   "b": ["2020-02-01", "2020-02-02", "2020-02-03", "2020-02-04"],
                   "c": ["2020-03-01", "2020-03-02", "2020-03-03", "2020-03-04"]})
        df["a"] = pd.to_datetime(df["a"])
        print(df)
        print(df.loc[0, "a"])
        print(type(df.loc[0, "a"]))

        Timestamp = df.loc[0, "a"]
        print(type(Timestamp))
        py_datetime = Timestamp.date()
        print(py_datetime)

        :param timestamp: 利用 pd.to_datetime 將字串轉換成時間
        :return: Python 內建的時間格式
        """
        return timestamp.date()


# @total_ordering
class DateTime(JiKan):
    def __init__(self, year=None, month=None, day=None, hour=None, minute=None, second=None, microsecond=None):
        """
        Date + Time

        now 和 today 實際上應該是等價的
        """
        super().__init__()
        self.year = self.current.year if year is None else year
        self.month = 1 if month is None else month
        self.day = 1 if day is None else day
        self.hour = 0 if hour is None else hour
        self.minute = 0 if minute is None else minute
        self.second = 0 if second is None else second
        self.microsecond = 0 if microsecond is None else microsecond
        self.current_datetime = None

    def __add__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, TimeDelta):
            time_delta = datetime.timedelta(days=other.days, seconds=other.seconds)
            temp_datetime = self.current_datetime + time_delta
            return DateTime.fromDateTimeToMyDateTime(temp_datetime)

    def __sub__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, TimeDelta):
            time_delta = datetime.timedelta(days=other.days, seconds=other.seconds)
            temp_datetime = self.current_datetime - time_delta
            return DateTime.fromDateTimeToMyDateTime(temp_datetime)
        elif isinstance(other, Date) or isinstance(other, DateTime):
            other_datetime = other.toDateTime()
            time_delta = self.current_datetime - other_datetime
            return TimeDelta.fromTimeDelta(time_delta)

    """
    __lt__: <
    __le__: <=
    __gt__: >
    __ge__: >=
    __eq__: ==
    __ne__: !=
    """
    def __lt__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_datetime = other.toDateTime()
            return self.current_datetime < other_datetime

    def __le__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_datetime = other.toDateTime()
            return self.current_datetime <= other_datetime

    def __gt__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_datetime = other.toDateTime()
            return self.current_datetime > other_datetime

    def __ge__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_datetime = other.toDateTime()
            return self.current_datetime >= other_datetime

    def __eq__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_datetime = other.toDateTime()
            return self.current_datetime == other_datetime

    def __ne__(self, other):
        if self.current_datetime is None:
            self.current_datetime = self.toDateTime()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_datetime = other.toDateTime()
            return self.current_datetime != other_datetime

    # def __setattr__(self, key, value):
    #     self.__dict__[key] = value
    #
    # def __getattr__(self, key):
    #     return self.__dict__[key]
    #
    # def __setitem__(self, key, value):
    #     self.__dict__[key] = value
    #
    # def __getitem__(self, key):
    #     return self.__dict__[key]

    def __repr__(self):
        # year=None, month=None, day=None, hour=None, minute=None, second=None, microsecond
        return f"jikan.DateTime(year={self.year}, month={self.month}, day={self.day}, " \
               f"hour={self.hour}, minute={self.minute}, second={self.second}, microsecond={self.microsecond})"

    def __str__(self):
        return "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.{:06d}".format(
            self.year, self.month, self.day, self.hour, self.minute, self.second, self.microsecond)

    @staticmethod
    def fromDateTimeToMyDateTime(date_time):
        return DateTime(date_time.year,
                        date_time.month,
                        date_time.day,
                        date_time.hour,
                        date_time.minute,
                        date_time.second,
                        date_time.microsecond)

    def toDateTime(self):
        return datetime.datetime(self.year,
                                 self.month,
                                 self.day,
                                 self.hour,
                                 self.minute,
                                 self.second,
                                 self.microsecond)

    def toDate(self):
        return datetime.date(self.year, self.month, self.day)

    @staticmethod
    def now() -> datetime.datetime:
        return nowDatetime()

    @staticmethod
    def today() -> datetime.datetime:
        return nowDatetime()

    @staticmethod
    def timedelta():
        pass


# @total_ordering
class StructTime(JiKan):
    def __init__(self):
        super().__init__()

    def toStructTime(self):
        pass


# @total_ordering
class Date(JiKan):
    def __init__(self, year=None, month=None, day=None):
        super().__init__()
        self.year = self.current.year if year is None else year
        self.month = 1 if month is None else month
        self.day = 1 if day is None else day
        self.current_date = None

    def __add__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, TimeDelta):
            time_delta = datetime.timedelta(days=other.days, seconds=other.seconds)
            temp_date = self.current_date + time_delta
            return Date.fromDateToMyDate(temp_date)

    def __sub__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, TimeDelta):
            time_delta = datetime.timedelta(days=other.days, seconds=other.seconds)
            temp_date = self.current_date - time_delta
            return Date.fromDateToMyDate(temp_date)
        elif isinstance(other, Date):
            other_date = other.toDate()
            time_delta = self.current_date - other_date
            return TimeDelta.fromTimeDelta(time_delta)

    """
    __lt__: <
    __le__: <=
    __gt__: >
    __ge__: >=
    __eq__: ==
    __ne__: !=
    """

    def __lt__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_date = other.toDate()
            return self.current_date < other_date

    def __le__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_date = other.toDate()
            return self.current_date <= other_date

    def __gt__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_date = other.toDate()
            return self.current_date > other_date

    def __ge__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_date = other.toDate()
            return self.current_date >= other_date

    def __eq__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_date = other.toDate()
            return self.current_date == other_date

    def __ne__(self, other):
        if self.current_date is None:
            self.current_date = self.toDate()

        if isinstance(other, Date) or isinstance(other, DateTime):
            other_date = other.toDate()
            return self.current_date != other_date

    def __repr__(self):
        return f"jikan.Date({self.year}, {self.month}, {self.day})"

    def __str__(self):
        return f"{self.year}-{self.month}-{self.day}"

    def toDate(self):
        return datetime.date(year=self.year, month=self.month, day=self.day)

    @staticmethod
    def fromDateToMyDate(py_date):
        return Date(year=py_date.year, month=py_date.month, day=py_date.day)

    def toDateTime(self):
        return datetime.datetime(year=self.year, month=self.month, day=self.day)

    @staticmethod
    def now():
        current = nowDatetime()
        return Date(year=current.year, month=current.month, day=current.day)

    @staticmethod
    def today() -> datetime.date:
        return todayDate()

    @staticmethod
    def timedelta():
        pass


@total_ordering
class Hms(JiKan):
    # datetime 的 小時、分、秒 的部分
    def __init__(self, hour=0, minute=0, second=0):
        super().__init__()
        self.minute, self.second = divmod(second, 60)
        self.hour, self.minute = divmod(minute, 60)
        days, self.hour = divmod(self.hour + hour, 24)

        if days > 0:
            print("Hms(JiKan) 範圍為 23:59:59 內，超出天數為:", days)

    def __repr__(self):
        return "Hms({:02d} : {:02d} : {:02d})".format(self.hour, self.minute, self.second)

    __str__ = __repr__

    # region total_ordering: 使得我可以只定義 __eq__ 和 __gt__ 就可進行完整的比較
    # https://python3-cookbook.readthedocs.io/zh_CN/latest/c08/p24_making_classes_support_comparison_operations.html
    def __eq__(self, other):
        return self.hour == other.hour and self.minute == other.minute and self.second == other.second

    def __gt__(self, other):
        # __gt__: 一般排序後會被放在後面
        if self.hour > other.hour:
            return True
        elif self.hour < other.hour:
            return False
        else:
            # self.hour == other.hour
            if self.minute > other.minute:
                return True
            elif self.minute < other.minute:
                return False
            else:
                # self.minute == other.minute
                if self.second > other.second:
                    return True
                else:
                    # self.second <= other.second
                    return False

    def __add__(self, other):
        return Hms(hour=self.hour + other.hour,
                   minute=self.minute + other.minute,
                   second=self.second + other.second)

    def __sub__(self, other):
        return Hms(hour=self.hour - other.hour,
                   minute=self.minute - other.minute,
                   second=self.second - other.second)

    def toMinute(self):
        return self.hour * 60 + self.minute

    def toSecond(self):
        return self.hour * 3600 + self.minute * 60 + self.second

    @staticmethod
    def fromDatetime(date_time: datetime.datetime):
        return Hms(hour=date_time.hour, minute=date_time.minute, second=date_time.second)

    # def __setattr__(self, key, value):
    #     self.__dict__[key] = value
    #
    # def __getattr__(self, key):
    #     return self.__dict__[key]
    #
    # def __setitem__(self, key, value):
    #     self.__dict__[key] = value
    #
    # def __getitem__(self, key):
    #     return self.__dict__[key]

    @staticmethod
    def now():
        pass

    @staticmethod
    def timedelta():
        pass


@total_ordering
class SystemTime(JiKan):
    # datetime 的 小時、分、秒 的部分
    def __init__(self, sys_time=None):
        super().__init__()
        if sys_time is None:
            self.sys_time = time.time()
        else:
            self.sys_time = sys_time

    def __repr__(self):
        return "SystemTime({:04f})".format(self.sys_time)

    __str__ = __repr__

    # region total_ordering: 使得我可以只定義 __eq__ 和 __gt__ 就可進行完整的比較
    # https://python3-cookbook.readthedocs.io/zh_CN/latest/c08/p24_making_classes_support_comparison_operations.html
    def __eq__(self, other):
        return self.sys_time == other.now_sys_time

    def __gt__(self, other):
        return self.sys_time > other.now_sys_time

    def __add__(self, other):
        sys_time = self.sys_time + other.now_sys_time
        return SystemTime(sys_time=sys_time)

    def __sub__(self, other):
        sys_time = self.sys_time - other.now_sys_time
        return SystemTime(sys_time=sys_time)


# @total_ordering
class TimeDelta:
    def __init__(self, days=0, hours=0, minutes=0, seconds=0):
        self.minutes, self.seconds = divmod(seconds, 60)
        self.hours, self.minutes = divmod(self.minutes + minutes, 60)
        self.days, self.hours = divmod(self.hours + hours, 24)
        self.days += days
        self.current_timedelta = self.toTimeDelta()

    def __add__(self, other):
        # 根據運算的對象，返還相同類型的物件
        if isinstance(other, TimeDelta):
            other_timedelta = other.toTimeDelta()
            temp_timedelta = self.current_timedelta + other_timedelta
            return TimeDelta.fromTimeDelta(temp_timedelta)

    def __sub__(self, other):
        # 根據運算的對象，返還相同類型的物件
        if isinstance(other, TimeDelta):
            other_timedelta = other.toTimeDelta()
            temp_timedelta = self.current_timedelta - other_timedelta
            return TimeDelta.fromTimeDelta(temp_timedelta)

    """
    __lt__: <
    __le__: <=
    __gt__: >
    __ge__: >=
    __eq__: ==
    __ne__: !=
    """

    def __eq__(self, other):
        if isinstance(other, TimeDelta):
            other_timedelta = other.toTimeDelta()
            return self.current_timedelta == other_timedelta

    def __gt__(self, other):
        if isinstance(other, TimeDelta):
            other_timedelta = other.toTimeDelta()
            return self.current_timedelta > other_timedelta

    def __repr__(self):
        return f"jikan.TimeDelta(days={self.days}, hours={self.hours}, minutes={self.minutes}, seconds={self.seconds})"

    def __str__(self):
        return "{} days, {:02d}:{:02d}:{:02d}".format(self.days, self.hours, self.minutes, self.seconds)

    def toTimeDelta(self):
        return datetime.timedelta(days=self.days, hours=self.hours, minutes=self.minutes, seconds=self.seconds)

    def toTime(self):
        return datetime.timedelta(days=self.days, hours=self.hours, minutes=self.minutes, seconds=self.seconds)

    @staticmethod
    def fromTimeDelta(time_delta):
        return TimeDelta(days=time_delta.days, seconds=time_delta.seconds)

    @staticmethod
    def delta(seconds=0, minutes=0, hours=0, days=0):
        return datetime.timedelta(seconds=seconds, minutes=minutes, hours=hours, days=days)

    @staticmethod
    def seconds(s):
        return datetime.timedelta(seconds=s)

    @staticmethod
    def minutes(m):
        return datetime.timedelta(minutes=m)

    @staticmethod
    def hours(h):
        return datetime.timedelta(hours=h)

    @staticmethod
    def days(d):
        return datetime.timedelta(days=d)


def nowDatetime() -> datetime.datetime:
    """
    datetime.datetime.now() = datetime.datetime.today()

    :return: ex: 2020-06-26 11:41:04.197777
    """
    return datetime.datetime.now()


def todayDate() -> datetime.date:
    """

    :return: ex: datetime.date(2020, 6, 28)
    """
    return datetime.date.today()


if __name__ == "__main__":
    def buildInFunction():
        # region datetime
        target_month = datetime.datetime(2010, 11, 1)
        target_tuple = target_month.timetuple()
        next_month = datetime.datetime(target_tuple.tm_year, target_tuple.tm_mon + 1, 1)
        last_day = next_month - datetime.timedelta(days=1)
        print(last_day)
        # endregion

        # region struct_date
        """ ============================== struct_date ============================== """
        """時間元組
        很多Python函數用一個元組裝起來的 9 組數字處理時間:
        tm_year(4位數年)      2008
        tm_mon(月)            1 到 12
        tm_mday(日)           1 到 31
        tm_hour(小時)         0 到 23
        tm_min(分鐘)          0 到 59
        tm_sec(秒)            0 到 61 (60 或 61 是閏秒)
        tm_wday(一周的第幾日)  0 到6 (0 是周一)
        tm_yday(一年的第幾日)  1 到 366(儒略歷)
        tm_isdst(夏令時)      -1, 0, 1, -1 是決定是否為夏令時的旗幟
    
        [獲取當前時間]
        從返回浮點數的時間戳方式向時間元組轉換，只要將浮點數傳遞給如 localtime 之類的函數。
    
        time.gmtime([secs])
        接收時間戳（1970紀元後經過的浮點秒數）並返回格林威治天文時間下的時間元組t。註：t.tm_isdst始終為 0"""
        struct_localtime = time.localtime(time.time())
        print("當前時間的時間元組:")
        # time.struct_time(tm_year=2020, tm_mon=3, tm_mday=18,
        #                  tm_hour=9, tm_min=15, tm_sec=31,
        #                  tm_wday=2, tm_yday=78, tm_isdst=0)
        print(struct_localtime)
        week_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        week = week_list[struct_localtime.tm_wday]
        print("week:", week)

        # gmtime: time.struct_time(tm_year=2020, tm_mon=3, tm_mday=18,
        #                          tm_hour=1, tm_min=49, tm_sec=48,
        #                          tm_wday=2, tm_yday=78, tm_isdst=0)
        print("gmtime:", time.gmtime())

        """time.timezone
        屬性time.timezone是當地時區（未啟動夏令時）距離格林威治的偏移秒數（>0，美洲;<=0大部分歐洲，亞洲，非洲）。"""
        print(time.timezone)

        """日歷（Calendar）模塊
        此模塊的函數都是日歷相關的，例如列印某月的字元月歷。
        星期一是默認的每周第一天，星期天是默認的最後一天。更改設置需調用calendar.setfirstweekday()函數。
        模塊包含了以下內置函數："""

        """[獲取某月日歷]
        Calendar模塊有很廣泛的方法用來處理年歷和月歷，例如列印某月的月歷："""
        cal = calendar.month(2020, 6)
        print(cal)

        """ [calendar.calendar]
        返回一個多行字元串格式的 year 年年歷，3 個月一行，間隔距離為 c。
        每日寬度間隔為 w 字元。每行長度為 21 * W + 18 + 2 * C。l 是每星期行數。"""
        calendar_ = calendar.calendar(2020)
        print(calendar_)

        """calendar.isleap(year)
        是閏年返回 True，否則為 False。"""
        print(calendar.isleap(2020))  # True

        # time.struct_time(tm_year=2009, tm_mon=1, tm_mday=1,
        #                  tm_hour=0, tm_min=0, tm_sec=0,
        #                  tm_wday=3, tm_yday=1, tm_isdst=-1)
        print(datetime.datetime(2009, 1, 1).timetuple())

        """獲取任意給定日期所在月份的最後一天"""
        dt = datetime.date(1952, 2, 12)
        print(calendar.monthrange(dt.year, dt.month)[1])

        cal = calendar.month(1952, 2)
        print(cal)
        # endregion

        # region date
        print(datetime.date.today())  # 2020-03-18

        """date: 可運算和比較"""
        today = datetime.date.today()
        the_past = datetime.date(today.year, 1, 1)
        time_to_past = abs(today - the_past)
        print(time_to_past.days)
        # endregion

        # region time
        now = datetime.datetime.now()
        current_time = now
        one_second = datetime.timedelta(seconds=1)
        one_minute = datetime.timedelta(minutes=1)
        one_hour = datetime.timedelta(hours=1)

        for i in range(10):
            current_time += one_second
            current_time += one_minute
            current_time += one_hour
            print(current_time.strftime("%H:%M:%S"))
            time.sleep(1)

        print(now < now + one_second)
        # endregion

        # region timestamp
        """ ============================== timestamp ============================== """
        """[時間戳]都以自從1970年1月1日午夜（歷元）經過了多長時間來表示。
        時間戳單位最適於做日期運算。但是1970年之前的日期就無法以此表示了。
        太遙遠的日期也不行，UNIX和Windows只支持到2038年。"""
        timestamp = time.time()
        print("時間戳:", timestamp)  # 時間戳: 1593139866.2472804

        # 用 unixtimestamp 創建一個 datetime，unixtimestamp 只是以 1970年1月1日為起點記錄的秒數
        mydatetime = datetime.datetime.fromtimestamp(528756281)
        print("mydatetime:", mydatetime)  # mydatetime: 1986-10-04 04:44:41
        print("type:", type(mydatetime))  # mydatetime -> class 'datetime.datetime'
        print(mydatetime.timestamp())  # timestamp: 528756281.0
        # endregion

        # region Stamp
        """	time.clock()
        DeprecationWarning: time.clock has been deprecated in Python 3.3 and will be removed from Python 3.8: 
        use time.perf_counter or time.process_time instead
        用以浮點數計算的秒數返回當前的 CPU 時間。用來衡量不同程式的耗時，比time.time()更有用。"""
        print("time.perf_counter():", time.perf_counter())  # 返回系統執行時間
        print("time.process_time():", time.process_time())  # 返回進程執行時間

        """	time.sleep(secs)
        推遲調用線程的運行，secs指秒數。"""
        for i in range(10):
            print(i)
            time.sleep(1)
        # endregion

        # region Format
        """[獲取格式化的時間]
        你可以根據需求選取各種格式，但是最簡單的獲取可讀的時間模式的函數是asctime()
    
        time.ctime([secs])
        作用相当于asctime(localtime(secs))，未给参数相当于asctime()"""
        localtime = time.asctime(time.localtime(time.time()))
        print("localtime:", localtime)  # localtime: Wed Mar 18 09:47:55 2020
        print("ctime:", time.ctime())  # ctime: Wed Mar 18 09:47:55 2020

        """[格式化日期]
        我們可以使用 time 模塊的 strftime 方法來格式化日期：time.strftime(format[, t])
    
        python中時間日期格式化符號：
        %y 兩位數的年份表示（00-99）
        %Y 四位數的年份表示（000-9999）
        %m 月份（01-12）
        %d 月內中的一天（0-31）
        %H 24小時制小時數（0-23）
        %I 12小時制小時數（01-12）
        %M 分鐘數（00=59）
        %S 秒（00-59）
        %a 本地簡化星期名稱
        %A 本地完整星期名稱
        %b 本地簡化的月份名稱
        %B 本地完整的月份名稱
        %c 本地相應的日期表示和時間表示
        %j 年內的一天（001-366）
        %p 本地A.M.或P.M.的等價符
        %U 一年中的星期數（00-53）星期天為星期的開始
        %w 星期（0-6），星期天為星期的開始
        %W 一年中的星期數（00-53）星期一為星期的開始
        %x 本地相應的日期表示
        %X 本地相應的時間表示
        %Z 當前時區的名稱
        %% %號本身"""
        # 格式化成 2020-03-18 09:28:15 形式
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

        # 格式化成 Wed Mar 18 09:28:35 2020 形式
        print(time.strftime("%a %b %d %H:%M:%S %Y", time.localtime()))

        # 將格式字元串轉換為時間戳，接受時間元組並返回時間戳（1970紀元後經過的浮點秒數）。
        a = "Wed Mar 18 09:28:35 2020"
        print(time.mktime(time.strptime(a, "%a %b %d %H:%M:%S %Y")))

        # 毫秒 -> strftime('%Y-%m-%d %H:%M:%S.%f')

        # 秒數轉時間
        m, s = divmod(time.timezone, 60)
        h, m = divmod(m, 60)
        print("%02d:%02d:%02d" % (h, m, s))

        # 字串轉換為時間
        def strTodatetime(datestr, _format):
            return datetime.datetime.strptime(datestr, _format)

        print(time.strftime("%Y-%m-%d", time.localtime()))  # 2020-03-18
        print(strTodatetime("2020-03-18", "%Y-%m-%d"))  # 2020-03-18 00:00:00
        print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))  # 2020-03-18 10:12:46
        print(strTodatetime("2020-03-18", "%Y-%m-%d") - strTodatetime("2020-02-18", "%Y-%m-%d"))  # 29 days, 0:00:00

        # 格式化
        print(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))  # 2020-03-18 02:16:10

        """如何將字符串日期轉換為 datetime 呢？
        dateutil 中的 parser 模塊可以幫我們將幾乎任何形式的字符串日期數據解析為datetime 對象："""
        print(parse('January 31, 2010'))
        print(parse('31, March 31, 2010, 10:51pm'))

        """如何將 datetime 對象轉換為任何格式的日期？
        你可以用 strftime() 方法將 datetime 對象轉換為幾乎任何日期格式的表現形式。你需要傳入正確日期格式的表示符號作為參數："""
        dt = datetime.datetime(2001, 1, 31, 10, 51, 0)
        print(dt.strftime('%Y-%m-%d %H:%M:%S'))

        """將日期時間轉換為 Year-Qtr 的格式"""
        d1 = datetime.datetime(2010, 9, 28, 10, 40, 59)
        print(f'{d1.year}-Q{d1.month // 4 + 1}')  # 2010-Q3

        date_string = "1994-09-05"
        struct_date1 = parse(date_string)
        struct_date2 = datetime.datetime.strptime(date_string, "%Y-%m-%d")
        print(struct_date1)
        print(struct_date2)
        today = datetime.date.today()
        print(today)
        # endregion

    def computeDate():
        """
        日期(Date)相加減
        """
        today = Date()
        one_day = TimeDelta(days=1)
        yesterday = today - one_day
        tomorrow = today + one_day
        print("today:", today)
        print("one_day:", one_day)
        print("yesterday:", yesterday)
        print("tomorrow:", tomorrow)
        between = tomorrow - yesterday
        print("between:", between)

    def computeDatetime():
        """
        日期(DateTime)相加減
        """
        today = DateTime()
        one_day = TimeDelta(days=1)
        yesterday = today - one_day
        tomorrow = today + one_day
        print("today:", today)
        print("one_day:", one_day)
        print("yesterday:", yesterday)
        print("tomorrow:", tomorrow)
        between = tomorrow - yesterday
        print("between:", between)

    def compareDate():
        d1 = Date(year=2020, month=5, day=3)
        d2 = Date(year=2020, month=4, day=8)
        print(">:", d1 > d2)
        print(">=:", d1 >= d2)
        print("<:", d1 < d2)
        print("<=:", d1 <= d2)
        print("==:", d1 == d2)
        print("!=:", d1 != d2)

    def compareDateTime():
        d1 = DateTime(year=2020, month=5, day=3)
        d2 = DateTime(year=2020, month=4, day=8)
        print(">:", d1 > d2)
        print(">=:", d1 >= d2)
        print("<:", d1 < d2)
        print("<=:", d1 <= d2)
        print("==:", d1 == d2)
        print("!=:", d1 != d2)

    def datetimeToJikan():
        date_time = datetime.datetime(2020, 8, 22, 10, 15, 37)
        jikan_time = Hms.fromDatetime(date_time)
        print(jikan_time)

    # computeDate()
    # computeDatetime()
    # compareDate()
    # compareDateTime()
    datetimeToJikan()
