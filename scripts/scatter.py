import maya.cmds as cmds
import maya.OpenMaya as om

import math
import random

from basic_sampler import basicRandomSampling
from hdt import hdtPoissonDiscSampling

def mergeBoundingBoxes(bboxes):
    bbox = bboxes[0]
    for i in range(1, len(bboxes)):
        # Min X, Y, Z - coordinates
        if bbox[0] > bboxes[i][0]:
            bbox[0] = bboxes[i][0]
        if bbox[1] > bboxes[i][1]:
            bbox[1] = bboxes[i][1]
        if bbox[2] > bboxes[i][2]:
            bbox[2] = bboxes[i][2]
        # Max X, Y, Z - coordinates
        if bbox[3] < bboxes[i][3]:
            bbox[3] = bboxes[i][3]
        if bbox[4] < bboxes[i][4]:
            bbox[4] = bboxes[i][4]
        if bbox[5] < bboxes[i][5]:
            bbox[5] = bboxes[i][5]
            
    return bbox

def computeNormal(V0, V1, V2):
    E1 = V1 - V0
    E2 = V2 - V0
    
    # Normal = E1 x E2 (cross product)
    N = om.MFloatVector()
    N.x = (E1.y * E2.z) - (E1.z * E2.y)
    N.y = (E1.z * E2.x) - (E1.x * E2.z)
    N.z = (E1.x * E2.y) - (E1.y * E2.x)
    
    N.normalize()
    return (N.x, N.y, N.z)
        
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

def checkIntersections( fnMeshes, rayOrigin, rayDirection ):   
    # No specified triangle IDs
    triangleIds = None
    # IDs are not sorted
    sortedIds = False
    
    # Coordinate space constraints
    worldSpace = om.MSpace.kWorld

    # No specified radius to search around the ray origin
    maxParam = 9999999999
    
    # Do not test in negative direction
    biDirectionalTest = False

    # No intersection acceleration
    accelParams = None
    
    # References and pointers for saving intersection info
    hitPoint = om.MFloatPoint()
    
    hitRayParams = om.MScriptUtil(0.0)
    hitRayParamsPtr = hitRayParams.asFloatPtr()

    hitFace = om.MScriptUtil()
    hitFace.createFromInt(0)
    hitFacePtr = hitFace.asIntPtr()
    
    hitTriangle = None
    hitBarycentric1= None
    hitBarycentric2 = None

    # Tolerance value of the intersection
    hitTolerance = 0.0001

    # Arrays for storing multiple intersections
    closestFace = om.MScriptUtil()
    closestFace.createFromInt(0)
    minDistance = 9999999999
    intersectionPoint = (0,0,0)
    intersectionFound = False
    meshIndex = -1
    
    for i in range(len(fnMeshes)):
        # Select face ids
        faceIds = None
        if len(fnMeshes[i][1]) > 0:
            faceIds = om.MIntArray()
            for id in fnMeshes[i][1]:
                faceIds.append(id)
        
        # Check for intersection
        if fnMeshes[i][0].closestIntersection( rayOrigin, rayDirection, faceIds, triangleIds, sortedIds,
                                      worldSpace, maxParam, biDirectionalTest, accelParams, 
                                      hitPoint, hitRayParamsPtr, hitFacePtr, hitTriangle, 
                                      hitBarycentric1, hitBarycentric2, hitTolerance ):
                                          
            intersectionFound = True 
            hitDistance = hitRayParams.getFloat(hitRayParamsPtr)
            if hitDistance < minDistance:
                minDistance = hitDistance
                intersectionPoint = (hitPoint.x, hitPoint.y, hitPoint.z)
                closestFace = om.MScriptUtil(hitFacePtr).asInt()
                meshIndex = i
       
    faceNormal = (0,1,0)
        
    if intersectionFound:
        # Get the indices of the vertex normals of the intersection face
        normalIds = om.MIntArray()
        fnMeshes[meshIndex][0].getFaceNormalIds( closestFace, normalIds )

        # Get all normals of the mesh
        normals = om.MFloatVectorArray()
        fnMeshes[meshIndex][0].getNormals( normals, worldSpace )
        
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
        
        # Compute normal based on cross product
        faceNormal = computeNormal( points[normalIds[0]], points[normalIds[1]], points[normalIds[2]] )
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
        zAngle = math.acos( min( targetDir.y / xyLength, 1.0 ) )
    
    if targetDir.x > 0:
        zAngle *= -1.0
    
    #xAngle = math.acos( xyLength / targetDir.length)
    # Clamp to 1.0 in case of numerical error
    xAngle = math.acos( min( xyLength, 1.0 ) )
    if targetDir.z < 0:
        xAngle *= -1.0
    
    # Convert from radian to degrees
    xAngleDeg = xAngle * 180 / math.pi
    zAngleDeg = zAngle * 180 / math.pi

    return xAngleDeg, zAngleDeg

def generateScatterPoints( resolutionField, probabilityField, surfaceOrientationCheckBox, 
                           locatorColorFieldGrp, randomRotMaxSliderGrp, randomRotMinSliderGrp, 
                           minScaleFieldGrp, maxScaleFieldGrp, locatorGroupNameFieldGrp,
                           samplerOptionMenu, discRadiusField, *pArgs ):
           
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
    rotationMin = -cmds.intSliderGrp( randomRotMinSliderGrp, query=True, value=True )
    rotationMax = cmds.intSliderGrp( randomRotMaxSliderGrp, query=True, value=True )
    minScale = cmds.floatFieldGrp( minScaleFieldGrp, query=True, value1=True )
    maxScale = cmds.floatFieldGrp( maxScaleFieldGrp, query=True, value1=True )
    scatterGroupName = cmds.textFieldGrp( locatorGroupNameFieldGrp, query=True, text=True )
    samplingMethod = cmds.optionMenu( samplerOptionMenu, query=True, value=True )
    discRadius = cmds.floatFieldGrp( discRadiusField, query=True, value1=True )
    
    # Extract selected meshes and face ids
    meshDict = {}
    for s in selected:
        meshInfo = s.split(".")
        faceIds = []
        if len(meshInfo) == 2:
            faceIdsStr = meshInfo[1][2:len(meshInfo[1])-1]
            numbers = [int(word) for word in faceIdsStr.split(":")]
            
            if len(numbers) > 1:
                for i in range(numbers[0], numbers[1] + 1):
                    faceIds.append(i)
            else:
                faceIds.append(numbers[0])
        
        # If mesh name is no already in dictionary, add it with an empty list of face ids
        if meshInfo[0] not in meshDict:
            meshDict[meshInfo[0]] = []
            for id in faceIds:
                meshDict[meshInfo[0]].append(id)
                    
        else:
            for id in faceIds:
                meshDict[meshInfo[0]].append(id)
   
    # Get FnMesh of selected object to check ray imtersection
    fnMeshes = []
    for key in meshDict:
        fnMeshes.append((getFnMesh(key), meshDict[key]))
        
    # Get bounding boxes for all selected meshes
    bboxes = []
    for i in range(len(selected)):
        bboxes.append( cmds.exactWorldBoundingBox( selected[i] ) )

    # Merge bounding boxes into one box
    bbox = mergeBoundingBoxes(bboxes)
    
    # Select sampling method and generate scatter points
    samples = []
    if samplingMethod == 'Poisson-Disc':
        #Top/bottom
        samples = hdtPoissonDiscSampling( bbox[0], bbox[3], bbox[2], bbox[5], discRadius )

        #Right/Left
        #samples = hdtPoissonDiscSampling( bbox[0], bbox[3], bbox[1], bbox[4], discRadius )
    
        #Front/Back
        #samples = hdtPoissonDiscSampling( bbox[1], bbox[4], bbox[3], bbox[5], discRadius )
    else:
        samples = basicRandomSampling( bbox[0], bbox[2], bbox[3], bbox[5], resolution, probability )
   
    # Create a group for the samples
    sampleGroup = cmds.group( em=True, name=scatterGroupName )

    for coordinates in samples:
        
        """
        #Top
        rayOrigin = om.MFloatPoint(coordinates[0], bbox[4] + 10.0, coordinates[1], 1.0)
        #Bottom
        #rayOrigin = om.MFloatPoint(coordinates[0], bbox[1] - 10.0, coordinates[1], 1.0)

        #Left
        #rayOrigin = om.MFloatPoint(coordinates[0], coordinates[1], bbox[5] + 10.0 , 1.0)
        #Right
        #rayOrigin = om.MFloatPoint(coordinates[0], coordinates[1], bbox[2] - 10.0 , 1.0)

        #Front
        #rayOrigin = om.MFloatPoint(bbox[3] + 10.0 ,coordinates[0], coordinates[1], 1.0)
        #Back
        #rayOrigin = om.MFloatPoint(bbox[0] - 10.0 ,coordinates[0], coordinates[1], 1.0)

        # Cast ray in negative y-direction
        #Top
        rayDirection = om.MFloatVector(0, -1, 0)
        #Bottom
        #rayDirection = om.MFloatVector(0, 1, 0)
        #Right
        #rayDirection = om.MFloatVector(0, 0, -1)
        #Left
        #rayDirection = om.MFloatVector(0, 0, 1)
        #Front
        #rayDirection = om.MFloatVector(-1, 0, 0)
        #Back
        #rayDirection = om.MFloatVector(1, 0, 0)
        """
        
        rayOrigin = om.MFloatPoint(coordinates[0], bbox[4] + 10.0, coordinates[1], 1.0)
        
        # Cast ray in negative y-direction
        rayDirection = om.MFloatVector(0, -1, 0)

        # Cast ray and check for intersection with given mesh
        intersectionFound, intersectionPoint, faceNormal = checkIntersections(fnMeshes, rayOrigin, rayDirection)
        
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
	