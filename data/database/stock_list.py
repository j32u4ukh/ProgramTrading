import datetime
import functools
import logging

from data.database import DataBase
from submodule.Xu3.database import DataBase as Xu3DataBase


class StockListBase(Xu3DataBase):
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

    def __init__(self, db_name="stock_data", folder="data",
                 logger_dir="resource_data", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        super().__init__(db_name=db_name, folder=folder, logger_dir=logger_dir, logger_name=logger_name)
        self.getTable()

    def __del__(self):
        super().__del__()

    @staticmethod
    def sortStockWithPrice(stocks):
        """
        根據價格來排序 stocks

        :param stocks: ex: [(s_1, p_1), (s_2, p_2), ..., (s_n, p_n)]
        :return:
        """

        def comparePrice(sp1, sp2):
            """
            如果 x 應該排在 y 的前面，返回 -1，
            如果 x 應該排在 y 的後面，返回 1。
            如果 x 和 y 相等，返回 0。

            def customSort(x, y):
                if x > y:
                    return -1
                if x < y:
                    return 1
                return 0

            :param sp1:
            :param sp2:
            :return:
            """
            s1, p1 = sp1
            s2, p2 = sp2

            if p1 < p2:
                return -1
            elif p2 < p1:
                return 1
            else:
                return 0

        # 透過自定義規則函式 compareRequests 來對 requests 來進行排序
        return sorted(stocks, key=functools.cmp_to_key(comparePrice))

    def setLoggerLevel(self, level: logging):
        self.logger.setLevel(level=level)

    def getTable(self, table_name="", table_definition=""):
        """
        不同人的 StockList 或許會不一樣，table_definition 應該各自定義。

        :param table_name:
        :param table_definition:
        :return:
        """
        super().getTable(table_name=table_name, table_definition=table_definition)

    def addData(self, table_name=None, primary_column: str = None, values: list = None):
        # super().add_(primary_column="STOCK_ID", values=values)
        super().add(values=values, primary_column=primary_column)

    def isStockExists(self, stock_id):
        is_exist = super().isDataExists(primary_key="STOCK_ID", key_value=f"'{stock_id}'", table_name=self.table_name)

        return is_exist

    def selectByStockIds(self, stock_ids: list = None, sort_by: str = "CAST(PRICE as decimal)",
                         sort_type: Xu3DataBase.SortType = Xu3DataBase.SortType.A2Z):
        """
        根據股票代碼篩選出數據，返回數據也包含了該股票的價位(上一次更新 STOCK_LIST 時的價位)

        :param stock_ids: 要篩選出來的股票代碼
        :param sort_by: 排序依據
        :param sort_type: 排序類型(正序/逆序)
        :return:
        """
        if stock_ids is None:
            return None

        sql_stocks = [f"STOCK_ID = '{stock_id}'" for stock_id in stock_ids]

        if len(sql_stocks) == 1:
            where = sql_stocks[0]
        else:
            where = Xu3DataBase.sqlOr(sql_stocks)

        result = super().select(table_name=self.table_name, where=where, columns=None,
                                sort_by=sort_by, sort_type=sort_type,
                                limit=None, offset=0)

        return result


if __name__ == "__main__":
    pass
