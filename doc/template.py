#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


# plugin modname: conn_*
class TemplateConnectionPlugin:

    def __init__(self, tmp_dir, available_callback, unavailable_callback):
        # about available_callback:
        #   1. self.do_activate() must not be called in available_callback()
        #   2. self.deactivate() must not be called in available_callback()
        # about unavailable_callback:
        #   1. self.deactivate() is executed BEFORE unavailable_callback() is triggered, so it must not be called in unavailable_callback()
        #   2. self.do_activate() must not be called in unavailable_callback()
        assert False

    def dispose(self):
        assert False

    @property
    def network_type(self):
        # returns "wired", "wireless" or "mobile"
        assert False

    @property
    def business_attributes(self):
        # returns technical related business attributes:
        # {
        #    "bandwidth": 10,           # unit: KB/s, no key means bandwidth is unknown
        #    "billing": "traffic",      # values: "traffic" or "time", no key means no billing
        # }
        assert False

    def trigger_available_test(self):
        assert False

    def do_activate(self):
        # this function would be called in a thread, cancel_activate() is to cancel it.
        # returns {
        #    "managed-interfaces": ["ifname"],
        #    "managed-devices": ["devname"],
        #    "default-nameserver": ["hostname" or "hostname:port"],
        #    "default-gateway": ("nexthop", "interface"),
        #    "nameserver-list": [{
        #        "target": ["hostname" or "hostname:port"],
        #        "domain-list": ["domain"],
        #    }],
        #    "gateway-list": [{
        #        "target": ("next-hop","interface"),                               # one of them can be null
        #        "network-list": ["18.0.0.0/255.0.0.0","19.0.0.0/255.0.0.0"],
        #    }],
        # }
        assert False

    def cancel_activate(self):
        assert False

    def deactivate(self):
        assert False
