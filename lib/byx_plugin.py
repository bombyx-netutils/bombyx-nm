#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import libxml2
from byx_param import ByxParam


class ByxPluginManager:

    def __init__(self, param):
        self.param = param
        self.pluginDict = dict()

    def loadPlugins(self):
        for fn in os.listdir(self.param.libPluginDir):
            path = os.path.join(self.param.libPluginDir, fn)

            # get metadata.xml file
            metadata_file = os.path.join(path, "metadata.xml")
            if not os.path.exists(metadata_file):
                raise LoadPluginException("plugin %s has no metadata.xml" % (fn))                 # FIXME: one plugin fail should not affect others
            if not os.path.isfile(metadata_file):
                raise LoadPluginException("metadata.xml for plugin %s is not a file" % (fn))
            if not os.access(metadata_file, os.R_OK):
                raise LoadPluginException("metadata.xml for plugin %s is invalid" % (fn))

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
                raise LoadPluginException("invalid \"id\" property in metadata.xml for plugin %s" % (fn))

            # create plugin object
            obj = Plugin(self.param, fn, path, root)
            self.pluginDict[root.prop("id")].append(obj)

    def getPluginIdList(self, pluginType=None):
        if pluginType is None:
            return list(self.pluginDict.keys())
        else:
            return [x.id for x in self.pluginDict.values() if x.type == pluginType]

    def getPlugin(self, pluginId):
        return self.pluginDict[pluginId]


class Plugin:

    def __init__(self, param, pluginId, pluginDir, rootElem):
        self.id = pluginId
        self.type = rootElem.prop("type")
        self.singleton = (rootElem.prop("singleton") == "True")
        self.filename = rootElem.xpathEval(".//filename")[0].getContent()
        self.classname = rootElem.xpathEval(".//classname")[0].getContent()

    def getSingletonIntance(self, *kargs):
        pass

    def getInstance(self, instanceName, *kargs):
        modname = os.path.join(self.pObj.param.libPluginDir, cfg.get("main", "plugin"))
        modname = modname[len(self.pObj.param.libDir + "/"):]
        modname = modname.replace("/", ".")
        exec("from %s import Plugin" % (modname))
        code = ""
        code += "Plugin(self.pObj.param.tmpDir, path,"
        code += "       lambda: self.pObj.on_connection_available(self),"
        code += "       lambda reason: self.pObj.on_connection_unavailable(self, reason))"
        return eval(code)


class LoadPluginException(LoadPluginException):
    # FIXME: change name to LoadPluginError?
    pass
