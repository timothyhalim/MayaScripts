try:
    from PySide2.QtGui import *
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtGui import *
    from PySide.QtCore import *

#### MAYA COMMAND ####

from maya import cmds, mel
from time import sleep

def getShape(transform):
    shapes = cmds.listRelatives(transform, shapes=True, f=True)
    if shapes:
        return shapes[0]
    
def getObjectType(object):
    if cmds.nodeType(object) == "transform":
        shape = getShape(object)
        if shape:
            object = shape
    return cmds.nodeType(object)

# hasOverride = [o for o in cmds.ls("::*.overrideEnabled", o=True, ap=True) if cmds.getAttr(o+".overrideEnabled") and getObjectType(o) in ("mesh", "transform")]
# noRig = [o for o in hasOverride if not any(x in o for x in [":Rig", ":Camera"]) ]
# for x in noRig:
    # enableSelection(x)
    
def getMesh(transform):
    return cmds.listRelatives(transform, children=True, type="mesh")

def enableSelection(geo):
    if not cmds.getAttr(geo+".overrideEnabled", settable=True):
        cmds.delete(geo+".overrideEnabled", icn=True)
    try:
        cmds.setAttr (geo+".overrideEnabled", 0)
    except:
        print("Fail to set override on %s" %geo)

def getDescendantsShapes(obj):
    shapes = cmds.listRelatives(obj, f=True, shapes=True)
    if not isinstance(shapes, list):
        shapes = []
    allTransforms = cmds.listRelatives(obj, f=True, ad=True, type='transform')
    descShapes = cmds.listRelatives(allTransforms, f=True, shapes=True) if allTransforms else []
    shapes += descShapes if descShapes else []
    return shapes

def assignSurfaceShader(name,rgb,a):
    curRL = cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True )
    objList=cmds.ls(sl=True, l=True)
    if not cmds.objExists(name):
        cmds.shadingNode("surfaceShader", asShader=True, name=name)
        cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name+"_SG")
        cmds.connectAttr(name+'.outColor', name+'_SG.surfaceShader')
    try:
        cmds.setAttr (name+".outColor",rgb[0],rgb[1],rgb[2], type="double3")
        cmds.setAttr (name+".outMatteOpacity",a[0],a[1],a[2], type="double3")
    except:
        pass
    shaderSG = cmds.listConnections(name, d=True, et=True, t='shadingEngine')
    cmds.sets( objList, e=True, forceElement=shaderSG[0] )

def createContactLineTexture(name, radius=0.1):
    if not cmds.objExists(name):
        cmds.shadingNode("VRayDirt", asTexture=True, name=name)
    cmds.setAttr(name+".ignoreSelfOcclusion", 1)
    cmds.setAttr(name+".radius", radius)
    cmds.setAttr(name+".subdivs", 8)
    cmds.setAttr(name+".distribution", 0)
    cmds.setAttr(name+".falloff", 0)
    cmds.setAttr(name+".resultAffectInclusive", 0)
    cmds.setAttr(name+".blackColor", 1,1,1)
    cmds.setAttr(name+".whiteColor", 0,0,0)
    
    if not cmds.objExists(name+'_place2d'):
        cmds.shadingNode("place2dTexture", asUtility=True, name=name+'_place2d')
    if not cmds.isConnected(name+"_place2d.outUV", name+".uv"):
        cmds.connectAttr(name+"_place2d.outUV", name+".uv", force=True)
    if not cmds.isConnected(name+"_place2d.outUvFilterSize", name+".uvFilterSize"):
        cmds.connectAttr(name+"_place2d.outUvFilterSize", name+".uvFilterSize", force=True)
    
    if not cmds.objExists(name+"_Remap"):
        cmds.shadingNode("setRange", asTexture=True, name=name+"_Remap")
    if not cmds.isConnected(name+".outColor", name+"_Remap.value"):
        cmds.connectAttr(name+".outColor", name+"_Remap.value")
    cmds.setAttr(name+"_Remap.min", 0,0,0)
    cmds.setAttr(name+"_Remap.max", 1,1,1)
    cmds.setAttr(name+"_Remap.oldMin", 0.01,0.01,0.01)
    cmds.setAttr(name+"_Remap.oldMax", 0.08,0.08,0.08)

def createContactLineShader(name, radius=0.1):
    assignSurfaceShader(name+'_SS', (1,0,0), (1,1,1))
    createContactLineTexture(name+'_Contact', radius)
    if not cmds.isConnected(name+'_Contact_Remap.outValue', name+'_SS.outColor'):
        cmds.connectAttr(name+'_Contact_Remap.outValue', name+'_SS.outColor', force=True)
    if not cmds.isConnected(name+'_Contact_Remap.outValue', name+'_SS.outMatteOpacity'):
        cmds.connectAttr(name+'_Contact_Remap.outValue', name+'_SS.outMatteOpacity', force=True)
    
def addVraySubdiv(shapes=[], add=True):
    for shape in shapes:
        cmds.vray('addAttributesFromGroup', shape, 'vray_subdivision', add)
        cmds.vray('addAttributesFromGroup', shape, 'vray_subquality', add)

def importAlembic(filepath, namespace=""):
    print "Importing :", filepath
    cachePath = filepath
    cacheNS = namespace
    if cmds.namespace( ex=cacheNS ):
        existingNodes = cmds.ls( '%s:*' % cacheNS )
        if existingNodes:
            cmds.delete( existingNodes )
        cmds.namespace( rm=cacheNS )
    abc = cmds.file( cachePath, i=True, type='Alembic', rnn=True, ns=cacheNS )
    return abc
    
#### QT COMMAND ####

def getMayaWindow():
    for w in QApplication.topLevelWidgets():
        try:
            if w.objectName() == 'MayaWindow':
                return w
        except:
            pass
    return None
    
class FXHelper( QDialog ):
    def __init__( self, parent=None ):
        super( FXHelper, self ).__init__( parent )
        
        for w in QApplication.topLevelWidgets():
            if w.objectName == 'FXHelper':
                w.close()
                w.deleteLater()
        
        self.setWindowTitle("FX Helper - timo.ink" )
        self.objectName = 'FXHelper'
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.setupUI()
        self.show()
        
    def setupUI( self ):
        self.mainLayout = QVBoxLayout( self )
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.tabs = QTabWidget() 
        self.mainLayout.addWidget(self.tabs) 
        
        self.utilTab = QWidget()
        self.shaderTab = QWidget()
        
        # Add tabs 
        self.tabs.addTab(self.utilTab, "Utils") 
        self.tabs.addTab(self.shaderTab, "Shader") 
  
        # Util tab 
        self.utilTab.layout = QVBoxLayout( self.utilTab )
        self.utilTab.setLayout(self.utilTab.layout) 
        
        self.enableMeshSelectionBtn = QPushButton('Enable Mesh Selection')
        self.addVraySubdivBtn = QPushButton('Add Vray Subdiv')
        self.setVraySettingsBtn = QPushButton('Set Vray Settings')
        
        self.filePath = QLineEdit(self)
        self.filePath.setPlaceholderText('Cache folder path')
        self.filePath.setText(cmds.file(q=True, sceneName=True))
        
        self.fileList = QListWidget(self)
        self.fileList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.runBtn = QPushButton("Import")
        
        for w in [self.enableMeshSelectionBtn, self.addVraySubdivBtn, self.setVraySettingsBtn,
                  self.filePath, self.fileList, self.runBtn]:
            self.utilTab.layout.addWidget(w) 
        
        self.enableMeshSelectionBtn.clicked.connect(self.enableMeshSelection)
        self.addVraySubdivBtn.clicked.connect(self.addVraySubdiv)
        self.setVraySettingsBtn.clicked.connect(self.setVraySettings)
        self.filePath.textChanged.connect(self.updateList)
        self.runBtn.clicked.connect(self.importAbc)
        self.updateList()
  
        # Shader tab 
        self.shaderTab.layout = QVBoxLayout( self.shaderTab )
        self.shaderTab.setLayout(self.shaderTab.layout) 
        
        self.applyWhite = QPushButton('Assign White SS')
        self.applyBlack = QPushButton('Assign Black SS')
        self.applyChar = QPushButton('Assign Contact Char Shader')
        self.applyGround = QPushButton('Assign Contact Ground Shader')
        
        for w in [ self.applyWhite, self.applyBlack, self.applyChar, self.applyGround]:
            self.shaderTab.layout.addWidget(w) 
        self.shaderTab.layout.addStretch()
        
        self.applyWhite.clicked.connect(self.applyWhiteSS)
        self.applyBlack.clicked.connect(self.applyBlackSS)
        self.applyChar.clicked.connect(self.applyCharShader)
        self.applyGround.clicked.connect(self.applyGroundShader)
    
    def updateList(self):
        dir = self.filePath.text()
        self.fileList.clear()
        if os.path.isdir(dir):
            files = [f for f in os.listdir(dir) if f.lower().endswith('.abc')]
            self.fileList.addItems( sorted(files) )
            
    def importAbc(self):
        dir = self.filePath.text()
        files = [f.text() for f in self.fileList.selectedItems()]
        for f in files:
            filepath = None
            assetName = "_".join( f.split('.')[0].split("_")[0:-2] )
            filepath = os.path.join(dir, f)
            
            if os.path.isfile(filepath):
                importAlembic(filepath, namespace=assetName)
    
    def enableMeshSelection( self ):
        geoGrp = [geo for geo in cmds.ls(type="transform")]
        for geo in geoGrp:
            enableSelection(geo)
            meshes = getMesh(geo)
            if meshes:
                for mesh in meshes:
                    enableSelection(mesh)
        
    def addVraySubdiv( self ):
        shapes = getDescendantsShapes(cmds.ls(sl=1, l=1))
        addVraySubdiv(shapes, add=True)
        
    def setVraySettings( self ):
        cmds.loadPlugin("vrayformaya.mll") # load Vray
        cmds.setAttr("defaultRenderGlobals.currentRenderer", "vray", type="string")
        mel.eval("unifiedRenderGlobalsWindow")
        sleep(0.5)
        cmds.setAttr("vraySettings.animType", 1)
        cmds.setAttr("vraySettings.animBatchOnly", 1)
        cmds.setAttr("defaultRenderGlobals.startFrame", int(cmds.playbackOptions(q=True, ast=True)))
        cmds.setAttr("defaultRenderGlobals.endFrame", int(cmds.playbackOptions(q=True, aet=True)))
        cmds.setAttr("vraySettings.width", 1280)
        cmds.setAttr("vraySettings.height", 720)
        cmds.setAttr("vraySettings.samplerType", 4)
        cmds.setAttr("vraySettings.giOn", 0)
        cmds.setAttr("vraySettings.globopt_light_doLights", 0)
        cmds.setAttr("vraySettings.globopt_light_doDefaultLights", 0)
        cmds.setAttr("vraySettings.globopt_light_doShadows", 0)
        cmds.setAttr("vraySettings.globopt_mtl_SSSEnabled", 0)
        cmds.setAttr("vraySettings.globopt_mtl_glossy", 0)
        cmds.setAttr("vraySettings.globopt_mtl_reflectionRefraction", 0)
        cmds.setAttr("vraySettings.globopt_mtl_doMaps", 0)
        cmds.setAttr("vraySettings.globopt_mtl_filterMaps", 0)
        cmds.setAttr("vraySettings.cam_overrideEnvtex", 1)
        cmds.setAttr("vraySettings.cam_envtexGi", 0, 0, 0, type="double3")
        cmds.setAttr("vraySettings.cam_envtexBg", 0, 0, 0, type="double3")
        cmds.setAttr("vraySettings.cam_envtexReflect", 0, 0, 0, type="double3")
        cmds.setAttr("vraySettings.cam_envtexRefract", 0, 0, 0, type="double3")
        cmds.setAttr("vraySettings.relements_enableall", 0)
        
    def applyGroundShader( self ):
        shapes = getDescendantsShapes(cmds.ls(sl=1, l=1))
        transforms = cmds.listRelatives(shapes, f=True, p=True, type='transform')
        createContactLineShader('Ground', radius=0.5)
        
        if not cmds.objExists('Char_VOP'):
            cmds.createNode('VRayObjectProperties', name='Char_VOP')
        cmds.sets( transforms, e=True, remove='Char_VOP' )
        if not cmds.isConnected('Char_VOP.outColor', 'Ground_Contact.exclude'):
            cmds.connectAttr('Char_VOP.outColor', 'Ground_Contact.exclude', force=True)
            
        if not cmds.objExists('Ground_VOP'):
            cmds.createNode('VRayObjectProperties', name='Ground_VOP')
        cmds.sets( transforms, e=True, forceElement='Ground_VOP' )
        if not cmds.isConnected('Ground_VOP.outColor', 'Ground_Contact.resultAffect'):
            cmds.connectAttr('Ground_VOP.outColor', 'Ground_Contact.resultAffect', force=True)
        
    def applyCharShader( self ):
        sel = cmds.ls(sl=1, l=1)
        shapes = getDescendantsShapes(sel)
        transforms = cmds.listRelatives(shapes, f=True, p=True, type='transform')
        createContactLineShader('Char')
        
        if not cmds.objExists('Char_VOP'):
            cmds.createNode('VRayObjectProperties', name='Char_VOP')
        cmds.sets( transforms, e=True, forceElement='Char_VOP' )
        if not cmds.isConnected('Char_VOP.outColor', 'Char_Contact.resultAffect'):
            cmds.connectAttr('Char_VOP.outColor', 'Char_Contact.resultAffect', force=True)
            
        if not cmds.objExists('Ground_VOP'):
            cmds.createNode('VRayObjectProperties', name='Ground_VOP')
        cmds.sets( transforms, e=True, remove='Ground_VOP' )
        if not cmds.isConnected('Ground_VOP.outColor', 'Ground_Contact.resultAffect'):
            cmds.connectAttr('Ground_VOP.outColor', 'Ground_Contact.resultAffect', force=True)
            
    def applyWhiteSS( self ):
        assignSurfaceShader('White_SS', (1,1,1), (1,1,1))
        
    def applyBlackSS( self ):
        assignSurfaceShader('Black_SS', (0,0,0), (0,0,0))
    
#### RUN ####
FXHelper(parent=getMayaWindow())