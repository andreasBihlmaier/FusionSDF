import unittest
import xml.etree.ElementTree as ET

from typing import List

from .transform import Transform


class Pose:
    def __init__(self, translation: List[float] = [0, 0, 0], rotation: List[float] = [0, 0, 0], relative_to='__model__'):
        self.transform: Transform = Transform(translation, rotation)
        self.relative_to: str = relative_to


    def __str__(self):
        return f'Pose(translation={self.transform.get_translation()}, rotation={self.transform.get_rotation_rpy()}, relative_to="{self.relative_to}")'


    def to_sdf_element(self, node):
        translation = self.transform.get_translation()
        rotation = self.transform.get_rotation_rpy()
        # surpress zero pose
        if all([abs(v) < 1e-6 for v in translation + rotation]):
            return
        pose_node = ET.SubElement(node, 'pose')
        if self.relative_to:
            pose_node.attrib['relative_to'] = self.relative_to
        pose_node.text = ' '.join([str(value) for value in translation + rotation])

    
    def inverse(self):
        return Pose(self.transform.inverse().get_translation(), self.transform.inverse().get_rotation_rpy(), self.relative_to)


    def __mul__(self, other):
        combined = self.transform * other.transform
        return Pose(combined.get_translation(), combined.get_rotation_rpy(), self.relative_to)