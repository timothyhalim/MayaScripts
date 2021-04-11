rn = 'Box_PUB.ma'
cachePath = "Box_ANM.abc"

namespace = cmds.referenceQuery( rn, ns=True )[1:]
nodes = cmds.ls( cmds.referenceQuery( rn, n=True ), l=True )

cacheNS = '%s_ABC' % namespace
if cmds.namespace( ex=cacheNS ):
    existingNodes = cmds.ls( '%s:*' % cacheNS )
    if existingNodes:
        cmds.delete( existingNodes )
    cmds.namespace( rm=cacheNS )
    
cacheNodes = cmds.ls( cmds.file( cachePath, i=True, type='Alembic', rnn=True, ns=cacheNS ) )
alembicNode = []
for n in cacheNodes:
    if cmds.nodeType(n) == 'AlembicNode':
        cacheNodes.remove(n)
        n = cmds.rename(n, cacheNS+':AlembicNode')
        alembicNode.append(n)

connectedAttrs = cmds.listConnections(alembicNode, d=True, s=False, connections=True, plugs=True, scn=True)
connections = {}

while connectedAttrs:
    connections[connectedAttrs[0]] = connectedAttrs[1]
    connectedAttrs.pop(1)
    connectedAttrs.pop(0)
    
# Transfer connection
for c in connections:
    target = '%s:%s' %(namespace, connections[c].split( ':' )[-1])
    if cmds.objExists(target):
        cmds.connectAttr(c, target, f=True)
        
cmds.delete(cacheNodes)