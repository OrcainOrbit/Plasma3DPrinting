from datetime import time
import gcodeprocessor
import numpy as np

DWELL_TIME      = 2.0       # (sec)
AUX_SPEED       = 200.0     # (mm/min)
AUX_OFFSET_X    = 10.0      # (mm)
AUX_OFFSET_Y    = 10.0      # (mm)
AUX_OFFSET_Z    = 0.007      # (mm)
AUX_ON_CMD      = 'SET_PIN PIN=caselight1 VALUE=1'
AUX_OFF_CMD     = 'SET_PIN PIN=caselight1 VALUE=0'


np.printoptions(precision=3, suppress=True)

with open('input.gcode','r') as f:
    lines = f.readlines()

proc = gcodeprocessor.GCodeProcessor()

sections = proc.get_layers_cura(lines)
layers = sections[1]

# add comment identifying post process script
for i,l in enumerate(sections[0]):
    # find end of starting comments
    if l[0]!=';':
        sections[0].insert(i,';Post processing for aux device control using script from <URL>\n')
        #TODO add Github URL
        break

pen = gcodeprocessor.GCodePen()

file_lines = sections[0]
for layer in layers:

    # run GCODE recorder object for this layer
    # overwrites position history but retains starting position
    pen.record(layer)

    # print layer as normal
    file_lines.extend(layer)

    # move to new z height
    file_lines.append('G1 Z{} F2000\n'.format(pen.layer_height+AUX_OFFSET_Z))

    # turn on auxiliary device and pause until on
    file_lines.append(AUX_ON_CMD+'\n')
    file_lines.append('G4 P{}\n'.format(int(DWELL_TIME*1000)))

    # replay all extruding moves for layer
    file_lines.extend(pen.replay_offset(AUX_SPEED,AUX_OFFSET_X,AUX_OFFSET_Y))

    # turn off aux dev and pause
    file_lines.append(AUX_OFF_CMD+'\n')
    file_lines.append('G4 P{}\n'.format(int(DWELL_TIME*1000)))

    # return to layer height
    file_lines.append('G1 Z{} F2000\n'.format(pen.next_layer_height))

# append final GCODE from file
file_lines.extend(sections[-1])

with open('output.gcode','w') as f:
    f.writelines(file_lines)
