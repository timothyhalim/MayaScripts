#######################################
##                                   ##
##  Timothy Halim Septianjaya        ##
##  http://www.timo.ink              ##
##  Render Settings Export Import    ##
##  Created for Infinite Studio      ##
##  Batam, Indonesia                 ##
##  2018                             ##
##                                   ##
#######################################
'''
Usage:
for export:
    export_render_settings(xmlPath, openFolder=False)
where:
    xmlPath: is the destination path for xml file
    openFolder: by default set to False, if True, will open the folder path of xml file.

for import:
    import_render_settings(xmlPath, renderSettings=['defaultRenderGlobals','vraySettings'], attributes=['attribute'])
where:
    xmlPath: is the source path for xml file
    renderLayers: if provided it will import only the provided node ('defaultRenderGlobals' or 'vraySettings' or both)
    attributes: if provided it will import only the attributes provided.
'''


from maya import cmds, mel
import subprocess, os, sys
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

from Iris.Common.Maya.Scripts.Timo import MayaCommand
reload(MayaCommand)

def export_render_settings(xmlPath, renderSettings=[], openFolder=False):
    cmds.editRenderLayerGlobals( currentRenderLayer='defaultRenderLayer' )
    if renderSettings:
        renderLayers = list(renderSettings)
    else:
        renderSettings = ['defaultRenderGlobals','vraySettings','redshiftOptions']
    if xmlPath:
        if not os.path.exists(os.path.dirname(xmlPath)):
            os.makedirs(os.path.dirname(xmlPath))
        if os.path.isdir("/".join(xmlPath.split("/")[0:-1])):
            print xmlPath
            if renderSettings:
                root = ET.Element("RenderSettings")
                
                # Get Current Renderer
                renderSetting = 'defaultRenderGlobals'
                attribute = 'currentRenderer'
                setting = ET.SubElement(root, "settings")
                setting.attrib["name"] = 'defaultRenderGlobals'
                attributeElement = ET.SubElement(setting, "attribute")
                attributeElement.attrib["name"] = '%s' % (attribute)
                attributeElement.attrib["value"] = str( cmds.getAttr('%s.%s' %(renderSetting, attribute)) )
                attributeElement.attrib["type"] = str( cmds.getAttr('%s.%s' %(renderSetting, attribute), type=True) )
                
                for renderSetting in renderSettings:
                    setting = ET.SubElement(root, "settings")
                    setting.attrib["name"] = renderSetting
                    cmds.select(renderSetting)
                    attributes = cmds.listAttr( r=True, s=True )
                    for attribute in attributes:
                        attributeElement = ET.SubElement(setting, "attribute")
                        attributeElement.attrib["name"] = '%s' % (attribute)
                        attributeElement.attrib["value"] = str( cmds.getAttr('%s.%s' %(renderSetting, attribute)) )
                        attributeElement.attrib["type"] = str( cmds.getAttr('%s.%s' %(renderSetting, attribute), type=True) )
                
                tostring = ET.tostring(root)
                domObject = parseString(tostring)
                domObject.toprettyxml(encoding='utf-8')
                file_handle = open(xmlPath, "w")
                domObject.writexml(file_handle, addindent='\t', newl='\n')
                file_handle.close()
        if openFolder:
            print xmlPath
            subprocess.Popen(r'explorer /select,'+(xmlPath).replace("/", "\\"))

def import_render_settings(xmlPath, renderSettings=[], attributes=['attribute']):
    if os.path.exists(xmlPath):
        xmlRoot = None
        try:
            tree = ET.parse(xmlPath)
            root = tree.getroot()
            xmlRoot = root.getchildren()
        except Exception as e:
            raise Exception("%s is not a valid xml file" % xmlPath)
        
        if not attributes:
            attributes = ['members', 'layerOverrides', 'shaderOverrides']
        
        if xmlRoot:
            for xmlNode in xmlRoot:
                nodeName = xmlNode.attrib.get("name")
                specificxmlNode = xmlNode
                
                resume = False
                if renderSettings and nodeName in renderSettings:
                    resume = True
                elif not renderSettings:
                    resume = True
                    
                if resume:
                    attribElements = specificxmlNode.getchildren()
                    specificPresetName = specificxmlNode.attrib.get("name")
                    
                    for attribElement in attribElements:
                        attribName = attribElement.attrib.get("name")
                        attribValue = attribElement.attrib.get("value")
                        
                        setAttribute = MayaCommand.set_attribute('%s.%s' %(specificPresetName, attribName), attribValue)

#xmlPath = 'C:/Users/timothy.septianjaya/Documents/Local/tes.xml'
#export_render_settings(xmlPath)
#import_render_settings(xmlPath)
