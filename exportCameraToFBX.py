'''
Scripts to export maya camera to fbx

import thisScript  
run(cameraname, fbxoutputpath)
'''


from maya import cmds, mel
import os, subprocess

def run(cam, camFBXpath, openFolder=False):
	cmds.loadPlugin("fbxmaya.mll") # load fbx plugin
	if cam and camFBXpath:
		print 'Ti >> Exporting Camera'
		# Set Camera
		camClone = cmds.duplicate(cam, rr=True, name=cam+'_clone')[0]
		try:
			cmds.parent (camClone, world=True)
		except:
			pass
		cmds.select([cam, camClone])
		
		modelPanels = cmds.getPanel(type='modelPanel')
		visiblePanels = cmds.getPanel(vis=True)
		visibleModelPanels = [pan for pan in modelPanels if pan in visiblePanels]
		for panels in visibleModelPanels:
			mel.eval('enableIsolateSelect %s %d' % (panels, True) )
		
		# Unlock Attributes
		attr = ['.tx', '.ty', '.tz', '.rx', '.ry', '.rz']
		for a in attr:
			cmds.setAttr(camClone+a, lock=False)
		
		# Bake Camera
		cmds.refresh(suspend=True) # Pause Viewport
		currentFrame = cmds.currentTime(q=True)
		firstFrame = cmds.playbackOptions(min=True,q=True)
		lastFrame = cmds.playbackOptions(max=True,q=True)
		for i in range(int(firstFrame), int(lastFrame)+1):
			cmds.currentTime(int(i))
			worldTranslation = cmds.xform(cam, q=True, worldSpace=True, translation=True)
			tx = worldTranslation[0]
			ty = worldTranslation[1]
			tz = worldTranslation[2]
			worldRotation = cmds.xform(cam, q=True, worldSpace=True, rotation=True)
			rx = worldRotation[0]
			ry = worldRotation[1]
			rz = worldRotation[2]
			
			cmds.setAttr (camClone+'.tx', tx)
			cmds.setKeyframe (camClone+'.tx')
			cmds.setAttr (camClone+'.ty', ty)
			cmds.setKeyframe (camClone+'.ty')
			cmds.setAttr (camClone+'.tz', tz)
			cmds.setKeyframe (camClone+'.tz')
			cmds.setAttr (camClone+'.rx', rx)
			cmds.setKeyframe (camClone+'.rx')
			cmds.setAttr (camClone+'.ry', ry)
			cmds.setKeyframe (camClone+'.ry')
			cmds.setAttr (camClone+'.rz', rz)
			cmds.setKeyframe (camClone+'.rz')
			# cmds.setKeyframe(camClone, breakdown=0, hierarchy="none", controlPoints=0, shape=0)
		
		# Restore current frame
		cmds.currentTime(currentFrame)
		for panels in visibleModelPanels:
			mel.eval('enableIsolateSelect %s %d' % (panels, False) )
		cmds.refresh(suspend=False)
		
		# Export FBX
		if not os.path.exists(os.path.dirname(camFBXpath)):
			os.makedirs(os.path.dirname(camFBXpath))
		cmds.select(camClone)
		# FBX Setting
		mel.eval('FBXExportFileVersion -v FBX201000;')
		mel.eval('FBXExportConvertUnitString "cm";')
		mel.eval('FBXExportGenerateLog -v 0;')
		mel.eval('FBXExportInputConnections -v 0;') 
		mel.eval('FBXExport -f "%s" -s' %camFBXpath)
		# cmds.file( camFBXpath, force=True, options="v=0", type="FBX export", prompt=False, preserveReferences=True, exportSelected=True)
		
		# Clean Up
		print 'Ti >>', camFBXpath
		if openFolder:
			subprocess.Popen(r'explorer /select,'+(camFBXpath).replace("/", "\\"))
		cmds.delete(camClone)