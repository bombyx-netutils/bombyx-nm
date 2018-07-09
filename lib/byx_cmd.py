#!/usr/bin/env python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

# Copyright (c) 2005-2014 Fpemud <fpemud@sina.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import json
import dbus
from byx_common import ByxState
from byx_common import ByxHealth


class MainImpl:

    def show_status(self):
        dbusObj = self._getDbusObj()

        state, health = dbusObj.GetState()

        print("-- Active Connection ----")
        if state == ByxState.ACTIVE:
            conn = json.loads(dbusObj.GetActiveConnection(dbus_interface="org.fpemud.Bombyx"))
            print("ID:     %s" % (conn["id"]))
            if "name" in conn:
                print("Name:   %s" % (conn["name"]))
            print("Health: %s" % (self._healthToStr(health)))
        else:
            print("None")
        print("")

        print("-- Connections ----")
        for conn in json.loads(dbusObj.GetConnections(dbus_interface="org.fpemud.Bombyx")):
            s = ""
            s += conn["name"] if "name" in conn else conn["id"]
            print(s)
        print("")

    def enable(self, value):
        if value:
            self._getDbusObj().Enable(dbus_interface="org.fpemud.Bombyx")
        else:
            self._getDbusObj().Disable(dbus_interface="org.fpemud.Bombyx")

    def enable_network_type(self, network_type, value):
        if value:
            self._getDbusObj().EnableNetworkType(network_type, dbus_interface="org.fpemud.Bombyx")
        else:
            self._getDbusObj().DisableNetworkType(network_type, dbus_interface="org.fpemud.Bombyx")

    def activate_connection(self, connection_id):
        self._getDbusObj().Activate(connection_id, dbus_interface="org.fpemud.Bombyx")

    def deactivate_connection(self):
        self._getDbusObj().Deactiveate(dbus_interface="org.fpemud.Bombyx")

    def _getDbusObj(self):
        if not dbus.SystemBus().name_has_owner('org.fpemud.Bombyx'):
            raise Exception("bombyx is not running")
        return dbus.SystemBus().get_object("org.fpemud.Bombyx", "/org/fpemud/Bombyx")

    def _healthToStr(self, health):
        if health == ByxHealth.GOOD:
            return "Good"
        elif health == ByxHealth.AVERAGE:
            return "Average"
        elif health == ByxHealth.BAD:
            return "Bad"
