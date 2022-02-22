import datetime
import logging
from decimal import Decimal

from brokerage.request import Request
from data import parseOhlcData
from enums import BuySell
from submodule.Xu3.utils import getLogger
from submodule.events import Event


class Order:
    """ 交易系統
    * 處理交易請求(畢竟數據保留在此)，需訂閱報價
    * 成交後，通知 Reply 系統(將再通知用戶，以及紀錄庫存資訊，沒有庫存者將被禁止售出)
    """

    def __init__(self, logger_dir="brokerage", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__()

        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)
        self.logger.setLevel(logging.DEBUG)

        self.deal_requests = {}

        # 緩存交易系統需要處理的股票代碼(有些股票訂閱了，但沒有交易請求，可以直接忽略不處理)
        # TODO: 被交易完後，應從 self.stocks 當中移除
        self.stocks = set()

        # region 事件
        self.event = Event()

        # 成功買入事件
        # onBought(user, stock_id, guid, time, price, volumn)
        self.onBought = self.event.onBought

        # 成功賣出事件
        # onSold(user, stock_id, guid, time, price, volumn)
        self.onSold = self.event.onSold

    def setLoggerLevel(self, level):
        self.logger.setLevel(level=level)

    def subscribe(self, stock_id):
        if not self.deal_requests.__contains__(stock_id):
            self.deal_requests[stock_id] = dict(buy=[], sell=[])

    # 收到'購買'請求後的處理
    def buy(self, user: int, stock_id: str, guid: str, time: datetime.datetime, price: Decimal, volumn: int = 1):
        buy_requests = self.deal_requests[stock_id]["buy"]

        request = Request(user, guid, stock_id, time, price, volumn, BuySell.Buy)
        self.logger.info(f"New request: {request}", extra=self.extra)

        buy_requests.append(request)

        # 緩存交易系統需要處理的股票代碼
        self.stocks.add(stock_id)

        # sortDealRequests: price 由大到小，時間由早到晚
        self.deal_requests[stock_id]["buy"] = sorted(buy_requests)

        # 處理 buy_requests 和 sell_requests 之間的搓合
        if len(self.deal_requests[stock_id]["sell"]) > 0:
            self.checkRequestDeal(stock_id=stock_id)

    def sell(self, user: int, stock_id: str, guid: str, time: datetime.datetime, price: Decimal, volumn: int = 1):
        sell_requests = self.deal_requests[stock_id]["sell"]

        request = Request(user, guid, stock_id, time, price, volumn, BuySell.Sell)
        self.logger.info(f"New request: {request}", extra=self.extra)

        sell_requests.append(request)

        # 緩存交易系統需要處理的股票代碼
        self.stocks.add(stock_id)

        # sortDealRequests: price 由小到大，時間由早到晚
        self.deal_requests[stock_id]["sell"] = sorted(sell_requests)

        # 處理 buy_requests 和 sell_requests 之間的搓合
        if len(self.deal_requests[stock_id]["buy"]) > 0:
            self.checkRequestDeal(stock_id=stock_id)

    def onOhlcNotifyListener(self, stock_id, ohlc_data):
        self.logger.info(f"({stock_id}) {ohlc_data}", extra=self.extra)

        if stock_id in self.stocks:
            # date_time, open_value, high_value, low_value, close_value, volumn
            (date_time, _, high, low, _, volumn) = parseOhlcData(ohlc_data)
            self.checkOhlcDeal(stock_id=stock_id, date_time=date_time, high=high, low=low, volumn=volumn)

    def onTickNotifyListener(self):
        pass

    # 處理 buy_requests 和 sell_requests 之間的搓合
    def checkRequestDeal(self, stock_id):
        # 會在 buy() 或 sell() 的內部呼叫，而在呼叫前就會被排序，因此可以直接取用，無須再次排序
        # 又，當在 buy() 當中呼叫時，由於 sell_requests 沒有變化，還是已排序狀態；sell() 當中同理。
        buy_requests = self.deal_requests[stock_id]["buy"]
        sell_requests = self.deal_requests[stock_id]["sell"]
        buy_request = buy_requests[0]
        sell_request = sell_requests[0]
        bought_out = False
        sold_out = False

        while sell_request.price <= buy_request.price:
            deal_result = Request.deal(buy_request=buy_request, sell_request=sell_request)

            if deal_result is not None:
                # time, buyer_info, seller_info, sell_request.price, volumn
                time, buyer_info, seller_info, price, volumn = deal_result

                # onBought(user, stock_id, guid, time, price, volumn)
                buyer, buy_guid = buyer_info
                self.onBought(user=buyer, stock_id=stock_id, guid=buy_guid, time=time, price=price, volumn=volumn)

                # onSold(user, stock_id, guid, time, price, volumn)
                seller, sell_guid = seller_info
                self.onSold(user=seller, stock_id=stock_id, guid=sell_guid, time=time, price=price, volumn=volumn)

                self.logger.info(f"deal_result: {time}, {price}, {volumn}\n"
                                 f"buy_request: {buy_request}\n"
                                 f"sell_request: {sell_request}", extra=self.extra)

                if buy_request.volumn == 0:
                    del buy_requests[0]
                    bought_out = True

                if sell_request.volumn == 0:
                    del sell_requests[0]
                    sold_out = True

                if bought_out:
                    if len(buy_requests) > 0:
                        buy_request = buy_requests[0]
                        bought_out = False
                    else:
                        break

                if sold_out:
                    if len(sell_requests) > 0:
                        sell_request = sell_requests[0]
                        sold_out = False
                    else:
                        break

        self.logger.debug("===== START - 未成交請求 =============================================", extra=self.extra)
        # 下次 buy() 或 sell() 被呼叫時便會再各自排序，且交易後的請求也是維持原排序，無須再次排序
        self.deal_requests[stock_id]["buy"] = buy_requests
        self.deal_requests[stock_id]["sell"] = sell_requests

        for buy_request in self.deal_requests[stock_id]["buy"]:
            self.logger.debug(buy_request, extra=self.extra)

        for sell_request in self.deal_requests[stock_id]["sell"]:
            self.logger.debug(sell_request, extra=self.extra)

        self.logger.debug("===== END - 未成交請求 =============================================", extra=self.extra)

    def checkOhlcDeal(self, stock_id, date_time: datetime.datetime, high: Decimal, low: Decimal, volumn: int):
        buy_requests = self.deal_requests[stock_id]["buy"]
        sell_requests = self.deal_requests[stock_id]["sell"]

        if len(buy_requests) == 0 and len(sell_requests) == 0:
            self.logger.debug("No buy_requests or sell_requests.", extra=self.extra)
            return

        price = (high + low) / 2
        self.logger.debug(f"high: {high}, price: {price}, low: {low}", extra=self.extra)

        requests = Request.merge(price=price, buy_requests=buy_requests, sell_requests=sell_requests)

        self.logger.debug("===== Before process =====", extra=self.extra)

        for request in requests:
            self.logger.debug(request, extra=self.extra)

        self.logger.debug("==========================", extra=self.extra)

        r = 0
        request = requests[r]
        keep_buy = True
        keep_sell = True

        while keep_buy or keep_sell:
            # 快速檢查當前請求是否需要處理
            invalid_request = not keep_buy and request.buy_sell == BuySell.Buy
            invalid_request = invalid_request or (not keep_sell and request.buy_sell == BuySell.Sell)

            while invalid_request:
                r += 1

                # 還有剩餘請求
                if r < len(requests):
                    # 指向下一個請求
                    request = requests[r]

                    invalid_request = not keep_buy and request.buy_sell == BuySell.Buy
                    invalid_request = invalid_request or (not keep_sell and request.buy_sell == BuySell.Sell)

                # 已無剩餘請求
                else:
                    keep_buy = False
                    keep_sell = False
                    invalid_request = False

            if (not keep_buy) and (not keep_sell):
                self.logger.debug(f"keep_buy: {keep_buy}, keep_sell: {keep_sell}", extra=self.extra)
                break

            # 需要處理的請求
            # volumn, (buy_sell, user, stock_id, time, deal_price, deal_volumn, guid)
            volumn, (bs, user, _, time, deal_price, deal_volumn, guid) = request.dealOhlc(high=high,
                                                                                          low=low,
                                                                                          volumn=volumn)

            # 有交易
            if deal_volumn > 0:
                self.logger.info(f"{bs}, user: {user}, price: {deal_price}, volumn: {deal_volumn}, "
                                 f"guid: {guid}, time: {date_time}", extra=self.extra)

                if bs == BuySell.Buy:
                    self.onBought(user=user, stock_id=stock_id, guid=guid,
                                  time=time, price=deal_price, volumn=deal_volumn)
                else:
                    self.onSold(user=user, stock_id=stock_id, guid=guid,
                                time=time, price=deal_price, volumn=deal_volumn)

                # Ohlc 已無剩餘數量可交易
                if volumn == 0:

                    # 當前請求完成交易
                    if request.volumn == 0:
                        self.logger.info(f"當前請求完成交易，但 Ohlc 已無剩餘數量可交易, time: {date_time}", extra=self.extra)
                        del requests[r]
                    else:
                        # Ohlc 已無剩餘數量可交易
                        self.logger.info(f"當前請求未完成交易, 因 Ohlc 已無剩餘數量可交易，time: {date_time}",
                                         extra=self.extra)

                    break

            # 無交易
            else:
                r += 1

                # 當前購買價已低於 Ohlc 的最低價，後面的購買請求都可以忽略了
                if (request.buy_sell == BuySell.Buy) and keep_buy:
                    keep_buy = False
                    self.logger.info(f"Not keep buying, time: {date_time}", extra=self.extra)

                # 當前售出價已高於 Ohlc 的最低高價，後面的售出請求都可以忽略了
                elif (request.buy_sell == BuySell.Sell) and keep_sell:
                    keep_sell = False
                    self.logger.info(f"Not keep selling, time: {date_time}", extra=self.extra)

            # 檢查是否還有剩餘請求
            if r < len(requests):

                # 指向下一個請求
                request = requests[r]

            # 已無剩餘請求
            else:
                break

        self.logger.debug("===== After process =====", extra=self.extra)
        buy_requests = []
        sell_requests = []

        for request in requests:
            self.logger.debug(request, extra=self.extra)

            if request.buy_sell == BuySell.Buy:
                buy_requests.append(request)
            elif request.buy_sell == BuySell.Sell:
                sell_requests.append(request)

        self.deal_requests[stock_id]["buy"] = sorted(buy_requests)
        self.deal_requests[stock_id]["sell"] = sorted(sell_requests)

        self.logger.debug("==========================", extra=self.extra)


if __name__ == "__main__":
    def onBoughtListener(user, stock_id, guid, time, price, volumn):
        print(f"onBoughtListener | user: {user}, stock_id: {stock_id}, guid: {guid}, time: {time}, price: {price}, "
              f"volumn: {volumn}")


    def onSoldListener(user, stock_id, guid, time, price, volumn):
        print(f"onSoldListener | user: {user}, stock_id: {stock_id}, guid: {guid}, time: {time}, price: {price}, "
              f"volumn: {volumn}")


    order = Order()
    stock_id = "9527"
    order.subscribe(stock_id)

    order.onBought += onBoughtListener
    order.onSold += onSoldListener

    requests = [Request(0, "0", "9527", datetime.datetime(2021, 8, 20, 9, 0, 0), Decimal("11.20"), 1, BuySell.Buy),
                Request(2, "2", "9527", datetime.datetime(2021, 8, 20, 9, 1, 0), Decimal("11.25"), 1, BuySell.Buy),
                Request(5, "5", "9527", datetime.datetime(2021, 8, 20, 9, 1, 4), Decimal("11.10"), 1, BuySell.Buy),
                Request(7, "7", "9527", datetime.datetime(2021, 8, 20, 9, 2, 0), Decimal("11.05"), 1, BuySell.Buy),
                Request(8, "8", "9527", datetime.datetime(2021, 8, 20, 9, 2, 0), Decimal("11.30"), 1, BuySell.Buy),
                Request(1, "1", "9527", datetime.datetime(2021, 8, 20, 9, 1, 1), Decimal("11.20"), 1, BuySell.Sell),
                Request(3, "3", "9527", datetime.datetime(2021, 8, 20, 9, 0, 0), Decimal("11.15"), 1, BuySell.Sell),
                Request(4, "4", "9527", datetime.datetime(2021, 8, 20, 9, 0, 0), Decimal("11.30"), 3, BuySell.Sell),
                Request(6, "6", "9527", datetime.datetime(2021, 8, 20, 9, 2, 1), Decimal("11.20"), 1, BuySell.Sell),
                Request(9, "9", "9527", datetime.datetime(2021, 8, 20, 9, 1, 5), Decimal("11.15"), 1, BuySell.Sell)]

    requests = Request.sorted(requests)

    current_time = datetime.datetime(2021, 8, 20, 9, 0, 0)
    end_time = datetime.datetime(2021, 8, 20, 9, 5, 0)
    step = datetime.timedelta(seconds=1)
    request_sent = False

    while current_time < end_time:
        if current_time == datetime.datetime(2021, 8, 20, 9, 1, 0):
            ohlc_data = "2021/08/20 09:00, 11.10, 11.10, 11.05, 11.05, 1"
        elif current_time == datetime.datetime(2021, 8, 20, 9, 2, 0):
            ohlc_data = "2021/08/20 09:01, 11.10, 11.15, 11.10, 11.10, 1"
        elif current_time == datetime.datetime(2021, 8, 20, 9, 3, 0):
            ohlc_data = "2021/08/20 09:02, 11.15, 11.20, 11.10, 11.15, 1"
        else:
            ohlc_data = ""

        if ohlc_data != "":
            order.onOhlcNotifyListener(stock_id=stock_id, ohlc_data=ohlc_data)

        for request in requests:
            user, stock_id, guid, time, price, volumn, bs = request.unboxing()

            if time == current_time:
                request_sent = True

                if bs == BuySell.Buy:
                    order.buy(user, stock_id, guid, time, price, volumn)
                else:
                    order.sell(user, stock_id, guid, time, price, volumn)

        if request_sent:
            request_sent = False
            requests = [request for request in requests if request.time != current_time]

        current_time += step
