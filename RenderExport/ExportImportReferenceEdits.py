from maya import cmds

import os, re
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

def string_to_dict(text, pattern):
	regex = re.sub(r'{(.+?)}', r'(?P<_\1>.+)', pattern)
	keys = re.findall(r'{(.+?)}', pattern)
	values = list(re.search(regex, text).groups()) if re.search(regex, text) else ['' for i in keys]
	_dict = dict(zip(keys, values))
	return _dict

refEdits = []

# Get List of reference edit
def get_refedits( masterReference ):
	referenceFiles = cmds.referenceQuery(masterReference, ch=True, filename=True)
	for referenceFile in referenceFiles:
		for edit in cmds.referenceQuery(referenceFile, editStrings=True):
			if not edit in refEdits:
				refEdits.append (edit)
	return refEdits

# Export
def export_refedits( xmlPath, refEdits, excludeAttr=['renderLayerInfo', 'displaySmoothMesh', 'dispResolution', 'translateX', 'translateY', 'translateZ'], excludeType=['animCurveTL', 'animCurveTA', 'animCurveTU', 'blendShape', 'pairBlend', 'skinCluster', 'parentConstraint', 'hyperLayout', 'hyperView', 'joint', 'camera', 'blendShape', 'skinCluster'] ):
	if xmlPath:
		print 'Exporting Reference Edits to {xmlPath}'.format(xmlPath=xmlPath)
		if not os.path.exists(os.path.dirname(xmlPath)):
			os.makedirs(os.path.dirname(xmlPath))
		if os.path.isdir(os.path.dirname(xmlPath)):
			root = ET.Element("ReferenceEdits")
			root.attrib["fileName"] = cmds.file (q=True, sn=True)
			for edit in sorted(refEdits):
				tag = re.findall(r'\S+', edit)[0]
				editTypeList = [c.tag for c in root.getchildren()]
				if tag in editTypeList:
					editType = root.getchildren()[editTypeList.index(tag)]
				else:
					editType = ET.SubElement(root, tag)
					
				if edit.startswith(('connectAttr', 'disconnectAttr')):
					parameters = ' '.join(re.findall(r'-\S+', edit)) if re.findall(r'-\S+', edit) else ''
					command = re.sub(parameters, '', edit)
					connectPattern = '{command} "{source}" "{destination}"'
					cmd = string_to_dict(command, connectPattern)
					sourceOutput = cmd['source']
					sourceObject = '.'.join(sourceOutput.split('.')[:-1])
					sourceAttribute = sourceOutput.replace(sourceObject+'.', '')
					sourceObjectType = cmds.nodeType(sourceObject) if cmds.objExists(sourceObject) else None
					destInput = cmd['destination']
					destObject = '.'.join(destInput.split('.')[:-1])
					destAttribute = destInput.replace(destObject+'.', '')
					destObjectType = cmds.nodeType(destObject) if cmds.objExists(destObject) else None
					
					# Filter reference edit
					if (sourceObjectType and destObjectType):
						if ( not sourceObjectType in excludeType and not destObjectType in excludeType):
							if ( not sourceAttribute in excludeAttr and not destAttribute in excludeAttr):
								writeEdit = ET.SubElement(editType, "edit")
								writeEdit.attrib["command"] = edit
								# writeEdit.attrib["parameter"] = parameters
								# writeEdit.attrib["sourceAttribute"] = sourceAttribute
								# writeEdit.attrib["sourceObject"] = sourceObject
								# writeEdit.attrib["sourceObjectType"] = sourceObjectType
								# writeEdit.attrib["destAttribute"] = destAttribute
								# writeEdit.attrib["destObject"] = destObject
								# writeEdit.attrib["destObjectType"] = destObjectType
								# print '================'
								# print 'Command	:', edit
								# print 'Parameters |', parameters
								# print 'Source		| attribute:%s, type: %s, name:%s' %(sourceAttribute, sourceObjectType, sourceObject)
								# print 'Destination| attribute:%s, type: %s, name:%s' %(destAttribute, destObjectType, destObject)
				elif edit.startswith('parent'):
					# print edit
					pass
				elif edit.startswith('setAttr'):
					parameters = ' '.join(re.findall(r'-\S+', edit)) if re.findall(r'-\S+', edit) else ''
					command = re.sub('\s+', ' ', re.sub(parameters, '', edit))
					pattern = '{command} {attribute} {value}'
					cmd = string_to_dict(command, pattern)
					object = cmd['attribute']
					objName = '.'.join(object.split('.')[:-1])
					objType = cmds.nodeType(objName) if cmds.objExists(objName) else None
					objAttribute = object.replace(objName+'.', '')
					objValue = cmd['value']
					
					if objType:
						if not objType in excludeType:
							if not objAttribute in excludeAttr:
								writeEdit = ET.SubElement(editType, "edit")
								writeEdit.attrib["command"] = edit
								# writeEdit.attrib["parameter"] = parameters
								# writeEdit.attrib["objAttribute"] = objAttribute
								# writeEdit.attrib["objName"] = objName
								# writeEdit.attrib["objValue"] = objValue
								# writeEdit.attrib["objType"] = objType
								# print '================'
								# print 'Command	:', edit
								# print 'Parameters |', parameters
								# print 'setAttr	| attribute:%s, value:%s, type:%s, name:%s' %(objAttribute, objValue, objType, objName)
								
				elif edit.startswith(('addAttr', 'deleteAttr')):
					parameters = ' '.join(re.findall(r'-\S+\s\S+', edit)) if re.findall(r'-\S+\s\S+', edit) else ''
					command = re.sub('\s+', ' ', re.sub(parameters, '', edit))
					pattern = '{command} {object}'
					cmd = string_to_dict(command, pattern)
					objName = '.'.join(cmd['object'].replace('"','').split('.')[:-1]) if len(cmd['object'].replace('"','').split('.')) > 1 else cmd['object'].replace('"','')
					objAttribute = cmd['object'].replace('"','').split('.')[-1] if len(cmd['object'].replace('"','').split('.')) > 1 else 'None'
					objType = cmds.nodeType(objName) if cmds.objExists(objName) else None
					
					if objType:
						writeEdit = ET.SubElement(editType, "edit")
						writeEdit.attrib["command"] = edit
						# writeEdit.attrib["parameter"] = parameters
						# writeEdit.attrib["objAttribute"] = objAttribute
						# writeEdit.attrib["objName"] = objName
						# writeEdit.attrib["objType"] = objType
						# print '================'
						# print 'Command	:', edit
						# print 'Parameters |', parameters
						# print '			| type:%s, name:%s' %(objType, objName)
			
			tostring = ET.tostring(root)
			domObject = parseString(tostring)
			domObject.toprettyxml(encoding='utf-8')
			with open(xmlPath, "w") as f:
				domObject.writexml(f, addindent='\t', newl='\n')
		
		print 'Export of ReferenceEdits done!'

def import_refedits( xmlPath, type = ['connectAttr', 'disconnectAttr', 'parent', 'setAttr', 'addAttr', 'deleteAttr']):
	from maya import mel
	if xmlPath:
		if os.path.exists(xmlPath):
			xmlRoot = None
			try:
				tree = ET.parse(xmlPath)
				root = tree.getroot()
				xmlRoot = root.getchildren()
			except Exception, e:
				raise Exception("%s is not a valid xml file" % xmlPath)
			
			for xmlNode in xmlRoot:
				if xmlNode.tag in type:
					nodes = xmlNode.getchildren()
					for node in nodes:
						try:
							mel.eval( node.attrib.get('command') )
						except Exception, args:
							print Exception, args

# masterReference = 'X:/BOX/Episodes/EP102/Scenes/SH049.00/BOX_EP102_SH049.00_ANM.ma'
# xmlPath = 'X:/BOX/Episodes/EP102/Scenes/SH049.00/BOX_EP102_SH049.00_LGT_referenceEdit.xml'

# export_refedits( xmlPath, get_refedits( masterReference ) )
# import_refedits( xmlPath )