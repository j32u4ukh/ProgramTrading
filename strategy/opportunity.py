import datetime
import functools
from collections import OrderedDict
from decimal import Decimal
from decimal import ROUND_HALF_UP
from functools import total_ordering

import numpy as np

from enums import PerformanceStage
from submodule.Xu3.utils import getLogger


@total_ordering
class Opportunity:
    def __init__(self, stock_id: str, strategy_name: str, performances: dict,
                 trigger_price: Decimal = Decimal("10.0"), volumn: int = 1,
                 logger_dir="opportunity", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        """
        主要形成指標為該股票搭配策略，在回測的各個階段都獲得了正收益。
        接著查看是否有尚未觸發的購買時機，若無此項會被設為 0，使得整體分數歸零。
        若有尚未觸發的購買時機，則可進一步考慮其他子項目的分數。

        :param stock_id:
        :param strategy_name:
        :param performances:
        :param trigger_price:
        :param volumn:
        :param logger_dir:
        :param logger_name:
        """
        self.stock_id = stock_id
        self.strategy_name = strategy_name
        self.performances = performances

        self.trigger_price = trigger_price
        self.volumn = volumn

        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

        self.main_performance = self.computeMainPerformance()

        # 各項表現的幾何平均
        self.overall_performance = self.main_performance

        self.sub_performance = OrderedDict()

        self.additional_description = []

    def __eq__(self, other):
        is_main_performance_equal = self.main_performance == other.main_performance

        # 不同策略間比較，只比較收益表現
        if self.strategy_name != other.strategy_name:
            return is_main_performance_equal

        # 相同策略間，可進一步比較子項目的表現，數值高低由各策略定義
        else:
            if is_main_performance_equal:

                if self.sub_performance is not None:
                    for key in self.sub_performance.keys():
                        value = self.sub_performance[key]
                        other_value = other.sub_performance[key]

                        if value != other_value:
                            return False

                return True
            else:
                return False

    def __gt__(self, other):
        # __gt__: 回傳 True 會被放在後面
        performance = self.main_performance
        other_performance = other.main_performance

        # 策略相同
        if self.strategy_name == other.strategy_name:

            # 有 子項目表現
            if len(self.sub_performance) > 0:
                n_performance = Decimal("1.0")

                for key in self.sub_performance.keys():
                    performance *= self.sub_performance[key]
                    other_performance *= other.sub_performance[key]
                    n_performance += Decimal("1.0")

                performance = np.power(performance, Decimal("1.0") / n_performance)
                other_performance = np.power(other_performance, Decimal("1.0") / n_performance)

        return performance > other_performance

    # TODO: 設計簡易版和完整版的資訊呈現
    def __repr__(self):
        geo_performance, performances = self.getPerformance()
        description = f"Opportunity(stock_id: {self.stock_id}, performance: {self.overall_performance})"
        description += f"\nperformances: {self.main_performance} | {performances}"

        for key, value in self.sub_performance.items():
            description += f"\nsub_performance: {key} -> {value}"

        for additional_description in self.additional_description:
            description += f"\n{additional_description}"

        return description

    __str__ = __repr__

    @staticmethod
    def sortFilter(opportunities: list, reverse: bool = True, filter_value: Decimal = Decimal("1.0")):
        """

        :param opportunities:
        :param reverse:
        :param filter_value:
        :return:
        """
        opportunities = sorted(opportunities, reverse=reverse)

        opportunities = [opportunity for opportunity in opportunities if opportunity.overall_performance > filter_value]

        return opportunities

    def toString(self, full_version=True):
        if full_version:
            geo_performance, performances = self.getPerformance()
            description = f"Opportunity(stock_id: {self.stock_id}, performance: {self.overall_performance})"
            description += f"\nperformances: {self.main_performance} | {performances}"

            for key, value in self.sub_performance.items():
                description += f"\nsub_performance: {key} -> {value}"

            for additional_description in self.additional_description:
                description += f"\n{additional_description}"

        else:
            train_performance, _ = self.getPerformance(PerformanceStage.Train)
            validation_performance, _ = self.getPerformance(PerformanceStage.Validation)
            short_performance, _ = self.getPerformance(PerformanceStage.Short)
            description = f"Opportunity(stock_id: {self.stock_id}, Train: {train_performance}, " \
                          f"Validation: {validation_performance}, Short: {short_performance})"

        return description

    def computeMainPerformance(self):
        synthesize_performance = Decimal("1.0")
        n_performance = Decimal("0")

        # 不同階段的表現(訓練/驗證/測試)
        for stage in self.performances.values():
            for performance in stage:
                synthesize_performance *= performance
                n_performance += 1

        return np.power(synthesize_performance, Decimal("1.0") / n_performance)

    def getPerformance(self, stage: PerformanceStage = None):
        performances = []

        if stage is None:
            geo_performance = Decimal("1.0")

            for values in self.performances.values():
                for performance in values:
                    performances.append(performance)
                    geo_performance *= performance

            geo_performance = np.power(geo_performance, Decimal("1.0") / Decimal(str(len(performances))))

        else:
            if self.performances.__contains__(stage):
                geo_performance = Decimal("1.0")
                values = self.performances[stage]

                for performance in values:
                    performances.append(performance)
                    geo_performance *= performance

                geo_performance = np.power(geo_performance,
                                           Decimal("1.0") / Decimal(str(len(performances))))

            else:
                geo_performance = Decimal("-1")

        return geo_performance, performances

    def getMainPerformances(self):
        performances = []

        for stage in self.performances.values():
            for performance in stage:
                performances.append(performance)

        return performances

    def addDescription(self, description):
        self.additional_description.append(description)

    def addPerformance(self, key: PerformanceStage, value: Decimal):
        if not self.performances.__contains__(key):
            self.performances[key] = []

        self.performances[key].append(value)

    def addSubPerformance(self, key: str, value: Decimal):
        """
        各項 performance 以 1.0 為分界，共同衡量後超過 1.0 作為是否為適當的購買時機

        :param key: 分項表現的 名稱/類別
        :param value: 分項表現的數值
        :return:
        """
        # 紀錄子項目表現
        self.sub_performance[key] = value

        # 至少有一項是 main_performance
        n_performance = Decimal("1.0")
        self.overall_performance = self.main_performance

        for value in self.sub_performance.values():
            if value <= Decimal("0.0"):
                self.overall_performance = Decimal("0.0")
                break

            self.overall_performance *= value
            n_performance += 1

        # 各項表現的幾何平均
        geometric_factor = (Decimal("1.0") / n_performance).quantize(Decimal('0.0000'), ROUND_HALF_UP)
        self.overall_performance = np.power(self.overall_performance, geometric_factor)

    def setTriggerPrice(self, trigger_price: Decimal):
        self.trigger_price = trigger_price

    def setVolumn(self, volumn: int):
        self.volumn = volumn

    def formApiData(self):
        return self.stock_id, str(self.trigger_price), self.volumn


def sortOpportunity(opportunities, is_default=False):
    """
    將請求做排序，排序優先順序為: 價格(越高越前) -> 數量(越少越前) -> 時間(越早越前)
    XXX_requests -> [guid, stock_id, date_time, price, volumn]

    :param is_default:
    :param opportunities: 購買時機
    :return:
    """

    def compareOpportunities(op1: Opportunity, op2: Opportunity):
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

        :param op1: 購買時機 1
        :param op2: 購買時機 2
        :return:
        """
        if is_default:
            return 0
        else:
            v1, _ = op1.getPerformance(stage=PerformanceStage.Validation)
            v2, _ = op2.getPerformance(stage=PerformanceStage.Validation)

            if v1 > v2:
                return -1
            elif v1 < v2:
                return 1
            else:
                s1, _ = op1.getPerformance(stage=PerformanceStage.Short)
                s2, _ = op2.getPerformance(stage=PerformanceStage.Short)

                if s1 > s2:
                    return -1
                elif s1 < s2:
                    return 1
                else:
                    return 0

    # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
    return sorted(opportunities, key=functools.cmp_to_key(compareOpportunities))


if __name__ == "__main__":
    mean = np.mean([57000, 51000])
    std = np.std([57000, 51000])
    mean_std = (mean + std) / 50000.0

    op1 = Opportunity(stock_id="1",
                      strategy_name="strategy1",
                      performances=dict(train=[Decimal("57000"), Decimal("51000")]))
    op1.addSubPerformance(key="mean_std", value=Decimal(str(mean_std)))
    op1.addDescription(f"sum_performance: {Decimal('57000') + Decimal('51000')}")
    op1.addDescription(f"mean_std: {mean_std}")

    mean = np.mean([53000, 54000])
    std = np.std([53000, 54000])
    mean_std = (mean + std) / 50000.0

    op2 = Opportunity(stock_id="2",
                      strategy_name="strategy1",
                      performances=dict(train=[Decimal("53000"), Decimal("54000")]))
    op2.addSubPerformance(key="mean_std", value=Decimal(str(mean_std)))
    op2.addDescription(f"sum_performance: {Decimal('53000') + Decimal('54000')}")
    op2.addDescription(f"mean_std: {mean_std}")

    mean = np.mean([53500, 53500])
    std = np.std([53500, 53500])
    mean_std = (mean + std) / 50000.0
    op3 = Opportunity(stock_id="3",
                      strategy_name="strategy3",
                      performances=dict(train=[Decimal("53500"), Decimal("53500")]))
    op3.addSubPerformance(key="mean_std", value=Decimal(str(mean_std)))
    op3.addSubPerformance(key="time", value=Decimal("3"))
    op3.addDescription(f"sum_performance: {Decimal('53500') + Decimal('53500')}")
    op3.addDescription(f"mean_std: {mean_std}")

    mean = np.mean([53800, 53500])
    std = np.std([53800, 53500])
    mean_std = (mean + std) / 50000.0
    op4 = Opportunity(stock_id="4",
                      strategy_name="strategy3",
                      performances=dict(train=[Decimal("53800"), Decimal("53500")]))
    op4.addSubPerformance(key="mean_std", value=Decimal(str(mean_std)))
    op4.addSubPerformance(key="time", value=Decimal("0"))
    op4.addDescription(f"sum_performance: {Decimal('53800') + Decimal('53500')}")
    op4.addDescription(f"mean_std: {mean_std}")

    ops = [op1, op2, op3, op4]
    ops = Opportunity.sortFilter(ops, reverse=True, filter_value=Decimal("0.0"))
    # print(f"op1\n{op1}")
    # print(f"op2\n{op2}")
    # print(f"op1 > op2: {op1 > op2}")
    for op in ops:
        print(op)
        print()
