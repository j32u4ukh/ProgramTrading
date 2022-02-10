import datetime
from decimal import Decimal, ROUND_UP, ROUND_DOWN, ROUND_HALF_UP

import numpy as np

from data import StockCategory
from data.container.box import Box, BoxExplorer
from enums import OrderMode, OhlcType, StrategyMode, PerformanceStage
from strategy import Strategy
from strategy.opportunity import Opportunity
from utils import getStopValue as utilStopValue
from utils import getValidPrice, getLastValidPrice, getNextValidPrice, unitPrice


# 箱型策略(日 K 版)
class DayBoxStrategy(Strategy):
    # 券商伺服器應會有實際買賣後的結果，買和賣的事件也會有通知，可以兩邊都有一份，也可以系統保有實際的庫存，策略有需要時向系統詢問
    def __init__(self, stock_id: str, order_mode: OrderMode = OrderMode.Long, volumn: int = 1,
                 allowable_percent: Decimal = Decimal("0.1"), n_order_lim=1,
                 short_term: Decimal = 100,
                 logger_dir="strategy", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                 n_ohlc=5, days=1, threshold=2.0):

        super().__init__(stock_id=stock_id, ohlc_type=OhlcType.Day, minutes=0, hours=0, days=days,
                         order_mode=order_mode, volumn=volumn,
                         logger_dir=logger_dir, logger_name=logger_name,
                         allowable_percent=allowable_percent, n_order_lim=n_order_lim)
        # 突破價格
        self.upper_boundary_price = None

        # 跌破價格
        self.lower_boundary_price = None

        # 以 250 天作為一年的 K 棒個數參考值(每年實際上會有所不同)
        self.year_ohlc_number = Decimal("250")

        # 短期的定義(往回多少個 K 棒)
        self.short_term = short_term

        self.threshold = threshold

        # 管理箱型
        self.box_explorer = BoxExplorer(stock_id=stock_id,
                                        n_ohlc=n_ohlc,
                                        threshold=threshold,
                                        oc=self.oc,
                                        logger_dir=self.logger_dir,
                                        logger_name=self.logger_name)

        # 箱型形成事件
        self.box_explorer.onBoxFormed += self.onBoxFormedListener

        self.box = None

    @staticmethod
    def getBoxPriceLimit(price: Decimal) -> Decimal:
        pass

    # 設置 Logger 等級
    def setLoggerLevel(self, level):
        self.logger.setLevel(level)
        self.box_explorer.setLoggerLevel(level)
        self.order_list.setLoggerLevel(level)

    # Tick 數據監聽器
    def onTickNotifyListener(self, deal_time, deal_price, deal_volumn):
        pass

    # Ohlc 數據監聽器
    def onOhlcNotifyListener(self, date_time, open_value: Decimal, high_value: Decimal, low_value: Decimal,
                             close_value: Decimal, volumn):
        """
        DayBoxStrategy 的 Ohlc 產生的監聽器，輸入 1 日 K，再根據事前設定的時間區隔，組成新的 Ohlc。
        stock_data 依序為: 年/月/日, 開盤價, 最高價, 最低價, 收盤價, 成交量

        :param date_time: 年/月/日 -> datetime.datetime
        :param open_value: 開盤價
        :param high_value: 最高價
        :param low_value: 最低價
        :param close_value: 收盤價
        :param volumn: 成交量
        :return:
        """
        # super 本應置於函式最上面，但上方函式是在處理是否送出購買請求，因此其優先順位為最優先
        super().onOhlcNotifyListener(date_time, open_value, high_value, low_value, close_value, volumn)

        # 透過 OhlcContainer
        # Ohlc 物件足夠多會觸發 onOhlcFormedListener -> Ohlc 物件形成箱型後會觸發 onBoxFormedListener
        self.oc.addOhlc(date_time=date_time, volumn=volumn,
                        open_value=open_value, high_value=high_value, low_value=low_value, close_value=close_value)

        # 更新歷史最高最低價，以及認定箱型的價格區建
        # self.box_explorer.update() 只在箱型未形成時尋找與更新，因此無法取代這一行對 box_explorer 數據更新的功能
        self.updateExplorerData(high=high_value, low=low_value, close=close_value, vol=volumn)

        # 更新 StopValue
        is_modified = self.checkStopValue(price=close_value, date_time=date_time)

        if is_modified:
            self.logger.info("Called checkStopValue", extra=self.extra)

        # 若箱型出現了，則再接著讀取當前 成交價/賣價 ，判斷是否發生箱型突破
        if self.box is not None:
            # 同時考慮 是否突破 以及 獲利等級是否為正
            if high_value >= self.upper_boundary_price:
                # 紀錄箱型狀態的改變
                self.box.setStatus(status=Box.Status.Breakthrough, status_time=date_time)
                info = "箱型({})突破, time: {}, high_value: {:.2f}, boundary_price: {:.2f}".format(
                    self.box.getGuid(), date_time, high_value, self.upper_boundary_price)
                self.logger.info(f"({self.stock_id}) {info}", extra=self.extra)

                # 檢查是否符合限制，若符合，則以箱型上緣的價格掛價進場
                self.buyIfMeetTheLimitation(guid=self.box.getGuid(),
                                            time=date_time,
                                            price=getValidPrice(self.box.getHighest(), is_etf=self.is_etf),
                                            volumn=self.volumn)

                # 箱型突破後，再次重新尋找新的箱型
                self.box = None

            # 最高價跌破箱型底部，重新尋找箱型，避免在相對高點等不到突破
            if high_value <= self.lower_boundary_price:
                # 紀錄箱型狀態的改變
                self.box.setStatus(status=Box.Status.FallBelow, status_time=date_time)
                self.logger.info("({}) 最高價 ${:.2f} 跌破箱型底部價格 ${:.2f}".format(
                    self.stock_id, high_value, self.lower_boundary_price), extra=self.extra)

                # 箱型跌破後，再次重新尋找新的箱型
                self.box = None

    # 指定時間長度之 Ohlc 成形後放入 BoxContainer
    def onOhlcFormedListener(self, date_time, open_value: Decimal, high_value: Decimal, low_value: Decimal,
                             close_value: Decimal, volumn):
        # 若箱型尚未成形，則持續"搜尋 & 評估"
        if self.box is None:
            self.box_explorer.update()

    # 箱型成形後，等待與觀察箱型突破
    def onBoxFormedListener(self, box: Box):
        self.logger.info(f"({self.stock_id}) {self.oc.getLastValue(kind='stop')}", extra=self.extra)

        # 目前沒有箱型，則更新箱型(避免前一個相形還未突破，下一個相形就形成，進而造成價格錯置)
        if self.box is None:
            self.box = box

            # 箱型突破(價格比箱型上緣高出一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
            self.upper_boundary_price = getNextValidPrice(self.box.getHighest(), is_etf=self.is_etf)

            # 箱型跌破(價格比箱型下緣再低一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
            self.lower_boundary_price = getLastValidPrice(self.box.getLowest(), is_etf=self.is_etf)

            self.box.setBoundaryPrice(upper=self.upper_boundary_price, lower=self.lower_boundary_price)

            self.logger.info("({}) 突破價格: {:.2f}, 跌破價格: {:.2f}\n{}".format(
                self.stock_id, self.upper_boundary_price, self.lower_boundary_price, self.box), extra=self.extra)

            # 根據買入價往下"可容許損失值"，或箱型下緣之金額，checkStopValue 會處理
            # 觸發價: 箱型上緣高出一個價格單位；買入價: 型上緣價格
            is_modified = self.checkStopValue(price=getValidPrice(self.box.getHighest(), is_etf=self.is_etf),
                                              date_time=self.box.getStopTime())

            if is_modified:
                self.logger.info("Called checkStopValue", extra=self.extra)

    def onSoldListener(self, guid: str, time: datetime.datetime, price: Decimal, volumn: int):
        super().onSoldListener(guid=guid, time=time, price=price, volumn=volumn)

        trade_record = self.history.getTradeRecord(guid=guid)
        box = None

        if trade_record is not None:
            box = self.box_explorer.getBoxByGuid(guid=guid)

            if box is not None:
                self.logger.info(f"\n{trade_record.toString(guid=guid)}", extra=self.extra)

                # updateIncome(income, return_rate, annual_return_rate, income_time)
                box.updateIncome(income=trade_record.income,
                                 return_rate=trade_record.return_rate,
                                 annual_return_rate=trade_record.annual_return_rate,
                                 income_time=trade_record.sell_time)

        if trade_record is None or box is None:
            self.logger.error(f"require guid: {guid}", extra=self.extra)
            self.logger.error(f"stored guids: {[b.guid for b in self.box_explorer.iterBoxes()]}", extra=self.extra)

    # region 生命週期:
    # 訓練模式的事前設定
    def startTraining(self):
        super().startTraining()

        # 將調整之超參數: n_ohlc, price_lim, threshold
        self.logger.info(f"({self.stock_id}) 將調整之超參數 | "
                         f"n_ohlc: {self.box_explorer.n_ohlc}, "
                         f"price_lim: {self.box_explorer.price_lim}", extra=self.extra)

    # 訓練模式結束時固定執行事項，檢視訓練成果
    def endTraining(self, reset_requests=True):
        self.logger.debug(f"({self.stock_id})\n{self.box_explorer}", extra=self.extra)

        # 檢視各分項數值
        # self.box_explorer.checkScore()

        # 調整 BoxExplorer 的超參數
        self.box_explorer.modifySuperParams()
        # self.box_explorer.checkBayesProbability()

        super().endTraining(reset_requests=reset_requests)

        # region 箱型資訊還原
        self.box_explorer.reset()

        # 訓練模式結束後，將 self.box 設為 None 是正確的。
        # 該避免的是隔日事件後，改寫 self.box 的狀態。隔天仍維持 Box 的狀態，以尋求購買時機。
        self.box = None
        # endregion

    # 驗證模式的事前設定
    def startValidation(self):
        super().startValidation()

    # 驗證模式結束時固定執行事項
    def endValidation(self):
        super().endValidation()

        self.logger.info(f"({self.stock_id})\n{self.box_explorer}", extra=self.extra)

        if self.box is not None:
            self.logger.info(f"({self.stock_id}) 等待中購買時機\n{self.box}", extra=self.extra)
        else:
            self.logger.info(f"({self.stock_id}) 暫無購買時機", extra=self.extra)

    # 測試模式的事前設定
    def startTesting(self):
        super().startTesting()

    # 測試模式結束時固定執行事項
    def endTesting(self):
        super().endTesting()

        self.logger.info(f"({self.stock_id})\n{self.box_explorer}", extra=self.extra)

        if self.box is not None:
            self.logger.info(f"({self.stock_id}) 等待中購買時機\n{self.box}", extra=self.extra)
        else:
            self.logger.info(f"({self.stock_id}) 暫無購買時機", extra=self.extra)

    # endregion

    def getOpportunity(self) -> Opportunity:
        self.opportunity = super().getOpportunity()

        if self.box is not None:
            n_transform = self.box.scores["transform_score"]
            self.opportunity.addDescription(f"等待中購買時機\n{self.box}")
            self.opportunity.setTriggerPrice(trigger_price=self.box.getTrigerPrice())
            self.opportunity.setVolumn(volumn=self.volumn)
        else:
            # 子分項分數有 0，將導致 opportunity 分數為 0
            n_transform = 0.0
            self.opportunity.addDescription("\n暫無購買時機")

        # 各項 performance 以 1.0 為分界，共同衡量後超過 1.0 作為是否為適當的購買時機
        n_transform_value = Decimal(str(n_transform))

        if n_transform_value < Decimal("1.0"):
            n_transform_value = Decimal("0.0")
        else:
            n_transform_value = Decimal.log10(n_transform_value + 10)

        # 計算過去 30 天平均交易量
        last_volumns = self.oc.getLastValue(kind="volumn", n_ohlc=30)
        n_volumn = str(np.mean(last_volumns))

        # 計算以 500 為底的 n_volumn 的對數
        trading_volume = Decimal.log10(Decimal(n_volumn) / Decimal("500.0"))

        self.opportunity.addSubPerformance(key="n_transform", value=n_transform_value)
        self.opportunity.addSubPerformance(key="trading_volume", value=trading_volume)

        return self.opportunity

    def isMeetCondition(self, condition: Decimal):
        base_condition = super().isMeetCondition(condition)

        if base_condition:
            # TODO: 或許可移除，在事前就排除，沒有進入回測了
            # 排除國外成分 ETF
            if StockCategory.isForeignEtf(stock_id=self.stock_id):
                self.logger.info(f"({self.stock_id}) isForeignEtf", extra=self.extra)
                self.opportunity.addDescription(description=f"排除國外成分 ETF")
                return False

            short_term_ohlc = self.oc.getOhlc(n_ohlc=self.short_term)
            short_term_rate = (short_term_ohlc.close / short_term_ohlc.open)
            short_term_rate = short_term_rate.quantize(Decimal('0.0000'), ROUND_HALF_UP)

            # 年化報酬要求為 condition，則過了 short_term 天應該要有 condition ** year_index 的報酬率
            year_index = (self.short_term / self.year_ohlc_number).quantize(Decimal('0.0000'), ROUND_DOWN)

            # 根據當年實際的交易日數，原本定義的短期可能超過當年一半的交易日，因此這裡確保數值不大於 0.5
            year_index = min(year_index, Decimal("0.5"))

            # 短期報酬率門檻
            short_term_requirement = (condition ** year_index).quantize(Decimal('0.0000'), ROUND_HALF_UP)
            self.logger.info(f"({self.stock_id}) open: {short_term_ohlc.start_datetime}({short_term_ohlc.open}), "
                             f"close: {short_term_ohlc.stop_datetime}({short_term_ohlc.close})\n"
                             f"year_index: {year_index}, short_term_performance: {short_term_requirement}, "
                             f"short_term_rate: {short_term_rate}", extra=self.extra)

            meet_short_condition = short_term_rate >= short_term_requirement

            if meet_short_condition:
                sign = ">="
            else:
                sign = "<"

            self.opportunity.addPerformance(key=PerformanceStage.Short, value=short_term_rate)
            self.opportunity.addDescription(description=f"short_condition: ({short_term_rate} {sign} "
                                                        f"{short_term_requirement})")

            return meet_short_condition

        return False

    # 取得 Stop Value(停損/停利)
    def getStopValue(self, price: Decimal):
        """
        計算該價位下的 停損/停利 價格

        :param price: 購買價
        :return: 停損/停利 價格
        """
        # 根據'可允許跌幅'計算的 stop_value -> 已確保是有效價格
        util_stop_value = utilStopValue(price, is_etf=self.is_etf, percent=self.allowable_percent)

        if self.box is None:
            # 若目前無箱型，將 util_stop_value 作為 stop_value
            stop_value = util_stop_value
            self.logger.info(f"self.box is None, price: {price}, use util_stop_value: {util_stop_value}",
                             extra=self.extra)
        else:
            # 箱型下緣再低一個價格單位 或 買入價減可容許跌價，兩者取高者作為 stop_value
            stop_value = max(self.box.lower_boundary_price, util_stop_value)
            self.logger.info(f"self.box is not None, price: {price}, use box lower boundary: {stop_value}",
                             extra=self.extra)

        self.logger.debug(f"({self.stock_id}) stop_value: {stop_value}, current price: {price}", extra=self.extra)

        return stop_value

    # 重置判斷 Stop Value(停損/停利) 的機制
    def reviseStopValue(self, revise_date: datetime.date, revise_value: Decimal):
        super().reviseStopValue(revise_date, revise_value)

        self.box = None
        self.order_list.modifyStopValueDelta(delta_value=revise_value)

        date_time = datetime.datetime(revise_date.year, revise_date.month, revise_date.day)
        self.logger.info(f"({self.stock_id}) {revise_date} revise_value: {revise_value}"
                         f"\n{self.order_list.toString(time=date_time)}", extra=self.extra)

    # 若時間事隔一天時所作出的處理
    def onNextDayListener(self, date_time: datetime.date):
        super().onNextDayListener(date_time)

    # 更新隔日購買需求
    def nextDayBuyRequests(self, buy_requests):
        new_buy_requests = super().nextDayBuyRequests(buy_requests=buy_requests)

        return new_buy_requests

    def saveInfo(self):
        performance = [str(p) for p in self.performance[PerformanceStage.Train]]
        params = {"order_mode": self.order_mode.value,
                  "volumn": self.volumn,
                  "allowable_percent": str(self.allowable_percent),
                  "n_order_lim": self.n_order_lim,
                  "short_term": self.short_term,
                  "n_ohlc": self.box_explorer.n_ohlc,
                  "days": self.days,
                  "threshold": self.threshold,
                  "performance": performance}

        return self.__class__.__name__, params

    # 定義 訓練/驗證/測試 模式 與 所需的運算環節
    def getDataUsing(self, strategy_mode: StrategyMode):
        """
        不同策略根據不同的模式，所需流程也有所不同。

        use_tick: getSellRequests, nextDayBuyRequests, onNextDayListener, onNotifyTickListener
        use_request: onBoughtListener, onSoldListener
        use_ohlc: onNotifyOhlcListener
        use_clear: history

        :param strategy_mode: 策略模式
        :return:
        """
        if strategy_mode == StrategyMode.Train:
            use_tick = False
            use_request = True
            use_ohlc = True
            use_clear = True

        elif strategy_mode == StrategyMode.Validation:
            use_tick = False
            use_request = True
            use_ohlc = True
            use_clear = False

        # StrategyPhase.Test
        else:
            use_tick = False
            use_request = True
            use_ohlc = True
            use_clear = False

        return use_tick, use_request, use_ohlc, use_clear

    def setHistoryData(self, history):
        high_value = history["high"]
        low_value = history["low"]

        # 交易量(陣列)
        volumns = history["volumns"]

        # 初始化歷史交易量資訊 history_vol: 歷史平均交易量(由 n_volumn 筆數據平均而得)
        self.box_explorer.history_vol = np.mean(volumns[:-1])
        self.box_explorer.n_volumn = len(volumns[:-1])
        self.box_explorer.setHistoryData(high_value=high_value, low_value=low_value, vol=volumns[-1])

    def updateExplorerData(self, high: Decimal, low: Decimal, close: Decimal, vol):
        # 更新 box_explorer 的歷史數據
        self.box_explorer.setHistoryData(high_value=high, low_value=low, vol=vol)

        """
        根據現在價位調整箱型認定的價格區間，以當前價位每一跳金額的 2 倍為區間，因此有一定的穩定性，不會任意波動
        
        例如: 
        10 < p <= 50.0 的每一跳金額為 0.05，則以 0.1 作為價格區間。25.05 的箱型認定的價格區間為 2.6
        """
        step = unitPrice(close, is_etf=self.is_etf) * Decimal("2")
        price_lim = (close * self.allowable_percent) / step
        price_lim = price_lim.quantize(Decimal('0'), ROUND_UP) * step

        if self.box_explorer.price_lim != price_lim:
            self.logger.debug(f"({self.stock_id}) price: {close}, price_lim: {self.box_explorer.price_lim} -> "
                              f"{price_lim}", extra=self.extra)
            self.box_explorer.price_lim = price_lim


if __name__ == "__main__":
    # TODO: 探討為何賺得這麼少的原因，是沒有避開下跌波段嗎？停利上移幅度不大的原因是什麼呢？
    pass
