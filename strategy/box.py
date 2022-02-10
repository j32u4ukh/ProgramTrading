import datetime
import uuid

import numpy as np

from data.container.box import BoxExplorer
from enums import OrderMode, OhlcType
from strategy import Strategy
from utils import getValidPrice, getLastValidPrice, getNextValidPrice


class BoxStrategy(Strategy):
    # 券商伺服器應會有實際買賣後的結果，買和賣的事件也會有通知，可以兩邊都有一份，也可以系統保有實際的庫存，策略有需要時向系統詢問
    def __init__(self, stock_id: str, ohlc_type: OhlcType = OhlcType.Minute, order_mode: OrderMode = OrderMode.Long,
                 volumn=1, allowable_loss=0.5, n_order_lim=1, funds=30000,
                 price_lim=1.0, n_ohlc=10, minutes=1, hours=0, days=0, threshold=2.0):

        super().__init__(stock_id=stock_id, ohlc_type=ohlc_type, minutes=minutes, hours=hours, days=days,
                         order_mode=order_mode, volumn=volumn, logger_name="BoxStrategy",
                         allowable_loss=allowable_loss, n_order_lim=n_order_lim, funds=funds)
        self.last_close_price = 0

        # 突破價格
        self.upper_boundary_price = None

        # 跌破價格
        self.lower_boundary_price = None

        # 管理箱型
        self.box_explorer = BoxExplorer(stock_id=stock_id, n_ohlc=n_ohlc, price_lim=price_lim, threshold=threshold, oc=self.oc,
                                        logger_dir=self.logger_dir, logger_name=self.logger_name)

        # 箱型形成事件
        self.box_explorer.onBoxFormed += self.onBoxFormedListener

        self.box = None
        self.is_box_formed = False

    # 設置 Logger 等級
    def setLoggerLevel(self, level):
        self.logger.setLevel(level)
        self.box_explorer.setLoggerLevel(level)
        self.order_list.setLoggerLevel(level)

    # Tick 數據監聽器
    def onTickNotifyListener(self, deal_time, deal_price, deal_volumn):
        """

        :param deal_time: 交易時間 datetime
        :param deal_price: 成交價/股。
        :param deal_volumn: 成交量。
        :return:
        """
        # 若箱型出現了，則再接著讀取當前 成交價/賣價 ，判斷是否發生箱型突破
        if self.box is not None:
            if deal_price >= self.upper_boundary_price:
                info = "箱型突破, time: {}, deal_price: {:.2f}, boundary_price: {:.2f}".format(
                    deal_time, deal_price, self.upper_boundary_price)
                self.logger.info(f"({self.stock_id}) {info}")

                """
                當請求時間超過一天而被取消時，若造成策略決定購買的狀態仍維持，應會再次送出購買的請求，
                因此應該無須刻意記住被取消的購買請求。
                """
                # 檢查是否符合限制，若符合，則以箱型上緣的價格掛價進場
                self.buyIfMeetTheLimitation(guid=uuid.uuid4().hex,
                                            time=deal_time,
                                            price=self.box.getHighest(),
                                            volumn=self.volumn)

                # 箱型突破後，再次重新尋找新的箱型
                self.is_box_formed = False

            # 最高價跌破箱型底部，重新尋找箱型，避免在相對高點等不到突破
            elif deal_price <= self.lower_boundary_price:
                self.logger.info("({}) 當前價格 ${:.2f} 跌破箱型底部價格 ${:.2f}".format(
                    self.stock_id, deal_price, self.lower_boundary_price))

                self.is_box_formed = False

        # super 本應置於函式最上面，但上方函式是在處理是否送出購買請求，因此其優先順位為最優先
        super().onTickNotifyListener(deal_time, deal_price, deal_volumn)

        # Ohlc 物件足夠多會觸發 onOhlcFormedListener -> Ohlc 物件形成箱型後會觸發 onBoxFormedListener
        self.oc.addTick(date_time=deal_time, price=deal_price, volumn=deal_volumn)

        # 更新歷史最高最低價
        self.setHistoryPrice(high=deal_price, low=deal_price)

    # 指定時間長度之 Ohlc 成形後放入 BoxContainer
    def onOhlcFormedListener(self, date_time, open_value, high_value, low_value, close_value, volumn):
        # 若箱型尚未成形，則持續"搜尋 & 評估"
        if not self.is_box_formed:
            self.box_explorer.update()

    # Ohlc 數據監聽器
    def onOhlcNotifyListener(self, date_time, open_value, high_value, low_value, close_value, volumn):
        """
        Ohlc 產生的監聽器，輸入 1 分 K，再根據事前設定的時間區隔，組成新的 Ohlc。
        stock_data 依序為: 年/月/日 時:分, 開盤價, 最高價, 最低價, 收盤價, 成交量

        :param date_time: 年/月/日 時:分 -> datetime.datetime
        :param open_value: 開盤價
        :param high_value: 最高價
        :param low_value: 最低價
        :param close_value: 收盤價
        :param volumn: 成交量
        :return:
        """
        pass

    # 箱型成形後，等待與觀察箱型突破
    def onBoxFormedListener(self, box):
        self.box = box
        self.logger.info(f"({box.stock_id})\n{self.box_explorer}")

        # 根據買入價往下"可容許損失值"，或箱型下緣之金額，checkStopValue 會處理
        self.checkStopValue(price=self.box.getHighest())

        # 箱型突破(價格比箱型上緣高出一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
        self.upper_boundary_price = getNextValidPrice(self.box.getHighest(), is_etf=self.is_etf)

        # 箱型跌破(價格比箱型下緣再低一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
        self.lower_boundary_price = getLastValidPrice(self.box.getLowest(), is_etf=self.is_etf)

        self.logger.info("({}) 突破價格: {:.2f}, 跌破價格: {:.2f}".format(
            self.stock_id, self.upper_boundary_price, self.lower_boundary_price))

    # region 生命週期:
    # 訓練模式的事前設定
    def startTraining(self):
        super().startTraining()

        # 將調整之超參數: n_ohlc, price_lim, threshold
        self.logger.info(f"({self.stock_id}) 將調整之超參數 | n_ohlc: {self.box_explorer.n_ohlc}, "
                         f"price_lim: {self.box_explorer.price_lim}, threshold: {self.box_explorer.threshold}")

    # 訓練模式結束時固定執行事項，檢視訓練成果
    def endTraining(self, reset_requests=True):
        super().endTraining(reset_requests=reset_requests)

        # 調整之超參數: n_ohlc, price_lim
        self.logger.debug(f"({self.stock_id}) "
                          f"history_high: {self.box_explorer.history_high}, history_low: {self.box_explorer.history_low}")

        # self.box_explorer.checkBayesProbability()

        # 調整之超參數: n_ohlc
        if len(self.box_explorer.n_ohlcs) > 0:
            # 原始最低要求個數
            n_ohlc = self.box_explorer.n_ohlc

            # Ohlc 數據個數紀錄中位數
            ohlc_median = np.median(self.box_explorer.n_ohlcs)

            # 更新 Ohlc 數據最低要求個數
            self.box_explorer.n_ohlc = min(3, int(ohlc_median))
            self.logger.info(f"({self.stock_id}) Modify n_ohlc: {n_ohlc} -> {self.box_explorer.n_ohlc}")

        # 調整之超參數: price_lim
        if len(self.box_explorer.spreads) > 0:
            # 原始價格波動限制
            price_lim = self.box_explorer.price_lim

            # 價差數據紀錄中位數
            spread_median = np.median(self.box_explorer.spreads)

            # 更新價格波動限制
            self.box_explorer.price_lim = spread_median
            self.logger.info(f"({self.stock_id}) Modify price_lim: {price_lim} -> {self.box_explorer.price_lim}")

        # 調整之超參數: threshold
        if len(self.box_explorer.scores) > 0:
            scores = np.array(self.box_explorer.scores)

            # 原始門檻值
            threshold = self.box_explorer.threshold

            # 更新門檻值
            self.box_explorer.threshold = scores.mean() - scores.std()

            self.logger.info(f"({self.stock_id}) Modify threshold: {threshold} -> {self.box_explorer.threshold}")

        # 數據還原
        if reset_requests:
            self.oc.reset()

        self.box_explorer.reset()

    # 測試模式的事前設定
    def startTesting(self):
        super().startTesting()

    # 測試模式結束時固定執行事項
    def endTesting(self):
        super().endTesting()
    # endregion

    # 取得 Stop Value(停損/停利)
    def getStopValue(self, price):
        """
        計算該價位下的 停損/停利 價格

        :param price: 購買價
        :return: 停損/停利 價格
        """
        stop_value = max(self.box_explorer.getLowest(), price - self.allowable_loss)
        stop_value = getValidPrice(stop_value, is_etf=self.is_etf, func=round)
        self.logger.info(f"({self.stock_id}) stop_value: {stop_value}")

        return stop_value

    # 若時間事隔一天時所作出的處理
    def onNextDayListener(self, date_time: datetime.date):
        super().onNextDayListener(date_time)

        # 前一天的購買請求被取消後，相關狀態值恢復成原本的狀態，尋找下一次購買時機點
        # self.is_box_formed = False

    # 更新隔日購買需求
    def nextDayBuyRequests(self, buy_requests):
        """
        由 Ohlc 數據都還保留於 OhlcContainer 當中，隔一天仍可從數據中尋找箱型(但和之前的箱型會不盡相同)

        :param buy_requests: 前一天的購買請求
        :return:
        """
        new_buy_requests = []

        for buy_request in buy_requests:
            buy_time, buy_price, buy_volumn = buy_request

            # 移除 購買請求價格 與 當前價格 落差過大的請求 -> 價格落差在 2 次漲/跌停以內的才保留(漲/跌停: 10%)
            if self.last_close_price <= 1.21 * buy_price:
                new_buy_requests.append([buy_time, buy_price, buy_volumn])

        return new_buy_requests

    # 定義 訓練/測試模式 與 所需的運算環節
    def isTraining_(self, is_training):
        """
        訓練模式下，啟用不同數據，可在不同的函式中嵌入歷史數據的紀錄，如下方所記。

        use_tick: getSellRequests, nextDayBuyRequests, onNextDayListener, onNotifyTickListener
        use_request: onBoughtListener, onSoldListener
        use_ohlc: onNotifyOhlcListener
        use_clear: history

        :param is_training: 是否為訓練模式
        :return:
        """
        return super().getDataUsing(is_training=is_training,
                                    use_tick=True,
                                    use_request=True,
                                    use_ohlc=False,
                                    use_clear=True)

    def setHistoryData(self, history):
        low_value = history["low"]
        self.setHistoryPrice(high=history["high"], low=low_value)
        self.last_close_price = low_value

    def setHistoryPrice(self, high, low):
        self.box_explorer.setHistoryData(high_value=high, low_value=low)
