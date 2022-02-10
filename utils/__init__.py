from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

import numpy as np
from scipy.stats import truncnorm

import utils.globals_variable as gv

"""
EPS: 稅後淨利 / 股數
ROA(Return of asset): 稅後淨利 / 資產
ROE(Return of equity): 稅後淨利 / 淨值(股東權益)
本益比(PER): 股價 / EPS (通常為定值，用來判斷當前股價偏高或偏低)
股價淨值比(PBR): 淨值(股東權益) / 股數
殖利率(Yield): 每年回報多少 % 的股利

"""


def unitPrice(price, is_etf=False) -> Decimal:
    if is_etf:
        # 每受益權單位市價未滿 50 元者為 1 分；50 元以上為 5 分
        # https://www.twse.com.tw/zh/ETF/fund/0050
        if price < Decimal("50.0"):
            return Decimal("0.01")
        else:
            return Decimal("0.05")
    else:
        if price < Decimal("10.0"):
            return Decimal("0.01")
        elif price < Decimal("50.0"):
            return Decimal("0.05")
        elif price < Decimal("100.0"):
            return Decimal("0.1")
        elif price < Decimal("500.0"):
            return Decimal("0.5")
        elif price < Decimal("1000.0"):
            return Decimal("1.0")
        else:
            return Decimal("5.0")


def unitPrices(prices, is_etf=False):
    if is_etf:
        # 每受益權單位市價未滿 50 元者為 1 分；50 元以上為 5 分
        # https://www.twse.com.tw/zh/ETF/fund/0050
        unit_prices = np.ones_like(prices) * 0.05
        unit_prices[np.where(prices < 50.0)] = 0.01

    else:
        unit_prices = np.ones_like(prices) * 5.0
        unit_prices[np.where(prices < 1000.0)] = 1.0
        unit_prices[np.where(prices < 500.0)] = 0.5
        unit_prices[np.where(prices < 100.0)] = 0.1
        unit_prices[np.where(prices < 50.0)] = 0.05
        unit_prices[np.where(prices < 10.0)] = 0.01

    return unit_prices


def getValidPrice(price: Decimal, is_etf=False) -> Decimal:
    """
    當價格在變動時可能跨過價格單位的級距，或由外部添加價格到原始價格上，外部添加的數值不一定會符合價格跳動單位，
    透過此函式，可先:
    1.找出計算完的數值所在級距
    2.計算該數值為價格跳動單位多少倍(倍數須為整數)
    3.根據倍數和價格跳動單位，計算有效的價格

    :param price: 在外部計算後的價格(未考慮各級距的價格跳動單位)
    :param is_etf: 是否為 ETF
    :return: 符合價格跳動單位的價格
    """
    unit_price = unitPrice(price, is_etf=is_etf)
    unit = price // unit_price
    return (unit_price * unit).quantize(Decimal('.00'), ROUND_HALF_UP)


def getLastValidPrice(price, is_etf=False) -> Decimal:
    return getValidPrice(price=price - unitPrice(price=price, is_etf=is_etf), is_etf=is_etf)


def getNextValidPrice(price, is_etf=False) -> Decimal:
    return getValidPrice(price=price + unitPrice(price=price, is_etf=is_etf), is_etf=is_etf)


def getValidPrices(prices, is_etf=False):
    """
    當價格在變動時可能跨過價格單位的級距，或由外部添加價格到原始價格上，外部添加的數值不一定會符合價格跳動單位，
    透過此函式，可先:
    1.找出計算完的數值所在級距
    2.計算該數值為價格跳動單位多少倍(倍數須為整數)
    3.根據倍數和價格跳動單位，計算有效的價格

    :param prices: 在外部計算後的價格(未考慮各級距的價格跳動單位)
    :param is_etf: 是否為 ETF
    :return: 符合價格跳動單位的價格
    """
    unit_prices = unitPrices(prices, is_etf=is_etf)
    unit = (prices * 100) / (unit_prices * 100)
    unit = unit.astype(np.int)
    return unit_prices * unit


def alphaCost(price: Decimal, discount: Decimal, volumn=1) -> Decimal:
    # 交易手續費：群益會將小數點以下做四捨五入
    alpha = Decimal("0.001425") * discount

    # alpha_cost -> int
    alpha_cost = (price * alpha * volumn * Decimal("1000")).quantize(Decimal('0'), ROUND_HALF_UP)

    if alpha_cost < 20:
        alpha_cost = Decimal("20")

    return alpha_cost


def betaCost(price, is_etf, is_day_trading=False, volumn=1) -> Decimal:
    """
    證交稅 = 賣出成交金額 * beta

    :param price:
    :param is_etf:
    :param is_day_trading: 是否為當沖
    :param volumn:
    :return:
    """
    # 證交稅：股票 0.003(當沖為 0.0015) ETF 0.001(當沖沒有折扣)
    if is_etf:
        beta = Decimal("0.001")
    else:
        if is_day_trading:
            beta = Decimal("0.0015")
        else:
            beta = Decimal("0.003")

    # 小數點似乎是無條件捨去(Decimal -> ROUND_FLOOR)
    beta_cost = (price * beta * volumn * 1000).quantize(Decimal('0'), ROUND_FLOOR)

    return beta_cost


def getStopValue(price: Decimal, is_etf=False, spread: Decimal = None, percent: Decimal = Decimal("0.1")) -> Decimal:
    if spread is not None:
        return getValidPrice(price - spread, is_etf)

    if percent is not None:
        # percent 為跌幅，因此停損價是 price * (1 - percent)
        return getValidPrice(price * (Decimal("1") - percent), is_etf)

    return getValidPrice(price - Decimal("2.0"), is_etf)


def anyInArray(array, elements):
    """
    要尋找的任一元素，存在於 array 當中即返回 True，否則返回 False

    :param array: 被搜尋的陣列
    :param elements: 要尋找的元素們
    :return:
    """
    for element in elements:
        if element in array:
            return True

    return False


def computeProfit(price_buy, price_sell, is_etf=False):
    gv.initialize()
    e_capital_discount = gv.e_capital_discount

    buy_cost = price_buy * 1000 + alphaCost(price_buy, e_capital_discount)
    sell_cost = alphaCost(price_sell, e_capital_discount) + betaCost(price_sell, is_etf=is_etf)
    cost = buy_cost + sell_cost
    income = price_sell * 1000
    profit = income - cost

    return profit


def truncatedNormal(low=-0.5, high=0.5, loc=0, scale=1, size=None):
    high = max(high, low)
    low = min(high, low)

    return truncnorm.rvs(low, high, loc=loc, scale=scale, size=size)


if __name__ == "__main__":
    pass
