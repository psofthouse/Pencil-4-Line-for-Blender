import bpy
node = bpy.context.space_data.edit_tree.nodes.active

node.brush_type = 'NORMAL'
node.brush_map_on_gui = False
node.brush_map_opacity = 1.0
node.stretch = 0.0
node.stretch_random = 0.0
node.angle = 0.0
node.angle_random = 0.0
node.groove = 0.0
node.groove_number = 5
node.size = 16.0
node.size_random = 80.0
node.antialiasing = 0.5
node.horizontal_space = 0.10000000149011612
node.horizontal_space_random = 100.0
node.vertical_space = 0.10000000149011612
node.vertical_space_random = 100.0
node.reduction_start = 0.0
node.reduction_end = 1.0
