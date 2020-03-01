#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class ByxParam:

    def __init__(self):
        self.libDir = "/usr/lib/bombyx"
        self.libPluginDir = os.path.join(self.libDir, "plugins")

        self.runDir = "/run/bombyx"
        self.logDir = "/var/log/bombyx"
        self.tmpDir = "/tmp/bombyx"

        self.varDir = "/var/bombyx"
        self.varConnectionDir = os.path.join(self.varDir, "connections")

        self.etcDir = "/etc/bombyx"
        self.etcConnectionDir = os.path.join(self.etcDir, "connections")
        self.etcNtfacDir = os.path.join(self.etcDir, "ntfacs")

        self.ownResolvConf = os.path.join(self.tmpDir, "resolv.conf")
        self.pidFile = os.path.join(self.runDir, "bombyx.pid")
        self.logLevel = None
        self.abortOnError = False

        self.callingPointManager = None
        self.pluginManager = None

        self.dbusMainObject = None
        self.dbusIpForwardObject = None
        self.config = None
        self.trafficManager = None
        self.connectionManager = None
        self.daemon = None
