import datetime
import functools
from decimal import Decimal

import pandas as pd
from dateutil.parser import parse as time_parser

from enums import BuySell


class LocalTradeRecord:
    def __init__(self):
        self.path = "data/trade_record.csv"

        # number, stock_id, buy_time, sell_time, buy_price, sell_price, volumn, buy_cost, sell_cost, revenue
        self.df = pd.read_csv(self.path,
                              dtype={0: int, 1: str, 2: str, 3: str, 4: str, 5: str, 6: float, 7: str, 8: str, 9: str})

    # 交易紀錄索引值
    def getLastNumber(self):
        last_row = list(self.df.iloc[-1])

        return last_row[0]

    def getLastBuyTime(self, stock_id):
        sub_df = self.df[self.df["stock_id"] == stock_id].copy()
        sub_df.sort_values(by=["number", "buy_time"], inplace=True)
        last_buy = list(sub_df.iloc[-1])[2]

        return time_parser(last_buy)

    def saveTradeRecord(self, stock_id, buy_time: datetime.datetime, sell_time: datetime.datetime, buy_price: Decimal,
                        sell_price: Decimal, volumn: int, buy_cost: Decimal, sell_cost: Decimal, revenue: Decimal):
        """

        :param stock_id:
        :param buy_time:
        :param sell_time:
        :param buy_price:
        :param sell_price:
        :param volumn:
        :param buy_cost:
        :param sell_cost:
        :param revenue:
        :return:
        """
        number = self.getLastNumber() + 1
        data = {"number": number,
                "stock_id": stock_id,
                "buy_time": str(buy_time.date()),
                "sell_time": str(sell_time.date()),
                "buy_price": str(buy_price),
                "sell_price": str(sell_price),
                "volumn": volumn,
                "buy_cost": str(buy_cost),
                "sell_cost": str(sell_cost),
                "revenue": str(revenue)}
        self.df = self.df.append(data, ignore_index=True)
        self.df.to_csv(self.path, index=False)

        return data

        #     # 移除庫存
        #     self.api.removeInventory(guid=guid)
        #
        #     # TODO: 寫出交易紀錄，並更新資金(funds.csv)
        #     self.local_capital.allocateRevenue(deal_time=sell_time, remark=str(number), trade_revenue=trade_revenue)
        #     # self.api.recordTrading(stock_id=stock_id,
        #     #                        buy_price=str(buy_price),
        #     #                        sell_price=str(sell_price),
        #     #                        vol=buy_volumn,
        #     #                        buy_time=buy_time,
        #     #                        sell_time=sell_time,
        #     #                        buy_cost=str(buy_cost),
        #     #                        sell_cost=str(sell_cost),
        #     #                        revenue=str(revenue - buy_cost - sell_cost))
        #
        #     self.logger.info(f"record: {record}", extra=self.extra)
        #     f.write(record)

    def recordDividend(self, stock_id: str, revenue: str, pay_time: datetime.datetime = datetime.datetime.today()):
        last_buy = self.getLastBuyTime(stock_id=stock_id)
        buy_time = last_buy.strftime("%Y-%m-%d")
        sell_time = pay_time.strftime("%Y-%m-%d")

        number = self.getLastNumber() + 1
        data = {"number": number,
                "stock_id": stock_id,
                "buy_time": buy_time,
                "sell_time": sell_time,
                "buy_price": "0",
                "sell_price": "0",
                "volumn": 0,
                "buy_cost": "0",
                "sell_cost": "0",
                "revenue": revenue}
        self.df = self.df.append(data, ignore_index=True)
        self.df.to_csv(self.path, index=False)

        return data

    def renumber(self):
        n_data = len(self.df)
        numbers = list(range(1, n_data + 1))
        self.df["number"] = numbers
        self.df.to_csv(self.path, index=False)


def sortOperates(operates):
    """
    將操作做排序，排序優先順序為: 日期(越早越前) -> 操作類型(buy 優先，再來才是 sell)
    xxx_operate -> [datetime, buy/sell, cost/income]

    :param operates: 所有操作
    :return:
    """

    def compareOperates(op1, op2):
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

        :param op1: 請求 1
        :param op2: 請求 2
        :return:
        """
        # datetime, buy/sell, cost/income
        time1, buy_sell1, _ = op1
        time2, buy_sell2, _ = op2

        # 時間越早排越前面
        if time1 < time2:
            return -1
        elif time1 > time2:
            return 1

        # 數量少的排前面
        if buy_sell1.value < buy_sell2.value:
            return -1

        # 數量多的排後面
        elif buy_sell1.value > buy_sell2.value:
            return 1
        else:
            return 0

    # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
    return sorted(operates, key=functools.cmp_to_key(compareOperates))


def evaluateTradingPerformance():
    path = "data/trade_record.csv"
    # number,stock_id,buy_time,sell_time,buy_price,sell_price,volumn,buy_cost,sell_cost,revenue
    df = pd.read_csv(path)
    df["buy_time"] = pd.to_datetime(df["buy_time"])
    df["sell_time"] = pd.to_datetime(df["sell_time"])
    # print(df)

    # 排除使用策略時的交易
    # df = df[df["sell_time"] > datetime.datetime(2021, 1, 1)]

    # 只使用策略時的交易
    df = df[df["sell_time"] > datetime.datetime(2021, 1, 1)]

    # TODO: datetime buy/sell cost/income
    n_row = len(df)
    operates = []

    for r in range(n_row):
        row = df.iloc[r, :]
        (number, stock_id, buy_time, sell_time,
         buy_price, sell_price, volumn, buy_cost, sell_cost, revenue) = row.values

        operates.append([buy_time, BuySell.Buy, buy_cost])
        # operates.append([buy_time, "buy", buy_cost])

        # sell_cost 在進來前就被扣掉，應該可以忽略
        operates.append([sell_time, BuySell.Sell, buy_cost + revenue])
        # operates.append([sell_time, "sell", buy_cost + revenue])

    # print(operates)
    operates = sortOperates(operates)
    # print(operates)

    input_funds = 0
    funds = 0

    for operate in operates:
        _, op, fund = operate

        if op == BuySell.Buy:
            if fund > funds:
                gap = fund - funds

                input_funds += gap
                funds += gap
                print(f"資金不足，增資 {gap} 元, funds: {funds}, input_funds: {input_funds}")

            funds -= fund
            print(f"購買花費 {fund} 元, funds: {funds}, input_funds: {input_funds}")
        else:
            funds += fund
            print(f"售出收入 {fund} 元, funds: {funds}, input_funds: {input_funds}")

    return_rate = funds / input_funds
    during = operates[-1][0] - operates[0][0]
    n_year = during / datetime.timedelta(days=365.25)
    year_index = 1.0 / n_year
    annually_return_rate = pow(return_rate, year_index)
    print(f"{during.days} days, 報酬率: {return_rate}, 年報酬率: {annually_return_rate}")


# 交易紀錄索引值
def getLastNumber():
    path = "data/trade_record.csv"

    with open(path, "r") as file:
        for line in file:
            pass

        content = line.split(",")
        number = content[0]
        return int(number)


def renumber():
    path = "data/trade_record.csv"
    df = pd.read_csv(path,
                     dtype={0: int, 1: str, 2: str, 3: str, 4: str, 5: str, 6: str, 7: str, 8: str, 9: str})
    n_data = len(df)
    numbers = list(range(1, n_data + 1))
    df["number"] = numbers

    df.to_csv(path, index=False)


def getLastBuyTime(df, stock_id):
    sub_df = df[df["stock_id"] == stock_id].copy()
    sub_df.sort_values(by=["number", "buy_time"], inplace=True)
    last_buy = list(sub_df.iloc[-1])[2]

    return time_parser(last_buy)


# def recordDividend(stock_id: str, revenue: str, pay_time: datetime.datetime = datetime.datetime.today()):
#     path = "data/trade_record.csv"
#     df = pd.read_csv(path,
#                      dtype={0: int, 1: str, 2: str, 3: str, 4: str, 5: str, 6: str, 7: str, 8: str, 9: str})
#
#     last_buy = getLastBuyTime(df, stock_id=stock_id)
#     buy_time = last_buy.strftime("%Y-%m-%d")
#     sell_time = pay_time.strftime("%Y-%m-%d")
#
#     number = getLastNumber() + 1
#     df = df.append({"number": number,
#                     "stock_id": stock_id,
#                     "buy_time": buy_time,
#                     "sell_time": sell_time,
#                     "buy_price": "0",
#                     "sell_price": "0",
#                     "volumn": 0,
#                     "buy_cost": "0",
#                     "sell_cost": "0",
#                     "revenue": revenue}, ignore_index=True)
#     df.to_csv(path, index=False)


if __name__ == "__main__":
    evaluateTradingPerformance()
    # renumber()
    # number = getLastNumber()
    # print(f"number: {number}")


