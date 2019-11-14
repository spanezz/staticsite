import json
import os
try:
    import lmdb
except ModuleNotFoundError:
    lmdb = None


class lazy_value:
    '''Computes attribute value and caches it in the instance.
    From the Python Cookbook (Denis Otkidach)
    This decorator allows you to create a property which can be computed once and
    accessed many times. Sort of like memoization.
    '''
    def __init__(self, method, name=None):
        # record the unbound-method and the name
        self.method = method
        self.name = name or method.__name__
        self.__doc__ = method.__doc__

    def __get__(self, inst, cls):
        # self: <__main__.cache object at 0xb781340c>
        # inst: <__main__.Foo object at 0xb781348c>
        # cls: <class '__main__.Foo'>
        if inst is None:
            # instance attribute accessed on class, return self
            # You get here if you write `Foo.bar`
            return self
        # compute, cache and return the instance's attribute value
        result = self.method(inst)
        # setattr redefines the instance's attribute so this doesn't get called again
        setattr(inst, self.name, result)
        return result


if lmdb is not None:
    class Cache:
        def __init__(self, fname):
            self.fname = fname + ".lmdb"

        @lazy_value
        def db(self):
            os.makedirs(os.path.dirname(self.fname), exist_ok=True)
            return lmdb.open(self.fname, metasync=False, sync=False)

        def get(self, relpath):
            with self.db.begin() as tr:
                res = tr.get(relpath.encode(), None)
                if res is None:
                    return None
                else:
                    return json.loads(res)

        def put(self, relpath, data):
            with self.db.begin(write=True) as tr:
                tr.put(relpath.encode(), json.dumps(data).encode())
else:
    import dbm

    class Cache:
        def __init__(self, fname):
            self.fname = fname

        @lazy_value
        def db(self):
            os.makedirs(os.path.dirname(self.fname), exist_ok=True)
            return dbm.open(self.fname, "c")

        def get(self, relpath):
            res = self.db.get(relpath)
            if res is None:
                return None
            else:
                return json.loads(res)

        def put(self, relpath, data):
            self.db[relpath] = json.dumps(data)


class DisabledCache:
    """
    noop render cache, for when caching is disabled
    """
    def get(self, relpath):
        return None

    def put(self, relpath, data):
        pass


class Caches:
    """
    Repository of caches that, if kept across site builds, can speed up further
    builds
    """
    def __init__(self, root):
        self.root = root

    def get(self, name):
        return Cache(os.path.join(self.root, name))


class DisabledCaches:
    def get(self, name):
        return DisabledCache()
