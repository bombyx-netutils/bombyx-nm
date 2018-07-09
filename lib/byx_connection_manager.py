#!/usr/bin/env python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import glob
import logging
import threading
import configparser
from byx_common import ByxState
from byx_common import ByxNetworkType
from byx_ntfac_group import ByxNtfacGroup


class ByxConnectionManager:

    def __init__(self, param):
        self.param = param
        self.connList = []
        self.curConn = None

        # create connection list
        self._loadConnectionList(self.param.varConnectionDir)
        self._loadConnectionList(self.param.etcConnectionDir)

    def dispose(self):
        if self.curConn is not None:
            self._deactivateConn(self.curConn)
        for conn in self.connList:
            conn.dispose()

    def get_state(self):
        if self.curConn is not None:
            if self.curConn.activateThread is None:
                return ByxState.ACTIVE
            else:
                return ByxState.ACTIVATING
        else:
            return ByxState.IDLE

    def get_connection_id_list(self):
        return [x.id for x in self.connList]

    def get_current_connection_id(self):
        if self.curConn is not None:
            return self.curConn.id
        else:
            return None

    def get_connection_data(self, connection_id):
        conn = self._getConnectionById(connection_id)
        ret = dict()
        ret["id"] = conn.id
        if conn.name is not None:
            ret["name"] = conn.name
        ret["available"] = conn.isAvailable
        return ret

    def activate(self, connection_id):
        conn = self._getConnectionById(connection_id)
        if not conn.isAvailable:
            raise Exception("connection is not available")

        if self.curConn is not None:
            self._deactivateConn(self.curConn, False)
        self._activateConn(conn, True)

    def deactivate(self):
        if self.curConn is not None:
            self._deactivateConn(self.curConn, False)

    def get_managed_interface_list(self):
        if self.curConn is not None:
            if self.curConn.activeInfo is not None:
                if "managed-interfaces" in self.curConn.activeInfo:
                    return self.curConn.activeInfo["managed-interfaces"]
        return []

    def _getConnectionById(self, connection_id):
        for conn in self.connList:
            if conn.id == connection_id:
                return conn
        return None

    def on_config_changed(self):
        cfg = self.param.config

        # network is disabled, deactivate current connection
        if self.curConn is not None and not cfg.get_enable():
            self._deactivateConn(self.curConn, False)
            return

        # corresponding network type is disabled, deactivate current connection and try to select and activate another
        if self.curConn is not None and not cfg.get_enable_network_type(self.curConn.networkType):
            self._deactivateConn(self.curConn, False)
            self._selectAndActivate()
            return

        # no network connection, try to select and activate a connection
        if self.curConn is None:
            self._selectAndActivate()
            return

    def on_connection_available(self, connection):
        logging.info("Connection %s becomes available." % (connection.id))

        connection.isAvailable = True
        connection.unavailableReason = None

        # new connection has higher priority, switch to it
        if self.curConn is not None and not self.curConn.manualActive:
            if _connPriorityCmp(connection, self.curConn) > 0 and connection.autoActivate:
                if self.param.get_enable_network_type(connection.networkType):
                    self._deactivateConn(self.curConn, False)
                    self._activateConn(connection, False)
                    return

        # no current connection, try to select and activate the new connection
        if self.curConn is None:
            self._selectAndActivate()
            return

    def on_connection_unavailable(self, connection, reason):
        logging.info("Connection %s becomes unavailable." % (connection.id))

        bHasOldConn = False
        if self.curConn == connection:
            bHasOldConn = True
            self._deactivateConn(connection, False)

        connection.isAvailable = False
        connection.unavailableReason = reason

        if self.curConn is None and bHasOldConn:
            self._selectAndActivate()

    def _activateConn(self, connection, manualActive):
        assert self.curConn is None
        self.curConn = connection
        self.curConn.activate(manualActive)

    def _deactivateConn(self, connection, alreadyUnavailable):
        assert self.curConn is not None and connection == self.curConn
        self.curConn.deactivate(alreadyUnavailable)
        self.curConn = None

    def _selectAndActivate(self):
        assert self.curConn is None
        if not self.param.config.get_enable():
            return
        for netType in [ByxNetworkType.WIRED, ByxNetworkType.WIRELESS, ByxNetworkType.MOBILE]:
            if not self.param.config.get_enable_network_type(netType):
                continue
            tlist = [x for x in self.connList if x.networkType == netType and x.autoActivate]
            if len(tlist) > 0:
                tlist.sort(_connPriorityCmp)
                self._activateConn(tlist[0], False)
                return

    def _loadConnectionList(self, connDir):
        if os.path.exists(connDir):
            for fn in os.listdir(connDir):
                path = os.path.join(connDir, fn)
                if os.path.isdir(path):
                    self.connList.append(_Connection(self, path))


class _Connection:

    def __init__(self, pObj, path):
        self.pObj = pObj

        # static data
        self.id = None
        self.name = None
        self.priority = None
        self.networkType = None
        self.autoActivate = None
        self.ntfacDict = dict()

        # dynamic data
        self.isAvailable = False
        self.unavailableReason = None
        self.manualActive = None
        self.activeThread = None
        self.activeInfo = None              # valid when connection is active
        self.ntfacGroup = None              # valid when connection is active

        fn = os.path.join(path, "connection.ini")
        if not os.path.exists(fn):
            raise Exception("invalid connection configuration file %s" % (fn))

        cfg = configparser.SafeConfigParser()
        cfg.read(fn)
        self._initStaticData(fn, cfg)
        self._initNtfacDict(path)

        self.plugin = None
        if True:
            if not cfg.has_option("main", "plugin"):
                raise Exception("invalid connection configuration file %s" % (fn))
            if not cfg.get("main", "plugin").startswith("conn_"):
                raise Exception("invalid connection configuration file %s" % (fn))
            modname = os.path.join(self.pObj.param.libPluginDir, cfg.get("main", "plugin"))
            modname = modname[len(self.pObj.param.libDir + "/"):]
            modname = modname.replace("/", ".")
            exec("from %s import Plugin" % (modname))
            code = ""
            code += "Plugin(self.pObj.param.tmpDir, path,"
            code += "       lambda: self.pObj.on_connection_available(self),"
            code += "       lambda reason: self.pObj.on_connection_unavailable(self, reason))"
            self.plugin = eval(code)

        assert self.plugin.network_type in [ByxNetworkType.WIRED, ByxNetworkType.WIRELESS, ByxNetworkType.MOBILE]
        if self.networkType is None:
            self.networkType = self.plugin.network_type

    def dispose(self):
        assert self.activeThread is None
        assert self.activeInfo is None
        assert self.ntfacGroup is None
        self.plugin.dispose()

    def activate(self, manualActive):
        assert self.activeInfo is None and self.activateThread is None
        self.manualActive = manualActive
        self.activateThread = _ConnActivateThread(self)
        self.activateThread.start()

    def deactivate(self, alreadyUnavailable):
        if self.activateThread is not None:
            self.activateThread.stop()
            self.activateThread.join()
            self.activateThread = None

        if self.ntfacGroup is not None:
            self.ntfacGroup.dispose()
            self.ntfacGroup = None

        self.activeInfo = None
        if not alreadyUnavailable:
            self.plugin.deactivate()
        with open("/etc/resolv.conf", "w") as f:
            f.write("")
        self.manualActive = None

        logging.info("Connection %s deactivated." % (self.id))

    def _initStaticData(self, fn, cfg):
        self.id = os.path.basename(fn)
        if cfg.has_option("main", "name"):
            self.name = cfg.get("main", "name")
        if cfg.has_option("main", "priority"):
            self.priority = int(cfg.get("main", "priority"))
            if not (0 <= self.priority <= 10):
                raise Exception("invalid connection configuration file %s" % (fn))
        if cfg.has_option("main", "network-type"):
            self.networkType = bool(cfg.get("main", "network-type"))
        if cfg.has_option("main", "auto-activate"):
            self.autoActivate = bool(cfg.get("main", "auto-activate"))

    def _initNtfacDict(self, path):
        # global ntfac
        for fn in glob.glob(os.path.join(self.pObj.param.etcNtfacDir, "*.ntfac")):
            cfg = configparser.SafeConfigParser()
            cfg.read(fn)
            self.ntfacDict[cfg.get("main", "name")] = 10

        # local ntfac
        for fn in glob.glob(os.path.join(os.path.dirname(path), "*.ntfac")):
            cfg = configparser.SafeConfigParser()
            cfg.read(fn)
            self.ntfacDict[cfg.get("main", "name")] = 10


class _ConnActivateThread(threading.Thread):

    def __init__(self, param, pObj):
        self.param = param
        self.pObj = pObj
        self.bStop = False

    def run(self):
        try:
            # manipulate /etc/resolv.conf
            with open("/etc/resolv.conf", "w") as f:
                f.write("# Generated by bombyx\n")
                f.write("nameserver 127.0.0.1\n")
            if self.bStop:
                return

            # manipulate connection
            self.pObj.activeInfo = self.pObj.plugin.do_activate()
            if self.bStop:
                return

            # manipulate ntfac group
            self.pObj.ntfacGroup = ByxNtfacGroup(self.param, self.pObj.activeInfo, self.pObj.ntfacDict)
            if self.bStop:
                return

            logging.info("Connection %s activated." % (self.pObj.id))
        finally:
            self.pObj.activateThread = None

    def stop(self):
        self.bStop = True
        self.pObj.cancel_activate()


def _connPriorityCmp(conn1, conn2):
    pdict = {
        ByxNetworkType.WIRED: 3,
        ByxNetworkType.WIRELESS: 2,
        ByxNetworkType.MOBILE: 1,
    }
    if pdict[conn1.networkType] > pdict[conn2.networkType]:
        return 1
    elif pdict[conn1.networkType] < pdict[conn2.networkType]:
        return -1

    if conn1.priority > conn2.priority:
        return 1
    elif conn1.priority < conn2.priority:
        return -1

    return 0
