import traceback
import maya

import json

def getRenderSetupWindow():
	from maya.app.renderSetup.views import renderSetup
	window, propEditor = maya.app.renderSetup.views.renderSetup.createUI()
	
	return window

def getRenderSetupView():
	from maya.app.renderSetup.views.renderSetupWindow import RenderSetupView
	window = getRenderSetupWindow()
	view = window.findChild( RenderSetupView )
	
	return view

def import_render_layers( filepath ):
	rsWindow = getRenderSetupView()
	localModelRef = rsWindow.model()
	with open(filepath, "r") as file:
		# Catch all kind of errors but still continue to search for
		# the appropriate template files. The directory could contain
		# faulty json files and/or files which are not render setup template files.
		try:
			dic = json.load(file)
			objList = dic if isinstance(dic, list) else [dic]
			if localModelRef.isAcceptableTemplate(objList):
				# Only preserve a partial filepath (i.e. remove the user template directory part)
				localModelRef.importTemplate( objList )
		except Exception, args:
			# Ignore errors because there is no need to display unexpected json files
			print Exception, args
			traceback.print_exc()
			pass
		# renderSetup.instance().decode(json.load(file), renderSetup.DECODE_AND_OVERWRITE, None)
		
	try:
		maya.mel.eval('deleteUI unifiedRenderGlobalsWindow')
	except:
		pass

def export_render_layers( filepath, note = None):
	import maya.app.renderSetup.model.renderSetup as renderSetup
	with open( filepath, "w+") as file:
		json.dump(renderSetup.instance().encode(note), fp=file, indent=2, sort_keys=True)