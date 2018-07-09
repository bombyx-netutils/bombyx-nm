#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import json
import dbus
import dbus.service
import logging
from byx_common import ByxState


################################################################################
# DBus API Docs
################################################################################
#
# ==== Main Application ====
# Service               org.fpemud.Bombyx
# Interface             org.fpemud.Bombyx
# Object path           /
#
# Methods:
#   (state:int,health:int)      GetState()
#   info:json                   GetActiveConnection()
#   info:json                   GetConnections()
#
# Methods:
#   void            Enable()
#   void            Disable()
#   void            EnableNetworkType(network_type:str)
#   void            DisableNetworkType(network_type:str)
#   void            EnableAutoActivate()
#   void            DisableAutoActivate()
#   void            Activate(connection_id:str)
#   void            Deactiveate()
#
# Signals:
#                   StateChanged(state:int, connection_id:str)         # not implemented
#

class DbusMainObject(dbus.service.Object):

    def __init__(self, param):
        self.param = param
        self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

        # register dbus object path
        bus_name = dbus.service.BusName('org.fpemud.Bombyx', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/fpemud/Bombyx')

    def release(self):
        self.remove_from_connection()

    @dbus.service.method('org.fpemud.Bombyx', out_signature='ii')
    def GetState(self):
        cm = self.param.connectionManager
        state = cm.get_state()
        if state == ByxState.ACTIVE:
            health = cm.get_connection_data(cm.get_current_connection_id())["health"]
        else:
            health = -1
        return (state, health)

    @dbus.service.method('org.fpemud.Bombyx', out_signature='s')
    def GetActiveConnection(self):
        cm = self.param.connectionManager
        if cm.get_state() != ByxState.ACTIVE:
            ret = None
        else:
            ret = cm.get_connection_data(cm.get_current_connection_id())
        return json.dumps(ret)

    @dbus.service.method('org.fpemud.Bombyx', out_signature='s')
    def GetConnections(self):
        ret = []
        for cid in self.param.connectionManager.get_connection_id_list():
            ret.append(self.param.connectionManager.get_connection_data(cid))
        return json.dumps(ret)

    @dbus.service.method('org.fpemud.Bombyx')
    def Enable(self):
        self.param.config.set_enable(True)
        self.param.connectionManager.on_config_changed()

    @dbus.service.method('org.fpemud.Bombyx')
    def Disable(self):
        self.param.config.set_enable(False)
        self.param.connectionManager.on_config_changed()

    @dbus.service.method('org.fpemud.Bombyx', in_signature='s')
    def EnableNetworkType(self, network_type):
        self.param.config.set_enable_network_type(network_type, True)
        self.param.connectionManager.on_config_changed()

    @dbus.service.method('org.fpemud.Bombyx', in_signature='s')
    def DisableNetworkType(self, network_type):
        self.param.config.set_enable_network_type(network_type, False)
        self.param.connectionManager.on_config_changed()

    @dbus.service.method('org.fpemud.Bombyx')
    def EnableAutoActivate(self):
        self.param.config.set_auto_activate(True)
        self.param.connectionManager.on_config_changed()

    @dbus.service.method('org.fpemud.Bombyx')
    def DisableAutoActivate(self):
        self.param.config.set_auto_activate(False)
        self.param.connectionManager.on_config_changed()

    @dbus.service.method('org.fpemud.Bombyx', in_signature='s')
    def Activate(self, connection_id_id):
        self.param.connectionManager.deactivate()
        self.param.connectionManager.activate(connection_id_id)

    @dbus.service.method('org.fpemud.Bombyx')
    def Deactiveate(self):
        self.param.connectionManager.deactivate()

    @dbus.service.signal('org.fpemud.Bombyx', signature='is')
    def StateChanged(self, state, reason):
        pass


################################################################################
# DBus API Docs
################################################################################
#
# ==== Main Application ====
# Service               org.fpemud.IpForward
# Interface             org.fpemud.IpForward
# Object path           /
#
# Methods:
# void                  On()
# void                  Off()
#

class DbusIpForwardObject(dbus.service.Object):

    def __init__(self, param):
        # implement a fake IpForward object, since we always set ip_forward to 1
        bus_name = dbus.service.BusName('org.fpemud.IpForward', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/fpemud/IpForward')

    def release(self):
        self.remove_from_connection()

    @dbus.service.method('org.fpemud.IpForward')
    def On(self):
        pass

    @dbus.service.method('org.fpemud.IpForward')
    def Off(self):
        pass
