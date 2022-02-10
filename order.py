import datetime
import os
import pickle
from decimal import Decimal
from decimal import ROUND_HALF_UP
from functools import total_ordering

import utils
from enums import OrderMode
from error import StopValueError
from submodule.Xu3.utils import getLogger


# total_ordering: 使得我可以只定義 __eq__ 和 __gt__ 就可進行完整的比較
# https://python3-cookbook.readthedocs.io/zh_CN/latest/c08/p24_making_classes_support_comparison_operations.html
@total_ordering
class Order:
    """
    TODO: 思考 Order 是否需要 stock_id
    revenue: 交易收入(基本上都會是正的)
    cost: 交易成本(含買賣成本及手續費等，皆為正數)
    income: 交易收入 - 交易成本(可正可負)
    """

    def __init__(self, guid, time, price: Decimal, stop_value: Decimal, volumn: int = 1,
                 discount: Decimal = Decimal("1"), is_etf=False, order_mode=OrderMode.Long):
        # 全域唯一識別碼
        self.guid = guid

        # 買入價格
        self.price = Decimal("0")

        # 買入張數
        self.bought_volumn = 0

        # 可交易的數量
        self.volumn = 0

        # 已賣出張數
        self.sold_volumn = 0

        # 是否已全部賣光?
        self.sold_out = False

        # (首次)購買時間
        self.buy_time = None

        # (最終)售出時間
        self.sell_time = None

        # 券商手續費折扣
        self.discount = discount

        # 是否為 ETF
        self.is_etf = is_etf

        # 購買成本(因股票價格不同而不同) = 股票購買成本 + 券商手續費
        self.buy_cost = Decimal("0")

        # 出售成本(因股票價格不同而不同) = 券商手續費 + 政府之證交稅
        self.sell_cost = Decimal("0")

        # 營業額
        self.revenue = Decimal("0")

        # 報酬率 return_rate = 1.XX or 2.XX
        self.return_rate = Decimal("0")

        # order_mode 在策略階段就決定，進而決定停損價位
        self.order_mode = order_mode

        # 停損/停利 價格(在 Order 形成的同時就應存在)
        self.stop_value = Decimal("0")

        # 紀錄 stop_value 歷程(可用於計算每個 order 平均調整多少次、平均調整金額為多少，用於預測最終價格)
        self.stop_value_moving = []

        # 首次購買
        self.buy(time=time, price=price, volumn=volumn, stop_value=stop_value)

    # 用於事後追加本應為同一請求的 Order
    def __add__(self, other):
        if other.guid == self.guid:
            self.buy(time=other.time, price=other.price, volumn=other.volumn, stop_value=other.stop_value)

    # 用於事後追加本應為同一請求的 Order
    def __sub__(self, other):
        if other.guid == self.guid:
            self.sell(sell_time=other.sell_time, sell_price=other.sell_price, volumn=other.sell_volumn, is_trial=False)

    def __repr__(self):
        return f"Order(guid: {self.guid}, time: {self.buy_time}, price: {self.price}, stop_value: {self.stop_value}" \
               f"\nbought_volumn: {self.bought_volumn}, sold_volumn: {self.sold_volumn}, " \
               f"revenue: {self.revenue}, buy_cost: {self.buy_cost}, sell_cost: {self.sell_cost})"

    __str__ = __repr__

    def toString(self, time: datetime = None, price: Decimal = None):
        description = f"Order(time: {self.buy_time}, price: {self.price}, stop_value: {self.stop_value})"
        description += f"\nguid: {self.guid}"
        description += f"\nbought_volumn: {self.bought_volumn}, sold_volumn: {self.sold_volumn}, " \
                       f"buy_cost: {self.buy_cost}, sell_cost: {self.sell_cost}"

        if time is not None:
            _, _, (_, revenue, buy_cost, sell_cost) = self.sell(sell_time=time,
                                                                sell_price=price,
                                                                volumn=None,
                                                                is_trial=True)
            income = revenue - buy_cost - sell_cost

            description += f"\nrevenue: {revenue}, income: {income}"

        return description

    # region total_ordering: 使得我可以只定義 __eq__ 和 __gt__ 就可進行完整的比較
    # https://python3-cookbook.readthedocs.io/zh_CN/latest/c08/p24_making_classes_support_comparison_operations.html
    def __eq__(self, other):
        return (self.stop_value == other.stop_value and
                self.bought_volumn == other.volumn and
                self.buy_time == other.buy_time)

    def __gt__(self, other):
        # __gt__: 一般排序後會被放在後面
        # OrderMode.Long: stop_value 越小越後面，越大越前面 -> gt = True
        # OrderMode.Short: stop_value 越大越後面，越小越前面 -> gt = False
        gt = self.order_mode == OrderMode.Long

        if self.stop_value < other.stop_value:
            return gt
        elif self.stop_value > other.stop_value:
            return not gt
        else:
            # 數量越大越後面
            if self.bought_volumn > other.volumn:
                return True
            elif self.bought_volumn < other.volumn:
                return False
            else:
                # 時間越晚越後面
                if self.buy_time > other.buy_time:
                    return True
                elif self.buy_time < other.buy_time:
                    return False
                else:
                    # self.price == other.price and self.volumn == other.volumn and self.time == other.time
                    return False

    # endregion

    # 考慮可能無法一次購買到指定數量的情形，可追加數量(並更新 價格 和 stop_value 等數據)
    def buy(self, time: datetime.datetime, price: Decimal, volumn: int, stop_value: Decimal):
        total_volumn = Decimal(str(self.bought_volumn + volumn))

        # 更新買入價格(根據先後購買量進行價格的加權)
        origin_weight = self.bought_volumn / total_volumn
        append_weight = volumn / total_volumn
        self.price = (self.price * origin_weight + price * append_weight).quantize(Decimal('.00'), ROUND_HALF_UP)

        # 追加買入張數
        self.bought_volumn = int(total_volumn)

        # 追加可交易數量
        self.volumn += int(volumn)

        # 若 self.time 為 None 才初始化，後續追加的時間不應覆蓋，才能正確計算總歷時
        if self.buy_time is None:
            self.buy_time = time

        # 追加購買成本(因股票價格不同而不同) = 股票購買成本 + 券商手續費
        self.buy_cost += self.getBuyCost(price, volumn, self.discount)

        # 更新 stop_value
        self.stop_value = stop_value

    # 考慮可能會分批賣出，營業額、成本等數值會累加上去
    def sell(self, sell_time: datetime.datetime, sell_price: Decimal = None, volumn: int = None, is_trial=False):
        if self.bought_volumn == self.sold_volumn:
            print(f"此 Order 已完成交易\n{self}")
            self.sold_out = True
            return

        if self.sell_time is None:
            self.sell_time = sell_time

        # 若沒有給 sell_price 的數值，則以 stop_value 作為售價來計算
        if sell_price is None:
            sell_price = self.stop_value

        if volumn is None:
            # 尚未賣出的部分，若之前沒有部分賣出，則賣出全部
            volumn = self.volumn

        sold_volumn = self.sold_volumn + volumn

        # 判斷是否為當沖
        is_day_trading = sell_time.date() == self.buy_time.date()

        # 營業額
        revenue = self.revenue + sell_price * volumn * 1000

        # 總成本(購買成本 + 售出成本): 部分賣出時，購買成本根據賣出比例計算
        buy_cost = self.buy_cost * (Decimal(str(volumn)) / self.bought_volumn)

        # 剩餘 buy_cost = self.buy_cost * (float(self.volumn) / self.bought_volumn)

        # 出售成本(因股票價格不同而不同) = 券商手續費 + 政府的證交稅(考慮到可能有部分賣出的情形而設計)
        sell_cost = self.sell_cost + self.getSellCost(sell_price,
                                                      is_etf=self.is_etf,
                                                      discount=self.discount,
                                                      is_day_trading=is_day_trading,
                                                      volumn=volumn)

        # 並非試算模式
        if not is_trial:
            # 追加已售出數量
            self.sold_volumn = sold_volumn

            # 減少可交易數量
            self.volumn -= volumn

            # 是否已全部賣光?
            self.sold_out = self.sold_volumn == self.bought_volumn

            # 更新營業額
            self.revenue = revenue

            # 更新售出成本
            self.sell_cost = sell_cost

        return self.guid, (self.buy_time, self.price, sold_volumn), (sell_price, revenue, buy_cost, sell_cost)

    def modifyStopValue(self, stop_value: Decimal, is_force=False):
        # 強制模式(不考慮做多還是做空)
        if is_force:
            # 新舊 stop_value 變化量
            delta_value = stop_value - self.stop_value

            return self.modifyStopValueDelta(delta_value)
        else:
            # 做多: stop_value 應越來越高
            if self.order_mode == OrderMode.Long:
                if self.stop_value < stop_value:
                    self.stop_value_moving.append(stop_value - self.stop_value)
                    self.stop_value = stop_value
                    return stop_value
                else:
                    return Decimal("0")

            # TODO: 未來若是操作到會有負值的商品，例如負油價，返回值等可能需要做項對應的修改，目前假設價格都是正的
            # 做空: stop_value 應越來越低
            elif self.order_mode == OrderMode.Short:
                if self.stop_value > stop_value:
                    self.stop_value_moving.append(self.stop_value - stop_value)
                    self.stop_value = stop_value
                    return stop_value
                else:
                    return 0
            else:
                raise StopValueError(self.order_mode, self.stop_value, stop_value)

    # 預設就是強制模式，在特殊情況下對 stop_value 進行調整
    def modifyStopValueDelta(self, delta_value: Decimal):
        # 紀錄 stop_value 變化
        self.stop_value_moving.append(delta_value)

        # 更新 stop_value
        self.stop_value += delta_value

        return self.stop_value

    def getStopValue(self):
        return self.stop_value

    """ 買股票的交易成本
    https://www.cmoney.tw/learn/course/cmoney/topic/152
    """

    @staticmethod
    def getBuyCost(price: Decimal, volumn: int = 1, discount: Decimal = Decimal("1")) -> Decimal:
        return price * volumn * 1000 + utils.alphaCost(price, discount, volumn=volumn)

    @staticmethod
    def getSellCost(sell_price: Decimal, volumn=1, is_etf=False, is_day_trading=False,
                    discount: Decimal = Decimal("1")) -> Decimal:
        return (utils.alphaCost(price=sell_price, discount=discount, volumn=volumn) +
                utils.betaCost(price=sell_price, is_etf=is_etf, is_day_trading=is_day_trading, volumn=volumn))


class OrderList:
    def __init__(self, stock_id: str,
                 logger_dir="order_list", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

        self.orders = dict(sold_out=[], un_sold_out=[])

        # 股票代碼
        self.stock_id = stock_id

    def __repr__(self):
        return self.toString(value=None)

    __str__ = __repr__

    def __iter__(self):
        for order in self.orders:
            yield order

    def add(self, order: Order):
        self.orders["un_sold_out"].append(order)
        self.orders["un_sold_out"].sort()
        self.save()

    def getOrder(self, guid, has_sold_out=False):
        """
        根據 order 的 guid，取得 order

        :param guid: order 的 全域唯一識別碼
        :param has_sold_out: 若知道該 Order 是否已被售出，可調整尋找順序以加速找到(若給錯還是會去另一邊尋找)
        :return:
        """
        if has_sold_out:
            # 優先尋找已被售出的 Order
            keys = ["sold_out", "un_sold_out"]
        else:
            # 優先尋找尚未被售出的 Order
            keys = ["un_sold_out", "sold_out"]

        for key in keys:
            orders = self.orders[key]

            for order in orders:
                if order.guid == guid:
                    return order

        return None

    def getOrders(self, has_sold_out=False):
        if has_sold_out:
            orders = self.orders["sold_out"]
        else:
            orders = self.orders["un_sold_out"]

        return orders

    def sort(self):
        for orders in self.orders.values():
            # orders 排序的定義是根據 Order 定義的大小來排序的
            orders.sort()

    def modifyStopValue(self, price, is_force=False):
        """
        對未售出的 Order 進行 stop_value 的調整

        :param price: 根據此價格計算新的 stop_value
        :param is_force: 一般情況下，停損價只漲不跌，若 is_force = True，可以強制修改
        :return:
        """
        is_modified = False

        for order in self.orders["un_sold_out"]:
            origin_stop_value = order.stop_value
            return_code = order.modifyStopValue(price, is_force=is_force)

            if return_code == 0:
                if order.order_mode == OrderMode.Long:
                    self.logger.debug(f"({self.stock_id}) 做多: stop_value 應越來越高, "
                                      f"self.stop_value: {origin_stop_value}, stop_value: {price}", extra=self.extra)
                elif order.order_mode == OrderMode.Short:
                    self.logger.debug(f"({self.stock_id}) 做空: stop_value 應越來越低, "
                                      f"self.stop_value: {origin_stop_value}, stop_value: {price}", extra=self.extra)
            else:
                # 若之後想要呈現從多少上移 stop_value 到多少，可以讓 setStopValue 的 return_code
                # 回傳原始和新數值之間的價差，order 本身可以取得新 stop_value，搭配價差可算出原始 stop_value
                self.logger.info("({}) Update stop_value {:.2f} -> {:.2f}".format(
                    self.stock_id, origin_stop_value, price), extra=self.extra)

                is_modified = True

        # orders 當中只要有一筆成功被調整，就會返回 True
        return is_modified

    # 預設就是強制模式，在特殊情況下對 stop_value 進行調整
    def modifyStopValueDelta(self, delta_value: Decimal):
        for order in self.orders["un_sold_out"]:
            origin_stop_value = order.stop_value
            new_stop_value = order.modifyStopValueDelta(delta_value=delta_value)

            self.logger.info(f"({self.stock_id}) {origin_stop_value} -> {new_stop_value}", extra=self.extra)

    def sell(self, sell_time: datetime.datetime, sell_price: Decimal = None, guid: str = "", sell_volumn: int = 0,
             is_trial: bool = False):
        trade_records = []

        # 優先從未售出的部分尋找
        order = self.getOrder(guid=guid, has_sold_out=False)

        if order is None:
            self.logger.error(f"No Order({guid})", extra=self.extra)
        elif order.sold_out:
            self.logger.error(f"Order({guid}) has been sold out.", extra=self.extra)
        else:
            self.logger.info(f"Sell Order({guid})", extra=self.extra)

            # 在外部判斷可以成交才會進入此處，因此無須再檢查價格相關資訊
            # sell(self, sell_time: datetime.datetime, sell_price: float, volumn: int = None, is_trial: bool)
            (guid,
             (buy_time, buy_price, buy_volumn),
             (sell_price, revenue, buy_cost, sell_cost)) = order.sell(sell_time=sell_time,
                                                                      sell_price=sell_price,
                                                                      volumn=sell_volumn,
                                                                      is_trial=is_trial)

            # 將 stop_value 變化幅度返回，並由 History 來紀錄
            # 紀錄 stop_value 平均調整次數，搭配平均調整金額，可預測最終價格
            trade_record = [guid, buy_time, buy_price, buy_volumn, sell_time, sell_price, sell_volumn,
                            revenue, buy_cost, sell_cost, order.stop_value_moving]
            trade_records.append(trade_record)

            # 該 Order 所買入的都賣出
            if order.sold_out:
                # 由於已完全售出，因此由 un_sold_out 移到 sold_out 管理
                self.orders["sold_out"].append(order)
                self.orders["un_sold_out"].remove(order)

            self.save()

        return trade_records

    def clear(self, sell_time: datetime.datetime, sell_price: Decimal = None, is_trial: bool = False):
        """
        試算出清結果，由於是試算，因此沒有實際對庫存做增減，只計算價值

        TODO: 目前沒有考慮價格與數量，之後若有實際要使用，需考慮進去
        無視價格高低，全部賣出

        :param sell_time:
        :param sell_price:
        :param is_trial:
        :return:
        """
        trade_records = []

        for order in self.orders["un_sold_out"]:
            # order.sell 只負責計算當前狀態賣出的結果，是否是自己要的價格需要自己判斷
            (guid,
             (buy_time, buy_price, buy_volumn),
             (sell_price, revenue, buy_cost, sell_cost)) = order.sell(sell_time=sell_time,
                                                                      sell_price=sell_price,
                                                                      is_trial=is_trial)

            # 印出售出的 order
            self.logger.info(f"({self.stock_id})\n{order}", extra=self.extra)

            # 將 stop_value 變化幅度返回，並由 History 來紀錄
            # order.volumn: 該 order 所擁有的可交易的數量
            trade_record = [guid, buy_time, buy_price, buy_volumn, sell_time, sell_price, order.volumn,
                            revenue, buy_cost, sell_cost, order.stop_value_moving]
            trade_records.append(trade_record)

        if not is_trial:
            self.orders["sold_out"] += self.orders["un_sold_out"]
            self.orders["sold_out"].sort()
            self.orders["un_sold_out"] = []

        # 不考慮是否為試算模式，皆返回模擬交易後的結果
        return trade_records

    def getOrderNumber(self):
        return len(self.orders["un_sold_out"])

    def setLoggerLevel(self, level):
        self.logger.setLevel(level)

    def toString(self, value: float = None, time: datetime = None, price: Decimal = None,
                 exclude_sold_out: bool = True):
        # TODO: value is None -> value = order.stop_value
        description = f"===== OrderList({self.stock_id}) ====="
        cost = Decimal("0")
        n_order = 0

        for order in self.orders["un_sold_out"]:
            description += f"\n{order.toString(time, price)}"
            cost += order.buy_cost
            n_order += 1

        # 若不排除已售出的 Order
        if not exclude_sold_out:
            description += "\n<<<<< 已售出 >>>>>"
            for order in self.orders["sold_out"]:
                description += f"\n{order.toString(time, price)}"
                cost += order.buy_cost
                n_order += 1

        if value is None:
            description += f"\n== 共有 {n_order} 個 order, 共花費 {cost} 元 =="
        else:
            description += f"\n== 共有 {n_order} 個 order, 共花費 {cost} 元, 價值 {value} 元 =="

        return description

    def getSellRequests(self, date_time: datetime.datetime):
        # 交易請求: (date_time, price, volumn)
        sell_requests = []
        orders = self.orders["un_sold_out"]

        for order in orders:
            if not order.sold_out:
                # order.volumn: 該 order 剩餘可交易數量
                sell_requests.append([order.guid, date_time, order.stop_value, order.volumn])

        return sell_requests

    def save(self, file_name=None):
        if file_name is None:
            file_name = self.stock_id

        with open(f"data/order_list/{file_name}.pickle", "wb") as f:
            pickle.dump(self, f)

    def load(self, file_name=None):
        if file_name is None:
            file_name = self.stock_id

        path = f"data/order_list/{file_name}.pickle"

        if os.path.exists(path):
            with open(path, "rb") as f:
                order_list = pickle.load(f)
                self.orders = order_list.orders
                del order_list


if __name__ == "__main__":
    import utils.globals_variable as gv
    from data import StockCategory

    gv.initialize()

    trade_records = """0056,2020-06-05,2020-06-09,28.78,28.80,1,28807,55,-62
2892,2020-06-10,2020-06-11,23.35,23.0,1,23372,89,-461
6005,2020-06-05,2020-06-11,10.15,10.30,1,10170,50,80
5880,2020-06-16,2020-06-17,20.80,20.80,1,20820,82,-102
2888,2020-06-15,2020-06-17,8.56,8.63,1,8580,45,5
6005,2020-07-07,2020-07-08,11.05,10.90,1,11070,52,-222
2823,2020-07-07,2020-07-10,22.90,22.40,1,22920,87,-607
2888,2020-07-07,2020-07-10,8.87,8.72,1,8890,46,-216
3048,2021-02-26,2021-03-16,24.05,32,1,24070,116,7814
1712,2021-03-29,2021-04-14,22.6,21.75,1,22620,85,-955
1310,2021-03-24,2021-04-21,19.05,21.65,1,19070.00,84,2496.00
2012,2021-03-23,2021-04-23,19.95,25.10,1,19970.00,95,5232.00
2012,2021-03-23,2021-04-23,0,0,0,0,0,590
2419,2021-04-28,2021-05-03,25.55,23.55,1,25570.00,90,-2110.00
3049,2021-03-29,2021-05-03,11.70,13.50,1,11720.0,60,1720.00
2329,2021-04-08,2021-05-04,17.40,17.45,1,17420.0,72,-42.00
2442,2021-03-23,2021-05-04,10.80,11.20,1,10820.0,53,327.00
5519,2021-04-07,2021-05-04,19.10,22.25,1,19120.0,86,3044.00
1417,2021-04-12,2021-05-04,12.55,13.90,1,12570.00,61,1269.00
2527,2021-03-18,2021-05-05,21.40,22.90,1,21420.0,88,1392.00
1732,2021-04-29,2021-05-05,28.50,28.40,1,28526.00,105,-225.00
1712,2021-03-29,2021-05-10,0,0,0,0,0,1290
2855,2021-03-22,2021-05-12,20.90,27.40,1,20920.0,102,6378.00
2880,2021-04-13,2021-05-12,18.80,17.80,1,18820.0,73,-1093.00
2892,2021-04-14,2021-05-12,22.30,20.70,1,22320.0,82,-1702.00
2890,2021-04-15,2021-05-12,12.85,12.60,1,12870.00,57,-327.00
2887,2021-04-15,2021-05-17,13.50,13.65,1,13520.0,60,70.00
6165,2021-05-25,2021-06-02,32.80,30.60,1,32820.00,111,-2331.00
3535,2021-05-25,2021-06-07,16.65,16.50,1,16670.00,69,-239.00
6205,2021-06-02,2021-06-07,31.60,29.65,1,31620.00,108,-2078.00
1108,2021-06-03,2021-06-07,14.50,13.65,1,14520.00,60,-930.00
4960,2021-05-31,2021-06-09,12.55,11.80,1,12570.00,55,-825.00
2390,2021-06-08,2021-06-15,25.00,29.75,1,25020.00,109,4621.00
8213,2021-06-11,2021-06-29,50.60,47.95,1,50647.00,163,-2835.00
1732,2021-06-28,2021-06-30,36.85,34.80,1,36884.00,124,-2194.00
1417,2021-06-25,2021-07-06,15.90,15.85,1,15920.00,67,-137.00
2885,2021-06-28,2021-07-12,26.55,25.60,1,26570.00,96,-1066.00
2390,2021-07-07,2021-07-13,26.80,25.40,1,26820.00,96,-1516.00
8478,2021-06-21,2021-07-13,57.60,68.60,1,57624.00,234,10742.00
6172,2021-07-05,2021-07-13,40.60,39.50,1,40620.00,138,-1258.00
2392,2021-05-27,2021-07-20,40.25,42.45,1,40270.00,146,1584.00
8213,2021-06-11,2021-07-27,0,0,0,0,0,3490.0
2885,2021-06-28,2021-07-12,0,0,0,0,0,1190.0
00639,2021-05-21,2021-07-27,17.25,16.45,1,17270.00,36,-856.00
00739,2021-04-26,2021-07-28,28.09,26.70,1,28110.00,46,-1456.00
4942,2021-05-31,2021-07-28,42.80,50.40,1,42820.00,171,7408.00
8103,2021-07-02,2021-07-28,43.65,45.60,1,43690.00,156,1774.00
8478,2021-07-23,2021-07-28,69.90,67.70,1,69965.00,232,-2462.00
2390,2021-07-30,2021-08-10,27.35,26.30,1,27370.00,98,-1168.00
00757,2021-06-11,2021-08-10,46.21,49.47,1,46230.00,70,3170.00
00668,2021-07-05,2021-08-10,35.09,35.27,1,35110.00,55,105.00
00762,2021-07-05,2021-08-10,41.54,42.03,1,41560.00,62,408.00
00646,2021-07-08,2021-08-10,37.33,37.80,1,37350.00,57,393.00
2855,2021-07-01,2021-08-12,26.95,26.10,1,26975.00,102,-977.00
1417,2021-07-26,2021-08-12,15.75,14.65,1,15770.00,63,-1183.00
1732,2021-07-30,2021-08-12,30.00,28.50,1,30028.00,111,-1639.00
2885,2021-08-05,2021-08-12,25.90,24.80,1,25924.00,97,-1221.00
2597,2021-08-13,2021-08-16,149.50,147.0,1,149564.00,503,-3067.00
6172,2021-07-22,2021-08-18,42.00,41.75,1,42020.00,145,-415.00
2392,2021-05-27,2021-07-20,0,0,0,0,0,2490.00
2545,2021-05-31,2021-08-25,40.95,37.45,1,40970.00,132,-3652.00
3003,2021-08-23,2021-08-27,93.50,95.60,1,93540.00,327,1733.00
4989,2021-08-26,2021-09-06,44.90,42.05,1,44920.0,146,-3016.00
3711,2021-08-25,2021-09-07,123.00,119.50,1,123052.00,409,-3961.00
3048,2021-08-25,2021-09-07,35.85,31.55,1,35870.00,114,-4434.00
3037,2021-08-27,2021-09-07,146.00,144.50,1,146062.00,494,-2056.00"""

    trs = trade_records.split("\n")

    for tr in trs:
        stock_id, buy_time, sell_time, buy_price, sell_price, vol, buy_cost, sell_cost, revenue = tr.split(",")

        is_etf = StockCategory.isEtf(stock_id=stock_id)
        bc = Order.getBuyCost(price=Decimal(buy_price), discount=gv.e_capital_discount)
        sc = Order.getSellCost(sell_price=Decimal(sell_price), discount=gv.e_capital_discount, is_etf=is_etf)

        if bc != Decimal(buy_cost) or sc != Decimal(sell_cost):
            print(f"bc: {bc}, sc: {sc}, is_etf: {is_etf}\n{tr}")
