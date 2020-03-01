#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import signal
import logging
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
from byx_util import ByxUtil
from byx_util import CallingPointManager
from byx_util import PluginManager
from byx_dbus import DbusMainObject
from byx_dbus import DbusIpForwardObject
from byx_common import ByxConfig
from byx_traffic_manager import ByxTrafficManager
from byx_connection_manager import ByxConnectionManager


class ByxDaemon:

    def __init__(self, param):
        self.param = param
        self.mainloop = None

    def run(self):
        try:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
            logging.getLogger().setLevel(ByxUtil.getLoggingLevel(self.param.logLevel))
            logging.info("Program begins.")

            # manipulate iptables
            if not self.param.abortOnError:
                ByxUtil.iptablesSetEmpty()
            else:
                if not ByxUtil.iptablesIsEmpty():
                    raise Exception("iptables is not empty, bombyx use iptables exclusively")

            # load configuration
            self.param.config = ByxConfig(self.param)
            logging.info("Configuration loaded.")

            # write pid file
            with open(self.param.pidFile, "w") as f:
                f.write(str(os.getpid()))

            # create main loop
            DBusGMainLoop(set_as_default=True)
            self.mainloop = GLib.MainLoop()

            # start supporting managers
            self.param.callingPointManager = CallingPointManager()
            self.param.pluginManager = PluginManager(self.param.libPluginDir)

            # start DBUS API server
            self.param.dbusMainObject = DbusMainObject(self.param)
            self.param.dbusIpForwardObject = DbusIpForwardObject(self.param)
            logging.info("DBUS-API server started.")

            # business initialize
            self.param.trafficManager = ByxTrafficManager(self.param)
            self.param.connectionManager = ByxConnectionManager(self.param)
            self.param.daemon = self

            # start main loop
            logging.info("Mainloop begins.")
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, self._sigHandlerINT, None)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self._sigHandlerTERM, None)
            self.mainloop.run()
            logging.info("Mainloop exits.")
        finally:
            if self.param.connectionManager is not None:
                self.param.connectionManager.dispose()
                self.param.connectionManager = None
            logging.shutdown()

    def _sigHandlerINT(self, signum):
        logging.info("SIGINT received.")
        self.mainloop.quit()
        return True

    def _sigHandlerTERM(self, signum):
        logging.info("SIGTERM received.")
        self.mainloop.quit()
        return True
