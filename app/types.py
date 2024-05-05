
class CustomDict(dict):
    ''' Allows for Dot Notation Access to Dictionary References '''

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class class_property(property):
    def __get__(self, _, owner_cls):
        return self.fget(owner_cls)
