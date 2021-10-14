'''
NParticle to Mesh

Convert Particle Instancer to mesh
Usage: 
1. Select nparticle/s
2. Set frame
3. Bake
'''

from maya import mel
import pymel.core as pm

from PySide2.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QProgressBar
from PySide2.QtCore import Qt

import traceback

### Maya Command

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

def pointMatrixMult(m1, m2):
    return mel.eval('pointMatrixMult ({%s}, {%s});' %(
        ", ".join([str(a) for a in m1]), 
        ", ".join([str(a) for a in [v for x in m2 for v in x]]), 
    ))

def bakeNParticles(nParticles=pm.ls(type='nParticle'), 
            startFrame = int(pm.playbackOptions(q=True, min=True)), 
            endFrame   = int(pm.playbackOptions(q=True, max=True))
        ):
    for nPtc in nParticles:
        pInst = pm.particleInstancer(nPtc, q=True, name=True)
        instances = []
        if pInst:
            pInst = pm.ls(pInst)[0]
            pName = nPtc
            pTrans = pm.ls(nPtc)[0].getTransform().name()
            objects            = mel.eval("particleInstancer -name {instancer} -q -object {particle}".format(
                                instancer = pInst, particle = pName))
            objectRotation     = mel.eval("particleInstancer -name {instancer} -q -rotation {particle} ".format(
                                instancer = pInst, particle = pName))
            objectRotationType = mel.eval("particleInstancer -name {instancer} -q -rotationType {particle} ".format(
                                instancer = pInst, particle = pName))
            objectPosition     = mel.eval("particleInstancer -name {instancer} -q -position {particle} ".format(
                                instancer = pInst, particle = pName))
            objectIndex        = mel.eval("particleInstancer -name {instancer} -q -objectIndex {particle} ".format(
                                instancer = pInst, particle = pName))
            objectScale        = mel.eval("particleInstancer -name {instancer} -q -scale {particle} ".format(
                                instancer = pInst, particle = pName))
            objectAimDir       = mel.eval("particleInstancer -name {instancer} -q -aimDirection {particle} ".format(
                                instancer = pInst, particle = pName))
            objectAimPos       = mel.eval("particleInstancer -name {instancer} -q -aimPosition {particle} ".format(
                                instancer = pInst, particle = pName))
            objectAimAxis      = mel.eval("particleInstancer -name {instancer} -q -aimAxis {particle} ".format(
                                instancer = pInst, particle = pName))
            objectAimUpAxis    = mel.eval("particleInstancer -name {instancer} -q -aimUpAxis {particle} ".format(
                                instancer = pInst, particle = pName))
            objectAimWorldUp   = mel.eval("particleInstancer -name {instancer} -q -aimWorldUp {particle} ".format(
                                instancer = pInst, particle = pName))
        
            bakeGroup          = pm.group(w=True, n=pTrans+"_BakedObjects", em=True)
                
            for fr in range(startFrame, endFrame+1):
                pm.currentTime(fr)
                print("Baking %s | Frame %04d" %(nPtc, fr))
                pCount = pm.nParticle(nPtc, q=True, ct=True)
                for i in range(pCount):
                    doubleAttrs = pm.nParticle(nPtc, q=True, ppd=True)
                    vectorAttrs = pm.nParticle(nPtc, q=True, ppv=True)
                    
                    pos = pm.nParticle(nPtc, q=True, order=i, at=objectPosition)
                    
                    if objectRotation:
                        rot = pm.nParticle(nPtc, q=True, order=i, at=objectRotation)

                    if objectScale:
                        size = pm.nParticle(nPtc, q=True, order=i, at=objectScale)
                    else:
                        size = (1,1,1)
                    
                    if objectIndex:
                        s = pm.nParticle(nPtc, q=True, order=i, at=objectIndex)
                        if isinstance(s, float):
                            s = [s]
                        sObjects = len(s)
                        instanceIndex = int(s[0])
                        if instanceIndex >= sObjects:
                            instanceIndex = sObjects-1
                    else:
                        instanceIndex = 0

                    if objectAimDir:
                        AimDirection = pm.nParticle(nPtc, q=True, order=i, at=objectAimDir)
                        objAimDir = mel.eval('unit(<<%s>>)' %([str(i) for i in AimDirection]))
                    else:
                        AimDirection = (1,0,0)
                        
                    if objectAimPos:
                        AimPosition = pm.nParticle(nPtc, q=True, order=i, at=objectAimPos)
                    else:
                        AimPosition = (0,0,0)
                        
                    if objectAimAxis:
                        AimAxis = pm.nParticle(nPtc, q=True, order=i, at=objectAimAxis)
                    else:
                        AimAxis = (1,0,0)
                        
                    if objectAimUpAxis:
                        AimUpAxis = pm.nParticle(nPtc, q=True, order=i, at=objectAimUpAxis)
                    else:
                        AimUpAxis = (0,1,0)

                    if objectAimWorldUp:
                        AimWorldUp = pm.nParticle(nPtc, q=True, order=i, at=objectAimWorldUp)
                    else:
                        AimWorldUp = (0,1,0)

                    matrix = pm.getAttr( pInst+".worldMatrix")
                    ObjAimAxis = pointMatrixMult (AimAxis, matrix)
                    ObjAimUp = pointMatrixMult (AimUpAxis, matrix)
                    ObjAimWup = pointMatrixMult (AimWorldUp, matrix)

                    instName = "%s_geo_%04d" %(pTrans, i)
                    instObject = pm.ls(instName)
                    if instObject:
                        instObject = instObject[0]
                    else:
                        instObject = pm.duplicate(objects[instanceIndex], name=instName, rr=True, instanceLeaf=True)[0]
                        
                    if not instObject in instances:
                        instances.append(instObject)
                    
                    if objectRotation:
                        for rotAttr in doubleAttrs:
                            if rotAttr == objectRotation:
                                pm.xform(instObject, ro=(rot[0], rot[0], rot[0]))
                        for rotAttr in vectorAttrs:
                            if rotAttr == objectRotation:
                                pm.xform(instObject, ro=rot)

                    elif objectAimDir:
                        pm.xform(instObject, ws=True, t=(0,0,0))
                        pm.xform(instObject, ws=True, t=(0,0,0), a=True, sh=(0,0,0))
                        pm.xform(bakeGroup, ws=True, t=objAimDir, a=True)
                        pm.aimConstraint(
                            bakeGroup, instObject, offset=(0,0,0), weight=1, aimVector=ObjAimAxis,
                            upVector=ObjAimUp, worldUpType="vector", worldUpVector=ObjAimWup
                        )
                        pm.aimConstraint(bakeGroup, instObject, e=True, rm=True)
                    elif objectAimPos:
                        pm.xform(instObject, ws=True, t=(0,0,0))
                        pm.xform(instObject, ws=True, t=pos, a=True, sh=(0,0,0))
                        pm.xform(bakeGroup, ws=True, t=AimPosition, a=True, sh=(0,0,0))
                        pm.aimConstraint(
                            bakeGroup, instObject, offset=(0,0,0), weight=1, aimVector=ObjAimAxis,
                            upVector=ObjAimUp, worldUpType="vector", worldUpVector=AimWorldUp
                        )
                        pm.aimConstraint(bakeGroup, instObject, e=True, rm=True)

                    if objectScale:
                        for scaleAttr in doubleAttrs:
                            if scaleAttr == objectScale:
                                pm.xform(instObject, s=(size[0], size[0], size[0]))
                        for scaleAttr in vectorAttrs:
                            if scaleAttr == objectScale:
                                pm.xform(instObject, s=size)
                    
                    pm.xform(instObject, ztp=True, wd=True, ws=True, cp=True, p=1)
                    pm.xform(instObject, ws=True, t=pos, a=True, wd=True)
                    
                    for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']:
                        pm.setKeyframe(instObject.name(), at=attr)
                        
                    
                        
        pm.xform(bakeGroup, a=True, t=(0,0,0))
        pm.parent(instances, bakeGroup, a=True)
        
        # Cleanup invisible frame
        for instObject in instances:
            keys = pm.keyframe(instObject.name(), query=True)
            for fr in keys:
                for attr in ['sx', 'sy', 'sz', 'v']:
                    if fr+1 not in keys:
                        pm.setKeyframe(instObject.name(), at=attr, t=fr+1, v=0)
                    if fr-1 not in keys:
                        pm.setKeyframe(instObject.name(), at=attr, t=fr-1, v=0)


### UI


class ParticleInstanceBaker(QDialog):
    def __init__(self):
        super(ParticleInstanceBaker, self).__init__(self.getAppWindow())
        self.closeExistingDialog()
        
        self.setWindowTitle("Particle Instance Baker")
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

        self.bakeFrameLayout = QHBoxLayout()
        self.bakeFrameLabel = QLabel('Frame :')
        self.bakeFrameStart = QSpinBox()
        self.bakeFrameDiv = QLabel('-')
        self.bakeFrameEnd = QSpinBox()
        for w in [self.bakeFrameLabel, self.bakeFrameStart, self.bakeFrameDiv, self.bakeFrameEnd]:
            self.bakeFrameLayout.addWidget(w)

        self.bakeButton = QPushButton("Bake Selected nParticles")

        for w in (self.bakeFrameLayout, self.bakeButton):
            try:
                self.masterLayout.addWidget(w)
            except:
                self.masterLayout.addLayout(w)
        

    def connectSignal(self):
        self.bakeButton.clicked.connect(self.bakeParticles)

    def initUI(self):
        self.bakeFrameLabel.setMaximumWidth(70)
        self.bakeFrameLabel.setMinimumWidth(70)
        for w in [self.bakeFrameStart, self.bakeFrameEnd]:
            w.setMinimum(-999999999)
            w.setMaximum(999999999)
        self.bakeFrameDiv.setMaximumWidth(10)
        self.bakeFrameDiv.setMinimumWidth(10)
        self.bakeFrameDiv.setAlignment(Qt.AlignCenter)
        
        self.bakeFrameStart.setValue(int(pm.playbackOptions(q=True, ast=True)))
        self.bakeFrameEnd.setValue(int(pm.playbackOptions(q=True, aet=True)))

    def bakeParticles(self):
        selectedParticles = []
        for o in pm.ls(sl=1):
            s = o.getShape()
            if s:
                oType = pm.nodeType(s)
                if oType == 'nParticle':
                    selectedParticles.append(s)

        bakeNParticles(
            nParticles=selectedParticles,
            startFrame= int(self.bakeFrameStart.text()),
            endFrame= int(self.bakeFrameEnd.text())
        )
        

w = ParticleInstanceBaker()
w.show()