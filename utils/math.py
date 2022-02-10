from collections import defaultdict

import numpy as np


def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    return np.exp(x) / np.sum(np.exp(x), axis=0)


def origin(x):
    return x


def relu(x):
    return np.maximum(0, x)


def sigmoid(x):
    y = 1 / (1 + np.exp(-x))
    return y


def absFunc(x):
    y = np.abs(x)
    return y


def geometricMean(numbers):
    """
    幾何平均: 數值全部相乘後，開數值個數的次方根(sqrt)

    利用'數值相乘'等於'對數相加'的特性，將所有數值轉為對數後相加，再利用指數還原數值。
    也因為是利用相加來計算，因此能大幅度避免溢位問題。

    注意: 若 numbers 當中有 0，將產生錯誤 RuntimeWarning: divide by zero encountered in log

    :param numbers: 要計算
    :return:
    """
    logs = np.log(numbers)

    return np.exp(np.mean(logs))


def getCubicInterpolation(points, x):
    """
    cubic interpolation
    參考網站: https://www.paulinternet.nl/?page=bicubic

    f(x) = ax^3 + bx^2 + cx + d
    f'(x) = 3ax^2 + 2bx + c
    令 p0: x = -1, p1: x = 0, p2: x = 1, p3: x = 2

    f(0) = d = p1
    f(1) = a + b + c + d = p2
    f'(0) = c = (p2 - p0) / 2
    f'(1) = 3a + 2b + c = (p3 - p1) / 2

    a = (-0.5p0 + 1.5p1 - 1.5p2 + 0.5p3)
    b = (p0 - 2.5p1 + 2p2 - 0.5p3)
    c = (-0.5p0 + 0.5p2)
    d = p1

    f(p0, p1, p2, p3, x) = (-0.5p0 + 1.5p1 - 1.5p2 + 0.5p3)x^3 + (p0 - 2.5p1 + 2p2 - 0.5p3)x^2 + (-0.5p0 + 0.5p2)x + p1
    :param points:
    :param x:
    :return:
    """
    a = -0.5 * points[0] + 1.5 * points[1] - 1.5 * points[2] + 0.5 * points[3]
    b = points[0] - 2.5 * points[1] + 2 * points[2] - 0.5 * points[3]
    c = -0.5 * points[0] + 0.5 * points[2]
    d = points[1]

    return a * np.power(x, 3) + b * np.power(x, 2) + c * x + d


class SparseBayes:
    def __init__(self, label: list, alpha: float, **kwargs):
        self.label = label
        self.n_label = len(self.label)
        self.feature = kwargs
        self.feature_list = []

        # 組合總數
        self.n_combination = self.n_label

        for key, value in kwargs.items():
            self.feature_list.append(key)
            self.n_combination *= len(value)

        self.alpha = alpha

        self.counter_dict = defaultdict(self.zero)

    @staticmethod
    def zero():
        return 0

    @staticmethod
    def dataFormer(raw_data):
        data = []

        for raw in raw_data:
            temp = ""
            for r in raw:
                temp += str(r)

            data.append(temp)

        return data

    def fit(self, data, label):
        for d_i, l_i in zip(data, label):
            tag = str(l_i)

            for d_j in d_i:
                tag += str(d_j)

            self.counter_dict[tag] += 1

    def predictProbablility(self, data):
        target = ""

        for d in data:
            target += str(d)

        numerators = [self.alpha for _ in range(len(self.label))]
        n_denominator = 0

        for key, value in self.counter_dict.items():
            if key.endswith(target):
                n_denominator += value

                # 取得第 1 個位置的類別，在 self.label 當中的索引值
                index = self.label.index(eval(key[0]))

                # 計算各個 label 的個數
                numerators[index] += value

        np_numerators = np.array(numerators)
        n_denominator += self.alpha * self.n_label
        probablility = np_numerators / n_denominator

        return probablility

    def prdeict(self, data):
        probablility = self.predictProbablility(data=data)

        # TODO: 機率相同時，先到先得
        index = int(np.argmax(probablility))

        return self.label[index]

    def predictProbablilityAndFit(self, data, label):
        probablility = self.predictProbablility(data=data)
        self.fit(data, label)

        return probablility

    def predictAndFit(self, data, label):
        prdeict_label = self.prdeict(data=data)
        self.fit(data, label)

        return prdeict_label


if __name__ == "__main__":
    num = 50
    x = np.random.randint(2, size=(num, 3))
    y = np.random.randint(3, size=(num,))

    model = SparseBayes(alpha=0.5, label=list(range(3)), f1=list(range(2)), f2=list(range(2)), f3=list(range(2)))
    model.fit(data=x, label=y)

    data = [0, 1, 0]
    probablility = model.predictProbablility(data=data)
    print(f"p(label|{data}): {probablility}")
    print(model.prdeict(data=[0, 1, 0]))
