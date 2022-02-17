from abc import ABCMeta, abstractmethod

from submodule.Xu3.database import DataBase as Xu3DataBase


def sqlGtPrice(value):
    return Xu3DataBase.sqlGt(key="CAST(PRICE as decimal)", value=value)


def sqlGePrice(value):
    return Xu3DataBase.sqlGe(key="CAST(PRICE as decimal)", value=value)


def sqlEqPrice(value):
    return Xu3DataBase.sqlEq(key="CAST(PRICE as decimal)", value=value)


def sqlNePrice(value):
    return Xu3DataBase.sqlNe(key="CAST(PRICE as decimal)", value=value)


def sqlLePrice(value):
    return Xu3DataBase.sqlLe(key="CAST(PRICE as decimal)", value=value)


def sqlLtPrice(value):
    return Xu3DataBase.sqlLt(key="CAST(PRICE as decimal)", value=value)


""" NOTE: 有必要額外寫介面嗎？ """


class IDayOhlcData(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    def getDay(self):
        pass


class IMinuteOhlcData(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    def getMinute(self):
        pass
