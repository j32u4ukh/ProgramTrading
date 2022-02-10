import numpy as np
from scipy import stats


def descriptiveStatistics(data, title=None) -> str:
    """

    :param data:
    :param title:
    :return: 敘述性統計
    """
    if title is None:
        title = "敘述性統計"

    description = "===== {} =====".format(title)

    if len(data) == 0:
        description = "{}\n數據筆數為 0，故無法進行敘述統計。".format(description)
        return description

    np_data = np.array(data)
    description = "{}\n平均數:\t{}".format(description, np.mean(np_data))

    n_data = len(np_data)
    if n_data <= 1:
        description = "{}\n標準誤:\t{}".format(description, np.std(np_data))
    else:
        description = "{}\n標準誤:\t{}".format(description, np.std(np_data, ddof=1))

    description = "{}\n中間值:\t{}".format(description, np.median(np_data))

    try:
        mod_value = stats.mode(np_data)[0][0]
        description = "{}\n眾數:\t{}".format(description, mod_value)
    except IndexError:
        description = "{}\n眾數:\t{}".format(description, "-")
    except ValueError:
        description = "{}\n眾數:\t{}".format(description, "-")

    description = "{}\n標準差:\t{}".format(description, np.std(np_data))
    description = "{}\n變異數:\t{}".format(description, np.var(np_data))

    skew = stats.skew(np_data)
    description = "{}\n偏態:\t{}".format(description, skew)

    kurtosis = stats.kurtosis(np_data)
    description = "{}\n峰度:\t{}".format(description, kurtosis)

    max_value = np.max(np_data)
    min_value = np.min(np_data)
    description = "{}\n最大值:\t{}".format(description, max_value)
    description = "{}\n最小值:\t{}".format(description, min_value)

    description = "{}\n範圍:\t{}".format(description, max_value - min_value)
    description = "{}\n總和:\t{}".format(description, np.sum(np_data))
    description = "{}\n個數:\t{}".format(description, n_data)

    return description


def simpleDescriptiveStatistics(data, title=None):
    """

    :param data:
    :param title:
    :return: 簡化版敘述性統計
    """
    if title is None:
        title = "簡化版敘述性統計"

    description = "===== {} =====".format(title)

    np_data = np.array(data)
    n_data = len(np_data)

    description = "{}\n平均數:\t{}".format(description, np.mean(np_data))
    description = "{}\n中間值:\t{}".format(description, np.median(np_data))
    description = "{}\n標準差:\t{}".format(description, np.std(np_data))
    description = "{}\n變異數:\t{}".format(description, np.var(np_data))
    max_value = np.max(np_data)
    min_value = np.min(np_data)
    description = "{}\n最大值:\t{}".format(description, max_value)
    description = "{}\n最小值:\t{}".format(description, min_value)
    description = "{}\n個數:\t{}".format(description, n_data)

    return description


def getKurtosis(data):
    np_data = np.array(data)
    mean = np.mean(np_data)
    x = np_data - mean
    power4 = np.array(list([4 for _ in range(len(np_data))]))
    power2 = np.array(list([2 for _ in range(len(np_data))]))
    mu4 = np.mean(np.power(x, power4))
    sigma2 = np.mean(np.power(x, power2))
    sigma4 = np.power(sigma2, 2.0)
    kurtosis = mu4 / sigma4 - 3
    return kurtosis


def getSkew(data):
    np_data = np.array(data)
    mean = np.mean(np_data)
    x = np_data - mean
    power3 = np.array(list([3 for _ in range(len(np_data))]))
    power2 = np.array(list([2 for _ in range(len(np_data))]))
    mu3 = np.mean(np.power(x, power3))
    sigma2 = np.mean(np.power(x, power2))
    sigma3 = np.power(sigma2, 1.5)
    skew = mu3 / sigma3
    return skew


def decilePercentage(data, title=None, reverse=False, min_quantile=5, max_quantile=10):
    """
    min_quantile=5, max_quantile=10 表示表示將數據分為 10 份，從第 5 份開始累計百分比與呈現數據。

    :param data: 數據
    :param title: 標題
    :param reverse: 是否反向排序
    :param min_quantile: 分位數從幾開始呈現
    :param max_quantile: 最大分位數，若為 10 表示將數據分為十份
    :return:
    """
    if title is None:
        title = "數值累計百分比"

    description = f"===== {title} ====="

    if len(data) == 0:
        description += "\n數據筆數為 0 筆，不足以進行 decilePercentage"
        return description

    # 排序
    data.sortFilter(reverse=reverse)

    # 轉換為 numpy array
    data = np.array(data)

    length = len(data)
    if length < max_quantile:
        max_quantile = length
        min_quantile = 0

    for i in range(min_quantile, max_quantile):
        # 取得該分位數的索引值
        idx = int(length * i / max_quantile * 1.0)
        
        # 取得該分位數的數值
        value = data[idx]

        # 小於當前數值的數據個數
        n_count = np.sum(np.where(data <= value, 1, 0))

        # 添加資訊進入 description
        description = "{}\n{:.2f}% 數據於 {} 以內".format(description, n_count / length * 100.0, value)

    value = data[-1]
    description = "{}\n數據最大值為 {}，數據平均值為 {}".format(
        description, value, np.mean(data))

    return description


if __name__ == "__main__":
    data = []
    # for _ in range(2000):
    #     val = random.normalvariate(0, 1)
    #     data.append(val)

    description = descriptiveStatistics(data)
    print(description)

    pos = [d for d in data if d > 0]
    neg = [d for d in data if d < 0]
    description = descriptiveStatistics(pos, title="pos")
    print(description)
    description = descriptiveStatistics(neg, title="neg")
    print(description)
