import datetime

from enums import OrderMode
import logging
from submodule.Xu3.utils import getLogger


class StopValueError(Exception):
    def __init__(self, order_mode, origin_value, new_value):
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
                                logger_level=logging.ERROR,
                                to_file=True,
                                time_file=False,
                                file_dir="error",
                                instance=True)

        self.order_mode = order_mode
        if order_mode == OrderMode.Long:
            self.message = "做多時，stop value 應越來越高"
        elif order_mode == OrderMode.Short:
            self.message = "做空時，stop value 應越來越低"

        self.origin_value = origin_value
        self.new_value = new_value

    def __str__(self):
        if self.order_mode == OrderMode.Long:
            msg = f"{self.message} ({self.origin_value} < {self.new_value})"
        elif self.order_mode == OrderMode.Short:
            msg = f"{self.message} ({self.origin_value} > {self.new_value})"
        else:
            msg = f"order_mode: {self.order_mode}, origin_value: {self.origin_value}, new_value: {self.new_value})"

        self.logger.error(msg, extra=self.extra)
        return msg


class SplitQuantityError(Exception):
    def __init__(self, volumn, *args):
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
                                logger_level=logging.ERROR,
                                to_file=True,
                                time_file=False,
                                file_dir="error",
                                instance=True)
        self.volumn = volumn
        self.sum_split = 0

        for arg in args:
            self.sum_split += arg

    def __str__(self):
        if self.volumn == self.sum_split:
            self.logger.error("數量足以劃分，重新檢視哪裡出錯了", extra=self.extra)
            return None
        elif self.volumn > self.sum_split:
            return f"劃分後數量({self.sum_split})少於原本的數量({self.volumn})"
        else:
            return f"劃分後數量({self.sum_split})超出原本的數量({self.volumn})"


class StrategyExistError(Exception):
    def __init__(self, stock_id, message=None):
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
                                logger_level=logging.ERROR,
                                to_file=True,
                                time_file=False,
                                file_dir="error",
                                instance=True)
        self.stock_id = stock_id
        self.message = message

    def __str__(self):
        error_message = f"不存在'策略({self.stock_id})'"

        if self.message is not None:
            error_message += f" {self.message}"

        return error_message
