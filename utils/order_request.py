import datetime
import functools
import json
from decimal import Decimal
from enums import BuySell

"""
request = (guid: str, stock_id: str, time: datetime.datetime, price: float, volumn: int)
"""


def sortRequests(requests, price_reverse=False):
    """
    將請求做排序，排序優先順序為: 價格(越高越前) -> 數量(越少越前) -> 時間(越早越前)
    XXX_requests -> [guid, stock_id, date_time, price, volumn]

    :param requests: 所有請求
    :param price_reverse: 反轉價格，越低排越前面。
    :return:
    """

    def compareRequests(r1, r2):
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

        :param r1: 請求 1
        :param r2: 請求 2
        :return:
        """
        # guid, stock_id, date_time, price, volumn = request
        # guid 和 stock_id 與排序無關
        _, _, time1, price1, volumn1 = r1
        _, _, time2, price2, volumn2 = r2

        # 價格越低排越前面
        if price_reverse:
            if price1 < price2:
                return -1
            elif price1 > price2:
                return 1
        # 價格越高排越前面
        else:
            if price1 > price2:
                return -1
            elif price1 < price2:
                return 1

        # 數量少的排前面
        if volumn1 < volumn2:
            return -1

        # 數量多的排後面
        elif volumn1 > volumn2:
            return 1
        else:
            # 時間早的排前面
            if time1 < time2:
                return -1

            # 時間晚的排後面
            elif time1 > time2:
                return 1

        return 0

    # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
    return sorted(requests, key=functools.cmp_to_key(compareRequests))


def sortDealRequests(requests: list, buy_sell: BuySell):
    """
    將請求做排序，排序優先順序為: 價格(越 高/低 越前) -> 時間(越早越前)
    XXX_requests -> [user, guid, date_time, price, volumn]

    :param requests: 所有請求
    :param buy_sell: 反轉價格，越低排越前面。
    :return:
    """

    def compareRequests(r1, r2):
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

        :param r1: 請求 1
        :param r2: 請求 2
        :return:
        """
        # user, guid, date_time, price, volumn = request
        # guid 和 stock_id 與排序無關
        _, _, time1, price1, volumn1 = r1
        _, _, time2, price2, volumn2 = r2

        # 價格越低排越前面
        if buy_sell == BuySell.Sell:
            if price1 < price2:
                return -1
            elif price1 > price2:
                return 1
            else:
                # 時間早的排前面
                if time1 < time2:
                    return -1

                # 時間晚的排後面
                elif time1 > time2:
                    return 1

                # 時間相同，出價也相同
                else:
                    return 0

        # 價格越高排越前面 BuySell.Buy
        else:
            if price1 > price2:
                return -1
            elif price1 < price2:
                return 1
            else:
                # 時間早的排前面
                if time1 < time2:
                    return -1

                # 時間晚的排後面
                elif time1 > time2:
                    return 1

                # 時間相同，出價也相同
                else:
                    return 0

    # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
    return sorted(requests, key=functools.cmp_to_key(compareRequests))


def saveRequests(requests, path):
    data = []

    for request in requests:
        guid, stock_id, time, price, volumn = request
        data.append([guid, stock_id, time.strftime('%Y-%m-%d %H:%M:%S'), str(price), volumn])

    with open(path, "w") as f:
        json.dump(data, f)


def loadRequests(path):
    requests = []

    with open(path, "r") as f:
        datas = json.load(f)

        for data in datas:
            guid, stock_id, time, price, volumn = data
            date_time = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
            requests.append([guid, stock_id, date_time, Decimal(price), volumn])

    return requests


if __name__ == "__main__":
    """
    request = (guid: str, stock_id: str, time: datetime.datetime, price: float, volumn: int)
    """

    requests = [["abc", "9527", datetime.datetime(2020, 4, 7), Decimal("56.1"), 8],
                ["def", "9527", datetime.datetime(2020, 4, 8), Decimal("36.1"), 6],
                ["ghi", "9527", datetime.datetime(2020, 4, 8), Decimal("50.1"), 6],
                ["jkl", "9527", datetime.datetime(2020, 4, 8), Decimal("10.1"), 6],
                ["mno", "9527", datetime.datetime(2020, 3, 7), Decimal("57.1"), 18],
                ["pqr", "3150", datetime.datetime(2020, 6, 7), Decimal("56.1"), 8],
                ["stu", "3150", datetime.datetime(2020, 4, 8), Decimal("36.1"), 6],
                ["vwx", "3150", datetime.datetime(2020, 6, 8), Decimal("56.1"), 6],
                ["zya", "3150", datetime.datetime(2020, 4, 6), Decimal("10.1"), 6],
                ["bcd", "3150", datetime.datetime(2020, 3, 7), Decimal("37.1"), 18]]

    sort_requests = sortRequests(requests)

    path = "data/buy_requests/sort_requests.json"
    saveRequests(sort_requests, path=path)

    del requests
    del sort_requests

    requests = loadRequests(path=path)

    for request in requests:
        print(request)
