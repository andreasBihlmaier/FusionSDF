#!/usr/bin/env python3

import argparse
import math
import os
import shutil

from pathlib import Path

import bpy


def find_meshes(directory):
    """Find all .obj, .stl, and .glb files in the given directory and its subdirectories."""
    mesh_extensions = ['*.obj', '*.stl', '*.glb', '*.gltf', '*.ply', '*.dae']
    mesh_files = []
    for ext in mesh_extensions:
        mesh_files.extend(directory.rglob(ext))
    return mesh_files


def main():
    parser = argparse.ArgumentParser(description="Optimize SDF files in the specified directory.")
    parser.add_argument('sdf_dir', type=str, help='Directory containing SDF file (exported by FusionSDF) to optimize')
    parser.add_argument('--angle_limit', type=float, default=5.0, help='Angle limit for mesh simplification in degrees')
    args = parser.parse_args()

    sdf_dir = Path(args.sdf_dir)
    if not sdf_dir.exists() or not sdf_dir.is_dir():
        print(f'Error: "{sdf_dir}" does not exist or is not a directory')
        return
    print(f"Optimizing SDF files in directory: {sdf_dir}")

    sdf_file_path = sdf_dir / 'model.sdf'
    if not sdf_file_path.exists():
        print(f'Error: No such file: {sdf_file_path}') 
        return

    meshes_dir = sdf_dir / 'meshes'
    if not meshes_dir.exists():
        print(f'Directory "{sdf_dir}" does not contain a "meshes" directory. Exiting.')

    sdf_orig_file_path = sdf_dir / 'model.sdf.orig'
    if sdf_orig_file_path.exists():
        print(f'Warning: "{sdf_orig_file_path}" already exists. Will NOT copy "{sdf_file_path}" to "{sdf_orig_file_path}".')
    else:
        shutil.copy(sdf_file_path, sdf_orig_file_path)

    meshes_orig_dir = sdf_dir / 'meshes_orig'
    if meshes_orig_dir.exists():
        print(f'Warning: "{meshes_orig_dir}" already exists. Will NOT copy "{meshes_dir}" to "{meshes_orig_dir}".')
    else:
        shutil.copytree(meshes_dir, meshes_orig_dir)

    mesh_urisubstitutions = {}
    mesh_file_paths = find_meshes(meshes_dir)
    for mesh_file_path in mesh_file_paths:
        print(f'Processing mesh: "{mesh_file_path}"')

        bpy.ops.object.delete()

        if mesh_file_path.suffix == '.glb' or mesh_file_path.suffix == '.gltf':
            bpy.ops.import_scene.gltf(filepath=str(mesh_file_path))
        elif mesh_file_path.suffix == '.stl':
            bpy.ops.wm.stl_import(filepath=str(mesh_file_path))
        elif mesh_file_path.suffix == '.obj':
            bpy.ops.wm.obj_import(filepath=str(mesh_file_path))
        elif mesh_file_path.suffix == '.ply':
            bpy.ops.wm.ply_import(filepath=str(mesh_file_path))
        elif mesh_file_path.suffix == '.dae':
            bpy.ops.wm.collada_import(filepath=str(mesh_file_path))

        mesh = bpy.context.object
        print(f'Before simplification mesh has {len(mesh.data.vertices)} verts, {len(mesh.data.edges)} edges, and {len(mesh.data.polygons)} polys')
        modifier = mesh.modifiers.new(name='decimate', type='DECIMATE')
        modifier.decimate_type = 'DISSOLVE'
        modifier.angle_limit = math.radians(args.angle_limit)
        bpy.ops.object.modifier_apply(modifier='decimate')
        print(f'After simplification mesh has {len(mesh.data.vertices)} verts, {len(mesh.data.edges)} edges, and {len(mesh.data.polygons)} polys')

        # TODO assign Blender materials to meshes based on material name (+ colors) in .mtl files

        if mesh_file_path.suffix == '.obj':
            mtl_file_path = mesh_file_path.with_suffix('.mtl')
            if mtl_file_path.exists():
                mtl_file_path.unlink()
        mesh_file_path.unlink()

        export_mesh_file_path = mesh_file_path.with_suffix('.glb')
        bpy.ops.export_scene.gltf(filepath=str(export_mesh_file_path), export_format='GLB', export_materials='EXPORT', export_yup=True)
        mesh_urisubstitutions[str(mesh_file_path.relative_to(sdf_dir))] = str(export_mesh_file_path.relative_to(sdf_dir))
    
    with open(sdf_file_path, 'r') as file:
        sdf_content = file.read()
    for old_uri, new_uri in mesh_urisubstitutions.items():
        sdf_content = sdf_content.replace(f'{old_uri}</uri>', f'{new_uri}</uri>')
    with open(sdf_file_path, 'w') as file:
        file.write(sdf_content)


if __name__ == "__main__":
    main()