#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import json
import iptc
import logging
import pyroute2
import subprocess
import configparser
from gi.repository import Gio
from byx_util import ByxUtil


class ByxNtfacGroup:

    def __init__(self, param, activeInfo, ntfacNameList):
        self.param = param
        self.activeInfo = activeInfo
        self.logger = logging.getLogger(self.__module__ + "." + self.__class__.__name__)

        self.ntfacDict = dict()                 # dict<ntfac-name, ntfac-info>
        for ntfacName in ntfacNameList:
            self.ntfacDict[ntfacName] = _NtfacInfo(ntfacName, os.path.join(self.param.etcNtfacDir, ntfacName))

        self.stdoutDict = dict()                # dict<stdout, ntfac-name>
        self.stderrDict = dict()                # dict<stderr, ntfac-name>
        self.idTypeDict = dict()                # dict<id, type>

        self.hostManager = _HostManager(self.param)

        self.dnsServ = _Level2DnsServer(self.param)
        if "default-nameserver" in self.activeInfo:
            self.dnsServ.nameServerNewAsDefault("main", self.param.priority, self.activeInfo["default-nameserver"])
        i = 0
        for ns in self.activeInfo.get("nameserver-list", []):
            id = "main" if i == 0 else "main-%d" % (i)
            self.dnsServ.nameServerNew(id, self.param.priority, ns["target"], ns["domain-list"])
            i += 1

        self.gatewayManager = _GatewayManager(self.param)
        if "default-gateway" in self.activeInfo:
            self.gatewayManager.gatewayNewAsDefault("main", self.param.priority, self.activeInfo["default-gateway"])
        i = 0
        for gw in self.activeInfo.get("gateway-list", []):
            id = "main" if i == 0 else "main-%d" % (i)
            self.dnsServ.gatewayNew(id, self.param.priority, gw["target"], gw["network-list"])
            i += 1

        try:
            self.dnsServ.start()
            self.logger.info("Level 2 nameserver started.")

            self.gatewayManager.start()
            self.logger.info("Gateway manager started.")

            for ntfacName, ntfacInfo in self.ntfacDict.items():
                ntfacInfo.proc = Gio.subprocess(Gio.Subprocess.Flags.STDOUT_PIPE | Gio.Subprocess.Flags.STDERR_PIPE,
                                                ntfacInfo.execPath, *ntfacInfo.paramList)
                self.stdoutDict[ntfacInfo.proc.get_stdout_pipe()] = ntfacName
                self.stderrDict[ntfacInfo.proc.get_stderr_pipe()] = ntfacName
                ntfacInfo.proc.get_stdout_pipe().read_line_async(0, None, self._onReceive)        # fixme: 0 should be PRIORITY_DEFAULT, but I can't find it
                ntfacInfo.proc.get_stderr_pipe().read_async(0, None, self._on_error)              # fixme: 0 should be PRIORITY_DEFAULT, but I can't find it
                self.logger.info("Network traffic facility %s started." % (ntfacName))
        except BaseException:
            self._dispose()
            raise

    def dispose(self):
        self._dispose()

    def get_l2_nameserver_port(self):
        return self.dnsServ.dnsPort

    def _dispose(self):
        for ntfacName, ntfacInfo in self.ntfacDict.items():
            ntfacInfo.proc.send_signal(15)    # SIGTERM
            ntfacInfo.proc.wait()
            ntfacInfo.proc = None
            self.logger.info("Network traffic facility %s terminated." % (ntfacName))

        self.gatewayManager.stop()
        self.logger.info("Gateway manager stopped.")

        self.dnsServ.stop()
        self.logger.info("Level 2 nameserver stopped.")

    def _onReceive(self, source_object, res):
        try:
            line, len = source_object.read_line_finish_utf8(res)
            if line is None:
                raise Exception("socket closed by peer")

            jsonObj = json.loads(line)
            if jsonObj["operation"] == "new":
                if jsonObj["type"] == "host":
                    self.hostManager.hostNew(jsonObj["id"], self.ntfacDict[self.stdoutDict[source_object]].priority,
                                             jsonObj["data"]["hostname"], jsonObj["data"]["address"])
                elif jsonObj["type"] == "nameserver":
                    self.dnsServ.nameServerNew(jsonObj["id"], self.ntfacDict[self.stdoutDict[source_object]].priority,
                                               jsonObj["data"]["target"], jsonObj["data"]["domain-list"])
                elif jsonObj["type"] == "gateway":
                    self.gatewayManager.gatewayNew(jsonObj["id"], self.ntfacDict[self.stdoutDict[source_object]].priority,
                                                   jsonObj["data"]["target"], jsonObj["data"]["network-list"])
                elif jsonObj["type"] == "default-nameserver":
                    self.dnsServ.nameServerNewAsDefault(jsonObj["id"], self.ntfacDict[self.stdoutDict[source_object]].priority,
                                                        jsonObj["data"]["target"])
                elif jsonObj["type"] == "default-gateway":
                    self.dnsServ.gatewayNewAsDefault(jsonObj["id"], self.ntfacDict[self.stdoutDict[source_object]].priority,
                                                     jsonObj["data"]["target"])
                else:
                    raise Exception("invalid message")
                self.idTypeDict[jsonObj["id"]] = jsonObj["type"]
            elif jsonObj["operation"] == "update":
                if self.idTypeDict[jsonObj["id"]] == "host":
                    self.hostManager.hostUpdate(jsonObj["id"], jsonObj["data"]["address"])
                elif self.idTypeDict[jsonObj["id"]] == "nameserver":
                    self.dnsServ.nameServerUpdate(jsonObj["id"], jsonObj["data"]["domain-list"])
                elif self.idTypeDict[jsonObj["id"]] == "gateway":
                    self.gatewayManager.gatewayUpdate(jsonObj["id"], jsonObj["data"]["network-list"])
                else:
                    raise Exception("invalid message")
            elif jsonObj["operation"] == "delete":
                if self.idTypeDict[jsonObj["id"]] == "host":
                    self.hostManager.hostDelete(jsonObj["id"])
                elif self.idTypeDict[jsonObj["id"]] in ["nameserver", "default-nameserver"]:
                    self.dnsServ.nameServerDelete(jsonObj["id"])
                elif self.idTypeDict[jsonObj["id"]] in ["gateway", "default-gateway"]:
                    self.gatewayManager.gatewayDelete(jsonObj["id"])
                else:
                    raise Exception("invalid message")
                del self.idTypeDict[jsonObj["id"]]
            else:
                raise Exception("invalid message")

            self.dis.read_line_async(0, None, self._onReceive)
        except Exception as e:
            assert False

    def _onEror(self, source_object, res):
        assert False


class _NtfacInfo:

    def __init__(self, ntfacName, ntfacPath):
        # static data
        self.execPath = None
        self.paramList = []
        self.priority = None

        # dynamic data
        self.proc = None

        # initialize static data
        self._initStaticData(ntfacName, ntfacPath)

    def _initStaticData(self, ntfacName, ntfacPath):
        if not os.path.exists(ntfacPath):
            raise Exception("invalid network traffic facility %s" % (ntfacName))

        iniFile = os.path.join(ntfacPath, "ntfac.ini")
        if not os.path.exists(iniFile):
            raise Exception("invalid network traffic facility %s" % (ntfacName))

        cfg = configparser.SafeConfigParser()
        cfg.read(iniFile)

        if not cfg.has_option("main", "exec"):
            raise Exception("invalid network traffic facility %s" % (ntfacName))
        self.execPath = int(cfg.get("main", "exec"))

        for i in range(1, 10):
            if not cfg.has_option("main", "param%d" % (i)):
                break
            p = cfg.get("main", "param%d" % (i))
            p = p.replace("${CFG_DIR}", ntfacPath)
            self.paramList.append(p)

        if not cfg.has_option("main", "priority"):
            raise Exception("invalid network traffic facility %s" % (ntfacName))
        self.priority = int(cfg.get("main", "priority"))


class _HostManager:

    def __init__(self, param):
        self.param = param

    def hostNew(self, id, priority, hostname, address):
        assert False

    def hostUpdate(self, id, address):
        assert False

    def hostDelete(self, id):
        assert False


class _Level2DnsServer:

    def __init__(self, param):
        self.param = param
        self.cfgFile = os.path.join(self.param.tmpDir, "l2-dnsmasq.conf")
        self.pidFile = os.path.join(self.param.tmpDir, "l2-dnsmasq.pid")

        self.dnsServerDict = dict()                     # dict<id, (priority, target)>
        self.defaultDnsServerDict = dict()              # dict<id, (priority, target)>

        self.dataFullDict = _IdPriorityKeyValueDict()

        self.dnsPort = None
        self.dnsmasqProc = None

    def start(self):
        self.dnsPort = ByxUtil.getFreeSocketPort("tcp")
        self._runDnsmasq()

    def stop(self):
        if not self._isStarted():
            return
        self._stopDnsmasq()
        self.dnsPort = None

    def nameServerNew(self, id, priority, target, domainList):
        if id in self.dnsServerDict:
            raise Exception("namserver \"%s\" duplicates")

        self.dnsServerDict[id] = (priority, target)
        for domain in domainList:
            self.dataFullDict.set_priority_key_value(id, priority, domain, target)
        if self._isStarted():
            self._stopDnsmasq()
            self._runDnsmasq()

    def nameServerNewAsDefault(self, id, priority, target):
        if id in self.defaultDnsServerDict:
            raise Exception("default namserver \"%s\" duplicates")

        self.defaultDnsServerDict[id] = (priority, target)
        if self._isStarted():
            self._stopDnsmasq()
            self._runDnsmasq()

    def nameServerUpdate(self, id, domainList):
        assert id in self.dnsServerDict
        self.dataFullDict.remove_by_id(id)
        for domain in domainList:
            self.dataFullDict.set_priority_key_value(id, self.dnsServerDict[id][0], domain, self.dnsServerDict[id][1])
        if self._isStarted():
            self._stopDnsmasq()
            self._runDnsmasq()

    def nameServerDelete(self, id):
        if id in self.defaultDnsServerDict:
            del self.defaultDnsServerDict[id]
        elif id in self.dnsServerDict:
            self.dataFullDict.remove_by_id(id)
            del self.dnsServerDict[id]
        else:
            assert False
        if self._isStarted():
            self._stopDnsmasq()
            self._runDnsmasq()

    def _runDnsmasq(self):
        # select default nameserver
        defaultDnsServerPriority = 0
        defaultDnsServerTarget = None
        for id, value in self.defaultDnsServerDict.items():
            if value[0] >= defaultDnsServerPriority:
                defaultDnsServerPriority = value[0]
                defaultDnsServerTarget = value[1]

        # generate dnsmasq config file
        buf = ""
        buf += "strict-order\n"
        buf += "bind-interfaces\n"                            # don't listen on 0.0.0.0
        buf += "interface=lo\n"
        buf += "user=root\n"
        buf += "group=root\n"
        buf += "\n"
        buf += "domain-needed\n"
        buf += "bogus-priv\n"
        buf += "\n"
        buf += "no-hosts\n"
        buf += "\n"
        buf += "no-resolv\n"
        for target in defaultDnsServerTarget:
            buf += "server=%s\n" % (target.replace(":", "#"))
        for domain, nsList in self.dataFullDict.get_dict(defaultDnsServerPriority + 1).items():
            for ns in nsList:
                buf += "server=/%s/%s\n" % (domain, ns.replace(":", "#"))
        buf += "\n"
        with open(self.cfgFile, "w") as f:
            f.write(buf)

        # run dnsmasq process
        cmd = "/usr/sbin/dnsmasq"
        cmd += " --keep-in-foreground"
        cmd += " --port=%d" % (self.dnsPort)
        cmd += " --conf-file=\"%s\"" % (self.cfgFile)
        cmd += " --pid-file=%s" % (self.pidFile)
        self.dnsmasqProc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

    def _stopDnsmasq(self):
        self.dnsmasqProc.terminate()
        self.dnsmasqProc.wait()
        self.dnsmasqProc = None
        ByxUtil.forceDelete(self.pidFile)
        ByxUtil.forceDelete(self.cfgFile)

    def _isStarted(self):
        return self.dnsPort is not None


class _GatewayManager:

    def __init__(self, param):
        self.param = param

        self.gatewayDict = dict()               # dict<id, (priority, target)>
        self.defaultGatewayDict = dict()        # dict<id, (priority, target)>

        self.routeFullDict = _IdPriorityKeyValueDict()
        self.routeDict = dict()                 # dict<prefix, data>

        self.isStarted = False

    def start(self):
        self._refreshRoutes()
        for priority, target in self.defaultGatewayDict.values():
            self._addGatewayFwRules(target[1])
        for priority, target in self.gatewayDict.values():
            self._addGatewayFwRules(target[1])
        self.isStarted = True

    def stop(self):
        if not self.isStarted:
            return
        self._refreshRoutes()
        for priority, target in self.defaultGatewayDict.values():
            self._deleteGatewayFwRules(target[1])
        for priority, target in self.gatewayDict.values():
            self._deleteGatewayFwRules(target[1])
        self.isStarted = False

    def gatewayNew(self, id, priority, target, networkList):
        assert "0.0.0.0/0.0.0.0" not in networkList

        # record gateway information
        self.gatewayDict[id] = (priority, target)

        # update routes
        for prefix in networkList:
            self.routeFullDict.set_priority_key_value(id, priority, prefix, target)
        self._refreshRoutes()

        # update iptables
        assert target[1] is not None
        self._addGatewayFwRules(target[1])

    def gatewayNewAsDefault(self, id, priority, target):
        # record gateway information
        self.defaultGatewayDict[id] = (priority, target)

        # update routes
        self._refreshRoutes()

        # update iptables
        assert target[1] is not None
        self._addGatewayFwRules(target[1])

    def gatewayUpdate(self, id, networkList):
        # update routes, no need to update iptables
        self.routeFullDict.remove_by_id(id)
        for prefix in networkList:
            self.routeFullDict.set_priority_key_value(id, self.gatewayDict[id][0], prefix, self.gatewayDict[id][1])
        self._refreshRoutes()

    def gatewayDelete(self, id):
        if id in self.defaultGatewayDict:
            self._refreshRoutes()
            self._deleteGatewayFwRules(self.defaultGatewayDict[id][1])
            del self.defaultGatewayDict[id]
        else:
            self.routeFullDict.remove_by_id(id)
            self._refreshRoutes()
            self._deleteGatewayFwRules(self.gatewayDict[id][1])
            del self.gatewayDict[id]

    def _refreshRoutes(self):
        # select default gateway
        defaultGatewayPriority = 0
        defaultGatewayTarget = None
        for id, value in self.defaultGatewayDict.items():
            if value[0] >= defaultGatewayPriority:
                defaultGatewayPriority = value[0]
                defaultGatewayTarget = value[1]

        if defaultGatewayTarget is not None:
            with pyroute2.IPRoute() as ipp:
                try:
                    ipp.route("del", dst=_Helper.prefixConvert("0.0.0.0/0.0.0.0"))
                except pyroute2.netlink.exceptions.NetlinkError as e:
                    if e.code == 3:     # message: No such process
                        pass            # route does not exist, ignore
                    else:
                        raise
        else:
            pass

        newRouteDict = self.routeFullDict.get_dict()
        with pyroute2.IPRoute() as ipp:
            # remove routes
            for prefix in self.routeDict:
                if prefix not in newRouteDict:
                    try:
                        ipp.route("del", dst=_Helper.prefixConvert(prefix))
                    except pyroute2.netlink.exceptions.NetlinkError as e:
                        if e.code == 3:     # message: No such process
                            pass            # route does not exist, ignore
                        else:
                            raise

            # add or change routes
            for prefix, data in list(newRouteDict.items()):
                nexthop, interface = data
                if interface is not None:
                    idx_list = ipp.link_lookup(ifname=interface)
                    if idx_list == []:
                        del newRouteDict[prefix]
                        continue
                    assert len(idx_list) == 1
                    idx = idx_list[0]
                try:
                    if prefix not in self.routeDict:                                    # add
                        if nexthop is not None and interface is not None:
                            ipp.route("add", dst=_Helper.prefixConvert(prefix), gateway=nexthop, oif=idx)
                        elif nexthop is not None and interface is None:
                            ipp.route("add", dst=_Helper.prefixConvert(prefix), gateway=nexthop)
                        elif nexthop is None and interface is not None:
                            ipp.route("add", dst=_Helper.prefixConvert(prefix), oif=idx)
                        else:
                            assert False
                    else:                                                               # change
                        pass        # fixme
                except pyroute2.netlink.exceptions.NetlinkError as e:
                    if e.code == 17:                    # message: File exists
                        del newRouteDict[prefix]        # route already exists, retry in next cycle
                    elif e.code == 101:                 # message: Network is unreachable
                        del newRouteDict[prefix]        # nexthop is invalid, retry in next cycle
                    else:
                        raise
        self.routeDict = newRouteDict

    def _addGatewayFwRules(self, interface):
        filterTable = iptc.Table(iptc.Table.FILTER)
        natTable = iptc.Table(iptc.Table.NAT)
        for rule in self.__generateGatewayFwRulesFilterInputChain(interface):
            iptc.Chain(filterTable, "INPUT").append_rule(rule)
        for rule in self.__generateGatewayFwRulesNatPostChain(interface):
            iptc.Chain(natTable, "POSTROUTING").append_rule(rule)

    def _deleteGatewayFwRules(self, interface):
        filterTable = iptc.Table(iptc.Table.FILTER)
        natTable = iptc.Table(iptc.Table.NAT)
        for rule in self.__generateGatewayFwRulesFilterInputChain(interface):
            iptc.Chain(filterTable, "INPUT").delete_rule(rule)
        for rule in self.__generateGatewayFwRulesNatPostChain(interface):
            iptc.Chain(natTable, "POSTROUTING").delete_rule(rule)

    def __generateGatewayFwRulesFilterInputChain(self, gateway):
        ret = []

        rule = iptc.Rule()
        rule.in_interface = gateway
        rule.protocol = "icmp"
        rule.create_target("ACCEPT")
        ret.append(rule)

        rule = iptc.Rule()
        rule.in_interface = gateway
        match = iptc.Match(rule, "state")
        match.state = "ESTABLISHED,RELATED"
        rule.add_match(match)
        rule.create_target("ACCEPT")
        ret.append(rule)

        rule = iptc.Rule()
        rule.in_interface = gateway
        rule.create_target("DROP")
        ret.append(rule)

        return ret

    def __generateGatewayFwRulesNatPostChain(self, gateway):
        rule = iptc.Rule()
        rule.out_interface = gateway
        rule.create_target("MASQUERADE")
        return [rule]


class _IdPriorityKeyValueDict:

    def __init__(self):
        self.dictImpl = dict()

    def set_priority_key_value(self, id, priority, key, value):
        assert 0 <= priority <= 100
        if key not in self.dictImpl:
            self.dictImpl[key] = dict()
        if priority not in self.dictImpl[key]:
            self.dictImpl[key][priority] = dict()
        self.dictImpl[key][priority][id] = value

    def remove_by_id(self, id):
        ret = set()
        for key in list(self.dictImpl.keys()):
            for priority in list(self.dictImpl[key].keys()):
                if id in self.dictImpl[key][priority]:
                    del self.dictImpl[key][priority][id]
                    ret.add(key)
                    if len(self.dictImpl[key][priority]) == 0:
                        del self.dictImpl[key][priority]
                        if len(self.dictImpl[key]) == 0:
                            del self.dictImpl[key]
        return ret

    def get_dict(self, min_priority=0):
        ret = dict()
        for key, data in self.dictImpl.items():
            priority = sorted(list(data.keys()))[0]
            if priority >= min_priority:
                id = sorted(list(data[priority].keys()))[0]
                ret[key] = data[priority][id]
        return ret


class _Helper:

    @staticmethod
    def prefixConvert(prefix):
        tl = prefix.split("/")
        return tl[0] + "/" + str(ByxUtil.ipMaskToLen(tl[1]))
