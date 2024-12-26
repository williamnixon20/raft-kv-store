class KVStore:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key, "")

    def set(self, key, value):
        if(value is None):
            self.store[key] = ""
        else :
            self.store[key] = value
        return "OK"

    def strln(self, key):
        return len(self.get(key))

    def delete(self, key):
        return self.store.pop(key, "")

    def append(self, key, value):
        if key not in self.store or self.store[key] is None:
            self.store[key] = ""
        elif self.store[key] is None: 
            print("[APPEND IS NONE]")
            self.store[key] = ""
        self.store[key] += value
        return "OK"

    def get_all(self):
        return self.store
