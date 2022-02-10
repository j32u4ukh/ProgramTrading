import copy
import datetime
import logging
import uuid
from collections import defaultdict
from decimal import Decimal
from enum import Enum

import numpy as np

from data.container.ohlc import Ohlc, OhlcContainer
from submodule.Xu3.utils import getLogger
from submodule.events import Event
from utils.math import geometricMean, sigmoid


class Box:
    class Status(Enum):
        # 箱型跌破
        FallBelow = -1

        # 還在箱型內
        In = 0

        # 箱型突破
        Breakthrough = 1

    def __init__(self, stock_id: str, ohlc: Ohlc, scores: dict):
        # 將作為送出的請求的'全域唯一識別碼'(uuid.uuid4() 為物件, uuid.uuid4().hex 才是字串)
        self.guid = uuid.uuid4().hex

        # 股票代碼
        self.stock_id = stock_id

        # 實際數據
        self.ohlc = ohlc

        # 箱型突破(價格比箱型上緣高出一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
        self.upper_boundary_price = None

        # 箱型跌破(價格比箱型下緣再低一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
        self.lower_boundary_price = None

        # 用於紀錄各項數值，以觀察其分布情形(keys: BoxExplorer.score_keys)
        # copy.deepcopy: dict 為傳址，因此若外部對它做修改，Box 內的數值也會被修改到，因此需用 deepcopy
        self.scores = copy.deepcopy(scores)

        # 箱型形成時間(即為箱型中最後一筆 K 棒的結束時間)
        self.form_time = self.ohlc.stop_datetime

        """ 以下將記錄箱型形成後，所產生的相關資訊 """
        # 箱型狀態: 箱型內、突破、跌破
        self.status = Box.Status.In

        # 狀態改變的時間點
        self.status_time = None

        # 收益(可正可負): 將用於協助判斷，上方箱型各項狀態與收益之間的關係
        self.income = None

        # 報酬率
        self.return_rate = None

        # 年化報酬率
        self.annual_return_rate = None

        # 成交(獲得收益)時間
        self.income_time = None

        # 碰觸到最高價的次數
        self.n_high = np.sum(np.array(self.ohlc.highs) == self.ohlc.high)

        # 碰觸到最低價的次數
        self.n_low = np.sum(np.array(self.ohlc.lows) == self.ohlc.low)

    def __repr__(self):
        info = f"Box(stock_id: {self.stock_id}, form_time: {self.ohlc.start_datetime} ~ {self.ohlc.stop_datetime})"
        info += f"\nhigh: {self.ohlc.high}, low: {self.ohlc.low}, n_transform: {self.scores['transform_score']}"
        info += f"\nupper_boundary: {self.upper_boundary_price}, lower_boundary: {self.lower_boundary_price}"

        if self.status_time is not None:
            info += f"\nstatus: {self.status}, status_time: {self.status_time}"

        if self.income_time is not None:
            info += f"\nincome: {self.income}, income_time: {self.income_time}, " \
                    f"annual_return_rate: {self.annual_return_rate}"

        return info

    __str__ = __repr__

    def setStatus(self, status: Status, status_time: datetime.datetime):
        self.status = status
        self.status_time = status_time

    def setBoundaryPrice(self, upper: Decimal, lower: Decimal):
        # 箱型突破(價格比箱型上緣高出一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
        self.upper_boundary_price = upper

        # 箱型跌破(價格比箱型下緣再低一個價格單位，價格單位根據當前價格與是否為 ETF 而有所不同)
        self.lower_boundary_price = lower

    def updateIncome(self, income: Decimal, return_rate: Decimal, annual_return_rate: Decimal,
                     income_time: datetime.datetime):
        self.income = income
        self.income_time = income_time

        # 報酬率
        self.return_rate = return_rate

        # 年化報酬率
        self.annual_return_rate = annual_return_rate

    def getGuid(self):
        return self.guid

    def getDirection(self):
        margin_delta, delta = self.ohlc.getDirection()

        return margin_delta, delta

    def getStartTime(self):
        return self.ohlc.start_datetime

    def getStopTime(self):
        return self.ohlc.stop_datetime

    def getHighest(self):
        return self.ohlc.high

    def getLowest(self):
        return self.ohlc.low

    def getTrigerPrice(self):
        return self.upper_boundary_price

    def getSpread(self):
        spread = self.ohlc.getSpread()

        return spread


class BoxExplorer:
    def __init__(self, stock_id: str, n_ohlc: int, oc: OhlcContainer, threshold: float = 2.0,
                 logger_dir="box_explorer", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        """
        負責尋找箱型，找到後將形成 Box 物件

        :param stock_id: stock_id
        :param n_ohlc: 箱型形成至少包含多少個 Ohlc 物件
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

        # 至少需要的 K 棒個數 -> int
        self.n_ohlc = n_ohlc

        # 價格可容忍波動幅度 (影響了停損和購買價之間的差距)
        # -> 2 只是預設值，正常流程會先根據價位來更新 self.price_lim，接著再開始尋找箱型
        self.price_lim = Decimal("2")

        # OhlcContainer
        self.oc = oc

        # 固定不調整的超參數
        # 箱型分數的閾值(預設值，之後可能根據產業別、國家別等依據，尋找適合的閾值)
        self.threshold = threshold

        # 歷史價格區間
        self.history_high = Decimal("0")
        self.history_low = Decimal("1e5")

        # 歷史平均交易量(由 n_volumn 筆數據平均而得)
        self.history_vol = 0
        self.n_volumn = 0

        # 箱型 Ohlc
        self.ohlc = None

        # region 事件與監聽
        self.event = Event()
        self.onBoxFormed = self.event.onBoxFormed
        # endregion

        # 管理過程中形成的所有箱型
        self.boxes = []

        # 用於紀錄各項數值，以觀察其分布情形
        self.score_keys = ["x_score", "y_score", "transform_score", "delta_score"]

        # 存取各分項數值(最新一筆)(element: float)
        self.component_scores = dict()
        self.component_history = defaultdict(list)

        for key in self.score_keys:
            self.component_scores[key] = 0.0
            self.component_history[key] = []

        # self.component_history["score"] = []

        # 紀錄搜尋箱型的過程中，內含 Ohlc 個數(包括未能成型的情況)
        self.n_ohlcs = []

        # 價差紀錄會包含未形成箱型的情況，因此數據維度與分數類的不同
        self.spreads = []

    def __str__(self):
        info = f"BoxExplorer(stock_id: {self.stock_id}, n_ohlc: {self.n_ohlc}, " \
               f"price_lim: {self.price_lim}, threshold: {self.threshold})"

        if self.history_high != 0:
            info += f"\nhistory_high: {self.history_high}, history_low: {self.history_low}, " \
                    f"history_vol: {self.history_vol}"

        # TODO: 根據箱型的 direction, income, ...等資訊，衡量各項分數與收益之間的關係

        return info

    def update(self):
        # 取得"價格波動在容許範圍之內 & Ohlc 個數大於要求個數"之箱型
        self.findBox()

        # 若有找到箱型(spread <= self.price_lim & n_ohlc >= self.n_ohlc)
        if self.ohlc is not None:
            # 計算箱型分數
            score = self.computeBox()

            self.logger.debug(f"({self.stock_id}) Found box, score: {score}\n{self.ohlc}", extra=self.extra)

            # 若分數超過門檻值，表示箱型形成，觸發事件以通知策略
            if score >= self.threshold:
                box = Box(stock_id=self.stock_id,
                          ohlc=self.ohlc,
                          scores=self.component_scores)
                self.logger.info(f"({self.stock_id}) New box: {box.guid}", extra=self.extra)

                # 紀錄形成的箱型
                self.boxes.append(box)

                # 觸發箱型形成事件，通知策略
                self.onBoxFormed(box=box)

    def findBox(self):
        """
        取得最新的最高最低金額
        從最近的 K 棒往前數 self.n_ohlc 個 K 棒做為箱型判斷的依據，
        取得 self.n_ohlc 個 K 棒內的最高(self.high)和最低(self.low)值

         # 更新 box_explorer 的歷史數據
        self.box_explorer.setHistoryData(high_value=high, low_value=low, vol=vol)

        # 根據現在價位調整箱型認定的價格區間，由於是取價位的允許跌幅再四捨五入到整數位，因此有一定的穩定性，不會任意波動
        # 19 >> 1.9 >> 2； 23 >> 2.3 >> 2； 27 >> 2.7 >> 3
        price_lim = close * self.allowable_percent
        self.box_explorer.price_lim = price_lim.quantize(Decimal('0'), ROUND_HALF_UP)

        :return:
        """
        # Ohlc 總數
        n_data = len(self.oc)

        # 初始 Ohlc 個數
        n_ohlc = 0

        # Ohlc 總數大於至少所需的數量
        if n_data >= self.n_ohlc:
            n_offset = self.n_ohlc

            while n_offset > 0:
                # 計算當前個數的 Ohlc 的價差
                spread = self.oc.getSpread(n_ohlc=n_ohlc + n_offset)

                # 若前述價差在價格限制範圍內
                if spread <= self.price_lim:
                    # 增加 Ohlc 內的數據個數
                    n_ohlc += n_offset

                n_offset -= 1

        # n_ohlc = 0 -> getSpread(self.n_ohlc) > self.price_lim or n_data < self.n_ohlc
        if n_ohlc < self.n_ohlc:
            self.ohlc = None

            # 取出最低要求個數的 Ohlc，計算計算價差，此價差可能超出 self.price_lim
            spread = self.oc.getSpread(n_ohlc=self.n_ohlc)
        else:
            self.ohlc = self.oc.getOhlc(n_ohlc=n_ohlc, remove_raw_data=False)
            spread = self.ohlc.getSpread()

        # 紀錄 Ohlc 數據個數，用於調整 Ohlc 最低要求數量，self.n_ohlcs 個數為尋找箱型的次數
        self.n_ohlcs.append(n_ohlc)

        # 紀錄價差，用以調整價格波動限制，self.spreads 個數為尋找箱型的次數
        self.spreads.append(spread)

    def computeBox(self):
        """計算當前箱型之形狀的分數
        箱型評分要點：
        1. x_score: 持續時間越長越好(X 軸)
        2. y_score: 價格波動區間越小越好(Y 軸)，且不超過可忍受的價格波動範圍
        3. transform_score: 多次碰觸邊緣價格越好(最高或最低金額不只一次)
        4. delta_score: 將 delta 轉換為 0 ~ 1 之間的數值，delta = 0 對應到 delta_score = threshold，
                        只要不要負的太大，其他項的分數可以 cover 其低於門檻的部分
        vol_score: 箱型中的平均交易量 與 歷史平均交易量 的比值，不納入 vol_score，但保留紀錄，用於衡量交易量與收益之間的關係
        :return:
        """
        # 1. x_score: 持續時間越長越好(X 軸)
        # 要求至少 Ohlc 要有 self.n_ohlc 個，'當前個數'再和'最低要求個數'相除，越多比值越高
        # 透過取 ln 來減緩數值增長幅度
        n_ohlc = len(self.ohlc)

        # 0.0 <= np.log(float(n_ohlc) / self.n_ohlc) < +∞
        # threshold <= x_score <= +∞
        self.component_scores["x_score"] = self.threshold + np.log(float(n_ohlc) / self.n_ohlc)

        # 2. y_score: 價格波動區間越小越好(Y 軸)，已要求價格波動要小於 self.price_lim
        # 0 <= price_range <= self.price_lim
        price_range = self.ohlc.getSpread()

        # (price_range + self.price_lim) / self.price_lim 在 price_range 為 0 的時候，整體數值也可維持在 1
        # 1.0 <= (price_range + self.price_lim) / self.price_lim <= 2.0
        # threshold <= y_score <= threshold + 1.0
        self.component_scores["y_score"] = self.threshold + float((price_range + self.price_lim) / self.price_lim) - 1.0

        # 3. transform_score: 狀態值轉換次數
        # 使用每日收盤價作為判斷依據
        close_values = self.ohlc.getDatas(kind="close")

        # 計算狀態值轉換次數，維持同一數值(最好狀態)會計算成數值個數，一路往上或往下只會轉換 1 次
        n_transform = self.countTransform(close_values)

        # 希望至少轉換 2 次，若只轉換一次，會使得分數為 0 分
        self.component_scores["transform_score"] = self.threshold * (n_transform - 1) + 1e-8

        # 4. 考慮價格變化率的'大小 & 方向'
        margin_delta, delta = self.ohlc.getDirection()

        self.component_scores["delta_score"] = self.threshold * 2.0 * float(sigmoid(delta))

        # region 用於觀察、衡量交易量與收益之間的關係
        # vol_score: 箱型中的平均交易量 與 歷史平均交易量 的比值
        # 每個 K 棒的平均交易量
        avg_vol = float(self.ohlc.volumn) / n_ohlc

        # 0.0 < vol_score <= +∞
        vol_score = (avg_vol / self.history_vol) + 1.0
        self.component_history["vol"].append(vol_score)
        # endregion

        # 計算各項分數的幾何平均(個數為形成候選箱型的數量)
        scores = [value for value in self.component_scores.values()]
        score = geometricMean(scores)

        for key, value in self.component_scores.items():
            self.component_history[key].append(value)

        self.component_history["score"].append(score)

        return score

    def countTransform(self, values):
        """
        根據價格導數為 正、負、零 三種狀態，判斷

        :param values: 價格導數
        :return:
        """

        def getSign(value, mean):
            """
            根據數值相對於平均數的位置，返回不同狀態值

            :param value: 要比較的數值
            :param mean: 平均數
            :return: 狀態值(大於平均: 1, 等於平均: 0, 小於平均: -1)
            """
            if value > mean:
                return 1
            elif value < mean:
                return -1
            else:
                return 0

        n_value = len(values)
        mean = sum(values) / n_value
        sign = getSign(value=values[0], mean=mean)
        n_transform = 0

        for i in range(1, n_value):
            # 取得當前數值的狀態值
            curr_sign = getSign(value=values[i], mean=mean)

            # 若 當前狀態值 與 前一個狀態值 不同
            if curr_sign != sign:
                # 狀態值轉換次數加一
                n_transform += 1

                # 更新 前一個狀態值
                sign = curr_sign

        if n_transform == 0 and sign == 0:
            msg = f"箱型內價格皆相同(#value: {n_value}, mean: {mean})"
            transform_score = n_value
        else:
            transform_score = n_transform
            msg = f"箱型內價格發生 {n_transform} 次狀態轉變(#value: {n_value}, mean: {mean})"

        self.logger.debug(f"{msg}: {values}", extra=self.extra)

        return transform_score

    def getBox(self, index):
        return self.boxes[index]

    def getBoxByGuid(self, guid):
        for box in self.boxes:
            if box.getGuid() == guid:
                return box

        return None

    def iterBoxes(self):
        for box in self.boxes:
            self.logger.info(f"({self.stock_id}) guid: {box.guid}, id: {id(box)}", extra=self.extra)
            yield box

    # [目前無使用] 計算價格之位置分數
    def getPositionScore(self):
        """
        分子: 箱型最高價到歷史最高價
        分母: 歷史最高價到歷史最低價

        位置在 0.75 時，分數最高；位置越往上，分數下降較快；位置越往下，分數下降較慢。
        偏好上半部位置，但不能太高；但都是越接近歷史臨界價位，分數越低。
        :return:
        """

        def truncatedDistribution(x, x_hat, a, offset):
            y = -a * (x - x_hat) ** 2 + offset

            if y < 0:
                y = 0

            return y

        # 歷史最高 -> 箱型最高
        numerator = self.history_high - self.ohlc.high

        # 歷史最高 -> 歷史最低
        denominator = self.history_high - self.history_low

        # 位置參數
        pos_index = numerator / denominator

        score1 = truncatedDistribution(x=pos_index, x_hat=0.75, offset=0.625, a=10.0)
        score2 = truncatedDistribution(x=pos_index, x_hat=0.5, offset=0.5, a=2)

        # 在 0.75 的位置，兩個分配相加為 1(修改數值範圍: 1 <= position_score <= 2)
        score = score1 + score2 + 1

        return score

    # 設置 Logger 等級
    def setLoggerLevel(self, level):
        self.logger.setLevel(level)

    # 設置歷史價格區間
    def setHistoryData(self, high_value=None, low_value=None, vol=None):
        """
        設置歷史價格區間

        :param high_value: 歷史最高價
        :param low_value: 歷史最低價
        :param vol: 歷史平均交易量
        :return:
        """
        if high_value > self.history_high:
            self.logger.info(f"({self.stock_id}) history_high: {self.history_high} -> {high_value}", extra=self.extra)
            self.history_high = high_value

        if low_value < self.history_low:
            self.logger.info(f"({self.stock_id}) history_low: {self.history_low} -> {low_value}", extra=self.extra)
            self.history_low = low_value

        self.updateAvgVolumn(vol=vol)

    def updateAvgVolumn(self, vol):
        new_value_weight = 1.0 / (self.n_volumn + 1)
        origin_weight = new_value_weight * self.n_volumn

        # avg_volumn: 歷史平均交易量(由 n_volumn 筆數據平均而得)
        self.history_vol = self.history_vol * origin_weight + vol * new_value_weight
        self.n_volumn += 1

    def checkBayesProbability(self):
        # TODO: 根據所記錄的 boxes 來計算各參數下的 box 的獲利機率，再利用機率去決定是否送出購買請求，
        #  降低門檻值的影響(可以不用糾結於要設多少)
        pass

    # 超參數調整
    def modifySuperParams(self):
        """
        調整超參數 n_ohlc & price_lim

        :return:
        """
        # 更新之超參數: n_ohlc
        if len(self.n_ohlcs) > 0:
            # 原始最低要求個數
            n_ohlc = self.n_ohlc

            # Ohlc 數據個數紀錄平均數
            ohlc_mean = np.mean(self.n_ohlcs)
            self.logger.debug(f"({self.stock_id}) n_ohlcs: {sorted(self.n_ohlcs)}", extra=self.extra)

            # 更新 Ohlc 數據最低要求個數(最高價 1 個，最低價 1 個，至少還須再一個才算'箱型'吧，因此最低要求為 3 個)
            self.n_ohlc = max(3, int(ohlc_mean))
            self.logger.info(f"({self.stock_id}) Modify n_ohlc: {n_ohlc} -> {self.n_ohlc}", extra=self.extra)

        # # 更新之超參數: price_lim
        # if len(self.spreads) > 0:
        #     # 原始價格波動限制
        #     price_lim = self.price_lim
        #
        #     # 價差數據紀錄平均數
        #     spread_mean = np.mean(self.spreads)
        #     self.logger.debug(f"({self.stock_id}) spreads: {sorted(self.spreads)}", extra=self.extra)
        #
        #     # 更新價格波動限制(最小不得小於 2 倍單位價格)
        #     last_close_price = self.oc.getLastValue(kind="close")
        #     self.price_lim = max(spread_mean, unitPrice(last_close_price) * Decimal("2.0"))
        #     self.logger.info(f"({self.stock_id}) Modify price_lim: {price_lim} -> {self.price_lim}", extra=self.extra)

    def reset(self):
        """
        * 超參數(n_ohlc, price_lim)將在訓練模式後被修改，因此這裡不修改
        * OhlcContainer, history_high, history_low 訓練模式後仍繼續儲存數據，亦不修改

        :return:
        """
        self.ohlc = None
        self.n_ohlcs = []
        self.spreads = []


if __name__ == "__main__":
    from data.container import ohlcGenerator


    class BoxTester:
        def __init__(self):
            self.oc = OhlcContainer(minutes=1)
            self.box_explorer = BoxExplorer(stock_id="2330", n_ohlc=5, price_lim=Decimal("2.5"), oc=self.oc,
                                            threshold=1.5)

            high_value = Decimal("30.0")
            low_value = Decimal("29.0")

            # 交易量(陣列)
            volumns = [3, 3, 3, 1, 2, 3, 3, 1, 3, 3]

            # 初始化歷史交易量資訊 history_vol: 歷史平均交易量(由 n_volumn 筆數據平均而得)
            self.box_explorer.history_vol = np.mean(volumns[:-1])
            self.box_explorer.n_volumn = len(volumns[:-1])

            self.box_explorer.setHistoryData(high_value=high_value, low_value=low_value, vol=volumns[-1])
            print(self.box_explorer)

            datas = [(datetime.datetime(2020, 6, 4, 9, 1, 57), Decimal("31.5"), Decimal("33.0"), Decimal("30.1"),
                      Decimal("32.3"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 2, 57), Decimal("30.7"), Decimal("32.5"), Decimal("30.3"),
                      Decimal("31.5"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 3, 57), Decimal("29.7"), Decimal("31.5"), Decimal("29.3"),
                      Decimal("30.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 4, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 5, 57), Decimal("29.5"), Decimal("31.5"), Decimal("29.3"),
                      Decimal("30.7"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 6, 43), Decimal("29.5"), Decimal("30.7"), Decimal("29.3"),
                      Decimal("30.5"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 7, 57), Decimal("29.5"), Decimal("30.5"), Decimal("29.3"),
                      Decimal("29.3"), 3),
                     (datetime.datetime(2020, 6, 4, 9, 8, 43), Decimal("30.5"), Decimal("30.5"), Decimal("29.5"),
                      Decimal("29.5"), 2),
                     (datetime.datetime(2020, 6, 4, 9, 9, 29), Decimal("28.7"), Decimal("30.5"), Decimal("28.7"),
                      Decimal("30.2"), 1),
                     (datetime.datetime(2020, 6, 4, 9, 10, 3), Decimal("29"), Decimal("30.5"), Decimal("28.7"),
                      Decimal("28.7"), 3),
                     ]
            # self.oc.onOhlcFormed += onOhlcFormedListener

            for data in datas:
                self.oc.addOhlc(*data)

        @staticmethod
        def onOhlcFormedListener(date_time, open_value, high_value, low_value, close_value, volumn):
            print(f"onOhlcFormedListener: ({date_time}, {open_value}, {high_value}, {low_value}, "
                  f"{close_value}, {volumn})")

        @staticmethod
        def onBoxFormedListener(box: Box):
            print(box)
            print(f"high: {box.getHighest()}, low: {box.getLowest()}, avg_vol: {np.mean(box.ohlc.volumns)}")

        def testFindBox(self):
            n_test = 50

            if n_test > 1:
                self.box_explorer.setLoggerLevel(logging.INFO)

            for i in range(n_test):
                self.oc.reset()
                # 0: ohlc_time, 1: open_value, 2: high_value, 3: low_value, 4: close_value, 5: volumn
                og = ohlcGenerator(init_value=28, ohlc_time=datetime.datetime(year=1984, month=6, day=4),
                                   offset=(1 / 1.05, 1.05))
                data = next(og)
                self.box_explorer.setHistoryData(high_value=Decimal(str(data[2])), low_value=Decimal(str(data[3])),
                                                 vol=data[5])

                for _ in range(50):
                    data = next(og)
                    self.oc.addOhlc(*data)

                self.box_explorer.findBox()
                ohlc = self.box_explorer.ohlc

                if ohlc is not None:
                    if ohlc.getSpread() > self.box_explorer.price_lim:
                        print(f"Out of price_lim: {ohlc.getSpread()}", ohlc)
                    else:
                        print(ohlc)

                    # for n_ohlc in range(1, len(ohlc) + 1):
                    #     spread = self.oc.getSpread(n_ohlc)
                    #     print(f"n_ohlc: {n_ohlc}, spread: {spread}")

                    # print(ohlc.opens)
                    # print(ohlc.highs)
                    # print(ohlc.lows)
                    # print(ohlc.closes)
                    # print(ohlc.volumns)

        def testUpdate(self):
            self.box_explorer.onBoxFormed += self.onBoxFormedListener
            self.box_explorer.update()

            print(self.box_explorer)


    box_tester = BoxTester()
    box_tester.testFindBox()
