import maya.cmds as cmds
import maya.OpenMaya as om

from random import uniform as rand

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
    biDirectionalTest = False
    maxParam = 999999

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
    if intersectionFound:
        intersectionPoint = (intersectionPoints[0].x, intersectionPoints[0].y, intersectionPoints[0].z)
        
    return intersectionFound, intersectionPoint

def generateScatterPoints(num_points=50):
    # Check if a mesh is selected
    selected = cmds.ls( sl=True )
    if len(selected) == 0:
        print("No mesh selected")
        return
    
    # Get FnMesh of selected object to check ray imtersection
    fnMesh = getFnMesh(selected[0])
        
    for i in range( num_points ):
        # Instantiate a space locator
        spaceLoc = cmds.spaceLocator()
        
        # Set color of the locator
        shapeName = spaceLoc[0][0:7] + "Shape" + spaceLoc[0][7:]
        cmds.setAttr( "{}.overrideEnabled".format(shapeName), True )
        cmds.setAttr( "{}.overrideColor".format(shapeName), 17 )
        
        # Randomize ray origin
        rayOrigin = om.MFloatPoint(rand(10, -10), 0, rand(10, -10), 1.0)
        
        # Cast ray in negative y-direction
        rayDirection = om.MFloatVector(0, -1, 0)

        # Cast ray and check for intersection with given mesh
        intersectionFound, intersectionPoint = checkIntersection(fnMesh, rayOrigin, rayDirection)
        
        # Move locator to a random position
        if intersectionFound:
            cmds.move( intersectionPoint[0], intersectionPoint[1], intersectionPoint[2], spaceLoc )
        else :
            cmds.move( rayOrigin.x, rayOrigin.y, rayOrigin.z, spaceLoc )
        
    # Clear selection
    cmds.select(cl=True)
        
def createModels():
    # Get all space locators in the scene
    locators = cmds.ls( "locator*" )
    
    for i in range( len(locators) / 2 ):
        # Get position of current locator
        position = cmds.xform(locators[i], q=True, ws=True, t=True)
        
        # Create and move object to locator position
        cmds.move( position[0], position[1], position[2], cmds.polySphere()[0], a=True )
        
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