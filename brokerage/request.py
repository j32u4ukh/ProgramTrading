import datetime
import functools
from decimal import Decimal

from enums import BuySell


# @total_ordering
class Request:
    def __init__(self, user: int, guid: str, stock_id: str, time: datetime.datetime, price: Decimal, volumn: int = 1,
                 buy_sell: BuySell = BuySell.Buy):
        self.user = user
        self.guid = guid
        self.stock_id = stock_id
        self.time = time
        self.price = price
        self.volumn = volumn
        self.buy_sell = buy_sell

    # region TODO: 可能是不需要的，若無比較大小的需求，就把它們移除。註解掉，其他地方執行若無問題，就表示這部分是不需要的。
    # def __eq__(self, other):
    #     return (self.price == other.price) and (self.time == other.time)
    #
    # def __gt__(self, other):
    #     # 價格越低排越前面
    #     if self.buy_sell == BuySell.Sell:
    #         if self.price > other.price:
    #             return True
    #         elif self.price < other.price:
    #             return False
    #         else:
    #             # 時間早的排前面
    #             if self.time > other.time:
    #                 return True
    #
    #             # 時間晚的排後面
    #             elif self.time < other.time:
    #                 return False
    #
    #             # 時間相同，出價也相同
    #             else:
    #                 return True
    #
    #     # 價格越高排越前面 BuySell.Buy
    #     else:
    #         if self.price < other.price:
    #             return True
    #         elif self.price > other.price:
    #             return False
    #         else:
    #             # 時間早的排前面
    #             if self.time > other.time:
    #                 return True
    #
    #             # 時間晚的排後面
    #             elif self.time < other.time:
    #                 return False
    #
    #             # 時間相同，出價也相同
    #             else:
    #                 return True
    # endregion

    def __repr__(self):
        if self.buy_sell == BuySell.Buy:
            buy_sell = "Buy"
        else:
            buy_sell = "Sell"

        description = f"{buy_sell}Request(user: {self.user}, stock_id: {self.stock_id}, time: {self.time}, "
        description += f"price: {self.price}, volumn: {self.volumn}, guid: {self.guid})"

        return description

    __str__ = __repr__

    @staticmethod
    def deal(buy_request, sell_request):
        if sell_request.price > buy_request.price:
            return None

        if buy_request.buy_sell != BuySell.Buy:
            return None

        if sell_request.buy_sell != BuySell.Sell:
            return None

        volumn = min(buy_request.volumn, sell_request.volumn)
        buy_request.volumn -= volumn
        sell_request.volumn -= volumn

        time = max(buy_request.time, sell_request.time)

        buyer_info = (buy_request.user, buy_request.guid)
        seller_info = (sell_request.user, sell_request.guid)

        return time, buyer_info, seller_info, sell_request.price, volumn

    @staticmethod
    def merge(price, buy_requests: list, sell_requests: list):
        # buy_requests = Request.sorted(requests=buy_requests, buy_sell=BuySell.Buy)
        # sell_requests = Request.sorted(requests=sell_requests, buy_sell=BuySell.Sell)

        def compareRequests(r1: Request, r2: Request):
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
            if r1.buy_sell == BuySell.Buy:
                offset1 = r1.price - price
            else:
                offset1 = price - r1.price

            if r2.buy_sell == BuySell.Buy:
                offset2 = r2.price - price
            else:
                offset2 = price - r2.price

            # 買賣價格偏離成交價越多越優先(購買價越高 或 售出價越低)，購買價偏差校正後，兩者都是 offset 越小越優先

            # offset 小的排前面
            if offset1 < offset2:
                return 1

            # offset 大的排後面
            elif offset1 > offset2:
                return -1

            # offset 相同
            else:
                # 時間早的排前面
                if r1.time < r2.time:
                    return -1

                # 時間晚的排後面
                elif r1.time > r2.time:
                    return 1

                # 時間相同，offset 也相同
                else:
                    return 0

        # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
        # buy_requests, sell_requests 皆已排序，這裡只根據價格偏離來排序，其他參數則會按照原本的順序排序
        requests = buy_requests + sell_requests
        return sorted(requests, key=functools.cmp_to_key(compareRequests))

    @staticmethod
    def sorted(requests: list, buy_sell: BuySell = BuySell.Sell):
        """
        將請求做排序，排序優先順序為: 價格(越 高/低 越前) -> 時間(越早越前)
        XXX_requests -> [user, guid, date_time, price, volumn]

        :param requests: 所有請求
        :param buy_sell: 請求類型
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
            if buy_sell == BuySell.Sell:
                # 價格低的排前面
                if r1.price < r2.price:
                    return -1

                # 價格高的排後面
                elif r1.price > r2.price:
                    return 1

                else:
                    # 時間早的排前面
                    if r1.time < r2.time:
                        return -1

                    # 時間晚的排後面
                    elif r1.time > r2.time:
                        return 1

                    # 時間相同，出價也相同
                    else:
                        return 0

            # BuySell.Buy
            else:
                # 價格高的排前面
                if r1.price > r2.price:
                    return -1

                # 價格低的排後面
                elif r1.price < r2.price:
                    return 1

                else:
                    # 時間早的排前面
                    if r1.time < r2.time:
                        return -1

                    # 時間晚的排後面
                    elif r1.time > r2.time:
                        return 1

                    # 時間相同，出價也相同
                    else:
                        return 0

        # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
        return sorted(requests, key=functools.cmp_to_key(compareRequests))

    def unboxing(self):
        # user, stock_id, guid, time, price, volumn, buy_sell = request
        return self.user, self.stock_id, self.guid, self.time, self.price, self.volumn, self.buy_sell

    def dealOhlc(self, high, low, volumn):
        deal_price, deal_volumn = 0, 0

        if volumn == 0:
            return 0, (self.buy_sell, deal_price, deal_volumn)

        if self.buy_sell == BuySell.Buy:
            # 購買成交價最低不低於 low
            if self.price >= low:
                # 實際成交量不超過 Ohlc 剩餘成交量
                deal_volumn = min(self.volumn, volumn)

                # 購買成交價最高不超過 high
                deal_price = min(self.price, high)

                # 請求和 Ohlc 的數量皆扣除此次交易的數量
                self.volumn -= deal_volumn
                volumn -= deal_volumn

        else:
            # 售出成交價最高不超過 high
            if self.price <= high:
                # 實際成交量不超過 Ohlc 剩餘成交量
                deal_volumn = min(self.volumn, volumn)

                # 售出成交價最低不低於 low
                deal_price = max(self.price, low)

                # 請求和 Ohlc 的數量皆扣除此次交易的數量
                self.volumn -= deal_volumn
                volumn -= deal_volumn

        return volumn, (self.buy_sell, self.user, self.stock_id, self.time, deal_price, deal_volumn, self.guid)


if __name__ == "__main__":
    buy_requests = [Request(0, "0", "9527", datetime.datetime(2021, 8, 20, 9, 0, 0), Decimal("11.20"), 1, BuySell.Buy),
                    Request(2, "2", "9527", datetime.datetime(2021, 8, 20, 9, 1, 0), Decimal("11.10"), 1, BuySell.Buy),
                    Request(5, "5", "9527", datetime.datetime(2021, 8, 20, 9, 1, 4), Decimal("11.10"), 1, BuySell.Buy),
                    Request(7, "7", "9527", datetime.datetime(2021, 8, 20, 9, 2, 0), Decimal("11.05"), 1, BuySell.Buy),
                    Request(8, "8", "9527", datetime.datetime(2021, 8, 20, 9, 2, 0), Decimal("11.30"), 1, BuySell.Buy)]

    buy_requests = Request.sorted(buy_requests, buy_sell=BuySell.Buy)

    for buy_request in buy_requests:
        print(buy_request)

    sell_requests = [
        Request(1, "1", "9527", datetime.datetime(2021, 8, 20, 9, 1, 1), Decimal("11.20"), 1, BuySell.Sell),
        Request(3, "3", "9527", datetime.datetime(2021, 8, 20, 9, 0, 0), Decimal("11.15"), 1, BuySell.Sell),
        Request(4, "4", "9527", datetime.datetime(2021, 8, 20, 9, 0, 0), Decimal("11.30"), 3, BuySell.Sell),
        Request(6, "6", "9527", datetime.datetime(2021, 8, 20, 9, 2, 1), Decimal("11.20"), 1, BuySell.Sell),
        Request(9, "9", "9527", datetime.datetime(2021, 8, 20, 9, 1, 5), Decimal("11.15"), 1, BuySell.Sell)]

    sell_requests = Request.sorted(sell_requests, buy_sell=BuySell.Sell)

    for sell_request in sell_requests:
        print(sell_request)

    price = Decimal("11.20")
    requests = Request.merge(price=price, buy_requests=buy_requests, sell_requests=sell_requests)

    for request in requests:

        if request.buy_sell == BuySell.Buy:
            offset = request.price - price
        else:
            offset = price - request.price

        print(request, offset)
