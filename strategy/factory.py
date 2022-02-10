import datetime
import json
from decimal import Decimal

from enums import PerformanceStage
from strategy.day_box import DayBoxStrategy


# TODO: 輸入要建置的策略名稱，避免當一支股票有多支策略時被一起載入，一次一支策略即可
def buildStrategys(stock_ids, performance_filter=Decimal("1.04"),
                   logger_dir="strategy", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
    path = "data/trained_strategy.txt"
    strategys = []
    trained_stock_ids = []
    build_funcs = {"DayBoxStrategy": buildDayBoxStrategy}

    with open(path, "r") as f:
        trained = json.load(f)

        for stock_id in stock_ids:
            if not trained.__contains__(stock_id):
                print(f"({stock_id}) 沒有預訓練的策略")
                continue

            trained_stock_ids.append(stock_id)
            cls_dict = trained[stock_id]

            # 一個股票若同時有多支策略，會同時被引入
            for cls, params in cls_dict.items():
                ignore = False

                # 策略表現過濾器
                for p in params["performance"]:
                    if Decimal(p) < performance_filter:
                        ignore = True

                if not ignore:
                    buildFunc = build_funcs[cls]
                    strategy = buildFunc(stock_id=stock_id,
                                         params=params,
                                         logger_dir=logger_dir,
                                         logger_name=logger_name)
                    strategys.append(strategy)

    return strategys


def buildDayBoxStrategy(stock_id: str, params: dict, logger_dir: str, logger_name: str):
    strategy = DayBoxStrategy(stock_id=stock_id,
                              volumn=params["volumn"],
                              allowable_percent=Decimal(params["allowable_percent"]),
                              n_order_lim=params["n_order_lim"],
                              short_term=params["short_term"],
                              n_ohlc=params["n_ohlc"],
                              days=params["days"],
                              threshold=params["threshold"],
                              logger_dir=logger_dir,
                              logger_name=logger_name)

    performance = [Decimal(p) for p in params["performance"]]
    strategy.performance[PerformanceStage.Train] = performance

    return strategy


def hasTrainedStrategy(strategy_name):
    path = "data/trained_strategy.txt"
    trained_stock_ids = []

    with open(path, "r") as f:
        trained = json.load(f)

        for stock_id in trained.keys():
            cls_dict = trained[stock_id]

            for cls in cls_dict.keys():
                if cls == strategy_name:
                    trained_stock_ids.append(stock_id)

                    # 每次 break 只會跳出當前迴圈而已
                    break

    return trained_stock_ids


if __name__ == "__main__":
    def checkPerformance(stock_ids):
        path = "data/trained_strategy.txt"

        with open(path, "r") as f:
            trained = json.load(f)
            performances = dict()

            for stock_id in stock_ids:
                if not trained.__contains__(stock_id):
                    print(f"({stock_id}) 沒有預訓練的策略")
                    continue

                cls_dict = trained[stock_id]

                # 一個股票若同時有多支策略，會同時被引入
                for cls, params in cls_dict.items():
                    # 策略表現過濾器
                    for p in params["performance"]:
                        performances[stock_id] = Decimal(p)

        return performances


    def checkFilter(stock_ids, performance_filter=Decimal("1.04"),
                    logger_dir="strategy", logger_name=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")):
        strategys = buildStrategys(stock_ids,
                                   performance_filter=performance_filter,
                                   logger_dir=logger_dir,
                                   logger_name=logger_name)
        print(f"#stock_ids: {len(stock_ids)} -> #strategys: {len(strategys)}, performance_filter: {performance_filter}")
