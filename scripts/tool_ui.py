import maya.cmds as cmds
import functools

from scatter import generateScatterPoints, createModels

#----------------#
# User Interface #
#----------------#

def setSamplingMethod(samplerOptionMenu):
    option = cmds.optionMenu( samplerOptionMenu, query=True, value=True )
    
    if option == 'Poisson-Disc':
        cmds.floatFieldGrp( discRadiusField, edit=1, visible=True )
        cmds.intFieldGrp( resolutionField, edit=1, visible=False )
        cmds.floatSliderGrp( probabilityField, edit=1, visible=False )
    else:
        cmds.floatFieldGrp( discRadiusField, edit=1, visible=False )
        cmds.intFieldGrp( resolutionField, edit=1, visible=True )
        cmds.floatSliderGrp( probabilityField, edit=1, visible=True )


# Check if window exists
if cmds.window( 'scatterToolUI' , exists = True ) :
    cmds.deleteUI( 'scatterToolUI' ) 

# Create window 
toolWindow = cmds.window( 'scatterToolUI', title="Scatter Tool", width=300, height=300 )

cmds.columnLayout( adj=True )

cmds.separator( h=12, style="none" )
cmds.text( label="Random Scatter Point Generator" )
cmds.separator( h=12, style="none" )

samplerOptionMenu = cmds.optionMenu( label='Sampler' )
cmds.optionMenu( samplerOptionMenu, edit=1, changeCommand='setSamplingMethod(samplerOptionMenu)')

cmds.menuItem( label='Poisson-Disc' )
cmds.menuItem( label='Simple Randomizer' )

cmds.separator( h=6, style="none" )

discRadiusField = cmds.floatFieldGrp( numberOfFields=1, label="Disc Radius", value1=2 )

resolutionField = cmds.intFieldGrp( numberOfFields=1, label="Sample Resolution", value1=20, visible=False )

cmds.separator( h=6, style="none" )

probabilityField = cmds.floatSliderGrp( label="Probability Distribution", min=0.0, max=1.0, 
                                        value=0.5, step=0.01, field=True, visible=False )
                                        
cmds.separator( h=6, style="none" )

surfaceOrientationCheckBox = cmds.checkBoxGrp( numberOfCheckBoxes=1, label="Adjust to Surface", value1=True )

cmds.separator( h=12, style="none" )

cmds.text( label="Randomize Local Y-Axis Rotation" )

cmds.separator( h=6, style="none" )

randomRotMaxSliderGrp = cmds.intSliderGrp( label="Maximum Angle", min=0.0, max=180.0, 
                                          value=0, step=1.0, field=True )
                                          
cmds.separator( h=6, style="none" )

randomRotMinSliderGrp = cmds.intSliderGrp( label="Minimum Angle", min=-180.0, max=0.0, 
                                          value=0, step=1.0, field=True )

cmds.separator( h=12, style="none" )

cmds.text( label="Uniform Scale Randomization Interval" )

cmds.separator( h=6, style="none" )

minScaleFieldGrp = cmds.floatFieldGrp( numberOfFields=1, label="Minimum Scale", value1=1 )

cmds.separator( h=6, style="none" )
                                         
maxScaleFieldGrp = cmds.floatFieldGrp( numberOfFields=1, label="Maximum Scale", value1=1 )
                                         
cmds.separator( h=12, style="none" )

cmds.text( label="Scatter Group" )

cmds.separator( h=6, style="none" )

locatorGroupNameFieldGrp = cmds.textFieldGrp( label="Group Name", text="ScatterGroup" )

cmds.separator( h=6, style="none" )

locatorColorFieldGrp = cmds.intFieldGrp( numberOfFields=3, label="Scatter Point Color", 
                                         value1=255, value2=0, value3=0 )

cmds.separator( h=12, style="none" )

cmds.button( "Generate Scatter", command=functools.partial( generateScatterPoints,
                                                    resolutionField,
                                                    probabilityField,
                                                    surfaceOrientationCheckBox,
                                                    locatorColorFieldGrp,
                                                    randomRotMaxSliderGrp,
                                                    randomRotMinSliderGrp,
                                                    minScaleFieldGrp,
                                                    maxScaleFieldGrp,
                                                    locatorGroupNameFieldGrp,
                                                    samplerOptionMenu,
                                                    discRadiusField ) ) 
                                                    

cmds.separator( h=20 )

cmds.text( label="Replace Scatter Points With Selected Models" )

cmds.separator( h=12, style="none" )

scatterGroupNameFieldGrp = cmds.textFieldGrp( label="Scatter Group Name", text="ScatterGroup" )

cmds.separator( h=6, style="none" )

cmds.button( "Add Models", command=functools.partial( createModels, scatterGroupNameFieldGrp ) )

cmds.separator( h=12, style="none" )

#cmds.dockControl( area='right', content=toolWindow, allowedArea= "all" )
 
cmds.showWindow( toolWindow ) 