import datetime
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
from matplotlib import pyplot as plt

import utils.globals_variable as gv
from enums import ReportType
from history.capital import LocalCapital
from history.statistics import descriptiveStatistics, decilePercentage
from history.trade_record import LocalTradeRecord
from submodule.Xu3.utils import getLogger


# 單筆 Order 的交易紀錄(容許分次買賣)
class TradeRecord:
    def __init__(self):
        # record dict value:
        # [buy_time, buy_price, buy_volumn, sell_time, sell_price, sell_volumn, revenue, buy_cost, sell_cost,
        # stop_value_moving, income, return_rate, annual_return_rate]
        self.record = None

    def __getattr__(self, item):
        if self.record.__contains__(item):
            return self.record[item]
        else:
            return None

    def __len__(self):
        return len(self.income)

    def __repr__(self):
        return self.toString(guid=None)

    __str__ = __repr__

    def __add__(self, other):
        pass

    def toString(self, guid=None):
        # TODO: self.record

        if self.record is None:
            return "self.record is None"

        if guid is None:
            description = f"TradeRecord({self.record['buy_time']} ~ {self.record['sell_time']})"
        else:
            description = f"TradeRecord(guid: {guid}, {self.record['buy_time']} ~ {self.record['sell_time']})"

        for key, value in self.record.items():
            if key != 'buy_time' or key != 'sell_time':
                description += f"\n{key}: {value}"

        return description

    def add(self, buy_time: datetime.datetime, buy_price: Decimal, buy_volumn: int,
            sell_time: datetime.datetime, sell_price: Decimal, sell_volumn: int,
            revenue: Decimal, buy_cost: Decimal, sell_cost: Decimal, stop_value_moving: list,
            first_add: bool = False):
        if first_add:
            income, return_rate, annual_return_rate = self.derivedData(buy_time=buy_time,
                                                                       buy_cost=buy_cost,
                                                                       sell_time=sell_time,
                                                                       sell_cost=sell_cost,
                                                                       revenue=revenue)

            self.record = dict(buy_time=buy_time, buy_price=buy_price, buy_volumn=buy_volumn,
                               sell_time=sell_time, sell_price=sell_price, sell_volumn=sell_volumn,
                               revenue=revenue, buy_cost=buy_cost, sell_cost=sell_cost,
                               stop_value_moving=stop_value_moving,
                               income=income, return_rate=return_rate, annual_return_rate=annual_return_rate)
        else:
            self.record["sell_time"] = sell_time
            self.getWeightedData(kind="buy", new_price=buy_price, new_volumn=buy_volumn)
            self.getWeightedData(kind="sell", new_price=sell_price, new_volumn=sell_volumn)

            self.record["revenue"] += revenue
            self.record["buy_cost"] += buy_cost
            self.record["sell_cost"] += sell_cost

            self.record["stop_value_moving"] += stop_value_moving

            # 更新衍生數據
            income, return_rate, annual_return_rate = self.derivedData(buy_time=self.record["buy_time"],
                                                                       buy_cost=self.record["buy_cost"],
                                                                       sell_time=sell_time,
                                                                       sell_cost=self.record["sell_cost"],
                                                                       revenue=self.record["revenue"])

            self.record["income"] = income
            self.record["return_rate"] = return_rate
            self.record["annual_return_rate"] = annual_return_rate

    @staticmethod
    def derivedData(buy_time: datetime.datetime, buy_cost: Decimal, sell_time: datetime.datetime, sell_cost: Decimal,
                    revenue: Decimal):
        cost = buy_cost + sell_cost
        income = revenue - cost
        return_rate = (revenue / cost).quantize(Decimal('.0000'), ROUND_HALF_UP)
        during_days = Decimal(str((sell_time - buy_time) / datetime.timedelta(days=1)))
        during_days = max(during_days, Decimal("1"))
        annual_index = Decimal("365.25") / during_days
        annual_return_rate = np.power(return_rate, annual_index).quantize(Decimal('.0000'), ROUND_HALF_UP)

        return income, return_rate, annual_return_rate

    def getWeightedData(self, kind: str, new_price: Decimal, new_volumn: int):
        price = f"{kind}_price"
        volumn = f"{kind}_volumn"

        # 根據先後買入的數量為權重，對購買價做加權(若沒加買，則 new_weight 會是 0)
        origin_price = self.record[price]
        origin_volumn = self.record[volumn]
        result_volumn = origin_volumn + new_volumn

        origin_weight = Decimal(str(origin_volumn)) / result_volumn
        new_weight = Decimal(str(new_volumn)) / result_volumn

        self.record[price] = origin_weight * origin_price + new_weight * new_price
        self.record[volumn] = result_volumn


class History:
    """
    revenu: 營業額，revenu = income + cost
    income: 收入，正值為'利潤(profit)'，負值為'虧損(loss)'
    profit: 利潤(History 當中沒有細分到此項目)
    loss: 虧損(History 當中沒有細分到此項目)
    cost: 成本(買和賣都會產生成本)
    falling_price: 跌價(前一次購買到下一次購買之間為計算區間，購買價與區間最低價的落差，是為跌價)

    交易紀錄數據
    stock_id,buy_time,sell_time,buy_price,sell_price,volumn,buy_cost,sell_cost,revenue
    """

    def __init__(self, stock_id,
                 logger_dir="strategy", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.stock_id = stock_id

        self.logger_dir = logger_dir
        self.logger_name = logger_name

        # 紀錄交易(key: guid, value: TradeRecord)
        self.trade_record = dict()

        # 紀錄資金的變化
        self.funds_history = []

        # 紀錄收益
        self.income = []

        # 跌價
        self.falling_price = []

        self.report = None

    def __len__(self):
        return len(self.trade_record)

    def __repr__(self):
        description = f"===== History({self.stock_id}) ====="

        for guid, trade_record in self.trade_record.items():
            description += f"\n{trade_record.toString(guid=guid)}"

        description += f"\nFallingPrice ~ {self.getFallingPriceParam()}"

        # stop_value_moving: 平均調整金額；平均調整次數: n_stop_value_moving
        stop_value_moving, n_stop_value_moving = self.getStopValueParam()
        description += f"\nStopValue 平均調整金額: {stop_value_moving}, 平均調整次數: {n_stop_value_moving}, " \
                       f"每個 order 預期調整總金額: {stop_value_moving * n_stop_value_moving}"

        description += f"\n===== Total income: {self.getIncome()} ====="

        return description

    __str__ = __repr__

    def add(self, *trade_records):
        for trade_record in trade_records:
            (guid, buy_time, buy_price, buy_volumn,
             sell_time, sell_price, sell_volumn,
             revenue, buy_cost, sell_cost, stop_value_moving) = trade_record

            # 不包含 = 第一次添加
            first_add = not self.trade_record.__contains__(guid)

            if first_add:
                self.trade_record[guid] = TradeRecord()

            self.trade_record[guid].add(buy_time=buy_time,
                                        buy_price=buy_price,
                                        buy_volumn=buy_volumn,
                                        sell_time=sell_time,
                                        sell_price=sell_price,
                                        sell_volumn=sell_volumn,
                                        revenue=revenue,
                                        buy_cost=buy_cost,
                                        sell_cost=sell_cost,
                                        stop_value_moving=stop_value_moving,
                                        first_add=first_add)

    # 記錄歷史(完成買賣後的)資金變化
    def recordFunds(self, funds: Decimal):
        self.funds_history.append(funds)

    def getTradeRecord(self, guid):
        if self.trade_record.__contains__(guid):
            return self.trade_record[guid]
        else:
            return None

    def iterTradeRecord(self):
        for guid, trade_record in self.trade_record.items():
            yield guid, trade_record

    def display(self, *args):
        if self.report is None:
            self.report = Report(history=self, logger_dir=self.logger_dir, logger_name=self.logger_name)

        self.report.display(*args)

    def getIncome(self):
        income = Decimal("0")

        for trade_record in self.trade_record.values():
            income += trade_record.income

        return income

    def recordFallingPrice(self, falling_price: Decimal):
        """
        前一次購買到下一次購買之間為計算區間，購買價與區間最低價的落差

        :param falling_price: 跌價
        :return:
        """
        self.falling_price.append(falling_price)

    def getFallingPriceParam(self):
        if len(self.falling_price) > 0:
            self.falling_price.sort()

            mean = Decimal(str(np.mean(self.falling_price)))
            std = Decimal(str(np.std(self.falling_price)))

            mean = mean.quantize(Decimal('.0000'), ROUND_HALF_UP)
            std = std.quantize(Decimal('.0000'), ROUND_HALF_UP)

            return mean, std
        else:
            return Decimal("0.0000"), Decimal("0.0000")

    def resetFallingPrice(self):
        self.falling_price = []

    def getStopValueParam(self):
        stop_value_movings = []
        n_stop_value_movings = []

        for trade_record in self.trade_record.values():
            # stop_value_moving: 一維陣列 of Decimal
            stop_value_moving = trade_record.stop_value_moving

            # 併入 stop_value_movings(同為一維陣列)
            stop_value_movings += stop_value_moving

            # trade_record.n_stop_value_moving: int
            n_stop_value_movings.append(Decimal(str(len(stop_value_moving))))

        if len(stop_value_movings) > 0:
            stop_value_moving = np.mean(stop_value_movings)
            stop_value_moving = Decimal(str(stop_value_moving)).quantize(Decimal('.00'), ROUND_HALF_UP)
            n_stop_value_moving = np.mean(n_stop_value_movings)
            n_stop_value_moving = Decimal(str(n_stop_value_moving)).quantize(Decimal('.00'), ROUND_HALF_UP)
            return stop_value_moving, n_stop_value_moving
        else:
            # print("交易期間尚未發生 stop_value 的調整")
            return Decimal("0.00"), Decimal("0.00")

    def getTimeRange(self):
        start_time = datetime.datetime.today()
        stop_time = datetime.datetime(1970, 1, 1)

        for trade_record in self.trade_record.values():
            start_time = min(start_time, trade_record.buy_time)
            stop_time = max(stop_time, trade_record.sell_time)

        return stop_time - start_time

    def reset(self):
        # 紀錄交易(key: guid, value: TradeRecord)
        self.trade_record = dict()

        # 紀錄資金的變化
        self.funds_history = []

        # 紀錄收益
        self.income = []

        # 跌價
        self.falling_price = []

        self.report = None

    def reportResult(self, *args):
        if self.report is None:
            self.report = Report(history=self, logger_dir=self.logger_dir, logger_name=self.logger_name)

        self.report.report_(*args)


# TODO: 各指標皆須考慮無數值的問題(可能執行期間不足以產生特定數據)
class Report:
    def __init__(self, history: History,
                 logger_dir="report", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

        self.history = history
        self.stock_id = self.history.stock_id
        self.n_trade = Decimal(str(len(self.history)))

        self.zero_trading_msg = f"({self.stock_id}) 總交易次數為 0，因某些原因，一次交易都沒有成立"

        gv.initialize()

        # region 初始數據
        """
        數據報告應劃分為兩種導向: 1.交易導向 2.時間導向
        
        1. 交易導向: 以一次次的交易為計算單位，衡量每次交易的效益，history 原始數據即為'交易導向'
        2. 時間導向: 將同一天內的交易合併為一筆數據，衡量時間報酬率，評估每天、每年等時間區段可獲得的報酬率
           時間導向不討論 profit 和 loss，畢竟已經根據日期做了整合性的計算，再細分 profit 和 loss 的意義不大
        """
        self.trading_time = None
        self.trading_revenue = None
        self.trading_income = None
        self.trading_cost = None
        self.trading_profit = None
        self.trading_loss = None

        self.date_times = None
        self.date_incomes = None
        self.date_costs = None

        self.funds_history = self.history.funds_history

        # MDD(最大交易回落): 指帳戶淨值從最高點的滑落程度，意義在於，從任一時間點進場可能遇到的最糟狀況。
        self.max_drawdown = self.computeMaxDrawdown()

        # 年化風報比: 為了這些獲利須承擔多大的風險
        self.annualized_risk_ratio = Decimal("0")

        # 權益曲線(Equity Curve)反映的就是帳戶淨值的變化。 -> 剩餘資金 + cumDateIncome
        self.date_cum_incomes = []

        self.initTradingDict()
        self.initDateDict()
        # endregion

        # 跌價紀錄
        self.falling_price = self.history.falling_price

    def __str__(self):
        description = descriptiveStatistics(self.trading_income, f"Report({self.stock_id})")
        return description

    __repr__ = __str__

    def initTradingDict(self):
        if self.n_trade > 0:
            trading_time = []
            trading_revenue = []
            trading_income = []
            trading_cost = []

            for guid, trade_record in self.history.iterTradeRecord():
                trading_time.append(trade_record.buy_time)
                trading_revenue.append(trade_record.revenue)
                trading_income.append(trade_record.income)
                trading_cost.append(trade_record.buy_cost + trade_record.sell_cost)

            # TODO: 若未能交易，這些數值都會是空的
            self.trading_time = np.array(trading_time)
            self.trading_revenue = np.array(trading_revenue)
            self.trading_income = np.array(trading_income)
            self.trading_cost = np.array(trading_cost)

            # 風報比：常常聽到「風報比」這個詞，白話講就是「為了這些獲利須承擔多大的風險」。
            #  公式是 風報比 = 淨獲利 / MDD，這項在績效報告中並沒有，須自己運算。
            #  也可以進一步把風報比年化，以利不同回測長度的策略間比較，公式是 年化風報比 = (淨獲利 / 回測年數) / MDD。
            if len(self.trading_income) > 0:
                income = Decimal(str(self.trading_income.sum()))
                during_years = Decimal(str(self.history.getTimeRange() / datetime.timedelta(days=365.25)))

                # 若資金未曾下跌，max_drawdown 會是 0，這裡在避免 annualized_risk_ratio 除以 0
                self.max_drawdown = max(self.max_drawdown, Decimal("1e-8"))
                self.annualized_risk_ratio = ((income / during_years) / self.max_drawdown).quantize(
                    Decimal('.0000'), ROUND_HALF_UP)

                self.logger.info(f"({self.stock_id}) 年化風報比: {self.annualized_risk_ratio}", extra=self.extra)
                self.logger.info(f"({self.stock_id}) 最大交易回落: {self.max_drawdown}", extra=self.extra)
                self.logger.debug(f"({self.stock_id}) funds_history: {self.funds_history}", extra=self.extra)

            # TODO: income = 0 也被算入 profit，檢視是否會有何不協調的地方
            self.trading_profit = self.trading_income[np.where(self.trading_income >= 0)]
            self.trading_loss = self.trading_income[np.where(self.trading_income < 0)]
        else:
            self.logger.info(self.zero_trading_msg, extra=self.extra)

    def initDateDict(self):
        def zero():
            return 0

        if self.n_trade > 0:
            date_times = [trading_time.date() for trading_time in self.trading_time]
            n_data = len(date_times)

            # 根據日期區分的數據
            date_income_dict = defaultdict(zero)
            date_cost_dict = defaultdict(zero)

            for i in range(n_data):
                date_time = date_times[i]

                date_income_dict[date_time] += self.trading_income[i]
                date_cost_dict[date_time] += self.trading_cost[i]

            # 有序、不重複 日期陣列
            self.date_times = list(set(date_times))
            self.date_times.sort()

            date_incomes = []
            date_costs = []

            # 從'有序、不重複 日期陣列'，依序取出日期，再根據日期取出數據
            for date_time in self.date_times:
                date_incomes.append(date_income_dict[date_time])
                date_costs.append(date_cost_dict[date_time])

            self.date_incomes = np.array(date_incomes)
            self.date_costs = np.array(date_costs)

            # TODO: 標記特殊時間點的位置與資訊(權益創新高等)
            # TODO: 最大策略虧損：就是大家常聽到的Max Drawdown (MDD)。MDD概念從權益曲線圖(Equity Curve)上比較好理解，
            #  Drawdown(DD)就是指淨值從峰值滑落，當淨值創新高，DD會重新計算，而MDD就是最大的那個滑落值。
            # 時間導向之累積收益
            # 權益曲線(Equity Curve)反映的就是帳戶淨值的變化。 -> 剩餘資金 + cumDateIncome
            self.date_cum_incomes = np.cumsum(self.date_incomes)

    def computeMaxDrawdown(self):
        drawdowns = []
        highest = self.funds_history[0]
        lowest = self.funds_history[0]

        n_principal = len(self.funds_history)
        drawdown_formed = False

        for i in range(1, n_principal):
            funds = self.funds_history[i]

            # 更新最高價
            if funds > highest:

                if drawdown_formed:
                    drawdowns.append(highest - lowest)
                    lowest = funds
                    drawdown_formed = False

                highest = funds

            # 更新最低價
            if funds < lowest:
                lowest = funds

                # 當最低價第一次被更新，才形成了 drawdown
                drawdown_formed = True

        if len(drawdowns) == 0:
            # 當最低價第一次被更新，才形成了 drawdown
            if drawdown_formed:
                drawdown = highest - lowest
                drawdowns.append(drawdown)
                max_drawdown = drawdown

            # 資金未曾下跌過，drawdown = 0
            else:
                max_drawdown = 0
        else:
            max_drawdown = np.max(drawdowns)

        self.logger.debug(f"({self.stock_id}) max_drawdown: {max_drawdown}, drawdown: {drawdowns}", extra=self.extra)

        return max_drawdown

    def report_(self, *args):
        for report_type in args:
            # 總體報告
            if report_type == ReportType.Total:
                self.logger.info(f"\n{self.__str__()}", extra=self.extra)
            # 收益
            elif report_type == ReportType.Profit:
                self.reportProfit()
            # 虧損
            elif report_type == ReportType.Loss:
                self.reportLoss()
            # 淨益
            elif report_type == ReportType.Income:
                self.reportIncome()
            # TODO: 累積收益、累積虧損、累積淨利
            # 賺賠比
            elif report_type == ReportType.EarningLossRate:
                self.reportEarningLossRate()
            # 跌價
            elif report_type == ReportType.FallingPrice:
                self.reportFallingPrice()
            # 勝率(贏的次數/總次數)
            elif report_type == ReportType.WinRate:
                self.reportWinRate()
            # 勝率(贏的次數/總次數)
            elif report_type == ReportType.ReturnRate:
                self.reportReturnRate()

    """
    self.profit 和 self.loss 皆改為沒有值的地方填入 0，因此因該不會出現 ValueError，故移除
    """

    def reportProfit(self):
        if self.n_trade > 0:
            description = descriptiveStatistics(self.trading_profit, f"Profit({self.stock_id})")
            self.logger.info(f"\n{description}", extra=self.extra)

    def reportLoss(self):
        if self.n_trade > 0:
            description = descriptiveStatistics(self.trading_loss, f"Loss({self.stock_id})")
            self.logger.info(f"\n{description}", extra=self.extra)

    def reportIncome(self):
        if self.n_trade > 0:
            description = descriptiveStatistics(self.trading_income, f"Income({self.stock_id})")
            self.logger.info(f"\n{description}", extra=self.extra)

    def reportEarningLossRate(self):
        description = f"===== Earning Loss Rate({self.stock_id}) ====="
        if self.n_trade > 0:
            earning_loss_rate = self.getEarningLossRate()

            n_profit = len(self.trading_profit)
            total_profit = np.sum(self.trading_profit)
            description += "\n獲利: {} 次, 共獲利: {} 元".format(n_profit, total_profit)

            n_loss = len(self.trading_loss)
            total_loss = np.abs(np.sum(self.trading_loss))
            description += "\n虧損: {} 次, 共虧損: {} 元".format(n_loss, total_loss)

            if 0 < earning_loss_rate < 1.0:
                description += "\n賠賺比(每賠一次要賺多少次才能打平): {}".format(Decimal("1.0") / earning_loss_rate)
            elif earning_loss_rate >= 1.0:
                description += "\n賺賠比(每賺一次可以賠多少次): {}".format(earning_loss_rate)
            else:
                description += "\nearning_loss_rate: {}".format(earning_loss_rate)
        else:
            description += f"\n{self.zero_trading_msg}"

        self.logger.info(f"\n{description}", extra=self.extra)

    def getEarningLossRate(self):
        if self.n_trade > 0:
            mean_profit = Decimal("0")
            mean_loss = Decimal("1e-5")

            if len(self.trading_profit) > 0:
                mean_profit = np.mean(self.trading_profit)

            if len(self.trading_loss) > 0:
                mean_loss = np.abs(np.mean(self.trading_loss))

            earning_loss_rate = mean_profit / mean_loss

            return earning_loss_rate
        else:
            self.logger.info(self.zero_trading_msg, extra=self.extra)
            return Decimal("0")

    def reportFallingPrice(self):
        description = decilePercentage(data=self.falling_price,
                                       title=f"Falling Price({self.stock_id})",
                                       reverse=False,
                                       min_quantile=5,
                                       max_quantile=10)

        self.logger.info(f"\n{description}", extra=self.extra)

    def reportWinRate(self):
        """
        分子分母皆為 numpy.float64 的類型，因此當發生除以 0 時不會產生 ZeroDivisionError，
        而是產生 RuntimeWarning 但程式仍可正常運作。
        https://blog.csdn.net/yeshang_lady/article/details/103954522
        :return:
        """
        description = f"===== Win Rate({self.stock_id}) ====="

        if self.n_trade > 0:
            n_profit = Decimal(str(len(self.trading_profit)))
            description += "\n總共交易 {} 次，贏 {} 次，輸 {} 次，勝率為: {:.4f} %".format(
                self.n_trade, n_profit, len(self.trading_loss), n_profit / self.n_trade * Decimal("100.0"))
        else:
            description += f"\n{self.zero_trading_msg}"

        self.logger.info(f"\n{description}", extra=self.extra)

    def reportReturnRate(self):
        description = f"===== Return Rate({self.stock_id}) ====="

        if self.n_trade == 0:
            description += f"\n{self.zero_trading_msg}"
        else:
            annual_return_rate, (revenue, cost, return_rate), n_year = self.computeAnnualReturnRate()
            # revenue = np.sum(self.trading_revenue)
            # cost = np.sum(self.trading_cost)
            #
            # # return_rate = 1.XX or 2.XX
            # return_rate = revenue / cost

            # return_rate - 1.0: 僅呈現報酬的部分
            description += "\n總收益: {}, 總成本: {}, 總報酬率: {:.4f} %".format(
                revenue - cost, cost, (return_rate - Decimal("1.0")) * Decimal("100.0"))

            # 計算年化報酬時，return_rate 仍須保持 1.XX or 2.XX 的樣子才能正常的計算
            """
            1.1 * 1.1 = 1.21
            1.21**0.5 = 1.1
            但
            0.21**0.5 = 0.458257569495584 =/= 1.1
            """
            # n_year = Decimal(str(self.history.getTimeRange() / datetime.timedelta(days=365.25) + 1e-8))
            #
            # # 花費時間 self.time_range 獲得 return_rate 的報酬率，1 年最多可重複 year_index 次
            year_index = Decimal("1.0") / n_year
            description += "\nn_year: {:.4f}, year_index: {:.4f}".format(n_year, year_index)

            annual_return_rate = np.power(return_rate, year_index)
            description += "\n年化報酬率: {:.4f} %".format((annual_return_rate - Decimal("1.0")) * Decimal("100.0"))

            # 定存的(年化)報酬率: fixed_deposit_return_rate
            # 大盤的(年化)報酬率: market_return_rate
            if annual_return_rate < gv.fixed_deposit_return_rate:
                description = "{}\n表現差於定存和大盤".format(description)
            elif gv.fixed_deposit_return_rate <= annual_return_rate < gv.market_return_rate:
                description = "{}\n表現優於定存，但比大盤差".format(description)
            else:
                description = "{}\n表現優於大盤".format(description)

        self.logger.info(f"\n{description}", extra=self.extra)

    def computeAnnualReturnRate(self):
        if self.n_trade == 0:
            return 1.0, 0.0, 0.0

        revenue = np.sum(self.trading_revenue)
        cost = np.sum(self.trading_cost)

        # return_rate = 1.XX or 2.XX
        return_rate = revenue / cost

        # 計算年化報酬時，return_rate 仍須保持 1.XX or 2.XX 的樣子才能正常的計算
        """
        1.1 * 1.1 = 1.21
        1.21**0.5 = 1.1
        但
        0.21**0.5 = 0.458257569495584 =/= 1.1
        """
        # 花費幾年
        n_year = Decimal(str(self.history.getTimeRange() / datetime.timedelta(days=365.25) + 1e-8))

        # 花費時間 self.time_range 獲得 return_rate 的報酬率，1 年最多可重複 year_index 次
        year_index = Decimal("1.0") / n_year

        # 年化報酬率
        annual_return_rate = np.power(return_rate, year_index)

        return annual_return_rate, (revenue, cost, return_rate), n_year

    def display(self, *args):
        if ReportType.Total in args:
            self.displayCumIncome()
            self.displayIncome()

        if ReportType.CumIncome in args:
            self.displayIncome()

        if ReportType.Income in args:
            self.displayCumIncome()

        plt.legend(loc='best')
        plt.show()

    def displayIncome(self):
        plt.plot(self.date_times, self.date_incomes, "b-", label='income')

    def displayCumIncome(self):
        plt.plot(self.date_times, self.date_cum_incomes, "r-", label='cum_income')


if __name__ == "__main__":
    pass
