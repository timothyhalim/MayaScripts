'''
Maya 2 AE

Tools to send maya camera and null to AE
Tested on Windows only

'''

try:
    from PySide2.QtGui import *
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtGui import *
    from PySide.QtCore import *

import os
import subprocess
import math

from maya import cmds, mel
import maya.OpenMaya as om
import maya.OpenMayaUI as omui

#### UI ####
def getMayaWindow():
    for w in QApplication.topLevelWidgets():
        try:
            if w.objectName() == 'MayaWindow':
                return w
        except:
            pass
    return None
    
class ExtendedComboBox(QComboBox):
    def __init__(self, parent=None):
        super(ExtendedComboBox, self).__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setEditable(True)
        
        # add a filter model to filter matching items
        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.pFilterModel.setSourceModel(self.model())
        
        # add a completer, which uses the filter model
        self.completer = QCompleter(self.pFilterModel, self)
        # always show all (filtered) completions
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)
        
        # connect signals
        self.lineEdit().textEdited[unicode].connect(self.pFilterModel.setFilterFixedString)
        self.completer.activated.connect(self.onCompleterActivated)
        
    # on selection of an item from the completer, select the corresponding item from combobox 
    def onCompleterActivated(self, text):
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)
            
    # on model change, update the models of the filter and completer as well 
    def setModel(self, model):
        super(ExtendedComboBox, self).setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)
        
    # on model column change, update the model column of the filter and completer as well
    def setModelColumn(self, column):
        self.completer.setCompletionColumn(column)
        self.pFilterModel.setFilterKeyColumn(column)
        super(ExtendedComboBox, self).setModelColumn(column)

class SearchBox(QLineEdit):
    def __init__(self, parent=None, completerContents=[]):
        super(SearchBox, self).__init__(parent)

        self.completer = QCompleter(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(self.completer)
        self.updateCompletionList(completerContents)
        
    def updateCompletionList(self, autocomplete_list):
        self.autocomplete_model = QStandardItemModel()
        for text in autocomplete_list:
            self.autocomplete_model.appendRow(QStandardItem(text))
        self.completer.setModel(self.autocomplete_model)
        

class MAYA2AE( QMainWindow ):
    def __init__( self, parent=None ):
        super( MAYA2AE, self ).__init__( parent )
        
        windowName = 'MAYA2AE'
        for w in QApplication.topLevelWidgets():
            if w.objectName == windowName :
                w.close()
                w.deleteLater()
        
        self.setWindowTitle("MAYA2AE - timo.ink" )
        self.objectName = windowName
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.setupUI()
        self.initUI()
        self.show()
        
    def setupUI( self ):
        self.mainWidget = QWidget( self )
        self.mainHLayout = QHBoxLayout( self.mainWidget )
        self.mainLayout = QVBoxLayout( )
        self.mainHLayout.addLayout( self.mainLayout )
        self.setCentralWidget(self.mainWidget)
        
        # AE Info
        self.aeInfo = QGroupBox("After Effects :")
        self.aeLayout = QVBoxLayout(self.aeInfo)
        self.mainLayout.addWidget(self.aeInfo)
        
        self.adobePathLayout = QHBoxLayout()
        self.adobePathLabel = QLabel('Adobe Path :')
        self.adobePath = QLineEdit()
        for w in [self.adobePathLabel, self.adobePath]:
            self.adobePathLayout.addWidget(w)
        self.aeLayout.addLayout(self.adobePathLayout)
        
        self.AELayout = QHBoxLayout()
        self.AELabel = QLabel('After Effects :')
        self.AEVersion = QComboBox()
        for w in [self.AELabel, self.AEVersion]:
            self.AELayout.addWidget(w)
        self.aeLayout.addLayout(self.AELayout)
        
        self.missingAE = QLabel()
        self.missingAE.setAlignment(Qt.AlignCenter)
        self.aeLayout.addWidget(self.missingAE)
        
        # Create Locator Info
        self.tools = QGroupBox("Tools :")
        self.toolsLayout = QVBoxLayout(self.tools)
        self.mainLayout.addWidget(self.tools)
        
        self.createLocBtn = QPushButton('Create Locator')
        self.createLocBtn.clicked.connect(self.createLocator)
        self.toolsLayout.addWidget(self.createLocBtn)
        
        # Bake Options
        self.bakeGroup = QGroupBox("Bake :")
        self.bakeLayout = QVBoxLayout(self.bakeGroup)
        self.mainLayout.addWidget(self.bakeGroup)
        
        self.bakeFrameLayout = QHBoxLayout()
        self.bakeFrameLabel = QLabel('Frame :')
        self.bakeFrameStart = QSpinBox()
        self.bakeFrameDiv = QLabel('-')
        self.bakeFrameEnd = QSpinBox()
        for w in [self.bakeFrameLabel, self.bakeFrameStart, self.bakeFrameDiv, self.bakeFrameEnd]:
            self.bakeFrameLayout.addWidget(w)
        
        self.bakeFullPath = QCheckBox('Use Fullpath')
        self.bakeCamera = QCheckBox('Bake Renderable Camera')
        self.bakeFixFocalLength = QCheckBox('Fix Camera Focal Length')
        
        self.bakeOptionLayout = QHBoxLayout()
        self.bakeLabel = QLabel('Bake')
        self.bakeTranslate = QCheckBox('Translate')
        self.bakeRotate = QCheckBox('Rotate')
        self.bakeScale = QCheckBox('Scale')
        
        for w in [self.bakeTranslate, self.bakeRotate, self.bakeScale]:
            self.bakeOptionLayout.addWidget(w)
        
        self.bakeButton = QPushButton('Bake Selection')
        
        for w in [self.bakeFrameLayout, self.bakeFullPath, self.bakeCamera, self.bakeFixFocalLength, self.bakeOptionLayout, self.bakeButton]:
            try:
                self.bakeLayout.addWidget(w)
            except:
                self.bakeLayout.addLayout(w)
        
        # Export Options
        self.exportGroup = QGroupBox("Export :")
        self.exportLayout = QVBoxLayout(self.exportGroup)
        self.mainLayout.addWidget(self.exportGroup)
        
        self.exportListLayout = QHBoxLayout()
        self.exportListLabel = QLabel('Objects to export :')
        for w in [self.exportListLabel]:
            self.exportListLayout.addWidget(w)
        self.exportList = QListWidget()
        
        self.exportPathLayout = QHBoxLayout()
        self.exportPathLabel = QLabel('Export Path :')
        self.exportPath = SearchBox()
        for w in [self.exportPathLabel, self.exportPath]:
            self.exportPathLayout.addWidget(w)
        
        self.exportCompLayout = QHBoxLayout()
        self.exportCompLabel = QLabel('Comp Name :')
        self.exportComp = QLineEdit()
        for w in [self.exportCompLabel, self.exportComp]:
            self.exportCompLayout.addWidget(w)
        
        self.exportResolutionLayout = QHBoxLayout()
        self.exportResolutionLabel = QLabel('Resolution :')
        self.exportResolutionWidth = QSpinBox()
        self.exportResolutionDiv = QLabel('x')
        self.exportResolutionHeight = QSpinBox()
        for w in [self.exportResolutionLabel, self.exportResolutionWidth, self.exportResolutionDiv, self.exportResolutionHeight]:
            self.exportResolutionLayout.addWidget(w)
            
            
        self.exportFPSLayout = QHBoxLayout()
        self.exportFPSLabel = QLabel('FPS :')
        self.exportFPS = QDoubleSpinBox()
        for w in [self.exportFPSLabel, self.exportFPS]:
            self.exportFPSLayout.addWidget(w)

        self.exportStartFrameLayout = QHBoxLayout()
        self.exportStartFrameLabel = QLabel('Start Frame :')
        self.exportStartFrame = QSpinBox()
        for w in [self.exportStartFrameLabel, self.exportStartFrame]:
            self.exportStartFrameLayout.addWidget(w)

        self.exportToMM = QCheckBox('Change Units to mm')
        self.deleteUnknown = QCheckBox('Delete Unknown Node')
        self.deleteBaked = QCheckBox('Delete Baked after Export')
        self.deleteAfterImport = QCheckBox('Delete .JSX and .MA after AE import')
        
        self.exportButton = QPushButton('Export to AE')
        
        for w in [
            self.exportListLayout, self.exportList, 
            self.exportPathLayout, self.exportCompLayout, self.exportFPSLayout, self.exportStartFrameLayout,
            self.exportResolutionLayout, self.exportToMM, self.deleteUnknown, self.deleteBaked,  self.deleteAfterImport, self.exportButton
        ]:
            try:
                self.exportLayout.addWidget(w)
            except:
                self.exportLayout.addLayout(w)
        
    
    def initUI(self):
        self.adobePath.setText("C:\Program Files\Adobe")
        self.adobePath.textChanged.connect(self.checkAE)
        self.AELabel.setMaximumWidth(70)
        self.AELabel.setMinimumWidth(70)
        
        self.bakeFrameLabel.setMaximumWidth(70)
        self.bakeFrameLabel.setMinimumWidth(70)
        for w in [self.bakeFrameStart, self.bakeFrameEnd]:
            w.setMinimum(-999999999)
            w.setMaximum(999999999)
        self.bakeFrameDiv.setMaximumWidth(10)
        self.bakeFrameDiv.setMinimumWidth(10)
        self.bakeFrameDiv.setAlignment(Qt.AlignCenter)
        
        self.bakeFixFocalLength.setChecked(True)
        self.bakeTranslate.setChecked(True)
        self.bakeRotate.setChecked(True)
        self.deleteUnknown.setChecked(True)
        self.bakeButton.clicked.connect(self.bakeSelection)
        
        self.exportList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.exportList.itemSelectionChanged.connect(self.selectFromList)
        
        self.exportPathLabel.setMaximumWidth(70)
        self.exportPathLabel.setMinimumWidth(70)
        self.exportCompLabel.setMaximumWidth(70)
        self.exportCompLabel.setMinimumWidth(70)
        self.exportPath.setText(cmds.workspace(q=1, rd=1)+'data')
        
        mayaScene = cmds.file (q=1, sn=1)
        compName = os.path.splitext(os.path.basename(mayaScene))[0] if mayaScene else 'MAYA2AE'
        self.exportComp.setText(compName)
            
        self.exportResolutionLabel.setMaximumWidth(70)
        self.exportResolutionLabel.setMinimumWidth(70)
        for w in [self.exportResolutionWidth, self.exportResolutionHeight]:
            w.setMinimum(1)
            w.setMaximum(999999999)
        self.exportResolutionDiv.setMaximumWidth(10)
        self.exportResolutionDiv.setMinimumWidth(10)
        self.exportResolutionDiv.setAlignment(Qt.AlignCenter)
        
        self.exportResolutionWidth.setValue(1920)
        self.exportResolutionHeight.setValue(1080)

        self.exportFPSLabel.setMaximumWidth(70)
        self.exportFPSLabel.setMinimumWidth(70)
        self.exportFPS.setValue(mel.eval('float $fps = `currentTimeUnitToFPS`'))

        self.exportStartFrameLabel.setMaximumWidth(70)
        self.exportStartFrameLabel.setMinimumWidth(70)
        self.exportStartFrame.setValue(1)

        self.exportToMM.setChecked(True)
        self.exportButton.clicked.connect(self.export2ae)
        
        #connect outliner
        cw = QApplication.topLevelWidgets()
        outL = cmds.outlinerPanel(mbv=True, to=True)
        outLWidgets = [w for w in QApplication.topLevelWidgets() if not w in cw and w.parent().objectName() == 'MayaWindow']
        self.mainHLayout.addWidget(outLWidgets[0])
        
        self.checkAE()
        self.refreshFrameRange()
        self.registerScriptJobs()
        self.refreshExportList()
        self.getAllPaths()
        
    def registerScriptJobs(self):
        # Create the script job and store it's number.
        self.scriptJobs = [
            cmds.scriptJob( event =["playbackRangeSliderChanged", self.refreshFrameRange], compressUndo=True, protected=True ),
            cmds.scriptJob( event =["playbackRangeChanged", self.refreshFrameRange], compressUndo=True, protected=True ),
            cmds.scriptJob( conditionTrue=["delete", self.refreshExportList], compressUndo=True,  protected=True ),
            cmds.scriptJob( event=["NameChanged", self.refreshExportList], compressUndo=True,  protected=True ),
            cmds.scriptJob( event=["Undo", self.refreshExportList], compressUndo=True,  protected=True ),
            cmds.scriptJob( event=["Redo", self.refreshExportList], compressUndo=True,  protected=True )
        ] 
        self.referencesCallback = [
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterCreateReference, self.getAllPaths),
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterLoadReference, self.getAllPaths),
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterRemoveReference, self.getAllPaths),
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterUnloadReference, self.getAllPaths),
            om.MSceneMessage.addCallback(om.MSceneMessage.kAfterImport, self.getAllPaths),
        ]
        
    def unregisterScriptJobs(self):
        # Clean up the script job stuff prior to closing the dialog.
        for job in self.scriptJobs:
            cmds.scriptJob( kill=job, force=True )
        for cb in self.referencesCallback:
            om.MMessage.removeCallback(cb)
        
    def getAllPaths(self, *args, **kwargs):
        paths = [cmds.workspace(q=1, rd=1)+'data'] 
        paths += list(set([os.path.dirname(f) for f in cmds.file(q=1, r=1)]))
        paths += list(set([os.path.dirname(cmds.getAttr(o+'.abc_File')) for o in cmds.ls(type="AlembicNode", ap=True)]))
        paths.sort()
        self.exportPath.updateCompletionList(paths)
        
    def closeEvent( self, event ):
        self.unregisterScriptJobs()
        try:
            super( MAYA2AE, self ).closeEvent( event )
        except:
            pass
        
    def checkAE(self):
        self.adobeDir = self.adobePath.text().replace("\\","/")
        self.aeExe = "Support Files/AfterFX.exe"
        afterEffects = []
        
        if os.path.isdir(self.adobeDir):
            afterEffects = [ae for ae in os.listdir(self.adobeDir) if 'After Effects' in ae and os.path.exists(os.path.join(self.adobeDir, ae, self.aeExe).replace('\\', '/'))]
        
        if afterEffects:
            self.AEVersion.clear()
            self.AEVersion.addItems(afterEffects)
            
            self.missingAE.hide()
            self.AEVersion.show()
            self.AELabel.show()
            self.exportButton.setEnabled(True)
        else:
            self.missingAE.setText('After Effects not found in %s' %self.adobePath.text())
            self.missingAE.show()
            self.AEVersion.hide()
            self.AELabel.hide()
            self.exportButton.setEnabled(False)
        
    def createLocator(self):
        if cmds.draggerContext(ctx, exists=True):
            cmds.deleteUI(ctx)
        cmds.draggerContext(ctx, pressCommand=createLocOnClick, name=ctx, cursor='crossHair', image1='locator.png')
        cmds.setToolTo(ctx)
        
    def refreshFrameRange(self):
        self.bakeFrameStart.setValue(int(cmds.playbackOptions(q=True, ast=True)))
        self.bakeFrameEnd.setValue(int(cmds.playbackOptions(q=True, aet=True)))
        
    def refreshExportList(self):
        self.exportList.clear()
        baked = sorted(cmds.ls("::*.toAE", o=True))
        self.exportList.addItems(baked)
        
    def selectFromList(self):
        cmds.select([item.text() for item in self.exportList.selectedItems()])
        
    def bakeSelection(self):
        self.unregisterScriptJobs()
        
        start = int(self.bakeFrameStart.text())
        end = int(self.bakeFrameEnd.text())
        useFullPath = self.bakeFullPath.isChecked()
        bakeRenderCamera = self.bakeCamera.isChecked()
        t,r,s = (self.bakeTranslate.isChecked(), self.bakeRotate.isChecked(), self.bakeScale.isChecked())
        
        toBake = cmds.ls(sl=1, l=1, transforms=1)
        if bakeRenderCamera:
            toBake += getRenderCam()
        toBake = list(set(toBake))
        if toBake:
            cmds.undoInfo( openChunk= True, chunkName = "bakeCamLoc" )
            currentFrame = cmds.currentTime(q=True)
            cmds.refresh(suspend=True) # Pause Viewport
            try:
                baked = bakeCamLoc(
                    objects=toBake, fullpathname=useFullPath, 
                    startFrame=start, endFrame=end, 
                    bakeTranslate=t, bakeRotate=r, bakeScale=s
                )
                for obj in baked:
                    # objShape = getShape(obj)
                    objShape = obj
                    cmds.addAttr(objShape, ln="toAE", at='bool')
                    cmds.setAttr(objShape+".toAE", 1)
                    # cmds.setAttr(objShape+".toAE", 1, l=True)
                
                if self.bakeFixFocalLength.isChecked():
                    for cam in baked:
                        fixAEFocalLength( cam, startFrame=start, endFrame=end )
                self.refreshExportList()
                
            except Exception as e:
                cmds.error(e)
            finally:
                # Restore
                cmds.currentTime(currentFrame)
                cmds.refresh(suspend=False)
                cmds.undoInfo( closeChunk = True )
        else:
            self.messageDialog("No Object is selected")
            
        self.registerScriptJobs()
    
    def export2ae(self):
        exportDir = self.exportPath.text().replace('\\','/')
        compName = self.exportComp.text().replace('\\','/')
        
        self.refreshExportList()
        objectToExport = [str(self.exportList.item(i).text()) for i in range( self.exportList.count() )]
        if not exportDir:
            self.messageDialog("Export Path is empty")
            return
        if not compName:
            self.messageDialog("Export Comp Name is empty")
            return
        
        if objectToExport:
            cameras = [obj for obj in objectToExport if cmds.nodeType(getShape(obj)) == 'camera']
            if not cameras:
                self.messageDialog("No Camera to Export!")
                return
                
            if not os.path.exists( exportDir ):
                os.makedirs( exportDir )
            if not os.path.isdir( exportDir ):
                self.messageDialog("Export Path not exists")
                return
                    
            cmds.undoInfo( openChunk= True, chunkName = "ExportToAE" )
            try:
                mayaExportPath = '/'.join([exportDir, compName + '.ma'])
                jsxExportPath = '/'.join([exportDir, compName + '.jsx'])
                if os.path.isdir( exportDir ):
                    writeMA( mayaExportPath, objectToExport, 
                        convertToMM=self.exportToMM.isChecked(), 
                        convertResolution=(self.exportResolutionWidth.value(), self.exportResolutionHeight.value()), 
                        deleteUnknown=self.deleteUnknown.isChecked() 
                    )
                    writeJSX( {
                            'path': jsxExportPath, 
                            'start': self.exportStartFrame.value(),
                            'fps': self.exportFPS.value()
                        }, 
                        deleteAfterImport=self.deleteAfterImport.isChecked() 
                    )
                    if self.deleteBaked.isChecked():
                        cmds.delete(objectToExport)
                        self.refreshExportList()
                else:
                    cmds.error( '%s not Exist!' %exportDir )
                    
                if os.path.isfile(jsxExportPath):
                    aeVersion = str(self.AEVersion.currentText())
                    aePath = os.path.join(self.adobeDir, aeVersion, self.aeExe).replace('\\', '/')
                    print (aePath)
                    if aePath:
                        spawnAE(aePath, jsxExportPath)
            except Exception as e:
                cmds.error(e)
            finally:
                cmds.undoInfo( closeChunk = True )
        else:
            self.messageDialog("No Object to Export!")
            
    def messageDialog(self, text=""):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(text)
        msg.setWindowTitle("MAYA2AE")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        

#### MAYA COMMAND ####
def getShape(node):
    if cmds.nodeType(node) == 'transform':
        shape = cmds.listRelatives(node, f=True, s=True)
        if shape:
            return shape[0]
    return None
    
def getTransform(node):
    return cmds.listRelatives(node, p=True, f=True, type='transform')[0]
    
def calcDistance(p1, p2):
    return (
        (float(p2[0]) - float(p1[0]))**2 + 
        (float(p2[1]) - float(p1[1]))**2 + 
        (float(p2[2]) - float(p1[2]))**2
    )*0.5

def get_object_visibility(object):
    visible = cmds.getAttr("%s.visibility" %object)
    
    display_layer = cmds.listConnections(object , type="displayLayer")
    visible = cmds.getAttr("%s.visibility" %display_layer[0]) if display_layer else visible
    
    if not visible:
        return visible
        
    parents = cmds.listRelatives(object, p=True)
    if parents:
        visible = get_object_visibility(parents[0])
        
    return visible
    
ctx = 'myCtx'
def createLocOnClick():
    vpX, vpY, _ = cmds.draggerContext(ctx, query=True, anchorPoint=True)
    # print ("Click:", vpX, vpY)
    
    pos = om.MPoint()
    dir = om.MVector()
    hitpoint = om.MFloatPoint()
    
    view = omui.M3dView.active3dView()
    view.viewToWorld(int(vpX), int(vpY), pos, dir)
    
    cam = om.MDagPath()
    view.getCamera(cam)
    camPos = cmds.xform(getTransform(cam.fullPathName()), q=True, t=True, ws=True)
    
    nearest = None
    nearestDistance = None
    
    pos2 = om.MFloatPoint(pos.x, pos.y, pos.z)
    for mesh in cmds.ls( type="mesh", ap=True ):
        if not get_object_visibility(mesh):
            continue
        try:
            selectionList = om.MSelectionList()
            selectionList.add(mesh)
            dagPath = om.MDagPath()
            selectionList.getDagPath(0, dagPath)
            fnMesh = om.MFnMesh(dagPath)
            intersection = fnMesh.closestIntersection(
                om.MFloatPoint(pos2),
                om.MFloatVector(dir),
                None,
                None,
                False,
                om.MSpace.kWorld,
                99999,
                False,
                None,
                hitpoint,
                None,
                None,
                None,
                None,
                None
            )
        except:
            print ("Error reading on", mesh)
            continue
        if intersection:
            x = hitpoint.x
            y = hitpoint.y
            z = hitpoint.z
            
            distance = calcDistance((x,y,z), camPos)
            
            if nearest is None:
                nearest = (x,y,z)
                nearestDistance = distance
            else:
                if nearestDistance > distance :
                    nearest = (x,y,z) 
                    nearestDistance = distance
    
    cmds.setAttr(cmds.spaceLocator()[0]+'.translate', nearest[0], nearest[1], nearest[2], type="double3")
    # print ("Position:", nearest)
    # print ("Distance:", nearestDistance)

def spawnAE(aePath, jsx):
    subprocess.Popen([aePath, '-r', jsx])
    
def getRenderCam():
    renderCams = [getTransform(c) for c in cmds.ls(l=True, ca=True) if cmds.getAttr('%s.renderable' %c)]
    return renderCams

def bakeCamLoc(objects=[], fullpathname=True, startFrame=1, endFrame=1, bakeTranslate=True, bakeRotate=True, bakeScale=True):
    frames = range(startFrame, endFrame+1)
    bakeTransform = []
    if bakeTranslate:
        bakeTransform += ['tx', 'ty', 'tz']
    if bakeRotate:
        bakeTransform += ['rx', 'ry', 'rz']
    if bakeScale:
        bakeTransform += ['sx', 'sy', 'sz']
    
    transformsToBake = []
    dummies = []
    for obj in objects:
        origShape = getShape(obj)
        objName = obj.replace('|','_')[1:] if fullpathname else obj.split('|')[-1]
        
        # Create locator to get translate, rotate and scale
        dummyName = '%s_Temp' %objName
        if cmds.objExists(dummyName):
            cmds.delete(dummyName)
        dummy = cmds.spaceLocator(n=dummyName)[0]
        cmds.parentConstraint(obj, dummy) # Constraint dummy to original object
        
        isCamera = cmds.nodeType(getShape(obj)) == 'camera'
        bakedName = 'Cam_%s_Baked' %objName if isCamera else 'Null_%s_Baked' %objName
        
        # Delete existing baked objects
        if cmds.objExists(bakedName):
            cmds.delete(bakedName)
        
        if isCamera:
            # Create Camera
            baked = cmds.rename(cmds.camera()[0], bakedName)
            # Copy all atributes
            bakedShape = getShape(baked)
            attrs = cmds.listAttr(bakedShape)
            fail = []
            for attr in sorted(attrs):
                try:
                    attrType = cmds.getAttr( '%s.%s' %(origShape,attr), type=True )
                    if attrType not in [None, 'string', 'TdataCompound', 'matrix', 'double2', 'double3', 'message', 'float3']:
                        # if cmds.getAttr('%s.%s' %(bakedShape,attr), settable=True):
                        if cmds.getAttr('%s.%s' %(bakedShape,attr), keyable=True):
                            for i in frames:
                                value = cmds.getAttr( '%s.%s' %(origShape,attr), time=i )
                                cmds.setKeyframe( '%s.%s' %(bakedShape,attr),  t=i, v=value )
                except:
                    cmds.warning('Fail on %s.%s' %(bakedShape,attr))
        else:
            # Create locator and copy translate, rotate and scale
            baked = cmds.spaceLocator(n=bakedName)[0]
        transformsToBake.append((dummy, baked))
        
    # Copy translate, rotate and scale
    for i in frames:
        cmds.currentTime(i)
        for dummy, baked in transformsToBake:
            for attr in bakeTransform:
                value = cmds.getAttr('%s.%s' %(dummy,attr))
                cmds.setKeyframe( '%s.%s' %(baked,attr),  t=i, v=value )
    
    # Delete dummy after copying all translate, rotate and scale
    dummies = [dummy for dummy, baked in transformsToBake]
    bakedObjects = [baked for dummy, baked in transformsToBake]
    cmds.select(objects, r=True)
    cmds.delete(dummies)
    
    return bakedObjects
    
def fixAEFocalLength(cam, startFrame=1, endFrame=1):
    if cmds.nodeType(getShape(cam)) == 'camera':
        camShape = cmds.listRelatives(cam, s=True)[0]
        
        for i in range(startFrame, endFrame+1):
            hApt = cmds.getAttr( '%s.horizontalFilmAperture' %camShape, time=i ) *25.4
            vApt = cmds.getAttr( '%s.verticalFilmAperture' %camShape, time=i ) *25.4
            focalLength = cmds.getAttr( '%s.focalLength' %camShape, time=i )
            #diag = (hApt**2 + vApt**2)**.5
            diag = hApt
            FOV = 2 * math.degrees(math.atan( hApt/ (2*focalLength)))
            
            # make sure AE camera aperture is 36x24mm 
            # then adjust camera focal length
            defApt = (36, 24)
            ae_focalLength = (defApt[0]/2)/math.tan(math.radians(FOV/2))
            
            cmds.setKeyframe( '%s.horizontalFilmAperture' %camShape,  t=i, v=defApt[0]/25.4 ) 
            cmds.setKeyframe( '%s.verticalFilmAperture' %camShape,  t=i, v=defApt[1]/25.4 )
            cmds.setKeyframe( camShape, attribute='focalLength', t=i, v=ae_focalLength )
    
def writeMA(filepath, objects=[], convertToMM=True, convertResolution=(), deleteUnknown=False):
    # backup
    currentWorkingUnits = cmds.currentUnit(q=True)
    currentSelections = cmds.ls(sl=1)
    camWidth = cmds.getAttr('defaultResolution.width')
    camHeight = cmds.getAttr('defaultResolution.height')
    
    # set to mm
    if convertToMM: 
        cmds.currentUnit(l="mm")
    if convertResolution:
        cmds.setAttr('defaultResolution.width', convertResolution[0])
        cmds.setAttr('defaultResolution.height', convertResolution[1])
        cmds.setAttr('defaultResolution.deviceAspectRatio', (convertResolution[0]/float(convertResolution[1])))
    if deleteUnknown:
        for unk in cmds.ls(type='unknown'):
            cmds.lockNode(unk, lock=False)
            cmds.delete(unk)
    
    # export selection
    cmds.select(objects, r=True)
    filepath = cmds.file (filepath, force=True, options="v=0", typ="mayaAscii", exportSelected=True)
    print (filepath)
    cmds.select(currentSelections, r=True)
    
    # restore
    if convertToMM: 
        cmds.currentUnit(l=currentWorkingUnits)
    if convertResolution:
        cmds.setAttr('defaultResolution.width', camWidth)
        cmds.setAttr('defaultResolution.height', camHeight)
        cmds.setAttr('defaultResolution.deviceAspectRatio', (camWidth/float(camHeight)))
    
def writeJSX( data, deleteAfterImport=False ):
    compname = os.path.splitext(os.path.basename(data['path']))[0]
    dir = os.path.dirname(data['path'])

    jsxCmd = """
var compName = "{compName}"
var filePath = "{maPath}"
var startFrame = "{start}"
var fps = "{fps}"
""".format(compName=compname, maPath=dir, start=data['start'], fps=data['fps'])
    jsxCmd +="""
app.beginUndoGroup("Maya2AE");

var aeVersion = app.version;
aeVersion = parseFloat(aeVersion.substring(0, aeVersion.indexOf("x")));

//RENAME OLD
for(var index=1; index<=app.project.numItems; index++) { 
    var oldComp = app.project.item(index);
    if (oldComp.name == compName)
        {oldComp.name = oldComp.name + "_old_DELETE"; }
}
//IMPORT
app.project.importFile(new ImportOptions(File(filePath+"/"+compName+".ma")));

//RENAME CURRENT
for (var index=1; index <=app.project.numItems; index++) {
    var comp = app.project.item(index);

    if (comp.name == compName) {
        comp.frameRate = fps;

        if (aeVersion >= 17.1) {
            comp.displayStartFrame = startFrame;
        } else {
            comp.displayStartTime = startFrame/fps + 0.00001;
        }

        for (var compIndex=1; compIndex<=comp.numLayers; compIndex++) { 
            var theLayer = comp.layer(compIndex).name.replace("_BakedShape","");
            var newLayer = theLayer.replace("Null_","");
            comp.layer(compIndex).name=newLayer;
        }
    }

    if (comp.name=="Solids") { 
        for (var solidIndex= 1; solidIndex <= comp.numItems; solidIndex ++) {
            var theSolid=comp.item(solidIndex).name.replace("_BakedShape","");
            comp.item(solidIndex).name = theSolid
        }
    }  
}

app.endUndoGroup();
"""
    if deleteAfterImport:
        jsxCmd += """
var ma = new File(filePath + "/" + compName +".ma")
var jsx = new File(filePath + "/" + compName +".jsx")

ma.remove()
jsx.remove()
"""
    
    
    with open(data['path'], "w") as jsxFile:
        jsxFile.write(jsxCmd)

#### RUN ####
MAYA2AE(parent=getMayaWindow())
