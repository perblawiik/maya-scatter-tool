import random

def lerp( a, b, t ):
    return a * (1 - t) + b * t

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
               