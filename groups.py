
class CommandGroup():
    def __init__(self, prefix, action='set'):
        self.prefix = prefix
        self.rules = []
        self.action = action

    def append(self, rule):
        assert self.prefix == '' or rule.startswith(self.prefix + " "), \
                f"Rule doesn't match group prefix. Prefix: {self.prefix}, rule: {rule}"
        self.rules.append(f"{self.action} {rule}")

    def is_changed(self, other):
        if self.prefix == '':
            return True

        old = filter(lambda x: x.startswith(f"set {self.prefix} "), other)

        new_sorted = sorted(self.rules)
        old_sorted = sorted(old)

        return old_sorted != new_sorted
