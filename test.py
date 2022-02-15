from abc import ABCMeta, abstractmethod


class Parent:
    def __init__(self):
        self.val = 5

    def __del__(self):
        print("Parent __del__")

    def get(self):
        return self.val


class Interface(metaclass=ABCMeta):
    @abstractmethod
    def get(self):
        pass


class Child(Parent):
    def __init__(self):
        super().__init__()

    def __del__(self):
        super().__del__()


child = Child()
print(child.get())
