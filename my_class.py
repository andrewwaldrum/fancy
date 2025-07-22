# my_class.py
class MyClass:
    def __init__(self, path):
        self.path = path

    def greet(self, name):
        return f"Hello {name}, path is {self.path}"

    def add(self, a, b):
        return int(a) + int(b)