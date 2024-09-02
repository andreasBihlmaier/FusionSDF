# FusionSDF

Export [Fusion 360](https://www.autodesk.com/products/fusion-360/) designs to [SDF (Simulation Description Format)](http://sdformat.org/)

The goal of FusionSDF is to make as few assumptions about the structure of the design as possible and hence avoid restricting it. In the ideal case, exporting the design as an SDF can be an afterthought to completing the design, including components, bodies, joints, physical materials and appearances. The assumptions FusionSDF does make on the design are
- The top level component only consists of components and joints. Other elements at the top level, e.g. bodies, will be ignored.
- Every link is a component
- To be valid as ROS robot_description, all components must be linked by joints to form a tree structure. This implies there must be only one root link, i.e. one link that is not a child of any joint.
- Each rigid group corresponds to a single link
- No use of double underscores "__" in names

The generated SDF can be further optimized with [sdfopt](sdfopt/README.md), e.g. decimating meshes and adding better visual materials.


## Installation instructions
- In Fusion 360: Utilities -> Add-Ins -> Scripts and Add-Ins, Tab "Scripts" (shortcut: Shift + S)
- Click on the green plus sign next to "My Scripts". This opens a select folder dialog in the Fusion 360 Scripts directory (e.g. C:\Users\USERNAME\AppData\Roaming\Autodesk\Autodesk Fusion 360\API\Scripts). Keep this dialog open.
- Copy the entire FusionSDF folder (this entire git repository) into this Fusion 360 Scripts directory.
- In the Add new script dialog, select the FusionSDF directory that you just copied there.


## Usage
- **Save your design**
- Utilities -> Add-Ins -> Scripts and Add-Ins, Tab "Scripts" (shortcut: Shift + S)
- My Script -> FusionSDF
- Run
- Select folder for generated model.sdf + meshes
- Wait until FusionSDF is done (there is no progress bar yet). The final message in the Text Commands console should read "Saving SDF to $PATH".
- Optional: Use [sdfopt](sdfopt/README.md) to optimize the generated SDF.

### Settings via User Parameters
- Per body `_USE_MESH` setting to use mesh as collision geometry instead of oriented bounding box
- Per joint `_SWAP_PARENT_CHILD` setting to swap SDF joint child and parent

For example, to use a mesh of the body as collision element for `link1__body1_collision` add a user parameter `link1__body1_collision_USE_MESH` and set it to `1`.

### Mesh cache directory
Exporting the design's bodies as meshes makes up most of FusionSDF's runtime. When iterating on the design's component structure, joints or other aspects that _do not modify any body_, the repeated export of the same bodies can be avoided by caching them.

FusionSDF uses the directory `meshes_cache` for this purpose. It is easiest created by running FusionSDF once on the design and copying the generated `meshes` directory to `meshes_cache`. Afterwards you simply export to the same model directory (the folder you select when running FusionSDF).

_The cache must be updated manually_! When modifying a body in the design, manually delete it from `meshes_cache`, rerun FusionSDF and copy the newly exported body back afterwards. You can of course simply delete the entire `meshes_cache` directory and copy the newly generated `meshes` again.


## Tips & Tricks
- If you have many independent components in the design and want them to be part of a single link, then select all of them and create a Rigid Group. FusionSDF exports Rigid Groups as a single link.
- A typical workflow when working with existing CAD data (instead of a native Fusion 360 design), e.g. a STEP file, could look like the following. Save the intermediate design frequently, especially before running FusionSDF.
  - Create a new Design
  - Set "Do not capture Design History"
  - Import the CAD model
  - Optionally delete all small parts not relevant for the SDF (e.g. fasteners) or fuse them with other Bodies.
  - Create a new top-level Components for each link. Move the corresponding Components (and Bodies) into these link Components.
  - Create a Rigid Group of everything contained in each link Component.
  - Set "Caputure Design History"
  - Add Joints between the link components. Likely you want to use As-Built Joints.
  - Check and adjust each components/bodies Physical Material and Appearance.
  - Optionally set [FusionSDF User Parameters](#settings-via-user-parameters)
  - Run FusionSDF
- Some options to view the generated SDF:
  - Note: The `<uri>`s in the generated SDF's `<mesh>` are relative paths. For the following to work you either have to either
    - replace these relative paths by absolute `file://` paths,
    - copy the SDF folder to a `GZ_SIM_RESOURCE_PATH` directory and use `model://` URIs or
    - install the SDF folder from a ROS package and use `package://` URIs.
  - RViz: Use [view_sdf_rviz](https://github.com/Yadunund/view_sdf_rviz)
    - `ros2 launch view_sdf_rviz view_sdf.launch.py sdf_file:=SDF_FOLDER_PATH/model.sdf`
  - Gazebo:
    - `ros2 launch ros_gz_sim gz_sim.launch.py gz_args:=empty.sdf`
    - `ros2 run ros_gz_sim create -file SDF_FOLDER_PATH/model.sdf`


## Known limitations and issues
- Components containing a Rigid Group are assumed to _only_ consist of this Rigid Group with respect to joints to these Components.


## TODOs
- Resolve known limitations and issues
- sdfopt: Advanced material export via Blender (string matching of material name)
- Add a progress bar (exporting all design bodies as meshes can take some time)