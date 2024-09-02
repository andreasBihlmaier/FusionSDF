import xml.etree.ElementTree as ET

from enum import Enum
from typing import Dict, List

from .pose import Pose

class JointType(Enum):
    FIXED = 'fixed'
    REVOLUTE = 'revolute'
    CONTINUOUS = 'continuous'
    PRISMATIC = 'prismatic'



class Joint:
    def __init__(self, name, joint_type: JointType = JointType.FIXED, pose: Pose = None, parent: str = None, child: str = None):
        self.name = name
        self.joint_type: JointType = joint_type
        self.pose: Pose = pose
        self.parent: str = parent
        self.child: str = child
        self.axis_xyz: List[float] = None  # expressed in __model__ frame
        self.lower_limit: float = None
        self.upper_limit: float = None


    def __str__(self):
        return f'Joint({self.name}; type={self.joint_type.value}; pose={self.pose}; parent={self.parent}; child={self.child}; axis_xyz={self.axis_xyz}; lower_limit={self.lower_limit}; upper_limit={self.upper_limit})'


    def to_sdf_element(self, node):
        joint_node = ET.SubElement(node, 'joint', {'name': self.name, 'type': self.joint_type.value})
        if self.pose:
            self.pose.to_sdf_element(joint_node)
        parent_node = ET.SubElement(joint_node, 'parent')
        parent_node.text = self.parent
        child_node = ET.SubElement(joint_node, 'child')
        child_node.text = self.child
        axis_node = ET.SubElement(joint_node, 'axis')
        if self.axis_xyz is not None:
            xyz_node = ET.SubElement(axis_node, 'xyz', {'expressed_in': '__model__'})
            xyz_node.text = ' '.join([str(value) for value in self.axis_xyz])
        if self.lower_limit is not None:
            limit_node = ET.SubElement(axis_node, 'limit')
            lower_node = ET.SubElement(limit_node, 'lower')
            lower_node.text = str(self.lower_limit)
            upper_node = ET.SubElement(limit_node, 'upper')
            upper_node.text = str(self.upper_limit)