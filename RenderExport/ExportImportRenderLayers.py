#######################################
##                                   ##
##  Timothy Halim Septianjaya        ##
##  http://www.timo.ink              ##
##  Render Layer Export Import       ##
##  Created for Infinite Studio      ##
##  Batam, Indonesia                 ##
##  2018                             ##
##                                   ##
#######################################
'''
Usage:
for export:
    export_render_layers(xmlPath, renderLayers=['nameOfLayers', 'etc'], openFolder=False)
where:
    xmlPath: is the destination path for xml file
    renderLayers: by default will export all renderLayer in scene if provided it will export only the render layer in the list. 
    openFolder: by default set to False, if True, will open the folder path of xml file.

for import:
    import_render_layers(xmlPath, renderLayers=['nameOfLayers', 'etc'], attributes=['members', 'layerOverrides', 'shaderOverrides'])
where:
    xmlPath: is the source path for xml file
    renderLayers: if provided it will import only the list of render layer. The list should contain name of render layer inside the xml
    attributes: if provided it will import only the attributes provided.
'''

from maya import cmds, mel
import subprocess, os, sys
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

from Iris.Common.Maya.Scripts.Timo import MayaCommand
reload(MayaCommand)

def export_render_layers(xmlPath, renderLayers=[], openFolder=False):
    if renderLayers:
        renderLayers = list(renderLayers)
    else:
        renderLayers = [rl for rl in cmds.ls (type="renderLayer") if not cmds.referenceQuery( rl, isNodeReferenced=True )]
    if xmlPath:
        if not os.path.exists(os.path.dirname(xmlPath)):
            os.makedirs(os.path.dirname(xmlPath))
        if os.path.isdir("/".join(xmlPath.split("/")[0:-1])):
            if renderLayers:
                root = ET.Element("RenderLayers")
                curRL = cmds.editRenderLayerGlobals( q=True, currentRenderLayer=True ) # Get Current Render Layer
                cmds.refresh(suspend=True) # Pause Viewport
                for renderLayer in renderLayers:
                    cmds.editRenderLayerGlobals( currentRenderLayer=renderLayer ) # Change Current Render Layer
                    layer = ET.SubElement(root, "renderlayer")
                    layer.attrib["name"] = renderLayer
                    layer.attrib["enabled"] = str( cmds.getAttr('%s.renderable' %(renderLayer)) )
                    layer.attrib["layerShader"] = cmds.listConnections('%s.shadingGroupOverride' %renderLayer)[0] if cmds.listConnections('%s.shadingGroupOverride' %renderLayer) else 'None'
                    
                    # Render Layer Members
                    members = cmds.editRenderLayerMembers(renderLayer, q=True, fn=True)
                    if members and not renderLayer == 'defaultRenderLayer':
                        memberList = ET.SubElement(layer, "members")
                        for member in members:
                            memberNode = ET.SubElement(memberList, "member")
                            memberNode.attrib["name"] = '%s' % (member)
                    
                    # Render Layer Overrides
                    layerOverrides = cmds.getAttr( '%s.adjustments' %renderLayer, mi=True )
                    if layerOverrides:
                        overrides = ET.SubElement(layer, "layerOverrides")
                        for layerOverride in layerOverrides:
                            conObj = cmds.listConnections( '%s.adjustments[%s].plug' %(renderLayer, layerOverride), s=True, d=False, p=True )
                            object = conObj[0].split('.')[0] if conObj else None
                            attribute = conObj[0].split('.')[-1] if conObj else None
                            overrideValue = cmds.getAttr ('%s.adjustments[%s].value'  %( renderLayer, layerOverride) )
                            connectto = None
                            # print  '%s : %s.%s = %s' %(renderLayer, object, attribute, overrideValue)
                            if object and attribute:
                                connection = cmds.listConnections('%s.%s' %(object, attribute), s=True, d=False, p=True )
                                if connection:
                                    connectto = connection[0]
                                overrideData = ET.SubElement(overrides, "override")
                                overrideData.attrib["objectName"] = '%s' % (object)
                                overrideData.attrib["attribute"] = '%s' % (attribute)
                                overrideData.attrib["objectType"] = '%s' % (cmds.nodeType(object))
                                overrideData.attrib["value"] = '%s' % (overrideValue)
                                overrideData.attrib["connectto"] = '%s' % (connectto)
                    
                    # Render Layer Shader Overrides
                    shdOverCount = cmds.getAttr( '%s.outAdjustments' %renderLayer, mi=True )
                    if shdOverCount:
                        shdOvrData = ET.SubElement(layer, "shaderOverrides")
                        for shdOvr in shdOverCount:
                            shdGrp = cmds.listConnections( '%s.outAdjustments[%s].outValue' %(renderLayer, shdOvr), s=False, d=True, p=True )[0].split('.')[0]
                            shd =  cmds.listConnections( '%s.surfaceShader' %(shdGrp) )[0]
                            object = cmds.listConnections( '%s.outAdjustments[%s].outPlug' %(renderLayer, shdOvr), p=True )[0]
                            faces = 'None'
                            if 'objectGroups' in object:
                                faces = cmds.getAttr('%s.objectGrpCompList' %object)
                            shaderData = ET.SubElement(shdOvrData, "shader")
                            shaderData.attrib["name"] = '%s' % (shd)
                            shaderData.attrib["engine"] = '%s' % (shdGrp)
                            shaderData.attrib["object"] = '%s' % (object.split('.')[0])
                            shaderData.attrib["faces"] = '%s' % (faces)
                
                cmds.editRenderLayerGlobals( currentRenderLayer=curRL ) # Restore to pervious render layer
                cmds.refresh(suspend=False) # Resume Viewport
                
                tostring = ET.tostring(root)
                domObject = parseString(tostring)
                domObject.toprettyxml(encoding='utf-8')
                file_handle = open(xmlPath, "w")
                domObject.writexml(file_handle, addindent='\t', newl='\n')
                file_handle.close()
        if openFolder:
            subprocess.Popen(r'explorer /select,'+(xmlPath).replace("/", "\\"))

def import_render_layers(xmlPath, renderLayers=[], attributes=[]):
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
                renderLayer = xmlNode.attrib.get("name")
                resume = False
                if renderLayers and renderLayer in renderLayers:
                    resume = True
                elif not renderLayers:
                    resume = True
                
                if resume:
                    renderLayerEnable = xmlNode.attrib.get("enabled")
                    layerShader = xmlNode.attrib.get("layerShader") if xmlNode.attrib.get("layerShader") != 'None' else None
                    nodes = xmlNode.getchildren()
                    
                    members = []
                    layerOverrides = []
                    vopOverrides = []
                    shaderOverrides = []
                    for node in nodes:
                        if node.tag == 'members' and node.tag in attributes:
                            memberList = node
                            for member in memberList:
                                name = member.attrib.get("name")
                                if cmds.objExists(name):
                                    maObj = cmds.ls(name)
                                    for o in maObj:
                                        members.append(o)
                                
                        if node.tag == 'layerOverrides' and node.tag in attributes:
                            ovrXML = node
                            for layerOverride in ovrXML:
                                objectName = layerOverride.attrib.get("objectName")
                                attribute = layerOverride.attrib.get("attribute")
                                objectType = layerOverride.attrib.get("objectType")
                                value = layerOverride.attrib.get("value")
                                connectto = layerOverride.attrib.get("connectto") 
                                connectto = connectto if connectto and connectto != 'None' else None
                                layerOverrides.append(('%s.%s' %(objectName, attribute), value, connectto))
                                    
                        if node.tag == 'shaderOverrides' and node.tag in attributes:
                            shdXML = node
                            for shaderOverride in shdXML:
                                shader = shaderOverride.attrib.get("name")
                                shadingEngine = shaderOverride.attrib.get("engine")
                                object = shaderOverride.attrib.get("object")
                                faces = shaderOverride.attrib.get("faces")
                                shaderOverrides.append((shader, shadingEngine, object, faces))
                    
                    Layer = MayaCommand.Layer(
                        renderLayer,
                        over_write = False,
                        objects = members,
                        layer_overrides=layerOverrides,
                        layer_shader=layerShader
                    )
                    
                    if cmds.editRenderLayerGlobals( q=True, currentRenderLayer=True ) == renderLayer:
                        for data in shaderOverrides:
                            shader = data[0]
                            engine = data[1]
                            object = data[2]
                            faces = eval(data[3])
                            objects = []
                            if faces:
                                for face in faces:
                                    objects.append('%s.%s' %(object, face))
                                    
                            else:
                                objects = list(object)
                            
                            cmds.sets (objects, edit=True, forceElement=engine)
                        
                    rle = True if renderLayerEnable == 'True' else False
                    cmds.setAttr('%s.renderable' %(renderLayer), rle)
                
# xmlPath = 'C:/Users/timothy.septianjaya/Documents/Local/RL.xml'
# export_render_layers(xmlPath, renderLayers=[])
# import_render_layers(xmlPath, renderLayers=['CH'])
# import_render_layers(xmlPath, renderLayers=[])

