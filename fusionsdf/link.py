import xml.etree.ElementTree as ET

from enum import Enum
from typing import Dict, List

from .pose import Pose

class LinkGeometryType(Enum):
    BOX = 'box'
    CYLINDER = 'cylinder'
    MESH = 'mesh'



class LinkGeometry:
    def __init__(self, geometry_type: LinkGeometryType):
        self.geometry_type = geometry_type
        self.mesh_uri: str = None
        self.size: List[float] = None
        self.scale: float = 0.01  # cm to m


    def __str__(self):
        type_attributes = ''
        if self.geometry_type == LinkGeometryType.MESH:
            type_attributes = f'mesh_url={self.mesh_uri}'
        elif self.geometry_type == LinkGeometryType.BOX:
            type_attributes = f'size={self.size}'
        return f'LinkGeometry({self.geometry_type.value}; {type_attributes})'


    def to_sdf_element(self, node):
        geometry_node = ET.SubElement(node, 'geometry')
        if self.geometry_type == LinkGeometryType.MESH:
            mesh_node = ET.SubElement(geometry_node, 'mesh')
            scale_node = ET.SubElement(mesh_node, 'scale')
            scale_node.text = ' '.join([str(self.scale) for _ in range(3)])
            uri_node = ET.SubElement(mesh_node, 'uri')
            uri_node.text = self.mesh_uri
        elif self.geometry_type == LinkGeometryType.BOX:
            box_node = ET.SubElement(geometry_node, 'box')
            size_node = ET.SubElement(box_node, 'size')
            size_node.text = ' '.join([str(size) for size in self.size])



class LinkElementType(Enum):
    VISUAL = 'visual'
    COLLISION = 'collision'



class LinkElement:
    def __init__(self, element_type: LinkElementType, name: str):
        self.element_type: LinkElementType = element_type
        self.name: str = name
        self.pose: Pose = None
        self.geometry: LinkGeometry = None


    def __str__(self):
        return f'LinkElement(element_type={self.element_type.value}; {self.name}; pose={self.pose}, geometry={self.geometry})'


    def to_sdf_element(self, node):
        link_node = ET.SubElement(node, self.element_type.value, {'name': self.name})
        if self.pose is not None:
            self.pose.to_sdf_element(link_node)
        self.geometry.to_sdf_element(link_node)


class LinkInertial:
    def __init__(self, pose: Pose, mass: float, ixx: float, ixy: float, ixz: float, iyy: float, iyz: float, izz: float):
        self.pose: Pose = pose
        self.mass: float = mass
        self.ixx: float = ixx
        self.ixy: float = ixy
        self.ixz: float = ixz
        self.iyy: float = iyy
        self.iyz: float = iyz
        self.izz: float = izz


    def __str__(self):
        return f'LinkInertial(pose={self.pose}; mass={self.mass}; ixx={self.ixx}, ixy={self.ixy}, ixz={self.ixz}, iyy={self.iyy}, iyz={self.iyz}, izz={self.izz})'


    def to_sdf_element(self, node):
        inertial_node = ET.SubElement(node, 'inertial')
        self.pose.to_sdf_element(inertial_node)
        mass_node = ET.SubElement(inertial_node, 'mass')
        mass_node.text = str(self.mass)
        inertia_node = ET.SubElement(inertial_node, 'inertia')
        ixx_node = ET.SubElement(inertia_node, 'ixx')
        ixx_node.text = str(self.ixx)
        ixy_node = ET.SubElement(inertia_node, 'ixy')
        ixy_node.text = str(self.ixy)
        ixz_node = ET.SubElement(inertia_node, 'ixz')
        ixz_node.text = str(self.ixz)
        iyy_node = ET.SubElement(inertia_node, 'iyy')
        iyy_node.text = str(self.iyy)
        iyz_node = ET.SubElement(inertia_node, 'iyz')
        iyz_node.text = str(self.iyz)
        izz_node = ET.SubElement(inertia_node, 'izz')
        izz_node.text = str(self.izz)



class Link:
    def __init__(self, name):
        self.name: str = name
        self.pose: Pose = None
        self.visuals: Dict[str, LinkElement] = {}
        self.collisions: Dict[str, LinkElement] = {}
        self.inertial: LinkInertial = None

    def __str__(self):
        visuals = ', '.join([str(visual) for visual in self.visuals.values()])
        collisions = ', '.join([str(collision) for collision in self.collisions.values()])
        return f'Link({self.name}; pose={self.pose}; visuals=({visuals}); collisions=({collisions}); inertial={self.inertial})'

    def to_sdf_element(self, node):
        link_node = ET.SubElement(node, 'link', {'name': self.name})
        if self.pose is not None:
            self.pose.to_sdf_element(link_node)
        if self.inertial is not None:
            self.inertial.to_sdf_element(link_node)
        for visual in self.visuals.values():
            visual.to_sdf_element(link_node)
        for collision in self.collisions.values():
            collision.to_sdf_element(link_node)