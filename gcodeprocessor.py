import numpy as np

ary = np.array

class GCodePen:
    """
    Class and methods to parse G-Code and record tool position for layer replay with offset.
    Some slicer specific assumptions are made based on G-Code generated with CURA 4.3.
    """


    def __init__(self,starting_z = 0.0):
        self.pos = np.zeros(3)
        self.history = []
        self.axdict = {'x':0,'y':1,'z':2}

        # may need to obtain starting z height from previous layer
        # CURA moves to next layers starting position within the previous layer
        self.pos[2] = starting_z
        self.layer_height = 0.0
        self.next_layer_height = 0.0

        self.verbose = False

    def update_print_pos(self, line):
        """
        Update internal position tracking and append to move history
        :param line:
        :return:
        """
        l = line.lower().strip()
        # if line is a move command, check both interp and non-interp moves
        if 'g1' in l or 'g0' in l:
            # if line has an extruder position, assume it is a printed line
            # record any moves with Z parameter to keep track of layer heights
            if 'e' in l or 'z' in l:
                # update new position from current and command
                # try:
                for c in [c.strip().lower() for c in l.split(' ')]:
                    # check each parameter for each axis in case command mis-ordered
                    for ax in self.axdict:
                        if ax in c:
                            self.pos[self.axdict[ax]] = float(c.replace(ax,''))

                            if 'z' in l and self.verbose:
                                print('Recording layer at {}'.format(self.pos[2]))

                # only return 0 and append if line is successfully parsed
                self.history.append(np.copy(self.pos))
                return 0
            else:
                return -1
        else:
            return -1

    def bounding_box(self):
        """
        Returns maximum and minimum positions in current history
        :return:
        """
        min_pos = self.history[0]
        max_pos = self.history[0]
        for pos in self.history:
            # update max and min element wise
            min_pos = np.minimum(min_pos,pos)
            max_pos = np.maximum(max_pos,pos)
        return [min_pos,max_pos]

    def record(self,layer):
        """
        Reads lines of G-Code and record position to internal history
        :param layer:
        :return:
        """
        # reinitialize history list
        self.history = []
        for line in layer:
            self.update_print_pos(line)

        min_pos,max_pos = self.bounding_box()
        self.layer_height = min_pos[2]
        self.next_layer_height = max_pos[2]

    def replay_offset(self,speed,off_x,off_y):
        """
        Returns list of G-Code lines following recorded path IN X/Y ONLY with a specified offset
        :param speed:
        :param off_x:
        :param off_y:
        :return:
        """
        lines = ['']*len(self.history)
        for i,pos in enumerate(self.history):
            # visit each linear move location at set speed, assuming z height already set
            lines[i] = 'G1 X{} Y{} F{}\n'.format(pos[0]+off_x,pos[1]+off_y,speed)

        return lines

    def replay(self,speed):
        """
        Returns list of G-Code lines following the recorded 3d path at a set speed
        :param speed:
        :return :
        """
        lines = [''] * len(self.history)
        for i, pos in enumerate(self.history):
            # visit each linear move location at set speed
            lines[i] = 'G1 X{} Y{} Z{} F{}\n'.format(pos[0], pos[1], pos[2], speed)

        return lines

    def replay_2d(self,speed):
        """
        Returns list of G-Code lines following the recorded path IN X/Y ONLY at a set speed
        :param speed:
        :return :
        """
        lines = [''] * len(self.history)
        for i, pos in enumerate(self.history):
            # visit each linear move location at set speed
            lines[i] = 'G1 X{} Y{} F{}\n'.format(pos[0], pos[1], speed)

        return lines

    def grid_pass(self,speed,stepover,overhang=0.0,off_x=0.0,off_y=0.0):
        """
        Returns list of G-Code lines passing over entire printed area with specified step-over
        :param off_y:
        :param off_x:
        :param speed:
        :param stepover:
        :param overhang:
        :return:
        """
        #TODO add support for passes at variable angles

        min_pos,max_pos = self.bounding_box()
        off = np.array([off_x,off_y,0.0])
        min_pos += off
        max_pos += off

        y_vals = np.arange(min_pos[1]-overhang,max_pos[1]+overhang+stepover,stepover)
        x_vals = np.array([min_pos[0]-overhang,max_pos[0]+overhang])

        lines = []
        for y in y_vals:
            lines.append('G1 X{} Y{} F{}'.format(x_vals[0], y, speed))
            lines.append('G1 X{} Y{} F{}'.format(x_vals[1], y, speed))

        return lines


class GCodeProcessor:
    """
    Utility class for extracting relevant lines from 3d printer GCODE
    """

    def get_layers_cura(self,lines):
        """
        Returns list of layers as well as starting and ending G-Code
        Makes some slicer specific assumptions about G-Code file formatting according to CURA 4.3
        :param lines:
        :return:
        """
        layer_str = {}
        layer_end = {}
        layer_count = 0
        num = 0
        # search for layer starting line numbers, increased search time but makes parsing easier
        for i,l in enumerate(lines):
            l = l.lower().strip()
            if l[0] == ';':
                if 'layer_count:' in l.lower():
                    layer_count = int(l[l.find(':')+1:])
                elif 'layer:' in l.lower():
                    num = str(l[l.find(':') + 1:])
                    layer_str[num] = i
                # assuming all layers end in TIME_ELAPSED comment
                elif 'time_elapsed:' in l.lower():
                    layer_end[str(num)] = i

        start = lines[0:layer_str['0']]
        end = lines[layer_end[str(layer_count-1)]+1:]
        layers = [[]]*layer_count
        for l_n in layer_str:
            layers[int(l_n)] = lines[layer_str[l_n]:layer_end[l_n]+1]

        return start,layers,end
