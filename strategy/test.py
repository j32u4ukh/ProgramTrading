import numpy as np
from matplotlib import pyplot as plt


def computeCoeff(seed_value=30):
    prices = []
    range_value = 0
    for i in range(50):
        price_range = seed_value * 0.2
        for j in range(4):
            range_value = seed_value + np.random.random() * price_range - (price_range / 2)
            if range_value < 0:
                range_value = 0
            prices.append(range_value)

        seed_value = range_value
        # temp = [seed_value*0.9, seed_value*0.9, seed_value*1.1, seed_value*1.1]
        # np.random.shuffle(temp)
        # prices += temp
        # seed_value = temp[3]

    std_coeff = np.std(prices) / np.mean(prices)

    # 0.5 <= norm_std_coeff < 1
    std_score = 1.0 - std_coeff

    if std_score < 0:
        std_score = 0

    return std_score


coeffs = []
seed = np.random.randint(low=1, high=4000, size=5000)
for s in seed:
    coeff = computeCoeff(seed_value=s)
    coeffs.append(coeff)

print("max:", np.max(coeffs))
print("min:", np.min(coeffs))
x = list(range(len(coeffs)))
plt.hist(coeffs, bins=20)
plt.show()
