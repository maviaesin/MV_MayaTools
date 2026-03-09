# constants_library.py

DEFAULT_CAMERAS = ['persp', 'top', 'front', 'side']

DEFAULT_PREFIX = "GRP_"

PREFIXES = {
    "mesh": "SM_",  # Static Mesh (e.g., props, foliage, weapons)
    "skeletal_mesh": "SKM_",  # Skeletal Mesh (for rigging and skinned meshes)
    #"joint": "J_",  # Joint / Bone
    #"transform": "GRP_",  # Group (used for hierarchical organization)


    # Materials
    "lambert": "M_",  # Basic material (Lambert)
    "blinn": "M_",  # Blinn material
    "phong": "M_",  # Phong material

}


