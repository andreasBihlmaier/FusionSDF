import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

import adsk.core
import adsk.fusion

from .log import log
from .util import normalize_name, transform2_to_pose, prettify_xml, cm_to_m, kg_cm2_to_kg_m2, world_inertia_to_com_inertia, matrix3d_to_rpy, name_to_path
from .link import Link, LinkElement, LinkElementType, LinkGeometry, LinkGeometryType, LinkInertial
from .joint import Joint, JointType
from .pose import Pose



class SDF:
    def __init__(self, design: adsk.fusion.Design, meshes_cache_dir_path: Path = None):
        self.design = design
        self.meshes_cache_dir_path = meshes_cache_dir_path
        self.tmp_dir_path: Path = Path(tempfile.mkdtemp())
        self.tmp_meshes_dir_path: Path = self.tmp_dir_path / 'meshes'
        self.name: str = None
        self.links: Dict[str, Link] = {}
        self.joints: Dict[str, Joint] = {}
        self.fusion_joints: List[List[adsk.fusion.Joint, bool, str]] = []  # (fusion_joint, as_built, prefix)
        self.occurrences_in_rigid_groups: Dict[str, str] = {}  # occurrence.name -> link_name of rigid group
        self.root_link: str = None

        self.parse_root_component()


    def parse_root_component(self):
        root_component = self.design.rootComponent
        self.name = normalize_name(root_component.name)
        log(f'parse_root_component: {root_component.name}\n')

        for rigid_group in root_component.rigidGroups:
            self.add_rigid_group(root_component.occurrences, adsk.core.Matrix3D.create(), rigid_group, '')

        for occurrence in root_component.occurrences:
            self.parse_occurrence(occurrence, '')

        for joint in root_component.joints:
            self.add_joint(joint, False, '')
        for joint in root_component.asBuiltJoints:
            self.add_joint(joint, True, '')
        for fusion_joint, as_built, prefix in self.fusion_joints:
            self.add_joint(fusion_joint, as_built, prefix)

        links_with_parent_joints = set([joint.child for joint in self.joints.values()])
        root_links = set(self.links.keys()) - links_with_parent_joints
        if len(root_links) == 0:
            log(f'WARNING: No root link found\n')
        else:
            if len(root_links) != 1:
                log(f'WARNING: Multiple root links found: {root_links}\n')
            self.root_link = next(iter(root_links))
        
        # Add empty dummy link "base_link" so the <pose> of the root link works as intended
        self.links['base_link'] = Link('base_link')
        self.links['base_link'].inertial = LinkInertial(Pose(), mass=1e-4, ixx=1e-9, ixy=0, ixz=0, iyy=1e-9, iyz=0, izz=1e-9)
        self.joints['base_link_joint'] = Joint('base_link_joint', JointType.FIXED, None, 'base_link', self.root_link)
        self.root_link = 'base_link'


    def parse_occurrence(self, occurrence: adsk.fusion.Occurrence, prefix: str):
        log(f'parse_occurrence: {occurrence.name}; prefix="{prefix}"\n')

        self.add_link(occurrence, prefix)

        children_prefix = prefix + normalize_name(occurrence.name) + '__'

        rigid_group_link = None
        for rigid_group in occurrence.component.rigidGroups:
            rigid_group_link = self.add_rigid_group(occurrence.component.occurrences, occurrence.transform2, rigid_group, children_prefix)
        if rigid_group_link is not None:
            # TODO: Remove this workaround for joints between components with rigid groups
            occurrence.attributes.add('FusionSDF', 'link_name', rigid_group_link.name)

        for suboccurrence in occurrence.childOccurrences:
            self.parse_occurrence(suboccurrence, children_prefix)

        # Process joints last to ensure all links have FusionSDF/link_name attribute assigned
        for joint in occurrence.component.joints:
            self.fusion_joints.append([joint, False, children_prefix])

        for joint in occurrence.component.asBuiltJoints:
            self.fusion_joints.append([joint, True, children_prefix])


    def add_link(self, occurrence: adsk.fusion.Occurrence, prefix: str, rigid_group_pose: adsk.core.Matrix3D = None):
        link_name = prefix + normalize_name(occurrence.name)
        log(f'add_link: occurence="{occurrence.name}"; prefix="{prefix}" -> link_name={link_name}\n')

        if link_name in self.links:
            log(f'Link "{link_name}" already exists, skipping\n')
            return

        if occurrence.name in self.occurrences_in_rigid_groups:
            occurrence.attributes.add('FusionSDF', 'link_name', self.occurrences_in_rigid_groups[occurrence.name])
            log(f'Occurence "{occurrence.name}" is in rigid group "{self.occurrences_in_rigid_groups[occurrence.name]}", skipping\n')
            return
        occurrence.attributes.add('FusionSDF', 'link_name', link_name)

        if occurrence.bRepBodies.count == 0:  # skip empty links
            log(f'Link "{link_name}" has no bodies, skipping\n')
            return

        link = Link(link_name)
        if rigid_group_pose is not None:
            link.pose = rigid_group_pose
        else:
            link.pose = transform2_to_pose(occurrence.transform2)
        link_dir_path = self.tmp_meshes_dir_path / name_to_path(link.name)

        for body in occurrence.bRepBodies:
            log(f'visual: {body.name}\n')
            visual = LinkElement(LinkElementType.VISUAL, link.name + '__' + normalize_name(body.name) + '_visual')
            visual.geometry = LinkGeometry(LinkGeometryType.MESH)
            visual.geometry.mesh_uri = 'meshes/' + name_to_path(visual.name) + '.obj'
            if rigid_group_pose is not None:
                visual.pose = rigid_group_pose
            mesh_path = self.tmp_dir_path / visual.geometry.mesh_uri
            link.visuals[visual.name] = visual

            collision = LinkElement(LinkElementType.COLLISION, link.name + '__' + normalize_name(body.name) + '_collision')
            use_collision_mesh = False
            if self.design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
                use_collision_mesh_parameter = self.design.userParameters.itemByName(collision.name + '_USE_MESH')
                use_collision_mesh = use_collision_mesh_parameter is not None and use_collision_mesh_parameter.value
            if use_collision_mesh:
                log(f'using mesh for {collision.name}\n')
                collision.pose = visual.pose
                collision.geometry = visual.geometry
            else:
                log(f'using oriented minimum bounding box for {collision.name}\n')
                obb = body.orientedMinimumBoundingBox
                log(f'obb: centerPoint={obb.centerPoint.asArray()}; height={obb.height}; width={obb.width}; length={obb.length}; heightDirection={obb.heightDirection.asArray()}; widthDirection={obb.widthDirection.asArray()}; lengthDirection={obb.lengthDirection.asArray()}\n')
                obb_matrix3d = adsk.core.Matrix3D.create()
                obb_matrix3d.setWithCoordinateSystem(obb.centerPoint, obb.heightDirection, obb.widthDirection, obb.lengthDirection)
                collision.pose = Pose(cm_to_m(obb.centerPoint.asArray()), matrix3d_to_rpy(obb_matrix3d))
                if rigid_group_pose is not None:
                    collision.pose = rigid_group_pose * collision.pose
                collision.geometry = LinkGeometry(LinkGeometryType.BOX)
                collision.geometry.size = [cm_to_m(obb.height), cm_to_m(obb.width), cm_to_m(obb.length)]
            link.collisions[collision.name] = collision

            os.makedirs(link_dir_path, exist_ok=True)
            mesh_cache_path = self.meshes_cache_dir_path / visual.geometry.mesh_uri.removeprefix('meshes/')
            if mesh_cache_path.exists():
                log(f'using cached mesh "{mesh_cache_path}"\n')
                shutil.copy(mesh_cache_path, mesh_path)
                if mesh_cache_path.with_suffix('.mtl').exists():
                    shutil.copy(mesh_cache_path.with_suffix('.mtl'), mesh_path.with_suffix('.mtl'))
            else:
                export_manager = self.design.exportManager
                export_options = export_manager.createOBJExportOptions(body, str(mesh_path))
                export_options.sendToPrintUtility = False
                export_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
                if not export_manager.execute(export_options):
                    log(f'ERROR: Failed to export mesh "{mesh_path}"\n')

        physical_properties = occurrence.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
        center_of_mass = cm_to_m(physical_properties.centerOfMass.asArray())
        inertia_valid, xx, yy, zz, xy, yz, xz = physical_properties.getXYZMomentsOfInertia()
        if not inertia_valid:
            log(f'ERROR: Failed to get moments of inertia for "{link.name}"\n')
            xx, yy, zz, xy, yz, xz = 1, 1, 1, 0, 0, 0

        xx, yy, zz, xy, yz, xz = [kg_cm2_to_kg_m2(value) for value in [xx, yy, zz, xy, yz, xz]]
        ixx, iyy, izz, ixy, iyz, ixz = world_inertia_to_com_inertia([xx, yy, zz, xy, yz, xz], center_of_mass, physical_properties.mass) 

        inertial_pose_model = Pose(center_of_mass, [0, 0, 0])
        if rigid_group_pose is not None:
            inertial_pose_link = link.pose.inverse() * rigid_group_pose * inertial_pose_model
        else: 
            inertial_pose_link = link.pose.inverse() * inertial_pose_model
        inertial_pose_link.relative_to = None  # SDF does not support relative_to attribute for inertial pose
        link.inertial = LinkInertial(inertial_pose_link,
                                     physical_properties.mass,
                                     ixx, ixy, ixz, iyy, iyz, izz)

        self.links[link.name] = link
        return link


    def add_joint(self, fusion_joint: adsk.fusion.Joint, as_built: bool, prefix: str):
        joint_name = prefix + normalize_name(fusion_joint.name)
        log(f'add_joint: fusion_joint="{fusion_joint.name}"; prefix="{prefix}" -> joint_name="{joint_name}"\n')
        if joint_name in self.joints:
            log(f'Joint "{joint_name}" already exists, skipping\n')
            return

        joint = Joint(joint_name)
        fusion_joint_to_sdf_joint_type = {
            adsk.fusion.JointTypes.RigidJointType: JointType.FIXED,
            adsk.fusion.JointTypes.RevoluteJointType: JointType.REVOLUTE,
            adsk.fusion.JointTypes.SliderJointType: JointType.PRISMATIC}
        joint_motion = fusion_joint.jointMotion
        if joint_motion.jointType in fusion_joint_to_sdf_joint_type:
            joint.joint_type = fusion_joint_to_sdf_joint_type[joint_motion.jointType]
        else:
            log(f'ERROR: Unsupported joint type "{joint_motion.jointType}" for "{joint_name}, using fixed"\n')
            joint.joint_type = JointType.FIXED
        if joint.joint_type == JointType.REVOLUTE:
            joint.axis_xyz = joint_motion.rotationAxisVector.asArray()
            rotation_limits = joint_motion.rotationLimits
            if rotation_limits.isMinimumValueEnabled or rotation_limits.isMaximumValueEnabled:
                joint.lower_limit = rotation_limits.minimumValue
                joint.upper_limit = rotation_limits.maximumValue
            else:
                joint.joint_type = JointType.CONTINUOUS
        elif joint.joint_type == JointType.PRISMATIC:
            joint.axis_xyz = joint_motion.slideDirectionVector.asArray()
            slide_limits = joint_motion.slideLimits
            joint.lower_limit = cm_to_m(slide_limits.minimumValue)
            joint.upper_limit = cm_to_m(slide_limits.maximumValue)
        # Note: fusion_joint.isFlipped can be ignored
        if fusion_joint.occurrenceTwo.name in self.occurrences_in_rigid_groups:
            joint.parent = self.occurrences_in_rigid_groups[fusion_joint.occurrenceTwo.name]
        else:
            joint.parent = fusion_joint.occurrenceTwo.attributes.itemByName('FusionSDF', 'link_name').value
        if fusion_joint.occurrenceOne.name in self.occurrences_in_rigid_groups:
            joint.child = self.occurrences_in_rigid_groups[fusion_joint.occurrenceOne.name]
        else:
            joint.child = fusion_joint.occurrenceOne.attributes.itemByName('FusionSDF', 'link_name').value
        if self.design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
            swap_parent_child_parameter = self.design.userParameters.itemByName(joint.name + '_SWAP_PARENT_CHILD')
            if swap_parent_child_parameter is not None and swap_parent_child_parameter.value:
                joint.parent, joint.child = joint.child, joint.parent
                if joint.axis_xyz is not None:
                    joint.axis_xyz = [-value for value in joint.axis_xyz]
        if as_built:
            joint_origin = fusion_joint.geometry
        else:
            joint_origin = fusion_joint.geometryOrOriginOne
        if joint_origin is not None:
            joint.pose = Pose(cm_to_m(joint_origin.origin.asArray()), [0, 0, 0])

        self.joints[joint.name] = joint


    def add_rigid_group(self, parent_occurrences: adsk.fusion.Occurrences, parent_pose: adsk.core.Matrix3D, rigid_group: adsk.fusion.RigidGroup, prefix: str):
        link_name = prefix + normalize_name(rigid_group.name)
        log(f'add_rigid_group: rigid_group="{rigid_group.name}"; prefix="{prefix}" -> link_name={link_name}\n')

        # Create a temporary component for all the occurrences in the rigid group
        rigid_group_occurrence = parent_occurrences.addNewComponent(adsk.core.Matrix3D.create())
        rigid_group_component = rigid_group_occurrence.component
        rigid_group_component.name = link_name
        for occurrence in rigid_group.occurrences:
            for body in occurrence.bRepBodies:
                body.copyToComponent(rigid_group_occurrence)
        rigid_group_link = self.add_link(rigid_group_occurrence, '', rigid_group_pose=transform2_to_pose(parent_pose))
        rigid_group_occurrence.deleteMe()

        # Do not further process rigid group occurrences
        for occurrence in rigid_group.occurrences:
            self.occurrences_in_rigid_groups[occurrence.name] = link_name + '_1'  # components automatically get a ':1' suffix
        log(f'self.occurrences_in_rigid_groups: {self.occurrences_in_rigid_groups}\n')
        return rigid_group_link


    def print(self):
        log(f'SDF: {self.name}\n')
        log(f'tmp_dir_path: {self.tmp_dir_path}\n')
        log('Links:\n')
        for link in self.links.values():
            log(f'  {link}\n')

        log('Joints:\n')
        for joint in self.joints.values():
            log(f'  {joint}\n')


    def to_sdf_string(self):
        sdf_node = ET.Element('sdf', {'version': '1.11'})
        model_node = ET.SubElement(sdf_node, 'model', {'name': self.name})
        if self.root_link is not None:  # SDF expects canonical link as first link in model
            self.links[self.root_link].to_sdf_element(model_node)
        for link in self.links.values():
            if link.name == self.root_link:  # skip root link as it was already added
                continue
            link.to_sdf_element(model_node)
        for joint in self.joints.values():
            joint.to_sdf_element(model_node)
        return ET.tostring(sdf_node)


    def save(self, path: Path):
        log(f'Saving SDF to "{path}"\n')
        os.makedirs(path, exist_ok=True)

        mesh_dir_path = path / 'meshes'
        if mesh_dir_path.exists():
            shutil.rmtree(mesh_dir_path)
        if self.tmp_meshes_dir_path.exists():
            shutil.move(self.tmp_meshes_dir_path, path)

        # TODO
        with open(path / 'model.sdf', 'w') as f:
            f.write(prettify_xml(self.to_sdf_string()))