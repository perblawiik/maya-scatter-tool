import maya.cmds as cmds
import maya.OpenMaya as om
import math

from random import uniform as rand

def computeBoundingBox(fnMesh):
    points = om.MPointArray()
    fnMesh.getPoints(points, om.MSpace.kWorld)
    vertices = [om.MVector(points[i]) for i in range(points.length())]
    
    xMin = vertices[0].x
    yMin = vertices[0].y
    zMin = vertices[0].z
    
    xMax = vertices[1].x
    yMax = vertices[1].y
    zMax = vertices[1].z

    for vertex in vertices:
        if vertex.x < xMin:
            xMin = vertex.x
        if vertex.x > xMax:
            xMax = vertex.x
            
        if vertex.y < yMin:
            yMin = vertex.y
        if vertex.y > yMax:
            yMax = vertex.y
            
        if vertex.z < zMin:
            zMin = vertex.z
        if vertex.z > zMax:
            zMax = vertex.z
    
    min = (xMin, yMin, zMin)
    max = (xMax, yMax, zMax)
    
    return min, max

def getFnMesh(meshName):
    # Clear selection
    cmds.select(cl=True)
    om.MGlobal.selectByName(meshName)
    selectionList = om.MSelectionList()
    
    om.MGlobal.getActiveSelectionList(selectionList)
    item = om.MDagPath()
    selectionList.getDagPath(0, item)
    item.extendToShape()

    return om.MFnMesh(item)

def checkIntersection(fnMesh, rayOrigin, rayDirection):   
    # No specified face IDs
    faceIds = None
    # No specified triangle IDs
    triangleIds = None
    # IDs are not sorted
    sortedIds = False

    # No specified radius to search around the ray origin
    maxParam = 999999
    biDirectionalTest = False

    # Coordinate space constraints
    worldSpace = om.MSpace.kWorld

    # No intersection acceleration
    accelParams = None
    
    # Intersections should be sorted in ascending order
    sortIntersections = True

    # Arrays for saving intersection info
    intersectionPoints = om.MFloatPointArray()
    intersectionRayParams = om.MFloatArray()
    intersectionFaces = om.MIntArray()
    intersectionTriangles = None
    intersectBarycentrics1= None
    intersectBarycentrics2 = None

    # Tolerance value of the intersection
    intersectionTolerance = 0.0001

    # Finds all intersections
    intersectionFound = fnMesh.allIntersections(rayOrigin, rayDirection, faceIds, triangleIds, sortedIds,
                                  worldSpace, maxParam, biDirectionalTest,
                                  accelParams, sortIntersections, intersectionPoints,
                                  intersectionRayParams, intersectionFaces, intersectionTriangles, 
                                  intersectBarycentrics1, intersectBarycentrics2, intersectionTolerance)
                                  
    intersectionPoint = (0,0,0)
    faceNormal = (0,0,0)
    
    if intersectionFound:
        intersectionPoint = (intersectionPoints[0].x, intersectionPoints[0].y, intersectionPoints[0].z)
        
        normalIds = om.MIntArray()
        fnMesh.getFaceNormalIds(intersectionFaces[0], normalIds)
        
        normals = om.MFloatVectorArray()
        fnMesh.getNormals(normals,worldSpace)
        
        n = normalIds.length()
        sum = om.MFloatVector()
        for i in range(n):
            sum += normals[normalIds[i]]
            print((normals[normalIds[i]].x,normals[normalIds[i]].y,normals[normalIds[i]].z))
            
        sum /= n
        
        sum.normalize()
        faceNormal = (sum.x, sum.y, sum.z)
        print(faceNormal)
        
 
    return intersectionFound, intersectionPoint, faceNormal
    
    
def aimY(faceNormal):
    b = om.MFloatVector(faceNormal[0], faceNormal[1], faceNormal[2])
    
    xyLength = math.sqrt(b.x*b.x+b.y*b.y)
    vecLength = math.sqrt(b.x*b.x + b.y*b.y + b.z*b.z)
    if xyLength == 0:
        if b.x > 0:
            zAngle = math.pi*0.5
        else:
            zAngle = -math.pi *0.5 
    else:
        zAngle = math.acos(b.y/xyLength)
    
    xAngle = math.acos(xyLength/vecLength)
    
    if b.z > 0:
        xAngle = xAngle
    else:
        xAngle = -xAngle
    
    
    
    xAngleDeg = xAngle *180/math.pi
    
    
    if b.x > 0:
        zAngle = zAngle
    else:
        zAngle = -zAngle
    
    zAngleDeg = zAngle * 180/math.pi
    
    return xAngleDeg,zAngleDeg
        
            
    


def generateScatterPoints(num_points=10):
    # Check if a mesh is selected
    selected = cmds.ls( sl=True )
    if len(selected) == 0:
        print("No mesh selected")
        return
    
    # Get FnMesh of selected object to check ray imtersection
    fnMesh = getFnMesh(selected[0])
    
    # Compute bounding volume
    min, max = computeBoundingBox(fnMesh)
    
    for i in range( num_points ):
        # Randomize ray origin
        rayOrigin = om.MFloatPoint(rand(max[0], min[0]), max[1] + 10.0, rand(max[2], min[2]), 1.0)
        
        # Cast ray in negative y-direction
        rayDirection = om.MFloatVector(0, -1, 0)

        # Cast ray and check for intersection with given mesh
        intersectionFound, intersectionPoint, faceNormal = checkIntersection(fnMesh, rayOrigin, rayDirection)
        
        # Move locator to a random position
        if intersectionFound:
            # Instantiate a space locator
            spaceLoc = cmds.spaceLocator()
            
            # Set color of the locator
            shapeName = spaceLoc[0][0:7] + "Shape" + spaceLoc[0][7:]
            cmds.setAttr( "{}.overrideEnabled".format(shapeName), True )
            cmds.setAttr( "{}.overrideColor".format(shapeName), 17 )
            
            # Set position
            cmds.move( intersectionPoint[0], intersectionPoint[1], intersectionPoint[2], spaceLoc )
            
            xAngleDeg,zAngleDeg = aimY(faceNormal)
            
            cmds.setAttr( "{}.rx".format(spaceLoc[0]), xAngleDeg )
            cmds.setAttr( "{}.rz".format(spaceLoc[0]), -zAngleDeg )

            
            #cmds.rotate(xAngleDeg,0,0, spaceLoc )
            #cmds.rotate(0,0,zAngleDeg, spaceLoc )

            #cmds.rotete(zAngleDeg,spaceLoc)
            
            print(xAngleDeg)
            print(zAngleDeg)
        
    # Clear selection
    cmds.select(cl=True)
        
def createModels():
    # Get all space locators in the scene
    locators = cmds.ls( "locator*" )
    
    for i in range( len(locators) / 2 ):
        # Get position of current locator
        position = cmds.xform(locators[i], q=True, ws=True, t=True)
        rotation = cmds.xform(locators[i], q=True, ws=True, ro=True)

        
        # Create and move object to locator position
        cube =  cmds.polyCube()[0]
        cmds.move( position[0], position[1], position[2], cube, a=True )
        cmds.rotate(rotation[0],rotation[1],rotation[2], cube )

        # Remove locator
        cmds.delete( locators[i] )
        
    # Clear selection
    cmds.select(cl=True)
	
	
#----------------#
# User Interface #
#----------------#

# Check if window exists
if cmds.window( 'scatterToolUI' , exists = True ) :
    cmds.deleteUI( 'scatterToolUI' ) 

# Create window 
toolWindow = cmds.window( 'scatterToolUI', title="Scatter Tool", width = 200,
    mnb = False, mxb = False, sizeable = True, rtf = True )

general = cmds.rowColumnLayout ( nc = 1 , cw = ( 1 , 200 ) ) 

cmds.separator(h=10)
cmds.button( 'Generate Scatter' , c = 'generateScatterPoints( )' ) 
cmds.separator(h=10)
cmds.button( 'Add Models' , c = 'createModels( )' ) 
cmds.separator(h=10)

cmds.showWindow( toolWindow ) 
