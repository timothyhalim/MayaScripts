'''
Render Multi Layer

Auto Queuing to render multiple layer in local render
Currently support vray
'''

from maya import cmds, mel
import os, sys
import multiprocessing

class Stopwatch: 
    def __init__(self):
        self.WinID = "RenderStopwatch"
        self.render = False
        
    def showUI(self):
        if cmds.window(self.WinID, exists=True):
            cmds.deleteUI(self.WinID)
        cmds.window(self.WinID, title="Render Stopwatch")
        cmds.window(self.WinID, e=True, s=False, h=30, w=300)
        cmds.columnLayout("col", rowSpacing=5, parent = self.WinID)
        cmds.button("refresh_btn", label="Refresh Render Layer", width=350, command=lambda l: self.refreshList())
        cmds.textScrollList("renderLayer_list", allowMultiSelection=True, width=350, selectCommand= lambda : self.update())
        cmds.rowLayout("cam_row", nc=2, parent="col")
        cmds.optionMenu("camera_list", label="", width=265, changeCommand= lambda l: self.update())
        cmds.button("update_btn", label="Refresh", width=80, command=lambda l: self.updateCamera())
        cmds.rowLayout("rdr_row", nc=3, parent="col")
        cmds.button("renderLayer_btn", label="Render Selected Layer", width=215, enable=False, command=lambda l: self.startRender(objonly=False))
        cmds.optionMenu("render_res", label="", width=80, changeCommand=lambda l: self.changeRes() )
        cmds.menuItem( label="50%", parent ="render_res")
        cmds.menuItem( label="75%", parent ="render_res")
        cmds.menuItem( label="100%", parent ="render_res")
        cmds.menuItem( label="150%", parent ="render_res")
        cmds.optionMenu("render_res", edit=True, select=3)
        cmds.checkBox("cb_log", label="Log", width=50, value=False)
        cmds.rowLayout("rdr_row2", nc=2, parent="col")
        cmds.button("renderObject_btn", label="Render Selected Object", width=215, enable=False, command=lambda l: self.startRender(objonly=True))
        cmds.button("cancal_btn", label="Abort Render", width=130, enable=True, command=lambda l: self.abortRender())
        cmds.showWindow(self.WinID)
        
        # curRes = cmds.optionVar (q='renderViewTestResolution')
        self.refreshList()
        self.updateCamera()
        self.update()
        
    def refreshList(self):
        cmds.textScrollList("renderLayer_list",edit=True, removeAll=True)
        renderLayers = [rl for rl in cmds.ls (type= "renderLayer") if not cmds.referenceQuery( rl, isNodeReferenced=True )]
        for renderLayer in renderLayers:
            if cmds.getAttr('%s.renderable' %(renderLayer)):
                cmds.textScrollList("renderLayer_list", edit=True, append=renderLayer)
        
    def updateCamera(self):
        for item in cmds.optionMenu("camera_list", q=True, ill=True) or []:
            cmds.deleteUI(item)
        cameras = cmds.ls (type= "camera")
        for scene_camera in cameras:
            if cmds.getAttr('%s.renderable' %(scene_camera)):
                cmds.menuItem( label=scene_camera, parent ="camera_list")

    def update(self):
        selectedLayer = cmds.textScrollList("renderLayer_list", q=True, selectItem=True)
        selectedCamera = cmds.optionMenu("camera_list", query=True, value=True)
        if selectedLayer and selectedCamera:
            cmds.button("renderLayer_btn", edit=True, enable=True)
            cmds.button("renderObject_btn", edit=True, enable=True)
        else:
            cmds.button("renderLayer_btn", edit=True, enable=False)
            cmds.button("renderObject_btn", edit=True, enable=False)
            
    def changeRes (self):
        renderResolution = cmds.optionMenu("render_res", query=True, value=True)
        def case(x):
            return {
                '50%': 4,
                '75%': 5,
                '150%': 8,
            }.get(x, 1)
        mel.eval("setTestResolutionVar("+str(case(renderResolution))+")")
            
    def startRender(self, objonly=False):
        from datetime import datetime
        
        cmds.optionMenu("render_res", edit=True, enable=False)
        selectedLayer = cmds.textScrollList("renderLayer_list", q=True, selectItem=True)
        selectedCamera = cmds.optionMenu("camera_list", query=True, value=True)
        #print selectedLayer
        openfile = cmds.file (q=True, sn=True)
        #print openfile
        dir = os.path.dirname(openfile)
        
        cmds.progressWindow(isInterruptable=1, max=len(selectedLayer))
        prg = 0
        self.render = True
        mel.eval("vrayShowVFB")
        message = os.environ['COMPUTERNAME']+"\r\n"
        message += "%s Cores" %(multiprocessing.cpu_count())+"\r\n"
        message += "=======================\n"
        for layer in selectedLayer:
            if self.render:
                prg += 1
                if cmds.objExists(layer) and cmds.objectType(layer, isType='renderLayer'):
                    cmds.progressWindow(edit=True, progress=prg)
                    if cmds.progressWindow(query=True, isCancelled=True) :
                        self.render = False
                    cmds.editRenderLayerGlobals(currentRenderLayer=layer)
                    sys.stdout.write ("\nRendering %s" %(layer))
                    start_time = datetime.now()
                    sys.stdout.write ( "Start time: %s" %(start_time.strftime('%Y/%m/%d %H:%M:%S')) )
                    # cmds.vray("-testresolutionenabled", "1")
                    cmds.vray("vfbControl", "-setregion", "reset", "-clearimage")
                    if objonly:
                        mel.eval('optionVar -intValue renderViewRenderSelectedObj on')
                        mel.eval("renderWindowRenderCamera render renderView %s" %(selectedCamera))
                        mel.eval('optionVar -intValue renderViewRenderSelectedObj off')
                    else:
                        mel.eval("renderWindowRenderCamera render renderView %s" %(selectedCamera))
                    end_time = datetime.now()
                    td = end_time-start_time
                    render_time = "%02d:%02d:%02d" %(td.seconds//3600, (td.seconds//60)%60, td.seconds%60)
                    cmds.vray("vfbControl", "-historyselect", "0", "-historycomment", "%s\n%s" %(layer, render_time))
                    print "End time: %s" %(end_time.strftime('%Y/%m/%d %H:%M:%S'))
                    sys.stdout.write ("\n%s Render Duration: %s" %(layer, render_time))
                    #print "======================="
                    if cmds.checkBox("cb_log", query=True, value=True):
                        message += ("Rendering %s" %(layer)+"\r\n")
                        message += ("Start time: %s" %(start_time.strftime('%Y/%m/%d %H:%M:%S'))+"\r\n")
                        message += ("End time: %s" %(end_time.strftime('%Y/%m/%d %H:%M:%S'))+"\r\n")
                        message += ("Duration %s" %(end_time-start_time)+"\r\n")
                        message += ("======================="+"\r\n")
                    
        if cmds.checkBox("cb_log", query=True, value=True):
            title = cmds.file( q = True, sceneName = True ) 
            win = cmds.window(title=title)
            cmds.window(win, e=True, s=False, h=30, w=300)
            cmds.columnLayout(rs = 5, parent=win)
            cmds.scrollField( w=300, h=300, editable=False, wordWrap=False, text=message )
            cmds.showWindow(win)
        
        cmds.optionMenu("render_res", edit=True, enable=True)
        cmds.progressWindow(endProgress=1)
        
    def abortRender(self):
        self.render = False
        cmds.progressWindow(endProgress=1)
        
def run():
    RS = Stopwatch()
    RS.showUI()

