# constants_library.py

### LIST OF DEFAULT MAYA CAMERAS (TO EXCLUDE FROM SELECTION)
DEFAULT_CAMERAS = ['persp', 'top', 'front', 'side']

### DEFAULT PREFIX FOR UNCLASSIFIED OBJECTS
DEFAULT_PREFIX = "GRP_"

### PREFIX MAPPING BASED ON OBJECT TYPE
PREFIXES = {
    # Meshes
    "mesh": "SM_",          # Static Mesh (e.g., props, foliage, weapons)
    "skeletal_mesh": "SKM_", # Skeletal Mesh (for rigging and skinned meshes)

    # Materials
    "lambert": "M_",        # Basic Lambert material
    "blinn": "M_",          # Blinn material
    "phong": "M_",          # Phong material
}

### COMMENTED-OUT PREFIXES (CAN BE RE-ENABLED IF NEEDED)
# "joint": "J_",      # Joint / Bone
# "transform": "GRP_" # Group (used for hierarchical organization)

### SUFFIX MAPPING
SUFFIXES = {
    "low":  "_low",
    "high": "_high",
}
