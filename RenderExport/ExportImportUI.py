from maya import cmds, mel

import re, os
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

from Iris.Common.Maya.Scripts.Timo.RenderExport import ExportImportLightSetting
reload(ExportImportLightSetting)
from Iris.Common.Maya.Scripts.Timo.RenderExport import ExportImportRenderLayers
reload(ExportImportRenderLayers)
from Iris.Common.Maya.Scripts.Timo.RenderExport import ExportImportRenderSettings
reload(ExportImportRenderSettings)

class ExportImportData:
    def __init__(self):
        self.winID = 'ExportImportData'
        title = []
        for word in re.findall('^[a-z]+|[A-Z][^A-Z]*', self.winID):
            words = list(word)
            words[0] = words[0].upper()
            word = ''.join(words)
            title.append( word )
        self.title = ' '.join(title)
        self.xmlFile = ''
        self.xmlType = ''
        self.xmlValid = False
        self.cbxCount = 10
        self.objects = []
        self.attributes = []
        self.build_ui()
        
    def build_ui(self):
        if cmds.window(self.winID , exists=True):
            cmds.deleteUI(self.winID )
        cmds.window(self.winID , title=self.title + ' by Timo.ink' )
        cmds.window(self.winID , e=True, h=50, w=400)
        cmds.rowLayout("main_row", nc=3, adj=2, cw3=[5,250,5])
        cmds.columnLayout("spacer1", width=5, parent="main_row") #Padding
        cmds.columnLayout("main_col",rowSpacing=5, adj=True, parent="main_row")
        cmds.columnLayout("padding1", height=3, parent="main_col") #Padding
        cmds.rowLayout(parent="main_col", nc=2, cw2=[70,70])
        cmds.radioCollection('eiRadio')
        cmds.radioButton( label='Export', cc=lambda l: self.update_ui(), sl=True)
        cmds.radioButton( label='Import', cc=lambda l: self.update_ui())
        cmds.setParent("main_col")
        cmds.rowLayout(parent="main_col", nc=3, adj=2)
        cmds.text("xml_label", label="XML", width=25, align='right' )
        cmds.textFieldGrp("xml_path", adj=True, placeholderText="XML File", tcc=lambda l: self.update_ui(update=True) )
        cmds.button("xml_search", label="...", width=40, command=lambda l: self.get_xml_file() )
        cmds.setParent("main_col")
        
        cmds.frameLayout('obj_lay', label='Objects', labelAlign='top', borderStyle='in')
        cmds.columnLayout("obj_col",rowSpacing=5, adj=True)
        cmds.textScrollList('obj_list', sc=lambda : self.update_ui(update=False) )
        cmds.setParent("main_col")
        cmds.frameLayout('att_lay', label='Attributes', labelAlign='top', borderStyle='in')
        cmds.columnLayout("att_col",rowSpacing=5, adj=True)
        cmds.textScrollList('att_list', ams=True)
        cmds.setParent("main_col")
        cmds.button("xml_exec", label="Execute", width=40, command=lambda l: self.execute_command())
        
        cmds.columnLayout("padding2", height=3, parent="main_col") #Padding
        cmds.columnLayout("spacer2", width=5, parent="main_row") #Padding
        
        self.xmlImport = -1
        self.update_ui(update=True)
        # init UI
        cmds.textScrollList("obj_list", edit=True, selectIndexedItem=1)
        
    def showUI(self):
        cmds.showWindow(self.winID)
        
    def update_ui(self, update=True):
        rd = cmds.radioCollection( 'eiRadio', q=True, select=True )
        self.state = cmds.radioButton(rd, q=1, l=1)
        self.xmlImport = 0 if self.state == 'Export' else 1
        
        self.xmlFile = cmds.textFieldGrp("xml_path", q=True, text=True )
        # update textScrollList
        if self.xmlImport:
            self.objects = []
            self.attributes = []
            self.xml_file_check()
            cmds.textScrollList("obj_list", edit=True, ams=True)
        else:
            self.xmlValid = True if os.path.exists(os.path.dirname(cmds.textFieldGrp("xml_path", q=True, text=True ))) else False
            self.xmlType = ''
            self.objects = ['RenderLayers', 'RenderSettings', 'Lights']
            self.attributes = []
            cmds.textScrollList("obj_list", edit=True, ams=False)
        
        self.fill_ui(update=update)
        
        label = (self.xmlType if self.xmlType else 'Objects') if self.xmlImport else 'Data'
        cmds.frameLayout('obj_lay', edit=True, label=label)
        label = 'Attributes' if self.xmlImport else 'Objects'
        cmds.frameLayout('att_lay', edit=True, label=label)
            
        buttonEnable = True if self.xmlValid else False
        cmds.button("xml_exec", e=True, label=' '.join([self.xmlType, self.state]), enable=buttonEnable )
            
    def fill_textScrollList(self, name, list = []):
        cmds.textScrollList(name, edit=True, removeAll=True)
        if list:
            for item in list:
                cmds.textScrollList(name, edit=True, append=item)
            
    def fill_ui(self, update=False):
        if not self.xmlImport:
            exportData = cmds.textScrollList("obj_list", q=True, si=True)[0] if cmds.textScrollList("obj_list", q=True, si=True) else 'RenderLayers'
            if exportData == 'RenderLayers':
                self.attributes = [rl for rl in cmds.ls (type="renderLayer") if not cmds.referenceQuery( rl, isNodeReferenced=True )]
            elif exportData == 'RenderSettings':
                self.attributes = ['defaultRenderGlobals','vraySettings','redshiftOptions']
            elif exportData == 'Lights':
                lights = []
                lightTypes = cmds.listNodeTypes( 'light' )
                for lightType in lightTypes:
                    lights += cmds.ls(type=lightType, long=True)
                self.attributes = lights
                
        if update:
            self.fill_textScrollList("obj_list", list = self.objects)
        self.fill_textScrollList("att_list", list = self.attributes)
                
    def get_xml_file(self):
        dir = os.path.dirname(self.xmlFile) if self.xmlFile else ''
        xmlFile = cmds.fileDialog2(fm=self.xmlImport, ds=2, caption="XML File", startingDirectory=dir, fileFilter="XML Files (*.xml);; All Files (*.*)")
        if xmlFile:
            cmds.textFieldGrp("xml_path", e=True, text=xmlFile[0] )
            cmds.button("xml_exec", e=True, label=' '.join([self.xmlType, self.state]), enable=True)
        if self.xmlImport:
            self.update_ui(update=True)
    
    def xml_file_check(self):
        if self.xmlFile and os.path.exists(self.xmlFile):
            xmlRoot = None
            try:
                tree = ET.parse(self.xmlFile)
                root = tree.getroot()
                xmlRoot = root.getchildren()
                for xmlNode in xmlRoot:
                    nodes = xmlNode.getchildren()
                    if not xmlNode.attrib.get("name") in self.objects:
                        self.objects.append( xmlNode.attrib.get("name") )
                    for node in nodes:
                        if not node.tag in self.attributes:
                            self.attributes.append( node.tag )
                self.xmlType = root.tag
                self.xmlValid = True
            except Exception as args:
                print args
                self.xmlType = ''
                self.xmlValid = False
    
    def execute_command(self):
        if self.xmlImport:
            importData = cmds.textScrollList("obj_list", q=True, si=True)
            importAttr = cmds.textScrollList("att_list", q=True, si=True)
            if self.xmlType == 'RenderLayers':
                ExportImportRenderLayers.import_render_layers(self.xmlFile, renderLayers=importData, attributes=importAttr)
            elif self.xmlType == 'RenderSettings':
                ExportImportRenderSettings.import_render_settings(self.xmlFile, renderSettings=importData, attributes=importAttr)
            elif self.xmlType == 'Lights':
                ExportImportLightSetting.import_light_data(self.xmlFile, lightShapes=importData, attributes=importAttr)
                
        else:
            exportData = cmds.textScrollList("obj_list", q=True, si=True)
            exportObject = cmds.textScrollList("att_list", q=True, si=True)
            if exportData:
                if exportData[0] == 'RenderLayers':
                    ExportImportRenderLayers.export_render_layers(self.xmlFile, renderLayers=exportObject, openFolder=True)
                elif exportData[0] == 'RenderSettings':
                    ExportImportRenderSettings.export_render_settings(self.xmlFile, renderSettings=exportObject, openFolder=True)
                    print 'Exported'
                elif exportData[0] == 'Lights':
                    ExportImportLightSetting.export_light_data(self.xmlFile, lightShapes=exportObject, openFolder=True)

def run():
    ru = ExportImportData()
    ru.showUI()
    
#run()