import math

import bpy

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Function to create materials
def create_mat(name, color, roughness=0.6):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not principled:
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.inputs["Base Color"].default_value = color
    principled.inputs["Roughness"].default_value = roughness
    return mat

mat_orange = create_mat("RedPandaOrange", (0.7, 0.2, 0.05, 1), 0.85)
mat_dark = create_mat("RedPandaDark", (0.1, 0.02, 0.01, 1), 0.9)
mat_white = create_mat("RedPandaWhite", (0.85, 0.85, 0.8, 1), 0.8)
mat_black = create_mat("RedPandaBlack", (0.02, 0.02, 0.02, 1), 0.3)
mat_eye_highlight = create_mat("EyeHighlight", (1.0, 1.0, 1.0, 1), 0.1)

def add_subsurf_and_smooth(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_add(type='SUBSURF')
    mod = obj.modifiers[-1]
    mod.levels = 2
    mod.render_levels = 2
    bpy.ops.object.shade_smooth()

# Main Head
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
head = bpy.context.active_object
head.scale = (1.1, 0.9, 0.95)
head.data.materials.append(mat_orange)
add_subsurf_and_smooth(head)

# Snout (White base)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(0, -0.75, -0.2))
snout = bpy.context.active_object
snout.scale = (1.1, 0.85, 0.7)
snout.data.materials.append(mat_white)
add_subsurf_and_smooth(snout)

# Nose (Black, flatter)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0, -1.15, -0.05))
nose = bpy.context.active_object
nose.scale = (1.4, 0.7, 0.8)
nose.data.materials.append(mat_black)
add_subsurf_and_smooth(nose)

# Muzzle line
bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.25, location=(0, -1.13, -0.2))
line = bpy.context.active_object
line.rotation_euler = (math.pi/2 - 0.2, 0, 0)
line.data.materials.append(mat_black)

# Eyes (Dark)
for x in [-0.35, 0.35]:
    # Eye ball
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x, -0.82, 0.25))
    eye = bpy.context.active_object
    eye.scale = (1.1, 0.9, 1.0)
    eye.rotation_euler = (0.2, 0, x * 0.2)
    eye.data.materials.append(mat_black)
    add_subsurf_and_smooth(eye)
    
    # Catchlight
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.025, location=(x + (0.04 if x>0 else -0.04), -0.92, 0.28))
    light = bpy.context.active_object
    light.data.materials.append(mat_eye_highlight)
    add_subsurf_and_smooth(light)
    
    # Dark tear track
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(x*1.3, -0.8, -0.1))
    track = bpy.context.active_object
    track.scale = (0.5, 0.5, 1.8)
    track.rotation_euler = (0.4, -x * 0.4, 0)
    track.data.materials.append(mat_dark)
    add_subsurf_and_smooth(track)
    
    # White eyebrow markings
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(x*1.1, -0.75, 0.55))
    brow = bpy.context.active_object
    brow.scale = (1.2, 0.4, 0.8)
    brow.rotation_euler = (-0.2, x * 0.3, 0)
    brow.data.materials.append(mat_white)
    add_subsurf_and_smooth(brow)

# Cheeks (Wide fluffy white/orange sides)
for x in [-0.8, 0.8]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.45, location=(x, -0.4, -0.35))
    cheek = bpy.context.active_object
    cheek.scale = (1.1, 0.7, 1.2)
    cheek.rotation_euler = (0, -x * 0.3, -x * 0.2)
    cheek.data.materials.append(mat_white)
    add_subsurf_and_smooth(cheek)

# Ears (Large, somewhat pointed but rounded)
for x, angle in [(-0.7, 0.6), (0.7, -0.6)]:
    # Outer ear
    bpy.ops.mesh.primitive_cone_add(radius1=0.4, radius2=0.05, depth=0.7, location=(x, -0.1, 0.85))
    ear = bpy.context.active_object
    ear.rotation_euler = (-0.1, angle, 0)
    ear.scale = (1.2, 0.5, 1)
    ear.data.materials.append(mat_orange)
    add_subsurf_and_smooth(ear)
    
    # Inner ear fluff
    bpy.ops.mesh.primitive_cone_add(radius1=0.28, radius2=0.02, depth=0.6, location=(x*0.9, -0.22, 0.82))
    ear_inner = bpy.context.active_object
    ear_inner.rotation_euler = (-0.2, angle, 0)
    ear_inner.scale = (1.2, 0.3, 1)
    ear_inner.data.materials.append(mat_white)
    add_subsurf_and_smooth(ear_inner)

# Lighting & Camera
bpy.ops.object.light_add(type='AREA', location=(3, -4, 4))
light = bpy.context.active_object
light.data.energy = 200
light.data.size = 2.0
light.rotation_euler = (0.8, 0, 0.6)

bpy.ops.object.light_add(type='AREA', location=(-4, -2, 2))
light2 = bpy.context.active_object
light2.data.energy = 100
light2.data.size = 2.0
light2.rotation_euler = (1.0, 0, -0.8)

# Save
bpy.ops.wm.save_mainfile(filepath=r"C:\Users\artem\Desktop\aios-cli\aios-cli\landing\red_panda_v2.blend")
print("Realistic red panda generated.")
