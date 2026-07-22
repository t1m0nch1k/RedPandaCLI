
import bpy

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Materials
def create_mat(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not principled:
        principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.inputs["Base Color"].default_value = color
    return mat

mat_orange = create_mat("RedPandaOrange", (0.8, 0.25, 0.05, 1))
mat_white = create_mat("RedPandaWhite", (0.9, 0.9, 0.9, 1))
mat_black = create_mat("RedPandaBlack", (0.05, 0.05, 0.05, 1))

# Main Head
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
head = bpy.context.active_object
head.data.materials.append(mat_orange)

# Snout (White)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, -0.85, -0.2))
snout = bpy.context.active_object
snout.scale = (1.2, 0.8, 0.8)
snout.data.materials.append(mat_white)

# Nose (Black)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0, -1.3, -0.1))
nose = bpy.context.active_object
nose.scale = (1.5, 0.8, 0.8)
nose.data.materials.append(mat_black)

# Eyes (Black)
for x in [-0.4, 0.4]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(x, -0.85, 0.3))
    eye = bpy.context.active_object
    eye.data.materials.append(mat_black)

# Ears (Orange)
for x, angle in [(-0.8, 0.5), (0.8, -0.5)]:
    bpy.ops.mesh.primitive_cone_add(radius1=0.4, depth=0.8, location=(x, 0, 0.8))
    ear = bpy.context.active_object
    ear.rotation_euler = (0, angle, 0)
    ear.data.materials.append(mat_orange)

# Inner Ears (White)
for x, angle in [(-0.7, 0.5), (0.7, -0.5)]:
    bpy.ops.mesh.primitive_cone_add(radius1=0.25, depth=0.6, location=(x, -0.2, 0.75))
    ear_inner = bpy.context.active_object
    ear_inner.rotation_euler = (-0.2, angle, 0)
    ear_inner.data.materials.append(mat_white)

# Cheeks (White markings)
for x in [-0.7, 0.7]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(x, -0.6, -0.3))
    cheek = bpy.context.active_object
    cheek.scale = (1, 0.5, 1.2)
    cheek.data.materials.append(mat_white)

# Add lighting
bpy.ops.object.light_add(type='SUN', location=(5, -5, 5))
bpy.context.active_object.data.energy = 3

# Save to file
bpy.ops.wm.save_mainfile(filepath=r"C:\Users\artem\Desktop\aios-cli\aios-cli\landing\red_panda.blend")
print("Red panda head created successfully!")
