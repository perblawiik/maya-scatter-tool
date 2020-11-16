import maya.cmds as cmds
import maya.OpenMaya as om
import functools
import math

from random import uniform as rand
    
def basicSampling( xMin, zMin, xMax, zMax, resolution, P ):
   
    sizeX = (xMax - xMin)
    sizeZ = (zMax - zMin)
    
    delta = 0
    dimX = 0
    dimZ = 0
    
    # Adjust grid dimensions based on the largest side
    if sizeX >= sizeZ:
        dimX = resolution
        dimZ = int((sizeZ/sizeX) * dimX)
        
        delta = sizeX / resolution
    else:
        dimZ = resolution
        dimX = int((sizeX/sizeZ) * dimZ)
        
        delta = sizeZ / resolution
        
    # Generate a discrete grid by interpolating between min and max
    xValues = []
    zValues = []
    for i in range(dimX):
        xValues.append( lerp( xMin, xMax, i / float(dimX) ) )
        
    for i in range(dimZ):
        zValues.append( lerp( zMin, zMax, i / float(dimZ) ) )

    # Calculate a third of the cell size used for applying offsets
    deltaHalf = delta * 0.5
    
    # Sample xz-coordinates based on given probability P
    samples = []
    for j in range(1, dimZ):
        for i in range(1, dimX):
            if rand(1.0, 0.0) < P:
                # Add a random offset to reduce regular sampling artifacts
                x = xValues[i] + rand( deltaHalf, -deltaHalf )
                z = zValues[j] + rand( deltaHalf, -deltaHalf )
                samples.append((x, z))
    
    return samples
                
def lerp( a, b, t ):
    return a * (1 - t) + b * t
                
def getFnMesh( meshName ):
    # Clear selection
    cmds.select( cl=True )
    om.MGlobal.selectByName( meshName )
    selectionList = om.MSelectionList()
    
    om.MGlobal.getActiveSelectionList( selectionList )
    item = om.MDagPath()
    selectionList.getDagPath( 0, item )
    item.extendToShape()

    return om.MFnMesh(item)

def checkIntersection( fnMesh, rayOrigin, rayDirection ):   
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
    intersectionFound = fnMesh.allIntersections( rayOrigin, rayDirection, faceIds, triangleIds, sortedIds,
                                  worldSpace, maxParam, biDirectionalTest,
                                  accelParams, sortIntersections, intersectionPoints,
                                  intersectionRayParams, intersectionFaces, intersectionTriangles, 
                                  intersectBarycentrics1, intersectBarycentrics2, intersectionTolerance )
                                  
    intersectionPoint = (0,0,0)
    faceNormal = (0,0,0)
    
    if intersectionFound:
        # The first intersection point in the array is the closest to the ray origin
        intersectionPoint = (intersectionPoints[0].x, intersectionPoints[0].y, intersectionPoints[0].z)
        
        # Get the indices of the vertex normals of the intersection face
        normalIds = om.MIntArray()
        fnMesh.getFaceNormalIds( intersectionFaces[0], normalIds )
        
        # Get all normals of the mesh
        normals = om.MFloatVectorArray()
        fnMesh.getNormals( normals, worldSpace )
        
        # Sum the vertex normals to approximate the face normal
        n = normalIds.length()
        sum = om.MFloatVector()
        for i in range(n):
            sum += normals[normalIds[i]]
            
        sum /= n
        sum.normalize()
        faceNormal = (sum.x, sum.y, sum.z)

    return intersectionFound, intersectionPoint, faceNormal
    
def aimY(vec):
    # Convert to OpenMaya vector
    targetDir = om.MFloatVector(vec[0], vec[1], vec[2])
    
    xyLength = math.sqrt( targetDir.x * targetDir.x + targetDir.y * targetDir.y )

    # Make sure not to divide by zero (this is the case if targetDir is parallel to the z axis
    if xyLength < 0.00001:
        zAngle = math.pi * 0.5
        if targetDir.x < 0:
            zAngle *= -1.0
    else:
        zAngle = math.acos( targetDir.y / xyLength )
    
    if targetDir.x > 0:
        zAngle *= -1.0
    
    xAngle = math.acos( xyLength / targetDir.length() )
    if targetDir.z < 0:
        xAngle *= -1.0
    
    # Convert from radian to degrees
    xAngleDeg = xAngle * 180 / math.pi
    zAngleDeg = zAngle * 180 / math.pi

    return xAngleDeg, zAngleDeg

def generateScatterPoints( resolutionField, probabilityField, surfaceOrientationCheckBox, locatorColorFieldGrp, *pArgs ):
    # Check if a mesh is selected
    selected = cmds.ls( sl=True )
    if len(selected) == 0:
        print("No mesh selected")
        return
    
    # Get input field values from UI
    resolution = cmds.intFieldGrp( resolutionField, query=True, value1=True )
    probability = cmds.floatSliderGrp( probabilityField, query=True, value=True )
    useSurfaceOrientation = cmds.checkBoxGrp( surfaceOrientationCheckBox, query=True, value1=True )
    locatorColor = cmds.intFieldGrp( locatorColorFieldGrp, query=True, value=True )
    
    # Get FnMesh of selected object to check ray imtersection
    fnMesh = getFnMesh(selected[0])
    
    # Get bounding box coordinates
    bbox = cmds.exactWorldBoundingBox( selected[0] )
    
    # Generate sample coordinates
    samples = basicSampling( bbox[0], bbox[2], bbox[3], bbox[5], resolution, probability )
    
    for coordinates in samples:
        rayOrigin = om.MFloatPoint(coordinates[0], bbox[4] + 10.0, coordinates[1], 1.0)
        
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
            cmds.setAttr( "{}.overrideRGBColors".format(shapeName), True )
            cmds.setAttr( "{}.overrideColorR".format(shapeName), locatorColor[0] )
            cmds.setAttr( "{}.overrideColorG".format(shapeName), locatorColor[1] )
            cmds.setAttr( "{}.overrideColorB".format(shapeName), locatorColor[2] )
            
            # Set position
            cmds.move( intersectionPoint[0], intersectionPoint[1], intersectionPoint[2], spaceLoc )
            
            # Adjust orientation based on the face normal
            if useSurfaceOrientation:
                xAngleDeg, zAngleDeg = aimY( faceNormal )
                cmds.setAttr( "{}.rx".format(spaceLoc[0]), xAngleDeg )
                cmds.setAttr( "{}.rz".format(spaceLoc[0]), zAngleDeg )
    
    # Clear selection
    cmds.select( cl=True )
    
    return
        
def createModels():
    # Check if a mesh is selected
    selected = cmds.ls( sl=True )
    if len(selected) == 0:
        print("No mesh selected")
        return

    # Get all space locators in the scene
    locators = cmds.ls( "locator*" )
    
    for i in range( len(locators) / 2 ):
        # Get position and rotation of current locator
        position = cmds.xform( locators[i], q=True, ws=True, t=True )
        rotation = cmds.xform( locators[i], q=True, ws=True, ro=True )

        # Create and move object to locator position
        cmds.instance( selected )
        cmds.move( position[0], position[1], position[2], selected, a=True )
        cmds.rotate( rotation[0], rotation[1], rotation[2], selected )

        # Remove locator
        cmds.delete( locators[i] )
        
    # Clear selection
    cmds.select( cl=True )
	
	
#----------------#
# User Interface #
#----------------#

# Check if window exists
if cmds.window( 'scatterToolUI' , exists = True ) :
    cmds.deleteUI( 'scatterToolUI' ) 

# Create window 
toolWindow = cmds.window( 'scatterToolUI', title="Scatter Tool", width=300, height=300 )

cmds.columnLayout( adj=True )

cmds.separator( h=20, style="none" )
cmds.text( label="Scatter Point Generator" )
cmds.separator( h=10, style="none" )

resolutionField = cmds.intFieldGrp( numberOfFields=1, label="Sample Resolution", value1=20 )

cmds.separator( h=6, style="none" )

probabilityField = cmds.floatSliderGrp( label="Probability Distribution", min=0.0, max=1.0, 
                                        value=0.5, step=0.01, field=True )
                                        
cmds.separator( h=6, style="none" )

surfaceOrientationCheckBox = cmds.checkBoxGrp( numberOfCheckBoxes=1, label="Adjust to Surface", value1=True )

cmds.separator( h=6, style="none" )

locatorColorFieldGrp = cmds.intFieldGrp( numberOfFields=3, label="Scatter Point Color", 
                                         value1=255, value2=0, value3=0 )

cmds.separator( h=10, style="none" )

cmds.button( "Generate Scatter" , command=functools.partial( generateScatterPoints,
                                                    resolutionField,
                                                    probabilityField,
                                                    surfaceOrientationCheckBox,
                                                    locatorColorFieldGrp ) ) 
cmds.separator( h=20 )

cmds.button( "Add Models" , c = "createModels()" ) 

cmds.showWindow( toolWindow ) 
