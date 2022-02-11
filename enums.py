from enum import Enum


class OhlcType(Enum):
    # Tick
    Tick = 0
    # 1 分鐘 Ohlc
    Minute = 1
    # 完整日 Ohlc
    Day = 2
    # 週 Ohlc
    Week = 3
    # 月 Ohlc
    Month = 4


class Stage(Enum):
    """
    對於同時使用 API 與自己定義的類別(如回測系統)，同一個事件監聽器可能被不同需求所使用，
    利用不同 Stage 來區分不同需求
    """
    # 更新資料庫數據
    Update = "Update"
    # 更新 StockList(個股最新收盤價)
    UpdateStockList = "UpdateStockList"
    # 回測
    Backtest = "Backtest"
    # 交易
    Transaction = "Transcation"


class OrderMode(Enum):
    """
    參考網站
    https://rich01.com/long-shor/
    """
    # 多單
    Long = "Long"
    # 空單
    Short = "Short"


class ReportType(Enum):
    # 總體
    Total = "Total"
    # 收益
    Profit = "Profit"
    # 虧損
    Loss = "Loss"
    # 收益(Revenue - Cost)
    Income = "Income"
    # 累積收益
    CumIncome = "CumIncome"
    # 賺賠比
    EarningLossRate = "EarningLossRate"
    # 跌價
    FallingPrice = "FallingPrice"
    # 勝率(贏的次數/總次數)
    WinRate = "WinRate"
    # 報酬率
    ReturnRate = "ReturnRate"
    # 購買請求
    BuyRequest = "BuyRequest"
    # 售出請求
    SellRequest = "SellRequest"


class StrategyMode(Enum):
    # 訓練
    Train = "Train"
    # 驗證
    Validation = "Validation"
    # 測試
    Test = "Test"


class PerformanceStage(Enum):
    # 訓練
    Train = "Train"
    # 驗證
    Validation = "Validation"
    # 測試
    Test = "Test"
    # 短期表現(相較於 驗證|測試 時間較短，用於判斷表現是否持續成長)
    Short = "Short"


class Category(Enum):
    DayTrading = "DayTrading"
    NonDayTrading = "NonDayTrading"
    Etf = "Etf"
    Stock = "Stock"

    # 國內(大多數為 10% 漲跌幅限制)
    Domestic = "Domestic"

    # 國外(無漲跌幅限制)
    Foreign = "Foreign"


class CapitalType(Enum):
    NoneTpye = None
    Capital = "capital"
    Revenue = "revenue"


"""
以上為自己定義，以下為 API 所使用
"""


class RequestType(Enum):
    Buy = "Buy"
    Sell = "Sell"


class RequestElement(Enum):
    Time = 0
    Price = 1
    Volumn = 2


class OrderCondition(Enum):
    """
    # 文件中有些地方寫 IOC: 1，FOK: 2。推測是 for 期貨，證券還是用 IOC: 3，FOK: 4

    ROD(Rest of Day)：指「當日委託有效單」，送出委託之後，投資人只要不刪單且直到當日收盤前，此張單子都是有效的。
    當投資人使用限價單掛出時，系統自動設定為「ROD」委託。

    IOC(Immediate-or-Cancel)：指「立即成交否則取消」，投資人委託單送出後，允許部份單子成交，其他沒有滿足的單子則取消。
    當投資人掛出市價單時，系統會自動設定為「IOC」。

    FOK(Fill-or-Kill)：指「立即全部成交否則取消」，當投資人掛單的當下，只要全部的單子成交，沒有全部成交時則全部都取消。
    """
    ROD = 0
    IOC = 3
    FOK = 4


class SkStruct(Enum):
    # 字串內容刻意取的和原始物件名稱相同，方便事後回查
    QuoteStock = "SKSTOCK"  # [deprecated] (改用 QuoteStockLong)
    QuoteStockLong = "SKSTOCKLONG"

    Best5 = "SKBEST5"
    QuoteTick = "SKTICK"
    StockOrder = "STOCKORDER"
    StockStrategyOrder = "STOCKSTRATEGYORDER"

    # 新損益試算查詢物件
    TSProfitLossGWQuery = "TSPROFITLOSSGWQUERY"

    # MIT
    StockStrategyOrderMit = "STOCKSTRATEGYORDERMIT"

    # 移動停損(和 StockStrategyOrderMit 採用同一個物件對象 STOCKSTRATEGYORDERMIT)
    StockStrategyOrderMst = "STOCKSTRATEGYORDERMIT"

    # 出清
    StockStrategyOrderOut = "STOCKSTRATEGYORDEROUT"


class Commodity(Enum):
    # 在 API 當中使用通常為整數的形式存在，但每個需要市場代碼的 API ，其代碼與市場的對應似乎不是固定的
    # 在 A 函式中海外期貨可能是 5，在 B 函式中可能變成 3。若其實每個地方代碼都是固定的，那倒是可以將數值改成其對應的整數。
    # 目前以 Enum 的形式傳入，再透過各函式中定義轉換用字典來取得代碼。
    Security = "證券"
    Future = "期貨"
    Option = "選擇權"

    # 透過券商幫忙買賣國外的股票
    SubBrokerage = "複委託"

    ForeignFuture = "海外期貨"
    ForeignOption = "海外選擇權"


class SmartOrder(Enum):
    # 當沖
    DayTrade = "DayTrade"
    # 當沖(未成交入場單)
    DayTradeApproachYet = "DayTradeApproachYet"
    # 當沖(已進場單)
    DayTradeApproach = "DayTradeApproach"
    # 出清
    ClearOut = "ClearOut"
    # MIT單(Market If Touched)：若觸及設定之觸發價，即以市價送出委託。
    MIT = "MIT"
    # 二擇一
    OCO = "OCO"
    # 多次 IOC(IOC:「立即成交否則取消」)
    MIOC = "MIOC"
    # 移動停損
    MST = "MST"


class BuySell(Enum):
    # 買進
    Buy = 0
    # 賣出
    Sell = 1


class IsAsync(Enum):
    No = 0
    Yes = 1


# 買賣形式
class Flag(Enum):
    # 現股
    CurrentShares = 0
    # 融資
    Financing = 1
    # 融券
    SecuritiesLending = 2
    # 無券
    # TODO: 檢查 無券賣 的代號是否大多被改為 8
    WithoutSecurities = 3

    # 券差(目前的理解是: 有券，但不足，需要向證交所借一部分)
    # https://www.twse.com.tw/zh/page/products/trading/information5.html
    SemiSecurities = 9


class Period(Enum):
    # 盤中
    Intraday = 0
    # 盤後
    AfterHours = 1
    # 零股(目前零股即為盤後交易，之後才會推出盤中零股交易)
    OddShares = 2


class Prime(Enum):
    # 上市櫃
    ListedCompany = 0
    # 興櫃
    EmergingCompany = 1


class SpecialTradeType(Enum):
    # 市價
    MarketPrice = 1
    # 限價
    LimitPrice = 2


class QueryType(Enum):
    # 未實現
    UnAchieve = 0
    # 已實現
    Achieve = 1
    # 現股當沖
    StockDayTrade = 2
