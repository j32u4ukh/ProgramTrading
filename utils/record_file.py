import os


def clearTempFile(clear=True):
    if clear:
        buy_requests_dir = "data/buy_requests"

        # 取得所有檔案與子目錄名稱
        files = os.listdir(buy_requests_dir)

        for file in files:
            # real 開頭為實際庫存，不刪除。回測僅 test 模式會讀入，但不能改存內容
            if file.startswith("real"):
                continue

            os.remove(os.path.join(buy_requests_dir, file))

        order_list_dir = "data/order_list"

        # 取得所有檔案與子目錄名稱
        files = os.listdir(order_list_dir)

        for file in files:
            # real 開頭為實際庫存，不刪除。回測僅 test 模式會讀入，但不能改存內容
            if file.startswith("real"):
                continue

            os.remove(os.path.join(order_list_dir, file))
