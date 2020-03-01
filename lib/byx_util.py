#!/usr/bin/python3

import os
import iptc
import socket
import shutil
import libxml2
import logging


class ByxUtil:

    @staticmethod
    def getLoggingLevel(logLevel):
        if logLevel == "CRITICAL":
            return logging.CRITICAL
        elif logLevel == "ERROR":
            return logging.ERROR
        elif logLevel == "WARNING":
            return logging.WARNING
        elif logLevel == "INFO":
            return logging.INFO
        elif logLevel == "DEBUG":
            return logging.DEBUG
        else:
            assert False

    @staticmethod
    def iptablesIsEmpty():
        for tname in iptc.Table.ALL:
            table = iptc.Table(tname)
            for chain in table.chains:
                if not table.builtin_chain(chain):
                    return False
                if chain.rules != []:
                    return False
        return True

    @staticmethod
    def iptablesSetEmpty():
        for tname in iptc.Table.ALL:
            table = iptc.Table(tname)
            table.flush()
            for chain in table.chains:
                chain.flush()
        return True

    @staticmethod
    def getFreeSocketPort(portType):
        if portType == "tcp":
            stlist = [socket.SOCK_STREAM]
        elif portType == "udp":
            stlist = [socket.SOCK_DGRAM]
        elif portType == "tcp+udp":
            stlist = [socket.SOCK_STREAM, socket.SOCK_DGRAM]
        else:
            assert False

        for port in range(10000, 65536):
            bFound = True
            for sType in stlist:
                s = socket.socket(socket.AF_INET, sType)
                try:
                    s.bind((('', port)))
                except socket.error:
                    bFound = False
                finally:
                    s.close()
            if bFound:
                return port

        raise Exception("no valid port")

    @staticmethod
    def forceDelete(filename):
        if os.path.islink(filename):
            os.remove(filename)
        elif os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)

    @staticmethod
    def mkDirAndClear(dirname):
        ByxUtil.forceDelete(dirname)
        os.mkdir(dirname)

    @staticmethod
    def ensureDir(dirname):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    @staticmethod
    def ipMaskToLen(mask):
        """255.255.255.0 -> 24"""

        netmask = 0
        netmasks = mask.split('.')
        for i in range(0, len(netmasks)):
            netmask *= 256
            netmask += int(netmasks[i])
        return 32 - (netmask ^ 0xFFFFFFFF).bit_length()


class DynObject:
    # an object that can contain abitrary dynamically created properties and methods
    pass


class CallingPointManager:

    class CallingPointAlreadyExistException(Exception):
        # FIXME: change name to CallingPointAlreadyExistError?
        pass

    class CallingPointNotExistException(Exception):
        # FIXME: change name to CallingPointAlreadyExistError?
        pass

    def __init__(self):
        self.cpDict = dict()

    def get_calling_point(self, key):
        if key not in self.cpDict:
            raise self.CallingPointManager.CallingPointNotExistException()
        return self.parent.cpDict[key]

    def register_calling_point(self, key, obj):
        if key in self.cpDict:
            raise self.CallingPointAlreadyExistException()
        self.cpDict[key] = obj

    def unregister_calling_point(self, key):
        if key not in self.cpDict:
            raise self.CallingPointNotExistException()
        del self.cpDict[key]


class PluginManager:

    class LoadPluginException(Exception):
        # FIXME: change name to LoadPluginError?
        pass

    def __init__(self, pluginDir):
        self.pluginDict = dict()
        for fn in os.listdir(pluginDir):
            path = os.path.join(pluginDir, fn)

            # get metadata.xml file
            metadata_file = os.path.join(path, "metadata.xml")
            if not os.path.exists(metadata_file):
                raise self.LoadPluginException("plugin %s has no metadata.xml" % (fn))                 # FIXME: one plugin fail should not affect others
            if not os.path.isfile(metadata_file):
                raise self.LoadPluginException("metadata.xml for plugin %s is not a file" % (fn))
            if not os.access(metadata_file, os.R_OK):
                raise self.LoadPluginException("metadata.xml for plugin %s is invalid" % (fn))

            # check metadata.xml file content
            # FIXME
            tree = libxml2.parseFile(metadata_file)
            # if True:
            #     dtd = libxml2.parseDTD(None, constants.PATH_PLUGIN_DTD_FILE)
            #     ctxt = libxml2.newValidCtxt()
            #     messages = []
            #     ctxt.setValidityErrorHandler(lambda item, msgs: msgs.append(item), None, messages)
            #     if tree.validateDtd(ctxt, dtd) != 1:
            #         msg = ""
            #         for i in messages:
            #             msg += i
            #         raise exceptions.IncorrectPluginMetaFile(metadata_file, msg)

            # get data from metadata.xml file
            root = tree.getRootElement()
            if root.prop("id") != fn:
                raise self.LoadPluginException("invalid \"id\" property in metadata.xml for plugin %s" % (fn))
            if fn in self.pluginDict:
                raise self.LoadPluginException("already used \"id\" property in metadata.xml for plugin %s" % (fn))

            # create plugin object
            obj = DynObject()
            obj.id = fn
            obj.type = root.prop("type")
            obj.singleton = (root.prop("singleton") == "True")
            obj.filename = root.xpathEval(".//filename")[0].getContent()
            obj.classname = root.xpathEval(".//classname")[0].getContent()

            # record plugin object
            self.pluginDict[obj.id].append(obj)

    def queryPluginIdList(self, pluginType=None):
        if pluginType is None:
            return list(self.pluginDict.keys())
        else:
            return [x.id for x in self.pluginDict.values() if x.type == pluginType]

    def createIntance(self, pluginId, *kargs):
        assert self.singleton
        return None

    def createInstanceByName(self, pluginId, instanceName, *kargs):
        assert not self.singleton
        return None

        # modname = os.path.join(self.pObj.param.libPluginDir, cfg.get("main", "plugin"))
        # modname = modname[len(self.pObj.param.libDir + "/"):]
        # modname = modname.replace("/", ".")
        # exec("from %s import Plugin" % (modname))
        # code = ""
        # code += "Plugin(self.pObj.param.tmpDir, path,"
        # code += "       lambda: self.pObj.on_connection_available(self),"
        # code += "       lambda reason: self.pObj.on_connection_unavailable(self, reason))"
        # return eval(code)
