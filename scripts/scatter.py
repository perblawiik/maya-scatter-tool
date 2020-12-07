import maya.cmds as cmds
import maya.OpenMaya as om

import math
import random

from hdt import hdtPoissonDiscSampling

def clampMax(value, max):
    if value > max:
        return max
    return value    
    
def basicRandomSampling( xMin, zMin, xMax, zMax, resolution, P ):
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

    # Calculate half of the cell size used for applying offsets
    deltaHalf = delta * 0.5
    
    # Sample xz-coordinates based on given probability P
    samples = []
    
    # Use a specific starting seed
    random.seed(0)
    for j in range(1, dimZ):
        for i in range(1, dimX):
            if random.uniform(1.0, 0.0) < P:
                # Add a random offset to reduce regular sampling artifacts
                x = xValues[i] + random.uniform( deltaHalf, -deltaHalf )
                z = zValues[j] + random.uniform( deltaHalf, -deltaHalf )
                samples.append((x, z))
    
    random.seed()
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
        
        """
        # Get all points
        points = om.MPointArray()
        fnMesh.getPoints( points, worldSpace )
        
        E1 = points[normalIds[1]] - points[normalIds[0]]
        E2 = points[normalIds[2]] - points[normalIds[0]]
        
        # Normal = E1 x E2 (cross product)
        N = om.MFloatVector()
        N.x = (E1.y * E2.z) - (E1.z * E2.y)
        N.y = (E1.z * E2.x) - (E1.x * E2.z)
        N.z = (E1.x * E2.y) - (E1.y * E2.x)
        
        N.normalize()
        faceNormal = (N.x, N.y, N.z)
        """

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
        # Clamp to 1.0 in case of numerical error
        zAngle = math.acos( clampMax( targetDir.y / xyLength, 1.0 ) )
    
    if targetDir.x > 0:
        zAngle *= -1.0
    
    #xAngle = math.acos( xyLength / targetDir.length)
    # Clamp to 1.0 in case of numerical error
    xAngle = math.acos( clampMax( xyLength, 1.0 ) )
    if targetDir.z < 0:
        xAngle *= -1.0
    
    # Convert from radian to degrees
    xAngleDeg = xAngle * 180 / math.pi
    zAngleDeg = zAngle * 180 / math.pi

    return xAngleDeg, zAngleDeg

def generateScatterPoints( resolutionField, probabilityField, surfaceOrientationCheckBox, 
                           locatorColorFieldGrp, randomRotMaxSliderGrp, randomRotMinSliderGrp, 
                           minScaleFieldGrp, maxScaleFieldGrp, locatorGroupNameFieldGrp, *pArgs ):
                               
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
    rotationMin = cmds.intSliderGrp( randomRotMinSliderGrp, query=True, value=True )
    rotationMax = cmds.intSliderGrp( randomRotMaxSliderGrp, query=True, value=True )
    minScale = cmds.floatFieldGrp( minScaleFieldGrp, query=True, value1=True )
    maxScale = cmds.floatFieldGrp( maxScaleFieldGrp, query=True, value1=True )
    scatterGroupName = cmds.textFieldGrp( locatorGroupNameFieldGrp, query=True, text=True )
    
    # Get FnMesh of selected object to check ray imtersection
    fnMesh = getFnMesh(selected[0])
    
    # Get bounding box coordinates
    bbox = cmds.exactWorldBoundingBox( selected[0] )
    
    # POISSON DISC SAMPLING
    # ---------------------
    discRadius = 2;
    samples = hdtPoissonDiscSampling( bbox[0], bbox[3], bbox[2], bbox[5], discRadius )
    
    # ---------------------
    
    # Generate sample coordinates
    #samples = basicRandomSampling( bbox[0], bbox[2], bbox[3], bbox[5], resolution, probability )
    
    # Create a group for the samples
    sampleGroup = cmds.group( em=True, name=scatterGroupName )
        
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
                
            if (rotationMax - rotationMin) > 0:
                cmds.setAttr( "{}.ry".format(spaceLoc[0]), random.uniform( rotationMax, rotationMin ) )
            
            
            scaling = 1.0
            if (minScale >= maxScale):
                scaling = minScale
            else:
                scaling = random.uniform( maxScale, minScale )
            
            cmds.setAttr( "{}.sx".format(spaceLoc[0]), scaling )
            cmds.setAttr( "{}.sy".format(spaceLoc[0]), scaling )
            cmds.setAttr( "{}.sz".format(spaceLoc[0]), scaling )
            
            cmds.parent( spaceLoc, sampleGroup )
    
    # Clear selection
    cmds.select( cl=True )
        
def createModels( scatterGroupNameFieldGrp, *pArgs ):
    # Check if a mesh is selected
    selected = cmds.ls( sl=True )
    numModels = len(selected)
    if numModels == 0:
        print("No mesh selected")
        return
        
    groupName = cmds.textFieldGrp( scatterGroupNameFieldGrp, query=True, text=True )
    
    if len(groupName) == 0:
        print("Group name not found")
        return

    # Get all space locators from the given group name 
    locators = cmds.ls( groupName, dag=1, type="transform" )
    
    if len(locators) < 2:
        print("Group not found")
        return
    
    for i in range( 1, len(locators) - 1 ):
        # Create new object
        if numModels == 1:
            newObject = cmds.instance( selected )
        else:
            # Randomly select model    
            index = random.randint(0, numModels-1)
            newObject = cmds.instance( selected[index] )

        # Get position and rotation of current locator
        position = cmds.xform( locators[i], q=True, ws=True, t=True )
        rotation = cmds.xform( locators[i], q=True, ws=True, ro=True )
        scaling = cmds.xform( locators[i], q=True, ws=True, s=True )
        orignalScaling = cmds.xform( newObject, q=True, ws=True, s=True )
        
        cmds.move( position[0], position[1], position[2], newObject, a=True )
        cmds.rotate( rotation[0], rotation[1], rotation[2], newObject )
        cmds.scale( orignalScaling[0] * scaling[0], orignalScaling[1] * scaling[0], orignalScaling[2] * scaling[0], newObject)

        # Remove locator
        cmds.delete( locators[i] )
    
    # Remove group   
    cmds.delete( locators[0] ) 
    
    # Clear selection
    cmds.select( cl=True )
	
	
