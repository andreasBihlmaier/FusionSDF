# SDF optimize
Simplify meshes of FusionSDF exported SDFs (TODO and add materials to them) using blender.

## Installation
`pip install bpy`

## Usage
```
> python3 sdfopt.py --help
usage: sdfopt.py [-h] [--angle_limit ANGLE_LIMIT] sdf_dir

Optimize SDF files in the specified directory.

positional arguments:
  sdf_dir               Directory containing SDF file (exported by FusionSDF) to optimize

options:
  -h, --help            show this help message and exit
  --angle_limit ANGLE_LIMIT
                        Angle limit for mesh simplification in degrees
```