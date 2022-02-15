import datetime
import json
from decimal import Decimal

from data.database.stock_list import StockListBase
from enums import Category


class StockCategory:
    stock_category_path = "data/stock_category.json"
    stock_category = None

    @classmethod
    def loadStockCategory(cls):
        if cls.stock_category is None:
            with open(cls.stock_category_path) as f:
                cls.stock_category = json.load(f)

    @classmethod
    def saveStockCategory(cls, stock_category):
        with open(cls.stock_category_path, "w") as f:
            json.dump(stock_category, f)

    @classmethod
    def getStockByCategory(cls, category: list):
        cls.loadStockCategory()
        stocks = []

        # TODO: 篩選 day_trading/non_day_trading foreign_etf，目前被包含在 etf 之下
        def stockFilter(d_stock=False, d_etf=False, nd_stock=False, nd_etf=False):
            if d_stock:
                for stock in cls.stock_category["day_trading"]["stock"]:
                    stocks.append(stock)

            if d_etf:
                for stock in cls.stock_category["day_trading"]["etf"]:
                    stocks.append(stock)

                for stock in cls.stock_category["day_trading"]["foreign_etf"]:
                    stocks.append(stock)

            if nd_stock:
                for stock in cls.stock_category["non_day_trading"]["stock"]:
                    stocks.append(stock)

            if nd_etf:
                for stock in cls.stock_category["non_day_trading"]["etf"]:
                    stocks.append(stock)

                for stock in cls.stock_category["non_day_trading"]["foreign_etf"]:
                    stocks.append(stock)

        if (Category.DayTrading in category) and (Category.NonDayTrading not in category):
            # 只要 day_trading 的 stock
            if (Category.Stock in category) and (Category.Etf not in category):
                stockFilter(d_stock=True, d_etf=False, nd_stock=False, nd_etf=False)

            # 只要 day_trading 的 etf
            elif (Category.Stock not in category) and (Category.Etf in category):
                stockFilter(d_stock=False, d_etf=True, nd_stock=False, nd_etf=False)

            # 只要是 day_trading 就都要
            else:
                stockFilter(d_stock=True, d_etf=True, nd_stock=False, nd_etf=False)

        elif (Category.DayTrading not in category) and (Category.NonDayTrading in category):
            # 只要 non_day_trading 的 stock
            if (Category.Stock in category) and (Category.Etf not in category):
                stockFilter(d_stock=False, d_etf=False, nd_stock=True, nd_etf=False)

            # 只要 non_day_trading 的 etf
            elif (Category.Stock not in category) and (Category.Etf in category):
                stockFilter(d_stock=False, d_etf=False, nd_stock=False, nd_etf=True)

            # 只要是 non_day_trading 就都要
            elif Category.Etf in category:
                stockFilter(d_stock=False, d_etf=False, nd_stock=True, nd_etf=True)

        else:
            # 只要是 stock 就都要
            if (Category.Stock in category) and (Category.Etf not in category):
                stockFilter(d_stock=True, d_etf=False, nd_stock=True, nd_etf=False)

            # 只要是 etf 就都要
            elif (Category.Stock not in category) and (Category.Etf in category):
                stockFilter(d_stock=False, d_etf=True, nd_stock=False, nd_etf=True)

            # 我全都要
            else:
                stockFilter(d_stock=True, d_etf=True, nd_stock=True, nd_etf=True)

        return stocks

    @classmethod
    def isEtf(cls, stock_id: str):
        cls.loadStockCategory()

        condition1 = stock_id in cls.stock_category["day_trading"]["etf"]
        condition2 = stock_id in cls.stock_category["day_trading"]["foreign_etf"]
        condition3 = stock_id in cls.stock_category["non_day_trading"]["etf"]
        condition4 = stock_id in cls.stock_category["non_day_trading"]["foreign_etf"]

        return condition1 or condition2 or condition3 or condition4

    @classmethod
    def isDayTrading(cls, stock_id: str):
        cls.loadStockCategory()

        condition1 = stock_id in cls.stock_category["day_trading"]["etf"]
        condition2 = stock_id in cls.stock_category["day_trading"]["foreign_etf"]
        condition3 = stock_id in cls.stock_category["day_trading"]["stock"]

        return condition1 or condition2 or condition3

    @classmethod
    def isForeignEtf(cls, stock_id: str):
        cls.loadStockCategory()

        condition1 = stock_id in cls.stock_category["day_trading"]["foreign_etf"]
        condition2 = stock_id in cls.stock_category["non_day_trading"]["foreign_etf"]

        return condition1 or condition2


# Ohlc 數據分析
def parseOhlcData(ohlc_data: str, is_minute_data=False, is_str_datetime=False):
    """
    解析 Ohlc 字串數據，

    :param ohlc_data: 依序為: 年/月/日 時:分, 開盤價, 最高價, 最低價, 收盤價, 成交量
                      例： 2020/07/06 13:06, 335.500000, 336.000000, 335.500000, 335.500000, 77
    :param is_minute_data: 是否為 1 分 K(時間格式會有所不同)
    :param is_str_datetime: 是否以字串形式回傳時間
    :return:
    """
    split_data = ohlc_data.split(', ')

    if is_str_datetime:
        date_time = split_data[0]
    else:
        if is_minute_data:
            date_time = datetime.datetime.strptime(split_data[0], "%Y/%m/%d %H:%M")
        else:
            date_time = datetime.datetime.strptime(split_data[0], "%Y/%m/%d")

    open_value = Decimal(split_data[1])
    high_value = Decimal(split_data[2])
    low_value = Decimal(split_data[3])
    close_value = Decimal(split_data[4])
    volumn = int(split_data[5])

    return date_time, open_value, high_value, low_value, close_value, volumn


if __name__ == "__main__":
    # foreign_etf: (00712)
    StockCategory.loadStockCategory()
    stock_category = StockCategory.stock_category

    for etf in stock_category["day_trading"]["foreign_etf"]:
        print(etf)
