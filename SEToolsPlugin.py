"""A plugin designed to import and export SE formats from Autodesk Maya"""

# SE formats import / export plugin for Maya
# Developed by DTZxPorter

import os
import os.path
import math
import json
import maya.mel as mel
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
import maya.OpenMayaMPx as OpenMayaMPx
import seanim as SEAnim
import semodel as SEModel


def __first__(first_iter, second_iter):
    """Compare two iterable objects"""
    for elem in first_iter:
        if elem in second_iter:
            return first_iter
    return None


def __log_info__(format_str=""):
    """Logs a line to the console"""
    print "[SETools] " + format_str


def __about_window__():
    """Present the about information"""
    cmds.confirmDialog(message="A SE Formats import and export plugin for Autodesk Maya. SE Formats are open-sourced model and animation containers supported across various toolchains.\n\n- Developed by DTZxPorter\n- Version 4.0.0",
                       button=['OK'], defaultButton='OK', title="About SE Tools")


def __importfile_dialog__(filter_str="", caption_str=""):
    """Ask the user for an input file"""
    if cmds.about(version=True)[:4] == "2012":
        import_from = cmds.fileDialog2(
            fileMode=1, fileFilter=filter_str, caption=caption_str)
    else:
        import_from = cmds.fileDialog2(fileMode=1,
                                       dialogStyle=2,
                                       fileFilter=filter_str,
                                       caption=caption_str)

    if not import_from or import_from[0].strip() == "":
        return None

    path = import_from[0].strip()
    path_split = os.path.splitext(path)
    if path_split[1] == ".*":
        path = path_split

    return path


def __exportfile_dialog__(filter_str="", caption_str=""):
    """Ask the user for an export file"""
    if cmds.about(version=True)[:4] == "2012":
        save_to = cmds.fileDialog2(
            fileMode=0, fileFilter=filter_str, caption=caption_str)
    else:
        save_to = cmds.fileDialog2(fileMode=0,
                                   dialogStyle=2,
                                   fileFilter=filter_str,
                                   caption=caption_str)

    if not save_to or save_to[0].strip() == "":
        return None

    return save_to[0].strip()


def __reload_plugin__():
    """Reloads the plugin, not all Maya versions support this"""
    cmds.unloadPlugin("SEToolsPlugin.py")
    cmds.loadPlugin("SEToolsPlugin.py")


def __remove_menu__():
    """Removes the plugin menu"""
    if cmds.control("SEToolsMenu", exists=True):
        cmds.deleteUI("SEToolsMenu", menu=True)


def __create_menu__():
    """Creates the plugin menu"""
    __remove_menu__()

    # Create the base menu object
    cmds.setParent(mel.eval("$tmp = $gMainWindow"))
    menu = cmds.menu("SEToolsMenu", label="SE Tools", tearOff=True)

    # Animation menu controls
    anim_menu = cmds.menuItem(label="Animation", subMenu=True)

    cmds.menuItem(label="Import SEAnim File", command=lambda x: __import_seanim__(
    ), annotation="Imports a SEAnim File, resetting the scene first")
    cmds.menuItem(label="Import and Blend SEAnim File", command=lambda x: __import_seanim__(
        False, True), annotation="Imports a SEAnim file blending with existing animations")
    cmds.menuItem(label="Import SEAnim File At Current Time", command=lambda x: __import_seanim__(
        True, True), annotation="Imports a SEAnim file, blending with existing animations at the current scene time")
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Export SEAnim File", command=lambda x: __export_seanim__(
    ), annotation="Exports a SEAnim file using either selected joints or all of them")
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Edit Notetracks", command=lambda x: __edit_notetracks__(
    ), annotation="Edit notetracks in the current scene")

    cmds.setParent(anim_menu, menu=True)
    cmds.setParent(menu, menu=True)

    # Model menu controls
    model_menu = cmds.menuItem(label="Model", subMenu=True)

    cmds.menuItem(label="Import SEModel File",
                  annotation="Imports a SEModel File", command=lambda x: __import_semodel__())
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Export SEModel File", command=lambda x: __export_semodel__(
    ), annotation="Exports a SEModel file using either selected objects or all of them")

    cmds.setParent(model_menu, menu=True)
    cmds.setParent(menu, menu=True)
    cmds.menuItem(divider=True)

    # Scene controls
    cmds.menuItem(label="Clean Namespaces", command=lambda x: __purge_namespaces__(
    ), annotation="Removes all namespaces in the current scene")
    cmds.menuItem(label="Select All Joints", command=lambda x: __select_joints__(
    ), annotation="Selects all joints in the current scene")
    cmds.menuItem(label="Select Keyed Joints", command=lambda x: __select_keyframes__(
    ), annotation="Selects all joints with keyframes in the current scene")
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Reset Scene", command=lambda x: __scene_resetanim__(
    ), annotation="Resets the current scene to the bind position")
    cmds.menuItem(label="Clear Curves", command=lambda x: __purge_keyframes__(
    ), annotation="Clears all cached keyframe curves in the scene")
    cmds.menuItem(divider=True)

    # Reload and about controls
    cmds.menuItem(label="Reload Plugin", command=lambda x: __reload_plugin__(
    ), annotation="Attempts to reload the plugin")
    cmds.menuItem(label="About", command=lambda x: __about_window__())


def __removesel_notetracks__():
    """Remove selected notetracks"""
    existing_notes = __get_notetracks__()
    selected_items = cmds.textScrollList(
        "SENotesNoteList", query=True, selectItem=True)

    if not selected_items:
        return

    # Iterate, and remove if need be
    for sel_text in selected_items:
        note_name = sel_text[sel_text.find(" ") + 1:]
        note_frame = int(sel_text[:sel_text.find(" ")].replace(
            "[", "").replace("]", "").replace("\t", ""))

        if note_name not in existing_notes:
            continue
        if note_frame not in existing_notes[note_name]:
            continue

        existing_notes[note_name].remove(note_frame)

    # Remove from list
    cmds.textScrollList("SENotesNoteList", edit=True,
                        removeItem=selected_items)

    # Save the value
    cmds.setAttr("SENotes.Notetracks", json.dumps(
        existing_notes), type="string")


def __create_notetrack__():
    """Create a new notetrack at the current scene time"""
    current_frame = int(cmds.currentTime(query=True))

    # Ask the user for a name
    if cmds.promptDialog(title="SEAnim - Create Notetrack",
                         message="Enter in the new notetrack name:\t\t  ") != "Confirm":
        return
    new_name = cmds.promptDialog(query=True, text=True)

    # Add it with the add function
    if __add_notetrack__(new_name, current_frame):
        # Add to the list
        cmds.textScrollList("SENotesNoteList", append=[
            "[" + str(current_frame) + "\t] " + new_name], edit=True)


def __edit_notetracks__():
    """Shows the edit notetracks window"""
    if cmds.control("SENotesEditor", exists=True):
        cmds.deleteUI("SENotesEditor")

    wnd = cmds.window("SENotesEditor", title="SEAnim - Edit Notetracks",
                      width=400, height=325, retain=True, maximizeButton=False)
    wnd_layout = cmds.formLayout("SENotesEditor_Form")

    # Build list
    notetracks = __get_notetracks__()
    note_strings = []
    for note in notetracks:
        for frame in notetracks[note]:
            note_strings.append("[" + str(frame) + "\t] " + note)

    # Create required controls
    notetrack_ctrl = cmds.text(
        label="Frame:                   Notetrack:", annotation="Current scene notetracks")
    notelist_ctrl = cmds.textScrollList(
        "SENotesNoteList", append=note_strings, allowMultiSelection=True)
    add_ctrl = cmds.button(label="Add Notetrack",
                           command=lambda x: __create_notetrack__(),
                           annotation="Add a notetrack at the current scene time")
    remove_ctrl = cmds.button(label="Remove Selected",
                              command=lambda x: __removesel_notetracks__())
    clearall_ctrl = cmds.button(
        label="Clear All", command=lambda x: __clear_notetracks__())

    # Reflow the window control
    cmds.formLayout(wnd_layout, edit=True,
                    attachForm=[
                        (notetrack_ctrl, 'top', 10),
                        (notetrack_ctrl, 'left', 10),
                        (notelist_ctrl, 'left', 10),
                        (notelist_ctrl, 'right', 10),
                        (add_ctrl, 'left', 10),
                        (add_ctrl, 'bottom', 10),
                        (remove_ctrl, 'bottom', 10),
                        (clearall_ctrl, 'bottom', 10)
                    ],
                    attachControl=[
                        (notelist_ctrl, 'top', 5, notetrack_ctrl),
                        (notelist_ctrl, 'bottom', 5, add_ctrl),
                        (remove_ctrl, 'left', 5, add_ctrl),
                        (clearall_ctrl, 'left', 5, remove_ctrl)
                    ])

    cmds.showWindow(wnd)


def __clear_notetracks__():
    """Deletes all notetracks"""
    if cmds.objExists("SENotes"):
        cmds.delete("SENotes")

    # Clear the edit list of items
    notetracks = cmds.textScrollList(
        "SENotesNoteList", query=True, allItems=True)
    if notetracks:
        for note in notetracks:
            cmds.textScrollList("SENotesNoteList", edit=True, removeItem=note)


def __get_notetracks__():
    """Loads all the notetracks in the scene"""
    if not cmds.objExists("SENotes"):
        cmds.rename(cmds.spaceLocator(), "SENotes")

    if not cmds.objExists("SENotes.Notetracks"):
        cmds.addAttr("SENotes", longName="Notetracks",
                     dataType="string", storable=True)
        cmds.setAttr("SENotes.Notetracks", "{}", type="string")

    # Load the existing notetracks buffer, then ensure we have this notetrack
    return json.loads(cmds.getAttr("SENotes.Notetracks"))


def __add_notetrack__(name, frame):
    """Adds a notetrack to the scene"""
    current_notetracks = __get_notetracks__()

    # Ensure we have this notetrack
    if name not in current_notetracks:
        current_notetracks[name] = []

    added_res = False

    # Now, append the frame (If unique)
    frame = int(frame)
    if frame not in current_notetracks[name]:
        current_notetracks[name].append(frame)
        added_res = True

    # Save the value
    cmds.setAttr("SENotes.Notetracks", json.dumps(
        current_notetracks), type="string")
    return added_res


def __select_joints__():
    """Selects all the joints in the scene"""
    cmds.select(clear=True)
    for bone in cmds.ls(type="joint"):
        cmds.select(bone, add=True)


def __select_keyframes__():
    """Selects all keyframed joints in the scene"""
    cmds.select(clear=True)
    for bone in cmds.ls(type="joint"):
        if cmds.keyframe(bone + ".translate", query=True, timeChange=True):
            cmds.select(bone, add=True)
        elif cmds.keyframe(bone + ".rotate", query=True, timeChange=True):
            cmds.select(bone, add=True)
        elif cmds.keyframe(bone + ".scale", query=True, timeChange=True):
            cmds.select(bone, add=True)


def __purge_namespaces__():
    """Removes all the namespaces in the scene"""
    for bone in cmds.ls(type="joint"):
        if bone.find(":") > -1:
            try:
                cmds.rename(bone, bone.split(":")[-1])
            except RuntimeError:
                pass


def __get_nodenamespace__(name):
    """Gets the namespace of a node if any"""
    if name.find(":") > -1:
        return name[:name.find(":")]
    return None


def __create_nodenamespace__(node):
    """Creates the global namespace"""
    namespace = __get_nodenamespace__(node)
    if namespace is not None:
        if not OpenMaya.MNamespace().namespaceExists(":" + namespace):
            OpenMaya.MNamespace().addNamespace(":" + namespace)


def __get_parentname__(joint):
    """Gets the parent node name if any"""
    full_path = joint.fullPathName()
    split_path = full_path[1:].split("|")

    if len(split_path) > 2:
        return split_path[len(split_path) - 2]
    elif (len(split_path) == 2):
        select_list = OpenMaya.MSelectionList()
        select_list.add(full_path[0:full_path.find("|", 1)])

        result = OpenMaya.MDagPath()
        select_list.getDagPath(0, result)

        if (result.hasFn(OpenMaya.MFn.kJoint)):
            return split_path[len(split_path) - 2]

    return ""


def __disconnect_curve__(plug_source):
    """Disconnects an animation curve from the plug"""
    input_sources = OpenMaya.MPlugArray()
    plug_source.connectedTo(input_sources, True, False)

    if input_sources.length() > 0:
        con_node = input_sources[0]
        if con_node.node().hasFn(OpenMaya.MFn.kAnimCurve):
            dep_mod = OpenMaya.MDGModifier()
            dep_mod.disconnect(con_node, plug_source)
            dep_mod.doIt()


def __disconnect_curves__(joint_transform):
    """Disconnects any existing anim curves"""
    curve_plugs = ["translateX", "translateY", "translateZ",
                   "rotateX", "rotateY", "rotateZ", "scaleX", "scaleY", "scaleZ"]
    for plug in curve_plugs:
        __disconnect_curve__(OpenMaya.MFnDependencyNode(
            joint_transform).findPlug(plug, False))


def __scene_setinterpolation__(curve_path, interpol="none"):
    """Converts the given path to the given interpolation"""
    try:
        cmds.rotationInterpolation(curve_path, convert=interpol)
    except RuntimeError:
        pass


def __purge_keyframes__():
    """Removes all existing keyframes"""
    ext_frames = cmds.ls(type="animCurveTA") + cmds.ls(type="animCurveTL")
    if ext_frames:
        cmds.delete(ext_frames)


def __scene_resetanim__():
    """Resets the scene to bind position"""
    for bone in cmds.ls(type="joint"):
        # Fetch joint controller
        joint_controller = __scene_obtainjoint__(
            bone, True)

        # Disconnect animation curve, if connected
        __disconnect_curves__(joint_controller[0].transform())

    if cmds.objExists("SENotes"):
        cmds.delete("SENotes")


def __scene_getjoint__(joint_name):
    """Attempts to locate a joint in the scene"""
    joint_name = joint_name.strip()
    if joint_name == "":
        return None

    # Always resolve with non-namespace tags first
    if cmds.objExists(joint_name + ".t"):
        return joint_name

    # Attempt to resolve with any namespace
    joint_name = "*:" + joint_name
    if cmds.objExists(joint_name):
        # We must have only one result, otherwise, ignore this bone
        if len(cmds.ls(joint_name)) == 1:
            return joint_name

        __log_info__("SEAnim::GetJoint(%s) multiple "
                     "joint instances found, skipping..." % joint_name)
        return None

    # Joint is not in the scene
    __log_info__(
        "SEAnim::GetJoint(%s) joint was not found in the scene, skipping..." % joint_name)
    return None


def __is_rotation_bzero__(rotation):
    """Checks for zero rotation"""
    return (rotation[0] == 0.0 and rotation[1] == 0.0 and rotation[2] == 0.0)


def __scene_obtainjoint__(joint_name, reset_rest=True):
    """Attempts to fetch the joint object"""
    select_list = OpenMaya.MSelectionList()
    select_list.add(joint_name)

    # Attempt to get the path to the first item in the list
    result_path = OpenMaya.MDagPath()
    select_list.getDagPath(0, result_path)

    # Determine if valid, if so, construct a joint
    result_joint = OpenMayaAnim.MFnIkJoint(result_path)

    # Attempt to resolve rest positions
    if not cmds.objExists(joint_name + ".seanimRestT"):
        rest_translation = cmds.getAttr(joint_name + ".t")[0]
        rest_scale = cmds.getAttr(joint_name + ".scale")[0]
        rest_rotation_jo = cmds.getAttr(joint_name + ".jo")[0]
        rest_rotation_r = cmds.getAttr(joint_name + ".r")[0]

        # TODO: Make this take from the joint controller...

        # Take whichever one is used
        if __is_rotation_bzero__(rest_rotation_jo):
            rest_rotation = rest_rotation_r
        else:
            rest_rotation = rest_rotation_jo

        cmds.addAttr(joint_name, longName="seanimRestT",
                     dataType="double3", storable=True)
        cmds.addAttr(joint_name, longName="seanimRestS",
                     dataType="double3", storable=True)
        cmds.addAttr(joint_name, longName="seanimRestR",
                     dataType="double3", storable=True)

        cmds.setAttr(joint_name + ".seanimRestT",
                     rest_translation[0], rest_translation[1], rest_translation[2], type="double3")
        cmds.setAttr(joint_name + ".seanimRestS",
                     rest_scale[0], rest_scale[1], rest_scale[2], type="double3")
        cmds.setAttr(joint_name + ".seanimRestR",
                     rest_rotation[0], rest_rotation[1], rest_rotation[2], type="double3")
    else:
        # Fetch data from the saved rest positions
        rest_translation = cmds.getAttr(joint_name + ".seanimRestT")[0]
        rest_scale = cmds.getAttr(joint_name + ".seanimRestS")[0]
        rest_rotation = cmds.getAttr(joint_name + ".seanimRestR")[0]

    # Check whether or not to reset to rest position (Only reset if we have rest data available)
    if reset_rest:
        try:
            cmds.setAttr(
                joint_name + ".t", rest_translation[0], rest_translation[1], rest_translation[2])
            cmds.setAttr(joint_name + ".scale",
                         rest_scale[0], rest_scale[1], rest_scale[2])
            cmds.setAttr(joint_name + ".r", 0, 0, 0)
            cmds.setAttr(joint_name + ".jo",
                         rest_rotation[0], rest_rotation[1], rest_rotation[2])
        except RuntimeError:
            pass

    # Return the joint, and rest positions
    return (result_path, result_joint, rest_translation, rest_scale, rest_rotation)


def __scene_getcurve__(joint_transform, plug_name, curve_type):
    """Attempts to create a new scene curve for the given plug"""
    joint_plug = OpenMaya.MFnDependencyNode(
        joint_transform).findPlug(plug_name, False)
    joint_plug.setKeyable(True)
    joint_plug.setLocked(False)

    # If the plug is connected already, and the connection is a curve,
    # We can just grab the existing curve, else, make a new one...
    anim_curve = OpenMayaAnim.MFnAnimCurve()

    # Fetch connections, if we have one, connect, else, make a new one
    input_sources = OpenMaya.MPlugArray()
    joint_plug.connectedTo(input_sources, True, False)

    if input_sources.length() == 0:
        # Create a new curve with the type
        anim_curve.create(joint_plug, curve_type)
    elif input_sources[0].node().hasFn(OpenMaya.MFn.kAnimCurve):
        # Assign the existing curve to the controller
        anim_curve.setObject(input_sources[0].node())
        # Reset the interpolation type for the initial one, effects children
        if plug_name == "rotateX":
            __scene_setinterpolation__(joint_plug.name())
    else:
        # Fail, we can't animate this
        __log_info__(
            "SEAnim::GetCurve(%s) plug is already attached "
            "to another object, skipping..." % joint_plug.name())
        return None

    # Return the curve object
    return anim_curve


def __scene_getskin__(skin_name):
    """Gets a new skin object, or none if invalid"""
    if skin_name is None or skin_name == "" or skin_name.isspace():
        return None

    # Build the list and find the object
    select_list = OpenMaya.MSelectionList()
    select_list.add(skin_name)
    cluster_node = OpenMaya.MObject()
    select_list.getDependNode(0, cluster_node)
    # return cluster controller
    return OpenMayaAnim.MFnSkinCluster(cluster_node)


def __scene_newskin__(mesh_path, joints=[], max_influence=1):
    """Creates a skin cluster for the mesh"""
    skin_params = [x for x in joints]
    skin_params.append(mesh_path)

    # Create the skin cluster, maintaining the influence
    try:
        new_skin = cmds.skinCluster(
            *skin_params, tsb=True, mi=max_influence, nw=False)
    except RuntimeError:
        __log_info__(
            "SEModel::NewSkin(%s) could not create a new skinCluster, skipping..." % mesh_path)
        return None

    # Attach the controller, then return
    select_list = OpenMaya.MSelectionList()
    select_list.add(new_skin[0])

    # Attempt to get the path to the first item in the list
    result_cluster = OpenMaya.MObject()
    select_list.getDependNode(0, result_cluster)

    # Return it
    return OpenMayaAnim.MFnSkinCluster(result_cluster)


def __scene_bindmesh__(mesh_skin, weight_data):
    """Applies smooth skin bindings"""
    joint_indicies = {}

    # Build a list of API specific joint ids
    _tmp_array = OpenMaya.MDagPathArray()
    mesh_skin.influenceObjects(_tmp_array)
    _tmp_array_len = _tmp_array.length()

    # Iterate and assign indicies for names
    for idx in xrange(_tmp_array_len):
        joint_indicies[str(_tmp_array[idx].fullPathName())
                       ] = mesh_skin.indexForInfluenceObject(_tmp_array[idx])

    # Base format payload
    cluster_attr = str(mesh_skin.name()) + ".weightList[%d]"
    cluster_array_attr = (".weights[0:%d]" % (_tmp_array_len - 1))

    # Buffer for new indicies
    weight_values = [0] * _tmp_array_len

    # Iterate and apply weights
    for vertex, weights in weight_data:
        # Build final string
        if _tmp_array_len == 1:
            weight_payload = cluster_attr % vertex + ".weights[0]"
        else:
            weight_payload = cluster_attr % vertex + cluster_array_attr

        # Iterate over weights per bone
        for joint, weight_val in weights:
            weight_values[joint_indicies[joint]] = weight_val

        # Set all weights at once
        cmds.setAttr(weight_payload, *weight_values)
        # Clear for the next one
        weight_values = [0] * _tmp_array_len


def __build_image_path__(asset_path, image_path):
    """Builds the full image path"""
    root_path = os.path.dirname(asset_path)
    return os.path.join(root_path, image_path)


def __math_matrixtoquat__(maya_matrix):
    """Converts a Maya matrix array to a quaternion"""
    quat_x, quat_y, quat_z, quat_w = (0, 0, 0, 1)

    trans_remain = maya_matrix[0] + maya_matrix[5] + maya_matrix[10]
    if trans_remain > 0:
        divisor = math.sqrt(trans_remain + 1.0) * 2.0
        quat_w = 0.25 * divisor
        quat_x = (maya_matrix[6] - maya_matrix[9]) / divisor
        quat_y = (maya_matrix[8] - maya_matrix[2]) / divisor
        quat_z = (maya_matrix[1] - maya_matrix[4]) / divisor
    elif (maya_matrix[0] > maya_matrix[5]) and (maya_matrix[0] > maya_matrix[10]):
        divisor = math.sqrt(
            1.0 + maya_matrix[0] - maya_matrix[5] - maya_matrix[10]) * 2.0
        quat_w = (maya_matrix[6] - maya_matrix[9]) / divisor
        quat_x = 0.25 * divisor
        quat_y = (maya_matrix[4] + maya_matrix[1]) / divisor
        quat_z = (maya_matrix[8] + maya_matrix[2]) / divisor
    elif maya_matrix[5] > maya_matrix[10]:
        divisor = math.sqrt(
            1.0 + maya_matrix[5] - maya_matrix[0] - maya_matrix[10]) * 2.0
        quat_w = (maya_matrix[8] - maya_matrix[2]) / divisor
        quat_x = (maya_matrix[4] + maya_matrix[1]) / divisor
        quat_y = 0.25 * divisor
        quat_z = (maya_matrix[9] + maya_matrix[6]) / divisor
    else:
        divisor = math.sqrt(
            1.0 + maya_matrix[10] - maya_matrix[0] - maya_matrix[5]) * 2.0
        quat_w = (maya_matrix[1] - maya_matrix[4]) / divisor
        quat_x = (maya_matrix[8] + maya_matrix[2]) / divisor
        quat_y = (maya_matrix[9] + maya_matrix[6]) / divisor
        quat_z = 0.25 * divisor

    # Return the result
    return (quat_x, quat_y, quat_z, quat_w)


def __scene_resolve_animoverride__(joint_name, bone_anim_mods):
    """Attempts to resolve a relative parent type override"""
    try:
        # Resolve the parent tree
        parent_tree = cmds.ls(joint_name, long=True)[0].split('|')[1:-1]
        if not parent_tree:
            return None

        # Iterate over the tree
        for parent_name in parent_tree:
            if parent_name.find(":") > -1:
                parent_name = parent_name[parent_name.find(":") + 1:]

            # Attempt to locate a relative override
            for mod_bone in bone_anim_mods:
                if parent_name == mod_bone.name:
                    return mod_bone.modifier

        # No override found
        return None
    except RuntimeError:
        return None


def __scene_getobjectdag__(mobject):
    """Resolve the dag path object from a base type"""
    select_list = OpenMaya.MSelectionList()
    select_list.add(OpenMaya.MFnDagNode(mobject).fullPathName())

    result = OpenMaya.MDagPath()
    select_list.getDagPath(0, result)

    return result


def __scene_getmaterials__(mesh, path):
    """Gets materials for the given mesh"""
    result = []
    shaders = OpenMaya.MObjectArray()
    shaderindices = OpenMaya.MIntArray()
    mesh.getConnectedShaders(path.instanceNumber(), shaders, shaderindices)

    for index in xrange(shaders.length()):
        shadernode = OpenMaya.MFnDependencyNode(shaders[index])
        shaderplug = shadernode.findPlug("surfaceShader")
        matplug = OpenMaya.MPlugArray()
        shaderplug.connectedTo(matplug, True, False)

        if matplug.length() > 0:
            result.append(OpenMaya.MFnDependencyNode(matplug[0].node()).name())

    return result


def __bonelist_indexof__(bonelist, name):
    """Returns the first bone that matches."""
    for index in xrange(len(bonelist)):
        if (bonelist[index].name == name):
            return index
    return -1


def __import_seanim__(scene_time=False, blend_anim=False):
    """Asks for a file to import"""
    import_file = __importfile_dialog__(
        "SEAnim Files (*.seanim)", "Import SEAnim")
    if import_file:
        __load_seanim__(import_file, scene_time, blend_anim)


def __export_seanim__():
    """Asks for a file to export"""
    export_file = __exportfile_dialog__(
        "SEAnim Files (*.seanim)", "Export SEAnim")
    if export_file:
        __save_seanim__(export_file)


def __import_semodel__():
    """Asks for a file to import"""
    import_file = __importfile_dialog__(
        "SEModel Files (*.semodel)", "Import SEModel")
    if import_file:
        __load_semodel__(import_file)


def __export_semodel__():
    """Asks for a file to export"""
    export_file = __exportfile_dialog__(
        "SEModel Files (*.semodel)", "Export SEModel")
    if export_file:
        __save_semodel__(export_file)


def __save_semodel__(file_path):
    """Saves the scene as a SEModel file"""
    model = SEModel.Model()

    # We need to configure the scene, save current state and change back later
    currentunit_state = cmds.currentUnit(query=True, linear=True)
    currentangle_state = cmds.currentUnit(query=True, angle=True)
    cmds.currentUnit(linear="cm", angle="deg")

    # We need to get the current selection, or, select all if none
    select_list = OpenMaya.MSelectionList()
    OpenMaya.MGlobal.getActiveSelectionList(select_list)

    # If empty, select all joints/meshes
    if (select_list.length() == 0):
        mel.eval("string $selected[] = `ls -type joint`; select -r $selected;")
        mel.eval("string $transforms[] = `ls -tr`;string $polyMeshes[] = `filterExpand -sm 12 $transforms`;select -add $polyMeshes;")
        OpenMaya.MGlobal.getActiveSelectionList(select_list)

    # If still empty, error blank scene
    if (select_list.length() == 0):
        __log_info__(
            "SEModel::Export(%s) could not find any "
            "valid objects to export" % os.path.basename(file_path))
        return

    parent_stack = []
    unique_bones = set()

    # Build bones first
    for index in xrange(select_list.length()):
        depend_node = OpenMaya.MObject()
        select_list.getDependNode(index, depend_node)
        if not depend_node.hasFn(OpenMaya.MFn.kJoint):
            continue

        path = __scene_getobjectdag__(depend_node)
        controller = OpenMayaAnim.MFnIkJoint(path)
        tag_name = controller.name()

        if tag_name in unique_bones:
            continue
        unique_bones.add(tag_name)

        new_bone = SEModel.Bone()
        new_bone.name = tag_name
        parent_stack.append(__get_parentname__(controller))

        # Get the world and local space transforms,
        # semodels use both so we can help the loader later
        world_position = controller.getTranslation(OpenMaya.MSpace.kWorld)
        local_position = controller.getTranslation(OpenMaya.MSpace.kTransform)
        world_rotation = OpenMaya.MQuaternion()
        local_rotation = OpenMaya.MQuaternion()
        local_orientation = OpenMaya.MQuaternion()

        controller.getRotation(world_rotation, OpenMaya.MSpace.kWorld)
        controller.getRotation(local_rotation, OpenMaya.MSpace.kTransform)
        controller.getOrientation(local_orientation)

        # This is how maya's rotations for ikjoints work, they have two rotation
        # properties, rotation x joint orient
        local_rotation_mat = local_rotation * local_orientation

        scale_list = OpenMaya.MScriptUtil()
        scale_list.createFromList([1.0, 1.0, 1.0], 3)
        scale_ptr = scale_list.asDoublePtr()

        controller.getScale(scale_ptr)

        new_bone.globalPosition = (
            world_position.x, world_position.y, world_position.z)
        new_bone.localPosition = (
            local_position.x, local_position.y, local_position.z)
        new_bone.globalRotation = (
            world_rotation.x, world_rotation.y, world_rotation.z, world_rotation.w)
        new_bone.localRotation = (
            local_rotation_mat.x, local_rotation_mat.y, local_rotation_mat.z, local_rotation_mat.w)
        new_bone.scale = (OpenMaya.MScriptUtil().getDoubleArrayItem(scale_ptr, 0),
                          OpenMaya.MScriptUtil().getDoubleArrayItem(scale_ptr, 1),
                          OpenMaya.MScriptUtil().getDoubleArrayItem(scale_ptr, 2))
        new_bone.boneParent = -1    # Default to root bone for now, will modify after

        model.bones.append(new_bone)

    # We must generate the proper bone parent indices
    for index in xrange(len(parent_stack)):
        model.bones[index].boneParent = __bonelist_indexof__(
            model.bones, parent_stack[index])

    material_index = 0
    used_materials = {}
    unique_meshes = set()

    # We can now process meshes
    for index in xrange(select_list.length()):
        depend_node = OpenMaya.MObject()
        select_list.getDependNode(index, depend_node)
        path = __scene_getobjectdag__(depend_node)

        # Meshes at the base are transforms
        if not depend_node.hasFn(OpenMaya.MFn.kTransform):
            continue
        # If the transform is invalid, continue
        try:
            path.extendToShape()
        except RuntimeError:
            continue

        # We have a valid mesh
        controller = OpenMaya.MFnMesh(path)

        if path.partialPathName() in unique_meshes:
            continue
        unique_meshes.add(path.partialPathName())
        # Fetch materials and only keep unique ones
        mats = __scene_getmaterials__(controller, path)
        for mat in mats:
            if not mat in used_materials:
                used_materials[mat] = material_index
                new_mat = SEModel.Material()
                new_mat.name = mat
                model.materials.append(new_mat)
                material_index += 1

        new_mesh = SEModel.Mesh()

        vertex_iterator = OpenMaya.MItMeshVertex(path)
        face_iterator = OpenMaya.MItMeshPolygon(path)
        uv_sets = cmds.polyUVSet(
            path.partialPathName(), q=True, allUVSets=True)
        skin_cluster = __scene_getskin__(
            mel.eval("findRelatedSkinCluster " + path.partialPathName()))
        skin_joints = OpenMaya.MDagPathArray()
        model_joints = [x.name for x in model.bones]

        if skin_cluster is not None:
            skin_cluster.influenceObjects(skin_joints)

        uv_set_max = len(uv_sets)
        max_influence = 0

        # Set material indices
        for mat_index in xrange(uv_set_max):
            if (mat_index < len(mats)):
                new_mesh.materialReferences.append(
                    used_materials[mats[mat_index]])

        # Calculate maximum influence
        while not vertex_iterator.isDone():
            if skin_cluster is not None:
                # Get the weights to calculate maximum influence
                num_weights = OpenMaya.MScriptUtil()
                weight_values = OpenMaya.MDoubleArray()
                skin_cluster.getWeights(path, vertex_iterator.currentItem(
                ), weight_values, num_weights.asUintPtr())

                influence = 0

                for vindex in xrange(weight_values.length()):
                    if weight_values[vindex] > 0.000001:
                        influence += 1

                if influence > max_influence:
                    max_influence = influence
            vertex_iterator.next()

        vertex_iterator.reset()

        # Build the vertex buffer
        while not vertex_iterator.isDone():
            new_vertex = SEModel.Vertex(uv_set_max, max_influence)

            vertex_position = vertex_iterator.position(OpenMaya.MSpace.kWorld)
            vertex_normal = OpenMaya.MVector()
            vertex_color = OpenMaya.MColor()
            vertex_iterator.getNormal(vertex_normal)
            vertex_iterator.getColor(vertex_color)

            new_vertex.position = (
                vertex_position.x, vertex_position.y, vertex_position.z)
            new_vertex.normal = (
                vertex_normal.x, vertex_normal.y, vertex_normal.z)
            new_vertex.color = (vertex_color.r, vertex_color.g,
                                vertex_color.b, vertex_color.a)

            # Build uv layers from the set
            for uv_layer, uv_set in enumerate(uv_sets):
                # Fetch the face linked uvs
                uvus = OpenMaya.MFloatArray()
                uvvs = OpenMaya.MFloatArray()
                faceids = OpenMaya.MIntArray()
                vertex_iterator.getUVs(uvus, uvvs, faceids, uv_set)
                uvu = 0
                uvv = 0
                # Vertex uv is average of all face uvs
                count = uvus.length()
                for id in xrange(count):
                    uvu += (uvus[id] / count)
                    uvv += (uvvs[id] / count)
                new_vertex.uvLayers[uv_layer] = (uvu, 1 - uvv)

            # Build the weights if we have any
            if skin_cluster is not None:
                num_weights = OpenMaya.MScriptUtil()
                weight_values = OpenMaya.MDoubleArray()
                skin_cluster.getWeights(path, vertex_iterator.currentItem(
                ), weight_values, num_weights.asUintPtr())

                weight_index = 0

                for vindex in xrange(weight_values.length()):
                    if weight_values[vindex] > 0.000001:
                        new_vertex.weights[weight_index] = (model_joints.index(
                            skin_joints[vindex].partialPathName()), weight_values[vindex])
                        weight_index += 1

            new_mesh.vertices.append(new_vertex)
            vertex_iterator.next()

        # Build the face buffer
        while not face_iterator.isDone():
            indices = OpenMaya.MIntArray()
            face_iterator.getVertices(indices)

            if indices.length() < 3:
                continue

            if indices.length() == 3:
                # Default to tris
                new_face = SEModel.Face((indices[1], indices[0], indices[2]))
                new_mesh.faces.append(new_face)
            else:
                # Convert quat to tris
                new_face = SEModel.Face((indices[1], indices[0], indices[2]))
                new_face2 = SEModel.Face((indices[2], indices[0], indices[3]))
                new_mesh.faces.append(new_face)
                new_mesh.faces.append(new_face2)

            face_iterator.next()

        model.meshes.append(new_mesh)

    # Reconfigure the scene to our liking
    cmds.currentUnit(linear=currentunit_state, angle=currentangle_state)

    # Save as a file
    model.save(file_path)
    __log_info__(
        "SEModel::Export(%s) the model was saved successfully" % os.path.basename(file_path))


def __save_seanim__(file_path, save_positions=True, save_rotations=True, save_scales=True):
    """Saves the scene as a SEAnim file"""
    anim = SEAnim.Anim()
    anim.header.framerate = 30
    anim.header.animType = SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE

    # Calculate start and end frames
    start_frame = cmds.playbackOptions(query=True, ast=True)
    end_frame = cmds.playbackOptions(query=True, aet=True)

    # We need to configure the scene, save current state and change back later
    currentunit_state = cmds.currentUnit(query=True, linear=True)
    currentangle_state = cmds.currentUnit(query=True, angle=True)
    cmds.currentUnit(linear="cm", angle="deg")

    # Resolve a list of bones to export
    bone_list = cmds.ls(selection=True, type="joint")
    if not bone_list:
        bone_list = cmds.ls(type="joint")

    # Resolve a list of notetracks to export
    note_list = None
    if cmds.objExists("SENotes"):
        note_list = __get_notetracks__()

    if not bone_list and not note_list:
        __log_info__(
            "SEAnim::Export(%s) could not find any "
            "valid objects to export" % os.path.basename(file_path))
        return

    # Prepare the main progress bar (Requires mel, talk about pathetic)
    main_progressbar = mel.eval("$tmp = $gMainProgressBar")
    cmds.progressBar(main_progressbar, edit=True,
                     beginProgress=True, isInterruptable=False,
                     status='Exporting SEAnim...', maxValue=max(1, len(bone_list)))

    # Data for the current scene
    frame_range = xrange(int(start_frame), int(end_frame))

    # Loop through and export bone keyframes
    if bone_list:
        for bone in bone_list:
            cmds.progressBar(main_progressbar, edit=True, step=1)

            new_bone = SEAnim.Bone()
            new_bone.name = bone

            # Fetch scene frames from the current range
            for frame in frame_range:
                if save_positions:
                    new_bone.posKeys.append(SEAnim.KeyFrame(
                        frame, cmds.getAttr(bone + ".translate", time=frame)[0]))
                if save_rotations:
                    new_bone.rotKeys.append(SEAnim.KeyFrame(frame,
                                                            __math_matrixtoquat__(
                                                                cmds.getAttr(bone + ".matrix",
                                                                             time=frame))))
                if save_scales:
                    new_bone.scaleKeys.append(SEAnim.KeyFrame(frame,
                                                              cmds.getAttr(bone + ".scale",
                                                                           time=frame)[0]))

            # Add the new bone
            anim.bones.append(new_bone)

    # Close the progress bar
    cmds.progressBar(main_progressbar, edit=True, endProgress=True)

    # Fetch notetracks, if any
    if note_list:
        for note in note_list:
            for frame in note_list[note]:
                # Make and add a new notetrack
                new_note = SEAnim.Note()
                new_note.name = note
                new_note.frame = frame
                anim.notes.append(new_note)

    # Reconfigure the scene to our liking
    cmds.currentUnit(linear=currentunit_state, angle=currentangle_state)

    # Save as a file
    anim.save(file_path)
    __log_info__(
        "SEAnim::Export(%s) the animation was saved successfully" % os.path.basename(file_path))


def __load_semodel__(file_path=""):
    """Imports a SEModel file to the scene"""
    model = SEModel.Model(file_path)

    # We need to configure the scene, save current state and change back later
    autokeyframe_state = cmds.autoKeyframe(query=True)
    currentunit_state = cmds.currentUnit(query=True, linear=True)
    currentangle_state = cmds.currentUnit(query=True, angle=True)
    cmds.autoKeyframe(state=False)
    cmds.currentUnit(linear="cm", angle="deg")

    # Prepare the main progress bar (Requires mel, talk about pathetic)
    main_progressbar = mel.eval("$tmp = $gMainProgressBar")
    cmds.progressBar(main_progressbar, edit=True,
                     beginProgress=True, isInterruptable=False,
                     status='Loading SEModel...', maxValue=max(1,
                                                               model.header.boneCount + model.header.meshCount + model.header.matCount))

    # A list of IKJoint handles
    maya_joint_handles = [None] * model.header.boneCount
    maya_joint_paths = [None] * model.header.boneCount
    maya_joints = OpenMaya.MFnTransform()
    # Create root joints node
    maya_joint_node = maya_joints.create()
    maya_joints.setName("Joints")

    # Iterate over the bones and create those first
    for bone_idx, bone in enumerate(model.bones):
        cmds.progressBar(main_progressbar, edit=True, step=1)

        # Before creating the bone, we need to make the namespace
        __create_nodenamespace__(bone.name)

        # Create a new bone
        new_bone = OpenMayaAnim.MFnIkJoint()
        new_bone.create(maya_joint_node)
        # Set name and add to cache
        new_bone.setName(bone.name)
        maya_joint_handles[bone_idx] = new_bone

    # Iterate over the bones and set parents
    for bone_idx, bone in enumerate(model.bones):
        # Add the joint as a child of the original
        if bone.boneParent > -1:
            cmds.parent(maya_joint_handles[bone_idx].fullPathName(
            ), maya_joint_handles[bone.boneParent].fullPathName())

    # Iterate over the bones and set the actual data
    for bone_idx, bone in enumerate(model.bones):
        # Used for scale utils
        bone_scale = OpenMaya.MScriptUtil()
        new_bone = maya_joint_handles[bone_idx]
        maya_joint_paths[bone_idx] = new_bone.fullPathName()

        # Apply information, note: Check whether or not we have locals/globals
        new_bone.setTranslation(OpenMaya.MVector(
            bone.localPosition[0], bone.localPosition[1], bone.localPosition[2]),
            OpenMaya.MSpace.kTransform)
        new_bone.setOrientation(OpenMaya.MQuaternion(
            bone.localRotation[0], bone.localRotation[1], bone.localRotation[2],
            bone.localRotation[3]))

        # Create and apply scale
        bone_scale.createFromList(
            [bone.scale[0], bone.scale[1], bone.scale[2]], 3)
        new_bone.setScale(bone_scale.asDoublePtr())

    # Iterate over materials and create them next (If they aren't already loaded)
    for mat in model.materials:
        cmds.progressBar(main_progressbar, edit=True, step=1)

        # Only make if it doesn't exist
        if cmds.objExists(mat.name):
            continue

        # Create the material
        material = cmds.shadingNode("lambert", asShader=True, name=mat.name)
        material_group = cmds.sets(
            renderable=True, empty=True, name=("%sSG" % material))
        # Connect diffuse
        cmds.connectAttr(("%s.outColor" % material),
                         ("%s.surfaceShader" % material_group), force=True)
        # Create diffuse texture
        diffuse_image = cmds.shadingNode(
            'file', name=mat.name + "_c", asTexture=True)
        cmds.setAttr(("%s.fileTextureName" % diffuse_image),
                     __build_image_path__(file_path, mat.inputData.diffuseMap), type="string")
        cmds.connectAttr(("%s.outColor" % diffuse_image),
                         ("%s.color" % material))
        # Connect output mapping
        texture_2d = cmds.shadingNode("place2dTexture", name=(
            "place2dTexture_%s" % (mat.name + "_c")), asUtility=True)
        cmds.connectAttr(("%s.outUV" % texture_2d),
                         ("%s.uvCoord" % diffuse_image))

    # Create the root mesh node
    maya_meshs = OpenMaya.MFnTransform()
    maya_mesh_node = maya_meshs.create()
    maya_meshs.setName(os.path.splitext(os.path.basename(file_path))[0])

    # Iterate over the meshes and create them
    for mesh in model.meshes:
        cmds.progressBar(main_progressbar, edit=True, step=1)
        # Create root transform
        new_mesh_root = OpenMaya.MFnTransform()
        new_mesh_node = new_mesh_root.create(maya_mesh_node)
        new_mesh_root.setName("SEModelMesh")

        # Perform face validation, maya doesn't like faces with the same verts
        purge_map = []
        for face_idx in xrange(mesh.faceCount):
            face = mesh.faces[face_idx]
            # Compare indicies
            if face.indices[0] == face.indices[1]:
                purge_map.append(face_idx)
            elif face.indices[0] == face.indices[2]:
                purge_map.append(face_idx)
            elif face.indices[1] == face.indices[2]:
                purge_map.append(face_idx)

        # Remove all invalid faces, reverse order to prevent reordering
        for face_idx in reversed(purge_map):
            del mesh.faces[face_idx]
        mesh.faceCount = mesh.faceCount - len(purge_map)

        # Create mesh
        new_mesh = OpenMaya.MFnMesh()
        mesh_vertex_buffer = OpenMaya.MFloatPointArray(mesh.vertexCount)
        mesh_normal_buffer = OpenMaya.MVectorArray(mesh.vertexCount)
        mesh_color_buffer = OpenMaya.MColorArray(
            mesh.vertexCount, OpenMaya.MColor(1, 1, 1, 1))
        mesh_vertex_index = OpenMaya.MIntArray(mesh.vertexCount, 0)
        mesh_face_buffer = OpenMaya.MIntArray(mesh.faceCount * 3)
        mesh_face_counts = OpenMaya.MIntArray(mesh.faceCount, 3)
        mesh_weight_data = [None] * mesh.vertexCount
        mesh_weight_bones = set()

        # Support all possible UV layers
        mesh_uvid_layers = OpenMaya.MIntArray(mesh.faceCount * 3)
        mesh_uvu_layers = []
        mesh_uvv_layers = []

        # We must generate them this way to python doesn't clone an object
        for uv_layer in xrange(mesh.matReferenceCount):
            mesh_uvu_layers.append(OpenMaya.MFloatArray(mesh.faceCount * 3))
            mesh_uvv_layers.append(OpenMaya.MFloatArray(mesh.faceCount * 3))

        # Build buffers
        for vert_idx, vert in enumerate(mesh.vertices):
            mesh_vertex_buffer.set(vert_idx,
                                   vert.position[0], vert.position[1], vert.position[2])
            mesh_normal_buffer.set(OpenMaya.MVector(
                vert.normal[0], vert.normal[1], vert.normal[2]), vert_idx)
            mesh_color_buffer.set(vert_idx,
                                  vert.color[0], vert.color[1], vert.color[2], vert.color[3])
            mesh_vertex_index.set(vert_idx, vert_idx)

            # Build a payload set for this vertex
            vertex_weights = []
            # Iterate and create the weights
            for weight in vert.weights:
                # Weights are valid when value is > 0.0
                if weight[1] > 0.0:
                    mesh_weight_bones.add(maya_joint_paths[weight[0]])
                    vertex_weights.append(
                        (maya_joint_paths[weight[0]], weight[1]))

            # Add the weight set
            mesh_weight_data[vert_idx] = (vert_idx, vertex_weights)

        # Face buffer for maya is inverted 1->0->2
        for face_idx, face in enumerate(mesh.faces):
            mesh_face_buffer.set(face.indices[1], (face_idx * 3))
            mesh_face_buffer.set(face.indices[0], (face_idx * 3) + 1)
            mesh_face_buffer.set(face.indices[2], (face_idx * 3) + 2)

            mesh_uvid_layers.set((face_idx * 3), (face_idx * 3))
            mesh_uvid_layers.set((face_idx * 3) + 1, (face_idx * 3) + 1)
            mesh_uvid_layers.set((face_idx * 3) + 2, (face_idx * 3) + 2)

            # Do this per layer
            for uv_layer in xrange(mesh.matReferenceCount):
                mesh_uvu_layers[uv_layer].set(
                    mesh.vertices[face.indices[1]].uvLayers[uv_layer][0], (face_idx * 3))
                mesh_uvu_layers[uv_layer].set(
                    mesh.vertices[face.indices[0]].uvLayers[uv_layer][0], (face_idx * 3) + 1)
                mesh_uvu_layers[uv_layer].set(
                    mesh.vertices[face.indices[2]].uvLayers[uv_layer][0], (face_idx * 3) + 2)
                mesh_uvv_layers[uv_layer].set(
                    1 - mesh.vertices[face.indices[1]].uvLayers[uv_layer][1], (face_idx * 3))
                mesh_uvv_layers[uv_layer].set(
                    1 - mesh.vertices[face.indices[0]].uvLayers[uv_layer][1], (face_idx * 3) + 1)
                mesh_uvv_layers[uv_layer].set(
                    1 - mesh.vertices[face.indices[2]].uvLayers[uv_layer][1], (face_idx * 3) + 2)

        # Create
        new_mesh.create(mesh.vertexCount, mesh.faceCount, mesh_vertex_buffer, OpenMaya.MIntArray(
            mesh.faceCount, 3), mesh_face_buffer, new_mesh_node)
        # Set normals + colors
        new_mesh.setVertexNormals(mesh_normal_buffer, mesh_vertex_index)
        new_mesh.setVertexColors(mesh_color_buffer, mesh_vertex_index)

        # Apply UVLayers
        for uv_layer in xrange(mesh.matReferenceCount):
            # Use default layer, or, make a new one if need be, following maya names
            if uv_layer > 0:
                new_uv = new_mesh.createUVSetWithName(
                    ("map%d" % (uv_layer + 1)))
            else:
                new_uv = new_mesh.currentUVSetName()

            # Set uvs
            new_mesh.setCurrentUVSetName(new_uv)
            new_mesh.setUVs(
                mesh_uvu_layers[uv_layer], mesh_uvv_layers[uv_layer], new_uv)
            new_mesh.assignUVs(
                mesh_face_counts, mesh_uvid_layers, new_uv)

            # Set material, default to shader if not defined
            material_index = mesh.materialReferences[uv_layer]
            try:
                if material_index < 0:
                    cmds.sets(new_mesh.fullPathName(),
                              forceElement="initialShadingGroup")
                else:
                    cmds.sets(new_mesh.fullPathName(), forceElement=(
                        "%sSG" % model.materials[material_index].name))
            except RuntimeError:
                # Occurs when a material was already assigned to the mesh...
                pass

        # Prepare skin weights
        mesh_skin = __scene_newskin__(new_mesh.fullPathName(), [
            x for x in mesh_weight_bones], mesh.maxSkinInfluence)
        if mesh_skin is not None:
            __scene_bindmesh__(mesh_skin, mesh_weight_data)

    # Close the progress bar
    cmds.progressBar(main_progressbar, edit=True, endProgress=True)

    # Reconfigure the scene to our liking
    cmds.autoKeyframe(state=autokeyframe_state)
    cmds.currentUnit(linear=currentunit_state, angle=currentangle_state)

    # Finished model import
    __log_info__("SEModel::Import(%s) has been imported successfully"
                 % os.path.basename(file_path))


def __load_seanim__(file_path="", scene_time=False, blend_anim=False):
    """Imports a SEAnim file to the scene"""
    anim = SEAnim.Anim(file_path)

    # Calculate start and end frames, count-1 due to array syntax
    start_frame = 0
    if scene_time:
        start_frame = cmds.currentTime(query=True)
    end_frame = max(1, anim.header.frameCount - 1)
    end_frame = end_frame + start_frame

    cmds.playbackOptions(ast=0, minTime=0)
    cmds.playbackOptions(maxTime=end_frame, aet=end_frame)

    # We need to configure the scene, save current state and change back later
    autokeyframe_state = cmds.autoKeyframe(query=True)
    currentunit_state = cmds.currentUnit(query=True, linear=True)
    currentangle_state = cmds.currentUnit(query=True, angle=True)
    cmds.autoKeyframe(state=False)
    cmds.currentUnit(linear="cm", angle="deg", time="film")

    # Prepare the main progress bar (Requires mel, talk about pathetic)
    main_progressbar = mel.eval("$tmp = $gMainProgressBar")
    cmds.progressBar(main_progressbar, edit=True,
                     beginProgress=True, isInterruptable=False,
                     status='Loading SEAnim...', maxValue=max(1, len(anim.bones)))

    # If we aren't blending, we reset first
    if not blend_anim:
        __scene_resetanim__()

    # Iterate over bones in the animation, and attempt to animate them
    for bone in anim.bones:
        cmds.progressBar(main_progressbar, edit=True, step=1)

        # Resolve joint name, skip joints not found
        joint_name = __scene_getjoint__(bone.name)
        if not joint_name:
            continue

        # Attempt to resolve a parent override
        bone_anim_type = __scene_resolve_animoverride__(
            joint_name, anim.boneAnimModifiers)
        if bone_anim_type is None:
            bone_anim_type = anim.header.animType

        # Attempt to obtain the joint in the scene
        try:
            (joint_path, joint_object, rest_translation,
             _rest_scale, rest_rotation) = __scene_obtainjoint__(
                 joint_name, not blend_anim)
        except RuntimeError:
            __log_info__("SEAnim::ObtainJoint(%s) failed to obtain joint skipping..." %
                         joint_name)
            continue

        if bone.posKeys:
            curve_pos_x = __scene_getcurve__(joint_path.transform(
            ), "translateX", OpenMayaAnim.MFnAnimCurve.kAnimCurveTL)
            curve_pos_y = __scene_getcurve__(joint_path.transform(
            ), "translateY", OpenMayaAnim.MFnAnimCurve.kAnimCurveTL)
            curve_pos_z = __scene_getcurve__(joint_path.transform(
            ), "translateZ", OpenMayaAnim.MFnAnimCurve.kAnimCurveTL)

            # Resolve the relative transform
            if bone_anim_type == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE:
                rel_transform = (0, 0, 0)
            else:
                rel_transform = rest_translation

            # If we are animating the first frame, or static position,
            # explicitly set first transform
            if start_frame == 0:
                joint_object.setTranslation(OpenMaya.MVector(
                    bone.posKeys[0].data[0] + rel_transform[0],
                    bone.posKeys[0].data[1] + rel_transform[1],
                    bone.posKeys[0].data[2] + rel_transform[2]), OpenMaya.MSpace.kTransform)

            # Loop through and add keyframes
            for key in bone.posKeys:
                key_time = OpenMaya.MTime(start_frame + key.frame)
                if curve_pos_x:
                    curve_pos_x.addKeyframe(
                        key_time, key.data[0] + rel_transform[0],
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)
                if curve_pos_y:
                    curve_pos_y.addKeyframe(
                        key_time, key.data[1] + rel_transform[1],
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)
                if curve_pos_z:
                    curve_pos_z.addKeyframe(
                        key_time, key.data[2] + rel_transform[2],
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)

        if bone.scaleKeys:
            curve_scale_x = __scene_getcurve__(joint_path.transform(
            ), "scaleX", OpenMayaAnim.MFnAnimCurve.kAnimCurveTL)
            curve_scale_y = __scene_getcurve__(joint_path.transform(
            ), "scaleY", OpenMayaAnim.MFnAnimCurve.kAnimCurveTL)
            curve_scale_z = __scene_getcurve__(joint_path.transform(
            ), "scaleZ", OpenMayaAnim.MFnAnimCurve.kAnimCurveTL)

            # If we are animating the first frame, or static scale,
            # explicitly set first transform
            if start_frame == 0:
                cmds.setAttr(joint_name + ".scale", bone.scaleKeys[0].data[0],
                             bone.scaleKeys[0].data[1], bone.scaleKeys[0].data[2])

            # Loop through and add keyframes
            for key in bone.scaleKeys:
                key_time = OpenMaya.MTime(start_frame + key.frame)
                if curve_scale_x:
                    curve_scale_x.addKeyframe(
                        key_time, key.data[0],
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)
                if curve_scale_y:
                    curve_scale_y.addKeyframe(
                        key_time, key.data[1],
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)
                if curve_scale_z:
                    curve_scale_z.addKeyframe(
                        key_time, key.data[2],
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)

        if bone.rotKeys:
            curve_rot_x = __scene_getcurve__(joint_path.transform(
            ), "rotateX", OpenMayaAnim.MFnAnimCurve.kAnimCurveTA)
            curve_rot_y = __scene_getcurve__(joint_path.transform(
            ), "rotateY", OpenMayaAnim.MFnAnimCurve.kAnimCurveTA)
            curve_rot_z = __scene_getcurve__(joint_path.transform(
            ), "rotateZ", OpenMayaAnim.MFnAnimCurve.kAnimCurveTA)

            # Ensure joint orientation is 0
            joint_object.setOrientation(OpenMaya.MQuaternion(0, 0, 0, 1))

            # Resolve relative transform
            if bone_anim_type == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ADDITIVE:
                rel_transform = OpenMaya.MEulerRotation(
                    math.radians(rest_rotation[0]), math.radians(
                        rest_rotation[1]),
                    math.radians(rest_rotation[2])).asQuaternion()
            else:
                rel_transform = OpenMaya.MQuaternion(0, 0, 0, 1)

            # If we are animating the first frame, or static rotation,
            # explicitly set first transform
            if start_frame == 0:
                euler_frame = (OpenMaya.MQuaternion(
                    bone.rotKeys[0].data[0], bone.rotKeys[0].data[1],
                    bone.rotKeys[0].data[2],
                    bone.rotKeys[0].data[3]) * rel_transform).asEulerRotation()
                cmds.setAttr(joint_name + ".r", math.degrees(euler_frame.x),
                             math.degrees(euler_frame.y), math.degrees(euler_frame.z))

            # Loop through and add keyframes
            for key in bone.rotKeys:
                key_time = OpenMaya.MTime(start_frame + key.frame)
                euler_frame = (OpenMaya.MQuaternion(
                    key.data[0], key.data[1],
                    key.data[2], key.data[3]) * rel_transform).asEulerRotation()
                if curve_rot_x:
                    curve_rot_x.addKeyframe(
                        key_time, euler_frame.x,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)
                if curve_rot_y:
                    curve_rot_y.addKeyframe(
                        key_time, euler_frame.y,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)
                if curve_rot_z:
                    curve_rot_z.addKeyframe(
                        key_time, euler_frame.z,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear,
                        OpenMayaAnim.MFnAnimCurve.kTangentLinear)

            # Explicitly set the interpolation method, since we are converting from quats,
            # Note: Only one component needs to set it, they all apply
            __scene_setinterpolation__(joint_name + ".rotateX", "quaternion")

    # Close the progress bar
    cmds.progressBar(main_progressbar, edit=True, endProgress=True)

    # Import notetracks
    for note in anim.notes:
        __add_notetrack__(note.name, note.frame)

    # Reconfigure the scene to our liking
    cmds.autoKeyframe(state=autokeyframe_state)
    cmds.currentUnit(linear=currentunit_state, angle=currentangle_state)
    cmds.currentTime(start_frame)

    # Finished animation import
    __log_info__("SEAnim::Import(%s) has been imported successfully"
                 % os.path.basename(file_path))


class SEAnimFileManager(OpenMayaMPx.MPxFileTranslator):
    """Handles Maya Import / Export of SEAnim files"""

    def __init__(self):
        OpenMayaMPx.MPxFileTranslator.__init__(self)

    def haveWriteMethod(self):
        return True

    def haveReadMethod(self):
        return True

    def identifyFile(self, fileObject, buf, size):
        if os.path.splitext(fileObject.fullName())[1].lower() == ".seanim":
            return OpenMayaMPx.MPxFileTranslator.kIsMyFileType
        return OpenMayaMPx.MPxFileTranslator.kNotMyFileType

    def filter(self):
        return "*.seanim"

    def defaultExtension(self):
        return "seanim"

    def writer(self, fileObject, optionString, accessMode):
        __save_seanim__(fileObject.fullName())

    def reader(self, fileObject, optionString, accessMode):
        __load_seanim__(fileObject.fullName())


class SEModelFileManager(OpenMayaMPx.MPxFileTranslator):
    """Handles Maya Import / Export of SEModel files"""

    def __init__(self):
        OpenMayaMPx.MPxFileTranslator.__init__(self)

    def haveWriteMethod(self):
        return True

    def haveReadMethod(self):
        return True

    def identifyFile(self, fileObject, buf, size):
        if os.path.splitext(fileObject.fullName())[1].lower() == ".semodel":
            return OpenMayaMPx.MPxFileTranslator.kIsMyFileType
        return OpenMayaMPx.MPxFileTranslator.kNotMyFileType

    def filter(self):
        return "*.semodel"

    def defaultExtension(self):
        return "semodel"

    def writer(self, fileObject, optionString, accessMode):
        __save_semodel__(fileObject.fullName())

    def reader(self, fileObject, optionString, accessMode):
        __load_semodel__(fileObject.fullName())


def __seanim_manager__():
    """Create a new manager object"""
    return OpenMayaMPx.asMPxPtr(SEAnimFileManager())


def __semodel_manager__():
    """Create a new manager object"""
    return OpenMayaMPx.asMPxPtr(SEModelFileManager())


def initializePlugin(m_object):
    """Register the plugin"""
    m_plugin = OpenMayaMPx.MFnPlugin(m_object, "DTZxPorter", "3.0", "Any")
    try:
        m_plugin.registerFileTranslator(
            "SEAnim Animations", None, __seanim_manager__)
        m_plugin.registerFileTranslator(
            "SEModel Models", None, __semodel_manager__)
    except RuntimeError:
        __log_info__(
            "SETools::InitializePlugin() failed to register translators!")
    __create_menu__()


def uninitializePlugin(m_object):
    """Unregister the plugin"""
    m_plugin = OpenMayaMPx.MFnPlugin(m_object)
    try:
        m_plugin.deregisterFileTranslator("SEAnim Animations")
        m_plugin.deregisterFileTranslator("SEModel Models")
    except RuntimeError:
        __log_info__(
            "SETools::UninitializePlugin() failed to remove translators!")
    __remove_menu__()
