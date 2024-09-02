import math
import re
from xml.dom import minidom

from .pose import Pose

def normalize_name(name):
    # Convert the string to lower case
    name = name.lower()
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^a-z0-9_]+', '_', name)
    # Remove leading or trailing underscores (if any)
    name = name.strip('_')
    return name


def matrix3d_to_rpy(matrix3d):
    """
    Convert a 3D transformation matrix to roll, pitch, yaw angles.
    """
    # Extract the rotation matrix
    R = [[0, 0, 0],
         [0, 0, 0],
         [0, 0, 0]]
    for row in range(3):
        for col in range(3):
            R[row][col] = matrix3d.getCell(row, col)
    
    # Compute the Euler angles
    sy = math.sqrt(R[0][0] ** 2 + R[1][0] ** 2)
    
    singular = sy < 1e-6

    if not singular:
        roll = math.atan2(R[2][1], R[2][2])
        pitch = math.atan2(-R[2][0], sy)
        yaw = math.atan2(R[1][0], R[0][0])
    else:
        roll = math.atan2(-R[1][2], R[1][1])
        pitch = math.atan2(-R[2][0], sy)
        yaw = 0

    return [roll, pitch, yaw]


def transform2_to_pose(transform2):
    return Pose(cm_to_m(transform2.translation.asArray()), matrix3d_to_rpy(transform2))


def prettify_xml(ugly_xml):
  return minidom.parseString(ugly_xml).toprettyxml(indent='  ')


def cm_to_m(cm):
    if isinstance(cm, float):
        return cm / 100.0
    else:
        return [value / 100.0 for value in cm]


def kg_cm2_to_kg_m2(kg_cm2):
    return kg_cm2 / 10000.0


def world_inertia_to_com_inertia(inertia, center_of_mass, mass):
    # Parallel axis theorem
    x = center_of_mass[0]
    y = center_of_mass[1]
    z = center_of_mass[2]
    translation_matrix = [y**2+z**2, x**2+z**2, x**2+y**2,
                         -x*y, -y*z, -x*z]
    return [ i - mass*t for i, t in zip(inertia, translation_matrix)]


def name_to_path(name):
    return name.replace('__', '/')