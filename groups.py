

class CommandGroup():
    def __init__(self, prefix, action='set'):
        self.prefix = prefix
        self.rules = []
        self.action = action

    def append(self, rule):
        assert self.prefix == '' or rule.startswith(self.prefix + " "), \
                f"Rule doesn't match group prefix. Prefix: {self.prefix}, rule: {rule}"
        self.rules.append(rule)

    def is_changed(self, other):
        return True
