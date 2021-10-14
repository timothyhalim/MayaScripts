# Colorize Tool by Timothy Halim
# Created for technical director test at Lemon Sky
# 15 June 2021
#
# This tool will disconnect all texture and replace it with constant, 
# and store the connection data in a json file that can be used to restore it later
#
# Install:
# - Copy and paste content to maya script editor, and run it from there
# - Or use type "execfile('[path to this file]')" in script editor and run it
#
# Usage:
# - Get Selected Objects : This button will search all of the texture used for selected objects 
#                         and store the connections in a json file, 
#                         if nothing is selected then it will search all mesh in scene
# - Check Descendants : Enabling this, will search all of texture used for all of selected object descendants
# - Colorize : Will disconnect textures and replace it with constant color in the attribute
# - Restore : Will restore the connections stored in json file

import os
import json
import traceback
from PySide2.QtWidgets import QApplication, QDialog, QVBoxLayout, QPushButton, QCheckBox, QListWidget, QProgressBar
import pymel.core as pm

def undoOn(function):
    def funcCall(*args,**kwargs):
        result = None
        try:
            name = function.__name__
            pm.undoInfo(openChunk=True, chunkName=name)
            result = function( *args,**kwargs )
        except Exception as e:
            print(traceback.format_exc())
            pm.displayError( "Error : %s" %e )
        finally:
            pm.undoInfo(closeChunk=True)
        return result
    return funcCall

class ColorizeTool(QDialog):
    def __init__(self):
        super(ColorizeTool, self).__init__(self.getAppWindow())
        self.closeExistingDialog()
        
        self.setWindowTitle("Colorize Tool")
        self.setObjectName(self.__class__.__name__)
        
        self.buildUI()
        self.connectSignal()
        self.initUI()
        
    def getAppWindow(self):
        for w in QApplication.topLevelWidgets():
            if w.objectName() == 'MayaWindow':
                return w
    
    def closeExistingDialog(self):
        childWidgets = self.parent().findChildren(QDialog)
        for w in childWidgets:
            try:
                if w.objectName() == self.__class__.__name__:
                    if w.isVisible():
                        w.close()
            except:
                pass
    
    def buildUI(self):
        self.masterLayout = QVBoxLayout(self)
        
        self.getObjectButton = QPushButton("Get Selected Objects")
        self.checkHierarchy = QCheckBox("Check Descendants")
        self.checkDominant = QCheckBox("Get Dominant Color (slow)")
        self.progressBar = QProgressBar()
        self.objectListWidget = QListWidget()
        self.colorizeButton = QPushButton("Colorize")
        self.restoreButton = QPushButton("Restore")
        self.deleteButton = QPushButton("Delete Json")
        
        for w in (self.getObjectButton, self.progressBar, self.checkHierarchy, self.checkDominant, 
                self.objectListWidget, self.colorizeButton, self.restoreButton, self.deleteButton):
            self.masterLayout.addWidget(w)
    
    def connectSignal(self):
        self.getObjectButton.clicked.connect(self.getSelectedMesh)
        self.colorizeButton.clicked.connect(self.colorize)
        self.restoreButton.clicked.connect(self.restore)
        self.deleteButton.clicked.connect(self.delete)
    
    def initUI(self):
        self.checkHierarchy.setChecked(True)
        self.checkDominant.setVisible(int(pm.about(version=True)) > 2017)
        self.progressBar.setVisible(False)
        self.checkJson()

        if os.path.isfile(self.getJsonFile()):
            with open(self.getJsonFile(), "r+") as f:
                self.shaderData = json.load(f)
            self.meshes = []
            for k, v in self.shaderData.items():
                self.meshes += pm.ls(v['objects'])
            self.meshes = sorted(set(self.meshes))
            self.objectListWidget.clear()
            self.objectListWidget.addItems([m.name() for m in self.meshes])
    
    def getJsonFile(self):
        currentFile = pm.system.sceneName()
        currentDir = os.path.dirname(currentFile)
        outputName = '.'.join(os.path.basename(currentFile).split('.')[:-1]) + ".json"
        outputFile = os.path.join(currentDir,outputName).replace("\\", "/")
        return outputFile

    def checkJson(self):
        jsonExist = os.path.isfile(self.getJsonFile())
        self.colorizeButton.setEnabled(jsonExist)
        self.restoreButton.setEnabled(jsonExist)
        self.deleteButton.setEnabled(jsonExist)
    
    def getSelectedMesh(self):
        self.objectListWidget.clear()
        
        selection = pm.ls(sl=True)
        if selection:
            self.meshes = []
            for o in selection:
                shape = o.getShape() if hasattr(o, 'getShape') else None
                if shape and shape.nodeType() == 'mesh':
                    self.meshes.append(o)
                
                if self.checkHierarchy.isChecked():
                    childs = pm.listRelatives(o, ad=True)
                    for child in childs:
                        shape = child.getShape() if hasattr(child, 'getShape') else child
                        if shape and shape.nodeType() == 'mesh':
                            self.meshes.append(child.getTransform())
        else:
            self.meshes = [shape.getTransform() for shape in pm.ls(type='mesh')]
        
        self.meshes = sorted(set(self.meshes), key = lambda k : k.name())
        self.objectListWidget.addItems([m.name() for m in self.meshes])
        self.processData()

    @undoOn
    def processData(self):
        self.shaderData = {}
        shadingGroup = []
        
        processed = 0
        self.getObjectButton.setVisible(False)
        self.progressBar.setVisible(True)
        self.progressBar.reset()

        selection = pm.ls(sl=1)

        for obj in self.meshes:
            shadingEngines = pm.listConnections(obj.getShape(), type='shadingEngine')
            if not shadingEngines:
                continue
            
            objShadingGroup = shadingEngines[0]
            if objShadingGroup not in shadingGroup:
                shadingGroup.append(objShadingGroup)
            
            currentData = self.shaderData.get(objShadingGroup.name(), {'objects':[]})
            currentData['objects'] += [obj.name()]
            self.shaderData[objShadingGroup.name()] = currentData

        for sg in shadingGroup:
            currentData = self.shaderData[sg.name()]
            textureData = currentData.get('textures', [])
            colorData = currentData.get('colors', [])
            
            sgConnections = pm.listHistory(sg)
            sgTextures = pm.ls(sgConnections, textures=True)
            sgShaders = pm.ls(sgConnections, materials=True)

            if self.checkDominant.isChecked():
                totalArea = 0
                weightInfo = []
                for o in currentData['objects']:
                    processed += 1
                    self.progressBar.setValue(float(processed)/len(self.meshes) * 100)
                    
                    faceCount = pm.polyEvaluate(o, f=True)
                    for faceId in range(faceCount):
                        face = "%s.f[%d]" %(o, faceId)
                        pm.select(face)

                        area = pm.polyEvaluate(face, faceArea=True)[0]
                        bb = pm.polyEvaluate(boundingBoxComponent2d=True)

                        totalArea += area
                        x, y = ((bb[0][0]+bb[1][0])/2, (bb[0][1]+bb[1][1])/2)
                        weightInfo.append([area, x, y])
            
            for texture in sgTextures:
                connections = pm.listConnections(texture, connections=True, destination=True, plugs=True)
                
                for connection in connections:
                    source = connection[0]
                    destination = connection[1]
                    if destination.node() in sgShaders:
                        sdCon = (source.name(), destination.name())
                        if sdCon not in textureData:
                            rgba = [0,0,0,0]

                            if self.checkDominant.isChecked():
                                for area, x, y in weightInfo:
                                    r,g,b,a = pm.colorAtPoint(source, o='RGBA', u=x, v=y)

                                    weight = area/totalArea
                                    rgba[0] += r*weight
                                    rgba[1] += g*weight
                                    rgba[2] += b*weight
                                    rgba[3] += a*weight
                            else:
                                processed += 1
                                self.progressBar.setValue(float(processed)/len(shadingGroup) * 100)
                                maxSample = 10
                                
                                for u in range(maxSample):
                                    for v in range(maxSample):
                                        x = float(u)/maxSample
                                        y = float(v)/maxSample
                                        total = maxSample*maxSample
                                        
                                        r,g,b,a = pm.colorAtPoint(source, o='RGBA', u=x, v=y)
                                        
                                        rgba[0] += r/total
                                        rgba[1] += g/total
                                        rgba[2] += b/total
                                        rgba[3] += a/total

                            colorData += [(source.name(), rgba)]
                            textureData += [sdCon]

            currentData['textures'] = textureData
            currentData['colors'] = colorData
        
        pm.select(selection)
        if self.shaderData:
            jsonOutput = self.getJsonFile()
            with open(jsonOutput, "w+") as f:
                f.write(json.dumps(self.shaderData, indent=4))
        self.checkJson()
        
        self.progressBar.reset()
        self.progressBar.setVisible(False)
        self.getObjectButton.setVisible(True)
    
    @undoOn
    def colorize(self):
        jsonOutput = self.getJsonFile()
        if os.path.isfile(jsonOutput):
            with open(jsonOutput, "r+") as f:
                self.shaderData = json.load(f)
            for k, v in self.shaderData.items():
                for i in v['textures']:
                    rgba = next((c[1] for c in v['colors'] if c[0] == i[0]), None)
                    if rgba:
                        # pump up saturation
                        saturation = .8
                        iMax = rgba.index(max(rgba[0:3]))
                        iMin = rgba.index(min(rgba[0:3]))
                        if iMax != iMin:
                            iMid = next((i for i in range(3) if i != iMax and i != iMin), 0)
                            ratio = (rgba[iMax] - rgba[iMin])/rgba[iMax]
                            rgba[iMax] = rgba[iMax]
                            rgba[iMin] = rgba[iMin] * (1-saturation)
                            newRatio = (rgba[iMax] - rgba[iMin])/rgba[iMax]
                            rgba[iMid] = rgba[iMid] * ((1-saturation)-(ratio-newRatio))

                        if pm.connectionInfo( i[0], isSource=True):
                            destinations = pm.connectionInfo(i[0], destinationFromSource=True)
                            if destinations[0] == i[1]:
                                pm.disconnectAttr(i[0], destination=i[1])
                                pm.setAttr(i[1], rgba[0], rgba[1], rgba[2], type='double3')
        else:
            raise Exception(jsonOutput +" is missing")
    
    @undoOn
    def restore(self):
        jsonOutput = self.getJsonFile()
        if os.path.isfile(jsonOutput):
            with open(jsonOutput, "r+") as f:
                self.shaderData = json.load(f)
            for k, v in self.shaderData.items():
                for i in v['textures']:
                    if not pm.isConnected(i[0], i[1]):
                        pm.connectAttr(i[0], i[1], force=True)
        else:
            raise Exception(jsonOutput +" is missing")

    def delete(self):
        try:
            self.restore()
        except:
            pass

        jsonOutput = self.getJsonFile()
        if os.path.isfile(jsonOutput):
            os.remove(jsonOutput)
            self.checkJson()
        else:
            raise Exception(jsonOutput +" is missing")

w = ColorizeTool()
w.show()