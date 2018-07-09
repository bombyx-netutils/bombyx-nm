#!/usr/bin/env python3


class ByxNetworkType:
    WIRED = "wired"
    WIRELESS = "wireless"
    MOBILE = "mobile"


class ByxState:
    IDLE = 0
    ACTIVE = 1
    ACTIVATING = 2
    DEACTIVATING = 3


class ByxHealth:
    BAD = 0
    AVERAGE = 1
    GOOD = 2


class ByxConfig:

    def __init__(self, param):
        self.param = param

        self.enable = True
        self.enableNetworkType = {
            "wired": True,
            "wireless": True,
            "mobile": True,
        }
        self.priority = 1
        self.autoActivate = True

    def get_enable(self):
        return self.enable

    def set_enable(self, value):
        assert isinstance(value, bool)
        self.enable = value

    def get_enable_network_type(self, network_type):
        return self.enableNetworkType[network_type]

    def set_enable_network_type(self, network_type, value):
        assert network_type in self.enableNetworkType
        assert isinstance(value, bool)
        self.enableNetworkType[network_type] = value

    def get_priority(self):
        return self.priority

    def get_auto_activate(self):
        return self.autoActivate

    def set_auto_activate(self, value):
        assert isinstance(value, bool)
        self.autoActivate = value

    def _load(self):
        pass

    def _save(self):
        pass
