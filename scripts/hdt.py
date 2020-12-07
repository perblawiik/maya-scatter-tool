import math
import random

def generateInitialActiveLists(xMin, zMin, baseLength, numColumns, maxLevels):
    """ Generates a list of active lists and computes the squares of the base level (index 0)
        based on given minimum coordinates and base square length.
        Params
        ===
            xMin: Minimum x-coordinate of the bounding area of which to compute the base level
            zMin: Minimum z-coordinate of the bounding area of which to compute the base level
            baseLength: The side length of each square of the base level
            numColumns: Number of rows and columns of base squares
            maxLevels: Maximum number of active lists (limited by the numerical precision used)
            return: A list of active lists and with the squares of the base level
    """
    
    # Compute the min corner coordinates of each base square
    xValues = []
    zValues = []
    for i in range(numColumns):
        xValues.append( xMin + baseLength * i )
        zValues.append( zMin + baseLength * ( i + 1 ) )
    
    # Create a list of lists
    activeLists = [ [] for _ in range(maxLevels) ]
    
    # Add base squares to the base level (index 0) of active lists
    for i in range(numColumns):
        for j in range(numColumns):
            activeLists[0].append((xValues[i], zValues[j]))
            
    return activeLists

def farthestCornerDistance(P, C, squareLength):
    """ Computes the distance between given point and the farthest corner of given square.
        Params
        ===
            P: Location of the point to measure distane with
            C: Location of the center of the square to measure distance with
            squareLength: The side length of the square
            return: The distance between the farthest corner and the point.
    """
    A = abs(C[0] - P[0]) + squareLength * 0.5
    B = abs(C[1] - P[1]) + squareLength * 0.5
    return math.sqrt( A * A + B * B )
    
def euclideanDistance(P1, P2):
    """ Computes the euclidean distance between two 2D points.
        Params
        ===
            P1: Location of first point
            P2: Location of second point
            return: The euclidean distance between P1 and P2
    """
    A = P2[0] - P1[0]
    B = P2[1] - P1[1]
    return math.sqrt( A * A + B * B )
    

def isOutOfRange(x, min, max):
    """ Checks if the given value is outside of the given interval.
        Params
        ===
            x: Value of which to test
            min: Minimum value of the interval
            max: Maximum value of the interval
    """
    return  x < min or x > max
    

def checkNeighboursMinDistance(lookupGrid, cX, cZ, row, col, gridDims, radius, squareLength = 0):
    """ In a 3x3 neighbourhood from the given lookup grid, check min distance based on given disc radius.
        Function returns true if no points lays within the minimum distance of given coordinates.
        Params
        ===
            lookupGrid: An acceleration grid for quickly getting points close to each other
            cX: X-coordinate of point to check min distance
            cZ: Z-coordinate of point to check min distance
            row: Row index for the lookup grid of the point to check min distance
            col: Column index for the lookup grid of the point to check min distance
            gridDims: Num of rows and columns of the lookup grid
            radius: The radius used to check min distance
            squareLength (optional): Side length of a square to check if its covered by a point based on min distance
            return: A boolean set to True if the min distance check is passed
    """
    for i in range(-1, 2):
            # Make sure not to look outside of grid range
            if isOutOfRange(row + i, 0, gridDims - 1):
                continue
                
            for j in range(-1, 2):
                # Make sure not to look outside of grid range
                if isOutOfRange(col + j, 0, gridDims - 1):
                    continue 
                 
                lookupIndex = gridDims * (row + i) + (col + j)
                
                # Do minimum distance check with all points in current grid cell
                for point in lookupGrid[lookupIndex]:
                    # If a square length is provided, check if the square is clear from a point
                    if squareLength > 0:
                        if farthestCornerDistance(point, (cX, cZ), squareLength) < radius:
                            return False
                    else:
                        if euclideanDistance(point, (cX, cZ)) < radius:
                            return False
                        
    return True    

def hdtPoissonDiscSampling(xMin, xMax, zMin, zMax, radius):
    """ Generates a maximal point set within a given plane based on Poisson-Disc Sampling.
        The method is called Hierarchical Dart Throwing which relies on quadtree subdivisions of the sampling domain.
        Params
        ===
            xMin: Minimum x-coordinate of the sampling domain
            xMax: Maximum x-coordinate of the sampling domain
            zMin: Minimum z-coordinate of the sampling domain
            zMax: Maximum z-coordinate of the sampling domain
            radius: Disc radius (minimal distance between sample points)
            return: A list of sample points
    """
    # Base grid settings
    length = max(xMax - xMin, zMax - zMin)
    baseLength = length / math.ceil( length * ( 1.41421356237 / radius ) )
    numColumns = int(length / baseLength)
    
    # Store this as a variable to save computation time
    radiusInvert = 1 / radius 
    
    # Generate lists of active lists (including the base level squares)
    maxLevels = 16
    activeLists = generateInitialActiveLists(xMin, zMin, baseLength, numColumns, maxLevels)
    
    # Create a list to keep track of the area of the current active squares for each list
    activeListAreas = [0] * maxLevels
    areaTotal = length * length
    activeListAreas[0] = areaTotal
    
    # Create acceleration grid for minimum distance lookup where each cell has the length = disc radius
    gridDims = int(length * radiusInvert) + 1
    lookupGrid = [ [] for _ in range(gridDims*gridDims) ]
    
    # A list to store the final samples
    samples = []
    while areaTotal > 0.0000001:
        currentSquare = None
          
        # Select an active list based on the probability proportional to the area
        activeListIndex = 0
        previous = 0.0
        probabilityProportionalToArea = areaTotal * random.uniform(0, 0.999999)
        for i in range(len(activeLists)):
            # If the current active list does not contain any active squares, move on to check next level
            if len(activeLists[i]) > 0:
                if previous <= probabilityProportionalToArea and probabilityProportionalToArea < activeListAreas[i]:
                    # Randomly choose a square from the active list
                    randomIndex = random.randint( 0, len(activeLists[i]) - 1 )
                    currentSquare = activeLists[i][randomIndex]
                    
                    # Remove selected square from active list
                    activeLists[i].pop(randomIndex)
                    
                    # Save chosen active list index
                    activeListIndex = i
                    break
                    
            previous = activeListAreas[i]
            
        if currentSquare == None:
            continue;

        # Subtract current square area from total area and active list area
        squareLength = baseLength / pow(2, activeListIndex)
        squareArea = squareLength * squareLength
        activeListAreas[activeListIndex] = max(activeListAreas[activeListIndex] - squareArea, 0)
        areaTotal = max(areaTotal - squareArea, 0)
         
        # Calculate the center of the square point
        sX = currentSquare[0] + (squareLength * 0.5)
        sZ = currentSquare[1] - (squareLength * 0.5)
        
        # Calculate the row and column for the lookup grid
        sRow = int((sZ - zMin) * radiusInvert)
        sCol = int((sX - xMin) * radiusInvert)
        
        # Check 3x3 neighbourhood to see if the selected square is covered by a point
        squareIsClear = checkNeighboursMinDistance(lookupGrid, sX, sZ, sRow, sCol, gridDims, radius, squareLength)
        if squareIsClear == False:
            continue
        
        # Generate random point inside square (throw a dart)
        rX = currentSquare[0] + random.uniform(0, 1) * squareLength
        rZ = currentSquare[1] - random.uniform(0, 1) * squareLength
        rRow = int((rZ - zMin) * radiusInvert)
        rCol = int((rX - xMin) * radiusInvert)
        
        # Check if the new point satisfies the minimum distance requirement
        if checkNeighboursMinDistance(lookupGrid, rX, rZ, rRow, rCol, gridDims, radius):
            # Add new point to both lookup grid and samples set
            lookupGrid[gridDims * rRow + rCol].append((rX, rZ))
            samples.append((rX, rZ))
            
        # Subdivide the square into four child squares with half the side length 
        elif (activeListIndex + 1) < maxLevels:
            childLength = squareLength * 0.5
            childArea = (childLength * childLength)
            for i in range(2):
                for j in range(2):
                    childX = (currentSquare[0] + (childLength * i)) + (childLength * 0.5)
                    childZ = (currentSquare[1] - (childLength * j)) - (childLength * 0.5)
                    childRow = int((childZ - zMin) * radiusInvert)
                    childCol = int((childX - xMin) * radiusInvert)
                    
                    # Check 3x3 neighbourhood if the square is clear from any point
                    childIsClear = checkNeighboursMinDistance(lookupGrid, sX, sZ, sRow, sCol, gridDims, radius, childLength)
                    if childIsClear:
                        # Add child square to active list in next level
                        activeLists[activeListIndex + 1].append((childX, childZ))
                        # Update active list area
                        activeListAreas[activeListIndex + 1] += childArea
                        # Update total area
                        areaTotal += childArea
    
    return samples
        
