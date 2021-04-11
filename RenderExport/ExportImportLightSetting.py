#######################################
##                                   ##
##  Timothy Halim Septianjaya        ##
##  http://www.timo.ink              ##
##  Light Data Export Import         ##
##  Created for Infinite Studio      ##
##  Batam, Indonesia                 ##
##  2018                             ##
##                                   ##
#######################################
'''
Usage:
for export:
    export_light_data(xmlPath, lightShapes=[], openFolder=False)
where:
    xmlPath: is the destination path for xml file
    lightShapes: by default will export all light in scene if provided it will export the lights in the list. 
        The provided list should contain the light shape name not the transform name (e.g EXT_LGT:AmbientShape)
    openFolder: by default set to False, if True, will open the folder path of xml file.

for import:
    import_light_data(xmlPath, lightShapes=[], attributes = ['transforms', 'connections', 'attributes', 'illuminated', 'shadowed'])
where:
    xmlPath: is the source path for xml file
    lightShapes: if provided it will import only the list of light. The list should contain name of light inside the xml
    attributes: if provided it will import only the attributes provided.
'''

from maya import cmds, mel
import subprocess, os, sys
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

from Iris.Common.Maya.Scripts.Timo import MayaCommand
reload(MayaCommand)

def export_light_data(xmlPath, lightShapes=[], openFolder=False):
    if lightShapes:
        lights = list(lightShapes)
    else:
        lights = []
        lightTypes = cmds.listNodeTypes( 'light' )
        for lightType in lightTypes:
            lights += cmds.ls(type=lightType, long=True)
    
    if xmlPath:
        if not os.path.exists(os.path.dirname(xmlPath)):
            os.makedirs(os.path.dirname(xmlPath))
        if os.path.isdir("/".join(xmlPath.split("/")[0:-1])):
            root = ET.Element("Lights")
            for light in lights:
                lightData = ET.SubElement(root, "light")
                lightData.attrib["name"] = light
                lightData.attrib["type"] = cmds.nodeType(light)
                
                transformObj = cmds.listRelatives(light, parent=True, fullPath=True)[0]
                transformAttrs = cmds.listAttr(transformObj)
                transforms = ET.SubElement(lightData, "transforms")
                transforms.attrib["name"] = '%s' % (transformObj)
                for attr in transformAttrs:
                    value = None
                    try:
                        value = cmds.getAttr('%s.%s' %(transformObj, attr))
                    except Exception as args:
                        #print args
                        pass
                    
                    if value:
                        transformData = ET.SubElement(transforms, "transform")
                        transformData.attrib["name"] = '%s' % (attr)
                        transformData.attrib["value"] = '%s' % (value)
                
                targets = []
                if cmds.listConnections(light, d=False, s=True, p=True):
                    targets = [target for target in cmds.listConnections(light, d=False, s=True, p=True) if cmds.nodeType(target) != 'renderLayer']
                if targets:
                    connList = ET.SubElement(lightData, "connections")
                    for target in targets:
                        source = cmds.listConnections(target, d=True, s=False, p=True)[0].split('.')[-1]
                        con = ET.SubElement(connList, "connection")
                        con.attrib["target"] = '%s' % (target)
                        con.attrib["name"] = '%s' % (source)
                
                attrs = cmds.listAttr(light)
                attributes = ET.SubElement(lightData, "attributes")
                for attr in attrs:
                    value = None
                    try:
                        value = cmds.getAttr('%s.%s' %(light, attr), silent=True)
                        #print attr, value
                        attrData = ET.SubElement(attributes, "attribute")
                        attrData.attrib["name"] = '%s' % (attr)
                        attrData.attrib["value"] = '%s' % (value)
                    except Exception as args:
                        #print args
                        pass
                
                IlluminatedObject = cmds.lightlink(q=True, light=light, shapes=False)
                cmds.select(IlluminatedObject)
                IlluminatedObject = cmds.ls(sl=1, long=True)
                cmds.select(cl=True)
                illumobj = ET.SubElement(lightData, "illuminated")
                for obj in IlluminatedObject:
                    illData = ET.SubElement(illumobj, "object")
                    illData.attrib["name"] = '%s' % (obj)
            
                ShadowedObject = cmds.lightlink(q=True, light=light, shapes=False, shadow=True)
                cmds.select(ShadowedObject)
                ShadowedObject = cmds.ls(sl=1, long=True)
                cmds.select(cl=True)
                shdobj = ET.SubElement(lightData, "shadowed")
                for obj in ShadowedObject:
                    shdData = ET.SubElement(shdobj, "object")
                    shdData.attrib["name"] = '%s' % (obj)

            tostring = ET.tostring(root)
            domObject = parseString(tostring)
            domObject.toprettyxml(encoding='utf-8')
            file_handle = open(xmlPath, "w")
            domObject.writexml(file_handle, addindent='\t', newl='\n')
            file_handle.close()
        if openFolder:
            subprocess.Popen(r'explorer /select,'+(xmlPath).replace("/", "\\"))

def import_light_data(xmlPath, lightShapes=[], attributes=[]):
    if os.path.exists(xmlPath):
        xmlRoot = None
        try:
            tree = ET.parse(xmlPath)
            root = tree.getroot()
            xmlRoot = root.getchildren()
        except Exception as e:
            raise Exception("%s is not a valid xml file" % xmlPath)
        
        if not attributes:
            attributes = ['transforms', 'connections', 'attributes', 'illuminated', 'shadowed']
        
        if xmlRoot:
            for xmlNode in xmlRoot:
                lightNode = xmlNode.attrib.get("name")
                nodes = xmlNode.getchildren()
                resume = False
                if lightShapes and lightNode in lightShapes:
                    resume = True
                elif not lightShapes:
                    resume = True
                if resume:
                    if cmds.objExists(lightNode):
                        illuminatedObject = []
                        shadowedObject = []
                        connectedAttr = []
                        for node in nodes:
                            if node.tag == 'transforms' and node.tag in attributes:
                                objTransform = node.attrib.get("name")
                                for transform in node:
                                    attrname = '%s.%s' %( objTransform, transform.attrib.get("name") )
                                    attrvalue = transform.attrib.get("value")
                                    if cmds.objExists(objTransform):
                                        MayaCommand.set_attribute(attrname, attrvalue)
                                
                            elif node.tag == 'connections' and node.tag in attributes:
                                for attribute in node:
                                    attrname = '%s.%s' %( lightNode, attribute.attrib.get("name") )
                                    targetAttr = attribute.attrib.get("target")
                                    targetObj = targetAttr.split('.')[0]
                                    connectedAttr.append(attrname)
                                    if cmds.objExists(lightNode) and cmds.objExists(targetObj):
                                        if not cmds.isConnected(targetAttr, attrname):
                                            cmds.connectAttr(targetAttr, attrname)
                                            print '%s connected to %s' %(attrname, targetAttr)
                                            
                            elif node.tag == 'attributes' and node.tag in attributes:
                                for attribute in node:
                                    attrname = '%s.%s' %( lightNode, attribute.attrib.get("name") )
                                    attrvalue = attribute.attrib.get("value")
                                    if cmds.objExists(lightNode) and not attrname in connectedAttr:
                                        MayaCommand.set_attribute(attrname, attrvalue)
                                        
                            elif node.tag == 'illuminated' and node.tag in attributes:
                                for obj in node:
                                    name = obj.attrib.get("name")
                                    if cmds.objExists(name):
                                        illuminatedObject.append(name)
                                    
                            elif node.tag == 'shadowed' and node.tag in attributes:
                                for obj in node:
                                    name = obj.attrib.get("name")
                                    if cmds.objExists(name):
                                        shadowedObject.append(name)
                        
                        if illuminatedObject:
                            cmds.lightlink( m=True, light=lightNode, object=illuminatedObject )
                        if shadowedObject:
                            cmds.lightlink( m=True, light=lightNode, object=shadowedObject, shadow=True, )

# xmlPath = 'C:/Users/timothy.septianjaya/Documents/Local/LGT.xml'
# export_light_data(xmlPath, lightShapes=[])
# import_light_data(xmlPath, lightShapes=[], attributes=['transforms', 'connections', 'attributes', 'illuminated', 'shadowed'])