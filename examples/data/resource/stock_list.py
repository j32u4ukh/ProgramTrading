import datetime
import logging

from data.database import DataBase
from data.database.stock_list import StockListBase
from submodule.Xu3.database import DataBase as Xu3DataBase


class StockList(StockListBase):
    """
    未公開發行公司股票：對登錄財團法人中華民國證券櫃檯買賣中心創櫃板之股票，給予四位數字股票代號，公開發行時，沿用創櫃板之股票代號。

    公開發行公司股票：編碼原則為四位數字股票代號，新申請時，依其類別，於相同上市類別中，依序給號，相同上市類別之號碼用完後，
    再於上櫃相同類別中給號。未來若有更改產業類別或市場別變更，則依一碼到底原則，代號不予更動。

    ETF前二碼為數字，後加三碼流水編碼：
    指數股票型證券投資信託基金：以外幣計價者，第六碼
    為英文字母 K ；如為 槓桿型 ETF 第六碼為英文字母 L 、
    以外幣計價者第六碼為英文字母 M ；反向型 ETF 第六碼
    為英文字母 R 、以外幣計價者第六碼為英文字母 S 。
    """

    def __init__(self, db_name="stock_data", folder="examples/data",
                 logger_dir="resource_data", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(db_name=db_name, folder=folder, logger_dir=logger_dir, logger_name=logger_name)
        self.getTable()

    def __del__(self):
        super().__del__()

    def setLoggerLevel(self, level: logging):
        self.logger.setLevel(level=level)

    def getTable(self, table_name="", table_definition=""):
        table_name = "STOCK_LIST"

        # DAY: 是否有日線數據；MINUTE: 是否有 1 分線數據
        table_definition = """STOCK_ID TEXT  PRIMARY KEY NOT NULL,
        NAME    TEXT,    
        DAY     INT     NOT NULL,
        MINUTE  INT     NOT NULL,
        PRICE   TEXT    NOT NULL"""
        super().getTable(table_name=table_name, table_definition=table_definition)

    def selectByPriceRange(self, price_range: tuple, contain_price: bool = False,
                           sort_by: str = "CAST(PRICE as decimal)",
                           sort_type: Xu3DataBase.SortType = Xu3DataBase.SortType.A2Z):
        """
        TODO: price_range -> 設計 sqlWhere 等工具，讓 where 的內容更為彈性，而不是全都用 AND 連接起來

        :param price_range: 篩選的價格區間
        :param contain_price: 回傳值是否包含價格
        :param sort_by: 排序依據
        :param sort_type: 排序類型(正序/逆序)
        :return:
        """
        # price_range[0] <= CAST(PRICE as demical) AND CAST(PRICE as demical) < price_range[1]
        price_filter = Xu3DataBase.sqlAnd(DataBase.sqlGePrice(price_range[0]),
                                          DataBase.sqlLtPrice(price_range[1]))
        stocks = self.selectByPriceFilter(price_filter=price_filter,
                                          contain_price=contain_price,
                                          sort_by=sort_by,
                                          sort_type=sort_type)

        return stocks

    def selectByPriceFilter(self, price_filter: str, contain_price: bool = False,
                            sort_by: str = "CAST(PRICE as decimal)",
                            sort_type: Xu3DataBase.SortType = Xu3DataBase.SortType.A2Z):
        """
        使用 sqlWhere 等工具形成 price_filter，讓 where 的內容更為彈性，而不是全都用 AND 連接起來

        :param price_filter: 篩選的價格區間
        "{price_range[0]} <= CAST(PRICE as demical) AND CAST(PRICE as demical) < {price_range[1]}"
        :param contain_price: 回傳值是否包含價格
        :param sort_by: 排序依據
        :param sort_type: 排序類型(正序/逆序)
        :return:
        """
        result = super().select(table_name=self.table_name, where=price_filter, columns=None,
                                sort_by=sort_by, sort_type=sort_type,
                                limit=None, offset=0)
        stocks = []

        for res in result:
            # '9955', '', 0, 0, '18.2'
            stock_id, _, _, _, price = res

            if contain_price:
                stocks.append((stock_id, price))
            else:
                stocks.append(stock_id)

        return stocks

    def updateByStockId(self, stock_id, auto_commit, **kwargs):
        condition = f"STOCK_ID = '{stock_id}'"

        keys = []
        values = []

        for key, value in kwargs.items():
            # NAME: str, DAY: int, MINUTE: int
            keys.append(key.upper())

            if key.upper() == "NAME":
                values.append(f"'{value}'")
            else:
                values.append(f"{value}")

        new_content = f"{keys[0]} = {values[0]}"
        n_content = len(keys)

        for i in range(1, n_content):
            new_content += f", {keys[i]} = {values[i]}"

        self.logger.debug(f"condition: {condition}, new_content: {new_content}", extra=self.extra)
        self.update(new_content=new_content, condition=condition, auto_commit=auto_commit)


if __name__ == "__main__":
    class StockListTester:
        def __init__(self):
            self.stock_list = StockList()

        def selectByStockIds(self):
            results = self.stock_list.selectByStockIds(stock_ids=["00739"])

            output = []

            # ('2812', '', 1, 1, '11.6')
            for result in results:
                stock_id, _, _, _, price = result
                output.append((stock_id, price))

            print(output)

        def selectByPriceFilter(self, price_range: tuple):
            # selectByPriceFilter(self, price_filter: str, contain_price: bool = False,
            #                             sort_by: str = "CAST(PRICE as demical)", sort_type="ASC")
            price_filter = Xu3DataBase.sqlAnd(DataBase.sqlGePrice(price_range[0]),
                                              DataBase.sqlLtPrice(price_range[1]))
            print(f"price_filter: {price_filter}")
            stocks = self.stock_list.selectByPriceFilter(price_filter=price_filter, sort_by="STOCK_ID")

            for idx, stock in enumerate(stocks):
                print(idx, stock)

        def selectByPriceRange(self, price_range: tuple):
            stocks = self.stock_list.selectByPriceRange(price_range=price_range, sort_by="STOCK_ID")

            for idx, stock in enumerate(stocks):
                print(idx, stock)

        def display(self):
            head = self.stock_list.head(sort_by="STOCK_ID")

            for result in head:
                print(result)

            tail = self.stock_list.tail(sort_by="STOCK_ID")

            for result in tail:
                print(result)

        def close(self):
            self.stock_list.close(auto_commit=True)


    stock_list_tester = StockListTester()
    # # stock_list_tester.display()
    # stock_list_tester.selectByStockIds()
    # stock_list_tester.selectByPriceFilter(price_range=(29.5, 30))

    # stock_list = StockList()
    # result = stock_list.selectByStockIds(stock_ids=["00739"])
    # _, _, _, _, price = result.fetchone()
