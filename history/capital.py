import datetime
from decimal import Decimal, ROUND_HALF_UP
from dateutil.parser import parse as time_parser
import pandas as pd

from enums import CapitalType


class LocalCapital:
    def __init__(self):
        self.path = "data/funds.csv"
        # NUMBER,TIME,USER,TYPE,FLOW,STOCK,REMARK
        self.df = pd.read_csv(self.path, dtype={0: int, 1: str, 2: str, 3: str, 4: str, 5: str, 6: str})
        self.administrator = "j32u4ukh"
        self.users = ["ahuayeh"]
        self.number = self.getLastNumber()

    def getLastNumber(self):
        # [146, '2021/9/30', 'j32u4ukh', 'revenue', '2833', '421635', '79']
        data = list(self.df.iloc[-1])

        return data[0]

    def getUsersCapital(self):
        df = self.df[self.df["TYPE"] == CapitalType.Capital.value]
        admin_capital = self.getUserCapital(df=df, user=self.administrator, preprocess=True)
        users_capital = {self.administrator: admin_capital}

        for user in self.users:
            users_capital[user] = self.getUserCapital(df=df, user=user, preprocess=True)

        return users_capital

    @staticmethod
    def getUserCapital(df, user, preprocess=False):
        capital = Decimal("0")

        if preprocess:
            user_df = df[df["USER"] == user]
        else:
            user_df = df[(df["USER"] == user) & (df["TYPE"] == CapitalType.Capital.value)]

        n_data = len(user_df)

        for i in range(n_data):
            # NUMBER,TIME,USER,TYPE,FLOW,STOCK,REMARK
            data = user_df.iloc[i]
            capital += Decimal(data["FLOW"])

        return capital

    def getUsersStock(self, time: datetime.datetime = datetime.datetime.today()):
        self.df["TIME"] = pd.to_datetime(self.df["TIME"])
        df = self.df[self.df["TIME"] <= time]
        admin_stock = self.getUserStock(df=df, user=self.administrator, preprocess=True)
        users_stock = {self.administrator: admin_stock}

        for user in self.users:
            users_stock[user] = self.getUserStock(df=df, user=user, preprocess=True)

        return users_stock

    @staticmethod
    def getUserStock(df, user, time: datetime.datetime = datetime.datetime.today(), preprocess=False):
        if preprocess:
            user_df = df[df["USER"] == user]
        else:
            df["TIME"] = pd.to_datetime(df["TIME"])
            user_df = df[(df["USER"] == user) & (df["TIME"] <= time)]

        if len(user_df) == 0:
            return Decimal("0")

        data = user_df.iloc[-1]
        stock = Decimal(data["STOCK"])

        return stock

    def getCapitalSummary(self, time: datetime.datetime = datetime.datetime.today()):
        summary = dict()
        users = self.users.copy() + [self.administrator]

        capitals = self.getUsersCapital()
        last_time = time - datetime.timedelta(days=1)
        last_stocks = self.getUsersStock(time=last_time)
        curr_stocks = self.getUsersStock(time=time)

        for user in users:
            summary[user] = dict(capital=capitals[user],
                                 last_stock=last_stocks[user],
                                 stock=curr_stocks[user])

        return summary

    def allocateRevenue(self, deal_time: datetime.datetime, remark: str, trade_revenue: Decimal):
        summary = self.getCapitalSummary(time=deal_time)
        # print("summary:", summary)
        # {'j32u4ukh':
        #   {'capital': Decimal('451595.0'), 'last_stock': Decimal('456592.00'), 'stock': Decimal('456592.00')},
        # 'ahuayeh':
        #   {'capital': Decimal('200000.0'), 'last_stock': Decimal('203456'), 'stock': Decimal('203456')}}

        rate_dict = dict()
        total_last_stock = Decimal("0")

        # 取出所有用戶前一天的資金存量
        for user in summary.keys():
            user_summary = summary[user]
            last_stock = user_summary["last_stock"]

            rate_dict[user] = last_stock
            total_last_stock += last_stock

        # 根據用戶前一天的資金存量，計算資金比例
        for user, stock in rate_dict.items():
            rate_dict[user] = stock / total_last_stock
            # print(f"Last {user}: {rate_dict[user]}% ({stock})")

        allocated_revenu = Decimal("0")

        for user in self.users:
            stock = summary[user]["stock"]
            rate = rate_dict[user]

            # 將 trade_revenue 根據 user 交易日前一天的資金存量比例，計算 user 分配到的收益
            user_revenu = (trade_revenue * rate).quantize(Decimal('0'), ROUND_HALF_UP)

            # 累計已分配收益
            allocated_revenu += user_revenu

            # 更新 user 的資金存量
            stock += user_revenu

            self.add(time=deal_time,
                     user=user,
                     capital_type=CapitalType.Revenue,
                     flow=user_revenu,
                     stock=stock,
                     remark=remark)

        stock = summary[self.administrator]["stock"]

        # administrator 的損益為"總損益 - 已分配損益"，確保不因四捨五入的誤差，造成 "總分配損益" 和 "總損益" 有所偏差
        administrator_revenu = (trade_revenue - allocated_revenu).quantize(Decimal('0'), ROUND_HALF_UP)
        stock += administrator_revenu
        stock = stock.quantize(Decimal('0'), ROUND_HALF_UP)

        self.add(time=deal_time,
                 user=self.administrator,
                 capital_type=CapitalType.Revenue,
                 flow=administrator_revenu,
                 stock=stock,
                 remark=remark)

        self.save()

    def add(self, time: datetime.datetime, user: str, capital_type: CapitalType, flow: Decimal, stock: Decimal,
            remark: str):
        # NUMBER,TIME(2020/06/17),USER,TYPE,FLOW,STOCK,REMARK
        self.number += 1
        self.df = self.df.append({"NUMBER": self.number,
                                  "TIME": time.strftime("%Y/%m/%d"),
                                  "USER": user,
                                  "TYPE": capital_type.value,
                                  "FLOW": str(flow),
                                  "STOCK": str(stock),
                                  "REMARK": remark
                                  }, ignore_index=True)

    def save(self):
        self.df.sort_values(by=["NUMBER"], inplace=True)

        self.df["TIME"] = pd.to_datetime(self.df["TIME"])

        # 資金數據更新
        self.df.to_csv(self.path, index=False)


if __name__ == "__main__":
    lc = LocalCapital()
    # lc.save()

    records = """97,3003,2021-10-19,2021-11-23,91.00,95.00,1000.0,91039.00,325,3636.00
98,3588,2021-11-10,2021-11-23,138.50,155.00,1000.0,138559.00,531,15910.00"""

    trade_records = records.split("\n")

    for trade_record in trade_records:
        number, _, _, sell_time, _, _, _, _, _, revenue = trade_record.split(',')
        print(number, sell_time, revenue)
        # time_parser
        lc.allocateRevenue(deal_time=time_parser(sell_time), remark=number, trade_revenue=Decimal(revenue))

    # # NUMBER,TIME,USER,TYPE,FLOW,STOCK,REMARK
    # # 85,3048,2021-08-25,2021-10-12,0.00,29.50,0.1,1.00,8.00,2941.00
    # lc.allocateRevenue(deal_time=datetime.datetime(2021, 10, 12), remark="85", trade_revenue=Decimal("2941"))
    #
    # # 86,3048,2021-08-25,2021-10-12,0,0,0,0,0,1890
    # lc.allocateRevenue(deal_time=datetime.datetime(2021, 10, 12), remark="86", trade_revenue=Decimal("1890"))

    lc.save()