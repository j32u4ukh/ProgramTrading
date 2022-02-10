import datetime
import logging

import pandas as pd

from submodule.Xu3.utils import getLogger


# 管理庫存用的類別，包含讀取、更新和寫入，若單純只需要庫存的代碼陣列，可以使用 class Investment
class Inventory:
    def __init__(self, logger_dir="data", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        self.path = "data/inventory.csv"

        # https://stackoverflow.com/questions/39176131/pandas-load-data-with-data-type-issues
        # guid, date_time, stock_id, volumn, price
        self.df = pd.read_csv(self.path,
                              dtype={0: str, 1: str, 2: str, 3: int, 4: str})

        self.logger_dir = logger_dir
        self.logger_name = logger_name
        self.extra = {"className": self.__class__.__name__}
        self.logger = getLogger(logger_name=self.logger_name,
                                to_file=True,
                                time_file=False,
                                file_dir=self.logger_dir,
                                instance=True)

        self.check = None
        self.remove_orders = None

    def setLoggerLevel(self, level: logging):
        self.logger.setLevel(level)

    def findIndex(self, stock_id: str):
        stock_df = self.df[self.df["stock_id"] == stock_id].copy()

        if len(stock_df) == 0:
            return None

        return stock_df.index[0]

    def add(self, guid: str, stock_id: str, volumn: int, price: str, time: datetime.datetime = None):
        index = self.findIndex(stock_id=stock_id)

        if time is None:
            time = datetime.datetime.now()

        if self.check is None:
            self.check = []

        if self.remove_orders is None:
            self.remove_orders = []

            for idx, value in enumerate(self.df.values):
                self.remove_orders.append([idx, *list(value)])

        self.check.append(stock_id)

        # 新的庫存被加入
        if index is None:
            date_time = str(time.date())
            self.df = self.df.append({"guid": guid,
                                      "date_time": date_time,
                                      "stock_id": stock_id,
                                      "volumn": volumn,
                                      "price": price
                                      }, ignore_index=True)

            self.logger.info(f"Add [{guid}, {date_time}, {stock_id}, {volumn}, {price}]", extra=self.extra)
            return True

        # 股數與價格 可能被更新
        else:
            self.df.loc[index, "price"] = price
            n_order = len(self.remove_orders)

            for i in range(n_order):
                idx, _, _, r_stock_id, r_volumn, _ = self.remove_orders[i]

                # 為當前傳入的股票代碼
                if r_stock_id == stock_id:
                    sold_volumn = int(r_volumn) - int(volumn)

                    if sold_volumn == 0:
                        del self.remove_orders[i]
                        break

                    else:
                        # 沒有被完全賣光，因此無須傳遞索引值給刪除函式
                        self.remove_orders[i][0] = -1

                        self.remove_orders[i][4] = sold_volumn
                        self.df.loc[index, "volumn"] = volumn

            return False

    # TODO: 考慮出售零股，該庫存還會剩 1000 股在手上，不會被現有的機制篩選出來
    # 售出檢查模式，查詢損益時，要比對那些庫存沒有回報，代表該庫存已被售出
    def remove(self):
        remove_indexs = []

        for remove_order in self.remove_orders:
            idx, _, _, _, _, _ = remove_order
            self.logger.info(f"sold: {remove_order}", extra=self.extra)

            if idx != -1:
                remove_indexs.append(idx)

        # stock_ids = self.df["stock_id"].values
        # remove_ids = [stock_id for stock_id in stock_ids if stock_id not in self.check]
        # sold_df = self.df.loc[self.df["stock_id"].isin(remove_ids)].copy()
        # sold_df = self.df.iloc[remove_indexs].copy()
        # self.logger.info(f"sold_df\n{sold_df.iloc[:, 1:]}", extra=self.extra)

        self.df.drop(remove_indexs, inplace=True)
        self.df = self.df.reset_index(drop=True)

        return self.remove_orders

    def resetCheck(self):
        self.check = None

    def getInventory(self, id_only=True):
        if id_only:
            return list(self.df["stock_id"].values)
        else:
            return self.df.values

    def load(self, stock_id):
        df = self.df[self.df["stock_id"] == stock_id].copy()

        return df.values

    def printDataFrame(self):
        self.logger.info(f"\n{self.df.iloc[:, 1:]}", extra=self.extra)

    def save(self):
        # 利用時間欄位排序
        try:
            self.df["date_time"] = pd.to_datetime(self.df["date_time"])
            self.df.sort_values(by=["date_time", "price"], inplace=True)
        except TypeError as te:
            self.logger.error(f"type: {self.df['date_time'].dtype}\n{self.df['date_time']}\n{te.args}",
                              extra=self.extra)

        # 庫存數據更新
        self.df.to_csv(self.path, index=False)


if __name__ == "__main__":
    inventory = Inventory()
    inventory_ids = inventory.getInventory()
    df = inventory.df
    print(df)

    values = []

    for value in df.values:
        values.append(list(value))

    print(values)

    df.loc[0, "volumn"] = 1020
    print(df)
    del values[2]

    for value in values:
        guid, date_time, stock_id, volumn, price = value
        inventory.add(guid=guid, stock_id=stock_id, volumn=volumn, price=price)

    remove_orders = inventory.remove()
    print("remove_orders:", remove_orders)
    # inventory.save()
