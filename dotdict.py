

class dotdict(dict):
    """dot.notation to access dictionary attributes"""

#    def __getattr__(self, name):
#        val = self.get(name)
#        if type(val) is dict:
#            self.__setitem__(name, dotdict(val))
#            return self.__getitem__(name)
#        else:
#            return val

    def __getitem__(self, name):
        val = dict.__getitem__(self, name)
        if type(val) is dict:
            self.__setitem__(name, dotdict(val))
            return self.__getitem__(name)
        else:
            return val
            
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __getattr__ = __getitem__
