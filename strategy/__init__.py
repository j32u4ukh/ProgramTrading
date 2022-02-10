import datetime
import math
import os
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import utils
from data import StockCategory
from data.container import OhlcContainer
from data.the_world import TheWorld
from enums import OrderMode, OhlcType, ReportType, StrategyMode, PerformanceStage
from history import History
from order import OrderList, Order
from strategy.opportunity import Opportunity
from submodule.Xu3.utils import getLogger
from submodule.events import Event
from utils import globals_variable as gv
from utils.order_request import saveRequests, loadRequests


# TODO: 不要沒事一直印價格等資訊，發生重要事件時，再印出價格，甚至可以往回印一段時間
class Strategy(metaclass=ABCMeta):
    def __init__(self, stock_id: str = "0056", ohlc_type: OhlcType = OhlcType.Tick, minutes=1, hours=0, days=0,
                 order_mode: OrderMode = OrderMode.Long,
                 logger_dir="strategy", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                 allowable_loss: Decimal = Decimal("2.0"), allowable_percent: Decimal = Decimal("0.1"),
                 volumn: int = 1, n_order_lim: int = 1):
        """

        :param stock_id: 投資標的代碼
        :param ohlc_type: 告訴交易系統或回測系統，自己需要什麼類型的數據，Ohlc 數據 or Tick 數據
        :param minutes:
        :param hours:
        :param days:

        (minutes, hours, days) 共同構成此策略最小單位的數據，例如傳入 1 分 K 的數據，而時間設置為 (5, 0, 0)。
        則會先將 1 分 K 的數據累積到 5 分 K(由策略內的 OhlcContainer 自動進行)，再提供給策略做判斷。

        :param order_mode: 在策略階段就決定做多還是做空，進而決定停損價位
        :param logger_dir: logger 儲存資料夾
        :param logger_name: logger 名稱
        :param allowable_loss: 最大可容許跌價
        :param allowable_percent: 最大可容許跌幅(0.1 表示可容許跌價 10%)
        :param volumn: 每次交易購買的量(單位:張)，通常每季或每年才調整一次，調整頻率不應過高
        :param n_order_lim: 庫存數量上限
        """
        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

        self.stock_id = stock_id
        self.ohlc_type = ohlc_type
        self.minutes = minutes
        self.hours = hours
        self.days = days

        self.order_mode = order_mode
        self.volumn = volumn

        # 全部的數據, 由 OhlcContainer 協助轉換成 Ohlc
        self.oc = OhlcContainer(minutes=self.minutes, hours=self.hours, days=self.days)

        # Ohlc 形成事件
        self.oc.onOhlcFormed += self.onOhlcFormedListener

        gv.initialize()
        self.discount = gv.e_capital_discount

        # 判斷 stock_id 是否屬於 ETF
        self.is_etf = StockCategory.isEtf(stock_id=self.stock_id)

        # 判斷 stock_id 是否屬於國外成分 ETF
        self.is_foreign_etf = StockCategory.isForeignEtf(stock_id=self.stock_id)

        self.ALLOWABLE_LOSS = allowable_loss
        self.allowable_loss = allowable_loss

        self.allowable_percent = allowable_percent
        self.n_order_lim = n_order_lim

        self.guid = None
        self.peak_price = None
        self.valley_price = None

        # region 不在最一開始就設置資金，而是購買後若不足再增資即可
        # 實際投入資金(只因增資而增加)，會因為交易獲利而實際上不需投入那麼多資金
        self.input_funds = Decimal("0")

        # 目前有的資金(可能因增資或交易而增減)
        self.funds = Decimal("0")
        # endregion

        # 庫存
        self.order_list = OrderList(stock_id=self.stock_id,
                                    logger_dir=self.logger_dir,
                                    logger_name=self.logger_name)

        # TODO: 檢查這行是否還有必要，透過 pickle 來 儲存/載入 OrderList
        self.order_list.load()

        # test 模式中，載入現實世界的庫存，於相對應的時間更新
        self.the_world = None
        self.revise = None

        self.strategy_mode = StrategyMode.Train

        # TODO: 是否仿照 OrderList 弄一個現實世界用的 buy_request 記錄檔?
        self.buy_requests_path = os.path.join("data", "buy_requests", f"{self.logger.name}_{self.stock_id}.json")

        # 為交易紀錄寫一個類別，方便之後反查
        self.history = History(stock_id=stock_id, logger_dir=self.logger_dir, logger_name=self.logger_name)

        # 紀錄'訓練與測試'階段的表現
        self.performance = defaultdict(list)

        # 根據各項表現來形成購買時機
        self.opportunity = None

        # region Event
        self.event = Event()

        # onBuy(stock_id, time, price, volumn)
        self.onBuy = self.event.onBuy

        # onSell(stock_id, time, stop_value, volumn)
        self.onSell = self.event.onSell

        # onAchieveOrderNumberLimit(stock_id)
        self.onAchieveOrderNumberLimit = self.event.onAchieveOrderNumberLimit

        # onNewSellRequests(stock_id) 通知 回測系統/券商系統 該更新購買需求了
        self.onNewSellRequests = self.event.onNewSellRequests
        # endregion

    """ staticmethod """

    """ abstractmethod """

    # 設置 Logger 等級
    @abstractmethod
    def setLoggerLevel(self, level):
        pass

    @abstractmethod
    def setHistoryData(self, history):
        pass

    # region 價格變動 Listener
    # Tick 數據監聽器
    @abstractmethod
    def onTickNotifyListener(self, deal_time, deal_price: Decimal, deal_volumn: int):
        # 更新 peak_price 和 valley_price
        if self.peak_price is not None:
            self.peak_price = max(self.peak_price, deal_price)
            self.valley_price = min(self.valley_price, deal_price)

            self.logger.debug(f"peak: {self.peak_price}, valley: {self.valley_price}", extra=self.extra)

    # 利用 OhlcContainer 形成 Ohlc 數據
    @abstractmethod
    def onOhlcFormedListener(self, date_time, open_value, high_value, low_value, close_value, volumn):
        pass

    # Ohlc 數據監聽器
    @abstractmethod
    def onOhlcNotifyListener(self, date_time, open_value: Decimal, high_value: Decimal, low_value: Decimal,
                             close_value: Decimal, volumn):
        # 更新 peak_price 和 valley_price
        if self.peak_price is not None:
            if high_value > self.peak_price:
                self.logger.info(f"({self.stock_id}) {date_time} peak: {self.peak_price} -> {high_value}",
                                 extra=self.extra)
                self.peak_price = high_value.quantize(Decimal('.00'), ROUND_HALF_UP)

            if low_value < self.valley_price:
                self.logger.info(f"({self.stock_id}) {date_time} valley: {self.valley_price} -> {low_value}",
                                 extra=self.extra)
                self.valley_price = low_value.quantize(Decimal('.00'), ROUND_HALF_UP)

    # endregion

    # 訓練模式的事前設定
    @abstractmethod
    def startTraining(self):
        """
        TODO: 利用歷史數據調整超參數，並出清庫存來衡量表現。使用'請求處理系統'來模擬交易。
        TODO: init self.oc

        :return:
        """
        self.strategy_mode = StrategyMode.Train

        # 資金還原
        self.input_funds = Decimal("0")
        self.funds = Decimal("0")

        # 清空歷史紀錄
        self.history.reset()

    # 訓練模式結束時固定執行事項，檢視訓練成果
    @abstractmethod
    def endTraining(self, reset_requests=True):
        """ checkTrainingResult
        若在過程中使用到變數需要還原，可以在此步驟中進行，因為這裡會在 train 確實執行完後才被執行到。
        :return:
        """
        self.logger.info(f"當前資金: {self.funds}", extra=self.extra)

        # 確保有跌價紀錄 -> History 會使用到，即使不需要它來調整超參數也應保留
        self.recordFallingPrice()

        # 衡量資產
        self.measureAssets(strategy_mode=StrategyMode.Train)

        if reset_requests:
            # 將購買請求紀錄寫出
            saveRequests(requests=[], path=self.buy_requests_path)

            del self.order_list
            self.order_list = OrderList(stock_id=str(self.stock_id),
                                        logger_dir=self.logger_dir, logger_name=self.logger_name)

            # 在無數據的情況下儲存，相當於清空紀錄
            self.order_list.save()

    # 驗證模式的事前設定
    @abstractmethod
    def startValidation(self):
        """
        TODO: 不調整超參數，使用資產價值試算來衡量表現，保留當下的庫存狀態。使用'請求處理系統'來模擬交易。
         TODO: init self.oc
        :return:
        """
        self.strategy_mode = StrategyMode.Validation

        # 資金還原
        self.input_funds = Decimal("0")
        self.funds = Decimal("0")

        # 清空歷史紀錄
        self.history.reset()

    # 驗證模式結束時固定執行事項
    @abstractmethod
    def endValidation(self):
        self.logger.info(f"({self.stock_id}) 當前資金: {self.funds}", extra=self.extra)

        # 確保有跌價紀錄
        self.recordFallingPrice()

        # 衡量資產
        self.measureAssets(strategy_mode=StrategyMode.Validation)

        # 儲存 OrderList
        self.order_list.save()

    # 測試模式的事前設定
    @abstractmethod
    def startTesting(self):
        """
        TODO: 是否成功買到，由現實世界決定，不使用'請求處理系統'來模擬交易。
        TODO: 根據前面兩階段的調整與測試，以及數據所形成的購買時機，更新庫存的 stop_value。
        TODO: init self.oc
        :return:
        """
        self.strategy_mode = StrategyMode.Test

        # 資金還原
        self.input_funds = Decimal("0")
        self.funds = Decimal("0")

        # 清空歷史紀錄
        self.history.reset()

        # TheWorld: 用於將實際交易情形，鑲嵌至回測當中(是否購買到、多少錢買到都是由 TheWorld 告訴策略)
        self.the_world = TheWorld(stock_id=self.stock_id, order_list=self.order_list,
                                  logger_dir=self.logger_dir, logger_name=self.logger_name)
        self.the_world.onTheWorld += self.onTheWorldListener
        self.the_world.onRevise += self.onReviseListener

    # 測試模式結束時固定執行事項
    @abstractmethod
    def endTesting(self):
        self.logger.info(f"({self.stock_id}) 當前資金: {self.funds}", extra=self.extra)

        # 確保有跌價紀錄
        self.recordFallingPrice()

        # 衡量資產
        self.measureAssets(strategy_mode=StrategyMode.Test)

    @abstractmethod
    def getOpportunity(self) -> Opportunity:
        self.opportunity = Opportunity(stock_id=self.stock_id,
                                       strategy_name=self.__class__.__name__,
                                       performances=self.performance)

        return self.opportunity

    # 取得 Stop Value(停損/停利)
    @abstractmethod
    def getStopValue(self, price: Decimal) -> Decimal:
        pass

    # 重置判斷 Stop Value(停損/停利) 的機制
    @abstractmethod
    def reviseStopValue(self, revise_date: datetime.date, revise_value: Decimal):
        self.revise = None

    # 若時間事隔一天時所作出的處理
    @abstractmethod
    def onNextDayListener(self, date_time: datetime.date):
        if self.strategy_mode == StrategyMode.Test:
            # self.logger.debug(f"({self.stock_id}) {date_time}", extra=self.extra)
            self.the_world.onNextDayListener(date_time=date_time)

        # [常規檢查]
        # 檢查 stop_value(無論何種模式都需要)
        if len(self.oc) > 0:
            # 今天用'昨天'的收盤價來對 stop_value 做調整，因此無法使用到'今天'的數據
            last_close = self.oc.getLastValue(kind="close")
            is_modified = self.checkStopValue(price=last_close)

            # 若 orders 當中有一筆成功被調整，就印出 order_list 狀態資訊
            if is_modified:
                time = datetime.datetime(year=date_time.year, month=date_time.month, day=date_time.day)
                self.logger.info(f"({self.stock_id}) {date_time}\n{self.order_list.toString(time=time)}",
                                 extra=self.extra)

        if self.strategy_mode != StrategyMode.Test:
            # region 售出請求
            # 根據庫存與其停損價，取得售出請求
            sell_requests = self.getSellRequests(date_time=datetime.datetime(year=date_time.year,
                                                                             month=date_time.month,
                                                                             day=date_time.day))

            # 再次送出停損單
            for sell_request in sell_requests:
                guid, time, stop_value, volumn = sell_request

                self.onSell(guid=guid,
                            stock_id=self.stock_id,
                            time=time,
                            stop_value=stop_value,
                            volumn=volumn)
            # endregion

            # region 購買請求
            # # 若已達購買數量上限，原本未成交的購買請求就可以移除了
            # if self.getOrderNumber() == self.getOrderNumberLimit():
            #     self.onAchieveOrderNumberLimit(stock_id=self.stock_id)
            #
            # else:
            # 讀取自己的購買請求紀錄
            buy_requests = self.loadBuyRequest()

            # 更新購買請求紀錄
            buy_requests = self.nextDayBuyRequests(buy_requests=buy_requests)

            # 再次送出購買請求
            for buy_request in buy_requests:
                guid, stock_id, buy_time, buy_price, buy_volumn = buy_request
                self.logger.info(f"({self.stock_id}) Buy again: ({buy_time}, {buy_price}, {buy_volumn})",
                                 extra=self.extra)
                self.buyIfMeetTheLimitation(guid=guid, time=buy_time, price=buy_price, volumn=buy_volumn)
            # endregion

        # StrategyMode.Test
        else:
            # 特殊情況下才會作用，修正股利發放等影響 stop_value 的要素
            if self.revise is not None:
                revise_date, revise_value = self.revise
                self.reviseStopValue(revise_date=revise_date, revise_value=revise_value)

    # 更新購買需求
    @abstractmethod
    def nextDayBuyRequests(self, buy_requests):
        """
        移除 購買請求價格 與 當前價格 落差過大的請求 -> 價格落差在 1 次漲/跌停以內的才保留(漲/跌停: 10%)

        :param buy_requests: 原始購買請求
        :return:
        """
        last_close_price = self.oc.getLastValue(kind="close")
        new_buy_requests = []

        for buy_request in buy_requests:
            guid, stock_id, buy_time, buy_price, buy_volumn = buy_request

            # 計算價格落差比例
            if abs(last_close_price - buy_price) / buy_price <= Decimal("0.1"):
                new_buy_requests.append([guid, stock_id, buy_time, buy_price, buy_volumn])
            else:
                self.logger.info(f"移除請求: ({guid}, {stock_id}, {buy_time}, {buy_price}, {buy_volumn})",
                                 extra=self.extra)

        n_origin = len(buy_requests)
        n_new = len(new_buy_requests)

        if n_origin != n_new:
            self.logger.info(f"({self.stock_id}) n_buy_requests: {n_origin} -> {n_new}", extra=self.extra)

        # 更新為隔日後的請求(避免此處變數早已被清空，或是當天)
        self.updateBuyRequests(buy_requests=new_buy_requests)

        return new_buy_requests

    # 定義 訓練/測試模式 與 所需的運算環節
    @abstractmethod
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
        pass

    # 成功銷售後的處理
    @abstractmethod
    def onSoldListener(self, guid: str, time: datetime.datetime, price: Decimal, volumn: int):
        """

        :param guid:
        :param time:
        :param price:
        :param volumn:
        :return:
        """
        self.soldProcess(guid=guid, time=time, price=price, volumn=volumn, is_clear=False, is_trial=False)

    @abstractmethod
    def saveInfo(self):
        pass

    """ normal method """

    # 更新資金變化
    def onTheWorldListener(self, guid: str, time: datetime.datetime, price: str, volumn: int):
        self.onBought(guid=guid, time=time, price=Decimal(price), volumn=volumn)

    def onReviseListener(self, revise_date: datetime.date, revise_value: Decimal):
        self.revise = (revise_date, revise_value)
        # self.rejudge(rejude_date=rejude_date, price=price)

    # 確保有跌價紀錄
    def recordFallingPrice(self):
        # 若尚無沒有跌價紀錄，且 self.peak_price 也不是 None(有購買紀錄但尚未售出)，則將目前記錄中的跌價直接加到 history 中
        if len(self.history.falling_price) == 0:
            if self.peak_price is not None:
                falling_price = self.peak_price - self.valley_price
            else:
                falling_price = Decimal("0")

            self.history.recordFallingPrice(falling_price)
            self.logger.info(f"({self.stock_id}) falling_price: {falling_price} | "
                             f"peak: {self.peak_price}, valley: {self.valley_price}", extra=self.extra)

        self.logger.info(f"falling_price: {sorted(self.history.falling_price)}", extra=self.extra)

    # 衡量資產
    def measureAssets(self, strategy_mode: StrategyMode):
        last_date = self.oc.getLastValue(kind="stop")

        if strategy_mode == StrategyMode.Train:
            is_trial = False

        elif strategy_mode == StrategyMode.Validation:
            is_trial = True

        # strategy_mode == StrategyMode.Test
        else:
            is_trial = True

        funds_before = self.funds

        trade_records, delta_funds, delta_incomes = self.clear(clear_time=last_date, is_trial=is_trial)

        funds = (funds_before + delta_funds).quantize(Decimal('.00'), ROUND_HALF_UP)

        if delta_funds != 0:
            self.history.recordFunds(funds=funds)

        has_history = self.history is not None
        self.logger.info(f"self.history: {has_history}", extra=self.extra)

        if has_history:
            trade_records = self.history.trade_record

            for key, value in trade_records.items():
                self.logger.info(f"{key}: {value}", extra=self.extra)

        self.logger.info("\n==========\n==========", extra=self.extra)
        self.logger.info(f"({self.stock_id}) 資產總價值: {funds}\n"
                         f"{self.order_list.toString(value=float(delta_funds))}\n"
                         f"{self.history}", extra=self.extra)

        # 歷時多少年
        if strategy_mode == StrategyMode.Test:
            # time, price
            buy_time, _ = self.the_world.getData()
            time_range = datetime.datetime.now() - buy_time

        else:
            time_range = self.history.getTimeRange()

        n_year = Decimal(str(time_range / datetime.timedelta(days=365.25) + 1e-8))
        year_index = Decimal("1.0") / n_year

        performance_stage = PerformanceStage.Train

        if strategy_mode == StrategyMode.Train:
            performance_stage = PerformanceStage.Train
        elif strategy_mode == StrategyMode.Validation:
            performance_stage = PerformanceStage.Validation
        elif strategy_mode == StrategyMode.Test:
            performance_stage = PerformanceStage.Test

        # 實際報酬率(為 0.XX / 1.XX 的形式): 資產總價值 除以 實際投入資金
        if self.input_funds == 0.0:
            self.performance[performance_stage].append(Decimal("0.00"))
        else:
            real_return_rate = funds / self.input_funds

            # 年化報酬率
            try:
                annual_return_rate = Decimal(str(math.pow(real_return_rate, year_index)))
                annual_return_rate = annual_return_rate.quantize(Decimal('.00'), ROUND_HALF_UP)

            except ValueError:
                self.logger.error(f"real_return_rate: {real_return_rate}, year_index: {year_index}", extra=self.extra)
                annual_return_rate = Decimal("0.00")

            self.logger.info(f"({self.stock_id}) funds: {funds}, input_funds: {self.input_funds}"
                             f"\ntime_range: {time_range.days} days, 實際報酬率: {real_return_rate}"
                             f"\n(年)報酬率: {annual_return_rate}", extra=self.extra)
            self.performance[performance_stage].append(annual_return_rate)

    def loadBuyRequest(self):
        if os.path.exists(self.buy_requests_path):
            # 載入購買請求紀錄
            buy_requests = loadRequests(path=self.buy_requests_path)

            if len(buy_requests) > 0:
                self.logger.debug(f"({self.stock_id}) Load buy_requests: {buy_requests}", extra=self.extra)
        else:
            buy_requests = []

        return buy_requests

    def isMeetCondition(self, condition: Decimal):
        """
        TODO: condition 只篩選驗證階段的表現，訓練階段的表現在更之前就被篩選過了
        檢查是否符合條件，有或無，不像 performance 為連續型資料。

        :param condition:
        :return:
        """
        performance = None

        if self.opportunity is None:
            self.opportunity = self.getOpportunity()

        for performance in self.performance[PerformanceStage.Validation]:
            if performance < condition:
                self.opportunity.addDescription(description=f"Validation: ({performance} < {condition})")
                return False

        self.opportunity.addDescription(description=f"Validation: ({performance} >= {condition})")
        return True

    # 檢視 Stop Value 是否需要調整
    def checkStopValue(self, price: Decimal, date_time: datetime.datetime = None):
        if date_time is None:
            date_time = self.oc.getLastValue("stop")

        is_modified = False

        # TODO: 測試模式中，stop_value "不高於" TheWorld 中紀錄的數值
        if self.getOrderNumber() > 0:
            # 計算輸入價格對應的 StopValue
            new_stop_value = self.getStopValue(price)

            # 前一天收盤價
            last_close = self.oc.getLastValue(kind="close")
            self.logger.debug(f"({self.stock_id}) date_time: {date_time}, last_close: {last_close}", extra=self.extra)

            # 停損/停利 調整
            if self.is_foreign_etf and (last_close < new_stop_value):
                # 預期以這個價格售出(較前一天收盤價低一個價格單位)
                sell_price = utils.getLastValidPrice(price=last_close, is_etf=True)

                # 強制(is_force=True)將 stop_value 改為 sell_price
                is_modified = self.order_list.modifyStopValue(sell_price, is_force=True)

                self.logger.info(f"({self.stock_id}) 國外成分 ETF 前一天收盤價({last_close}) < 停損價({new_stop_value}), "
                                 f"委託價: ${sell_price}", extra=self.extra)
            else:
                is_modified = self.order_list.modifyStopValue(new_stop_value)

            # if self.strategy_mode == StrategyMode.Test:
            #     # time, price, revise, stop_value
            #     _, _, world_revise, world_stop_value = self.the_world.getData()
            #
            #     # 只有當前時間 等於或晚於 庫存實際交易時間，才會將 stop_value 校正到不高於 world_stop_value
            #     if (date_time >= world_revise) and (new_stop_value > world_stop_value):
            #         # 強制(is_force=True)將 stop_value 改為 world_stop_value
            #         self.logger.info(f"({self.stock_id}) stop_value 不可高於 world_stop_value: ${world_stop_value}",
            #                          extra=self.extra)
            #         is_modified = self.order_list.modifyStopValue(world_stop_value, is_force=True)

            # 若有調整，再把資訊印出即可
            if is_modified:
                self.logger.info(f"({self.stock_id}) {date_time} new_stop_value: {new_stop_value}"
                                 f"\n{self.order_list.toString(time=date_time)}", extra=self.extra)

        return is_modified

    # 共通的、提出'購買請求'前的 限制檢查，若符合限制則送出'購買請求'
    def buyIfMeetTheLimitation(self, guid: str, time: datetime.datetime, price: Decimal, volumn: int):
        if self.strategy_mode != StrategyMode.Test:
            # '現有庫存數量'是否少於'庫存數量上限'
            if self.getOrderNumber() < self.getOrderNumberLimit():
                buy_cost = Order.getBuyCost(price=price, volumn=volumn, discount=self.discount)

                # 檢查資金是否充足，若不足則增資
                if buy_cost > self.funds:
                    shortage = buy_cost - self.funds
                    self.funds += shortage
                    self.input_funds += shortage

                    self.logger.info(f"({self.stock_id}) 資金不足，增資: {shortage}"
                                     f"\nfunds: {self.funds}, input_funds: {self.input_funds}", extra=self.extra)

                self.onBuy(guid=guid, stock_id=self.stock_id, time=time, price=price, volumn=volumn)
                self.logger.info(f"({self.stock_id}) guid: {guid}\n{self.order_list.toString(time=time)}",
                                 extra=self.extra)
            else:
                self.logger.debug(f"({self.stock_id}) 庫存數量已達設定的上限: {self.getOrderNumberLimit()} | {time}",
                                  extra=self.extra)

    def updateBuyRequests(self, buy_requests, is_multi_stock=False):
        """
        TODO: is_multi_stock 應該可以移除，一支策略只會搭配一個股票，就算都是日線策略也是 N 個日線策略對 N 支股票

        更新購買請求紀錄

        :param buy_requests:
        :param is_multi_stock:
        :return:
        """
        # 若為多支股票混在一起的購買請求
        if is_multi_stock:
            # 透過股票代碼，篩選出當前策略的標的之購買請求
            self_buy_requests = [buy_request for buy_request in buy_requests if buy_request[1] == self.stock_id]
        else:
            self_buy_requests = buy_requests

        # 將購買請求紀錄寫出
        saveRequests(requests=self_buy_requests, path=self.buy_requests_path)

    # 成功購買後的處理
    def onBoughtListener(self, guid: str, time: datetime.datetime, price: Decimal, volumn: int):
        """
        當確實買到股票後的處理。
        TODO: API 中似乎可以同時送出並待成功買入後，立即根據停損價，掛出停損單

        :param guid:
        :param time:
        :param price:
        :param volumn:
        :return:
        """
        self.onBought(guid=guid, time=time, price=price, volumn=volumn)

    def onBought(self, guid: str, time: datetime.datetime, price: Decimal, volumn: int):
        # TODO: 回測中的購買成功 與 現實世界的購買成功 共同的部分，現實世界可能因為股利發放等原因
        self.logger.debug(f"({self.stock_id}) guid: {guid}, "
                          f"time: {time}, price: {price}, volumn: {volumn}", extra=self.extra)

        # 第 1 次進入 onBoughtListener 時，不會記錄跌價
        # 第 2 次進入 onBoughtListener 時，才會根據"被更新的 peak_price 和 valley_price"來計算跌價
        if self.peak_price is not None:
            self.logger.info(f"({self.stock_id}) peak_price: {self.peak_price}, valley_price: {self.valley_price}, "
                             f"FallingPrice: {self.peak_price - self.valley_price}", extra=self.extra)

            # 紀錄跌價: 紀錄第 N 筆買到的價格 → 持續更新'最高價'和'最低價' →
            #  第 N + 1 筆交易發生時，紀錄'最高價'和'最低價'的差距，作為跌價，並重新更新'最高價'和'最低價'
            self.history.recordFallingPrice(self.peak_price - self.valley_price)

        # 進入 onBoughtListener 時，重置 peak_price 和 valley_price
        self.peak_price = price
        self.valley_price = price
        self.logger.debug(f"({self.stock_id}) peak: {self.peak_price}, valley: {self.valley_price}", extra=self.extra)

        # 更新資金
        buy_cost = Order.getBuyCost(price=price, volumn=volumn, discount=self.discount)
        self.updateFunds(-buy_cost)

        # 根據策略，取得 stop_value
        stop_value = self.getStopValue(price)

        order = Order(guid=guid,
                      time=time,
                      price=price,
                      stop_value=stop_value,
                      volumn=volumn,
                      discount=self.discount,
                      is_etf=self.is_etf,
                      order_mode=self.order_mode)

        # 紀錄買到的股票
        self.order_list.add(order=order)
        self.logger.debug(f"({self.stock_id})\n{self.order_list.toString(time=time)}", extra=self.extra)

        # 成功買入後，立即根據停損價，掛出停損單
        self.onSell(guid=guid, stock_id=self.stock_id, time=time, stop_value=stop_value, volumn=volumn)

    def clear(self, clear_time: datetime.datetime, is_trial=True):
        trade_records, delta_funds, delta_incomes = self.soldProcess(time=clear_time,
                                                                     price=None,
                                                                     is_clear=True,
                                                                     is_trial=is_trial)

        return trade_records, delta_funds, delta_incomes

    def soldProcess(self, time: datetime.datetime, price: Decimal = None, guid: str = "", volumn: int = 0,
                    is_clear=False, is_trial=True):
        if is_clear:
            info = "出清"
        else:
            info = "成交"

        if price is None:
            info += f"資訊: time: {time}, volumn: {volumn}, 以 stop_value 出售"
        else:
            info += "資訊: time: {}, price: {:.2f}, volumn: {}".format(time, price, volumn)

        self.logger.info(f"({self.stock_id}) {info}", extra=self.extra)

        # trade_record = [guid, buy_time, buy_price, buy_volumn, sell_time, sell_price, sell_volumn,
        #                 revenue, buy_cost, sell_cost, order.stop_value_moving]
        if is_clear:
            # is_trial: 試算模式，Order 的售出數量實際上不會增加，OrderList 管理的 Order 也不受影響，僅計算清空時會獲得的數值
            # OrderList clear: 不考慮是否為試算模式，皆返回模擬交易後的結果
            trade_records = self.order_list.clear(sell_time=time,
                                                  sell_price=price,
                                                  is_trial=is_trial)
        else:
            # 一般賣出
            # OrderList sell(guid, sell_time, sell_price, sell_volumn, is_trial)
            trade_records = self.order_list.sell(guid=guid,
                                                 sell_time=time,
                                                 sell_price=price,
                                                 sell_volumn=volumn,
                                                 is_trial=False)

        # 由於可能是部分賣出，因此 TradeRecord 為部分的 Order，結構等也應比 Order 更為單純
        self.logger.debug(f"({self.stock_id}) is_clear: {is_clear}, is_trial: {is_trial}", extra=self.extra)

        # region 計算'資金 & 收益'變化量
        # 資金變化量
        delta_funds = Decimal("0")

        # 收益變化量
        delta_incomes = Decimal("0")

        # TODO: 在此生成 TradeRecord，直接將 TradeRecord 加入
        for trade_record in trade_records:
            # trade_record = [guid, buy_time, buy_price, buy_volumn, sell_time, sell_price, sell_volumn,
            #                 revenue, buy_cost, sell_cost, order.stop_value_moving]
            (guid, buy_time, buy_price, buy_volumn,
             sell_time, sell_price, sell_volumn,
             revenue, buy_cost, sell_cost, stop_value_moving) = trade_record
            self.logger.info(f"({self.stock_id})\n{trade_record}", extra=self.extra)

            # 累計資金變化量
            delta_fund = revenue - sell_cost
            delta_funds += delta_fund

            # 累計收益變化量
            delta_income = delta_fund - buy_cost
            delta_incomes += delta_income
        # endregion

        # 並非試算，有實際的資金流動
        if not is_trial:
            self.history.add(*trade_records)

            # 更新資金
            self.updateFunds(delta_funds)

            # 紀錄資金變化
            self.history.recordFunds(funds=self.funds)

            # delta_incomes: 收益變化量
            self.logger.info(f"({self.stock_id}) Income: {delta_incomes} -> "
                             f"{self.history.getIncome()}", extra=self.extra)

        # 檢視當前 OrderList 狀態
        self.logger.info(f"({self.stock_id})\n{self.order_list.toString(time=time)}", extra=self.extra)

        return trade_records, delta_funds, delta_incomes

    # 更新資金存量，必要時進行增資
    def updateFunds(self, delta_fund: Decimal):
        self.logger.info(f"({self.stock_id}) funds: {self.funds} -> {self.funds + delta_fund}", extra=self.extra)
        self.funds += delta_fund

        # TODO: 設立事件，提醒現實世界的我要去執行增資
        # 在意外資金不足時，進行額外增資
        if self.funds < Decimal("0.0"):
            self.logger.info(f"({self.stock_id}) 資金不足(fund: {self.funds})，現實世界需進行增資", extra=self.extra)

    # 取得庫存數量
    def getOrderNumber(self):
        """

        :return: 策略所管理庫存數量
        """
        return self.order_list.getOrderNumber()

    # 取得庫存數量上限
    def getOrderNumberLimit(self):
        return self.n_order_lim

    # 取得新的銷售請求
    def getSellRequests(self, date_time: datetime.datetime):
        return self.order_list.getSellRequests(date_time=date_time)

    def getRequests(self, request_type):
        requests = []
        # self.logger.info(f"({self.stock_id}) request_type: {request_type}", extra=self.extra)

        if request_type == ReportType.BuyRequest:
            buy_requests = self.loadBuyRequest()

            if len(buy_requests) == 0:
                self.logger.info(f"({self.stock_id}) 目前無購買請求", extra=self.extra)
            else:
                for buy_request in buy_requests:
                    guid, stock_id, buy_time, buy_price, buy_volumn = buy_request
                    requests.append([stock_id, buy_price, buy_volumn])

        elif request_type == ReportType.SellRequest:
            sell_requests = self.getSellRequests(date_time=datetime.datetime.today())

            if len(sell_requests) == 0:
                self.logger.info(f"({self.stock_id}) 目前無售出請求", extra=self.extra)
            else:
                for sell_request in sell_requests:
                    guid, time, stop_value, volumn = sell_request

                    # stop_value: 為了提供給 API 作為參數使用 Decimal -> str
                    requests.append([self.stock_id, str(stop_value), volumn])

        return requests

    # region 結束交易後
    # 利用交易歷史物件產生報表
    def reportResult(self, *args):
        if ReportType.BuyRequest in args:
            buy_requests = self.loadBuyRequest()

            if len(buy_requests) == 0:
                self.logger.info(f"({self.stock_id}) 目前無購買請求", extra=self.extra)
            else:
                for buy_request in buy_requests:
                    self.logger.info(f"({self.stock_id}) BuyRequest: {buy_request}", extra=self.extra)

        if ReportType.SellRequest in args:
            sell_requests = self.getSellRequests(date_time=datetime.datetime.today())

            if len(sell_requests) == 0:
                self.logger.info(f"({self.stock_id}) 目前無售出請求", extra=self.extra)
            else:
                for sell_request in sell_requests:
                    self.logger.info(f"({self.stock_id}) SellRequest: {sell_request}", extra=self.extra)

        self.history.reportResult(*args)

    # 呈現視覺化交易結果
    def display(self, *args):
        self.history.display(*args)
    # endregion
