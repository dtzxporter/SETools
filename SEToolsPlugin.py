# SE formats import / export plugin for Maya
# Developed by DTZxPorter

import os
import os.path
import maya.cmds as cmds
import maya.mel as mel
import math
import maya.OpenMaya as OpenMaya
import maya.OpenMayaAnim as OpenMayaAnim
import maya.OpenMayaMPx as OpenMayaMPx
import struct
import seanim as SEAnim
import re

MENU_DATA = {'menu' : ["SEAToolsPluginMenu", "SE Tools", None, None, None]}

INVALID_CHARS = r"[\W]"

GUN_BASE_TAGS = ["j_gun", "j_gun1", "tag_weapon", "tag_weapon1"]
VIEW_HAND_TAGS = ["tag_weapon", "tag_weapon1", "tag_weapon_right", "tag_weapon_left"]

# Fuck Maya 2012 (Max frame length is 999999)
MAX_FRAMELEN = 999999

# About info
def AboutWindow():
	result = cmds.confirmDialog(message="---  SE Tools plugin (v2.2.6)  ---\n\nDeveloped by DTZxPorter", button=['OK'], defaultButton='OK', title="About SE Tools")

# A list (in order of priority) of bone names to automatically search for when determining which bone to use as the root for delta anims
DeltaRootBones = ["tag_origin"]

# Compare two iterable objects
def first(a, b):
	for elem in a:
		if elem in b:
			return a
	return None

# Import file dialog, for importing .SE formats
def ImportFileSelectDialog():
	importFrom = None
	if cmds.about(version=True)[:4] == "2012": # Support for newer versions
		importFrom = cmds.fileDialog2(fileMode=1, fileFilter="SEAnim Files (*.seanim)", caption="Import SEAnim")
	else:
		importFrom = cmds.fileDialog2(fileMode=1, dialogStyle=2, fileFilter="SEAnim Files (*.seanim)", caption="Import SEAnim")

	if importFrom == None or len(importFrom) == 0 or importFrom[0].strip() == "":
		return None
	path = importFrom[0].strip()

	pathSplit = os.path.splitext(path) # Fix bug with Maya 2013
	if pathSplit[1] == ".*":
		path = pathSplit

	return path

# Attempt to resolve the animType for a bone based on a given list of modifier bones, returns None if no override is needed
def ResolvePotentialAnimTypeOverride(tagname, boneAnimModifiers):
	# Grab the parent tree
	try:
		parents = cmds.ls(tagname, long = True)[0].split('|')[1:-1]
		# Check if we even had parents
		if len(parents) == 0 or len(boneAnimModifiers) == 0:
			return None

		# Loop through parents
		for parent in parents:
			# Check parent name
			partag = parent
			# Check
			if partag.find(":") > -1:
				# Set it up
				partag = partag[partag.find(":") + 1:]
				# Continue
			for modBone in boneAnimModifiers:
				# Compare the parent
				if partag == modBone.name:
					# We are being overridden!
					return modBone.modifier
		return None
	except:
		return None

# Importer
def ImportSEAnim():
	# Get a file to import
	file_import = ImportFileSelectDialog()
	# Check
	if file_import == None:
		# No file selected
		pass
	else:
		# Ship file off
		LoadSEAnimBuildCurve(file_import)

# Merge Importer
def ImportMergeSEAnim():
	# Get a file to import
	file_import = ImportFileSelectDialog()
	# Check
	if file_import == None:
		# No file selected
		pass
	else:
		# Ship file off, allow merging of this anim with a current scene one
		LoadSEAnimBuildCurve(file_import, True)

# Clears the menu
def DeleteMenu():
	# Check for existing control, remove it if we can
	if cmds.control(MENU_DATA['menu'][0], exists=True):
		# Found it, delete it
		cmds.deleteUI(MENU_DATA['menu'][0], menu=True)

# Create the menu
def CreateMenu():
	# Set the diplay's parent
	cmds.setParent(mel.eval("$temp1=$gMainWindow"))
	
	# Purge old one
	DeleteMenu()

	# Make new menu
	menu = cmds.menu(MENU_DATA['menu'][0], label=MENU_DATA["menu"][1], tearOff=True)	# Recreate the base
	# Add children
	cmds.menuItem(label="Import <- SEAnim", command=lambda x:ImportSEAnim(), annotation="Imports a SEAnim, resetting the scene first")
	cmds.menuItem(label="Import and Blend <- SEAnim", command=lambda x:ImportMergeSEAnim(), annotation="Imports a SEAnim without resetting the scene (Blending the animations together)")
	cmds.menuItem(divider=True)
	cmds.menuItem(label="Export -> SEAnim", command=lambda x:ExportEntireSceneAnim(), annotation="Exports all joints, or all selected joints to a SEAnim file")
	cmds.menuItem(divider=True)
	cmds.menuItem(label="Clean Namespaces", command=lambda x:NamespaceClean(), annotation="Removes all namespaces from the scene")
	cmds.menuItem(label="Place Notetrack", command=lambda x:PlaceNote(), annotation="Places a notetrack at the current scene time")
	cmds.menuItem(label="Select All Joints", command=lambda x:SelectAllJoints(), annotation="Selects all joints")
	cmds.menuItem(label="Select Keyed Joints", command=lambda x:SelectKeyframes(), annotation="Selects keyed joints, this feature does not work with conversion rigs")
	cmds.menuItem(divider=True)
	cmds.menuItem(label="Reset Scene", command=lambda x:ResetSceneAnim(), annotation="Manually reset the scene to bind position")
	cmds.menuItem(divider=True)
	game_menu = cmds.menuItem(label="Game Specific Tools", subMenu=True)	# Make game specific submenu
	cmds.menuItem(label="Call of Duty", subMenu=True)
	cmds.menuItem(label="Attach Weapon to Rig", command=lambda x:WeaponBinder(), annotation="Attatches the weapon to the viewhands, does not work properly with conversion rigs")
	cmds.setParent(game_menu, menu=True) 	# Close out menu (Call of Duty)
	cmds.setParent(menu, menu=True) 		# Close out menu (Game tools)
	cmds.menuItem(divider=True)
	cmds.menuItem(label="Reload Plugin", command=lambda x:ReloadMayaPlugin(), annotation="Attempts to reload the plugin")
	cmds.menuItem(label="About", command=lambda x:AboutWindow())

# Reloads a maya plugin
def ReloadMayaPlugin():
	# Reload us as a plugin, be careful to unregister first!
	cmds.unloadPlugin('SEToolsPlugin.py')
	cmds.loadPlugin('SEToolsPlugin.py')

# Bind the weapon to hands
def WeaponBinder():
	# Call of Duty specific
	for x in xrange(0, len(GUN_BASE_TAGS)):
		try:
			# Select both tags and parent them
			cmds.select(GUN_BASE_TAGS[x], replace = True)
			cmds.select(VIEW_HAND_TAGS[x], toggle = True)
			# Connect
			cmds.connectJoint(connectMode = True)
			# Parent
			mel.eval("parent " + GUN_BASE_TAGS[x] + " " + VIEW_HAND_TAGS[x])
			# Reset the positions of both bones
			cmds.setAttr(GUN_BASE_TAGS[x] + ".t", 0, 0, 0)
			cmds.setAttr(GUN_BASE_TAGS[x] + ".jo", 0, 0, 0)
			cmds.setAttr(GUN_BASE_TAGS[x] + ".rotate", 0, 0, 0)
			# Reset the rotation of the parent tag
			cmds.setAttr(VIEW_HAND_TAGS[x] + ".jo", 0, 0, 0)
			cmds.setAttr(VIEW_HAND_TAGS[x] + ".rotate", 0, 0, 0)
			# Remove
			cmds.select(clear = True)
		except:
			pass


# Place a notetrack
def PlaceNote():
	# Notetrack number
	note_tracks = 0
	# We need to ask for a name
	if not (cmds.objExists("SENotes")):
		# We need to make the SENotes parent first
		base_track = cmds.spaceLocator()
		# Rename
		cmds.rename(base_track, "SENotes")
	# Notetrack name
	noteName = "new_notetrack" + str(note_tracks)
	# Now we can make the child (if you have > 50000 notetracks, we got a problem...)
	for npos in xrange(note_tracks, 50000):
		# Setup
		noteName = "new_notetrack" + str(npos)
		# Check
		if not (cmds.objExists(noteName)):
			# Exit
			break
	# Now make it and parent it
	notetrack = cmds.spaceLocator()
	# Rename
	cmds.rename(notetrack, noteName)
	# Parent it
	mel.eval("parent " + noteName + " SENotes")
	# Get current time
	currentFrame = cmds.currentTime(query = True)
	# Key it
	cmds.setKeyframe(noteName, time = currentFrame)
	# Log it
	print("A new notetrack was created")

# Selects all bones
def SelectAllJoints():
	# Clear current selection
	cmds.select(clear=True)
	# Get a list of bones
	boneList = cmds.ls(type = 'joint')
	# Iterate and select ones with frames on loc/rot/scale
	for bone in boneList:
		# Select it
		cmds.select(bone, add=True)

# Selects bones with keyframes
def SelectKeyframes():
	# Clear current selection
	cmds.select(clear=True)
	# Get a list of bones
	boneList = cmds.ls(type = 'joint')
	# Iterate and select ones with frames on loc/rot/scale
	for bone in boneList:
		# Check for loc
		keysTranslate = cmds.keyframe(bone + ".translate", query=True, timeChange=True)
		keysRotate = cmds.keyframe(bone + ".rotate", query=True, timeChange=True)
		keysScale = cmds.keyframe(bone + ".scale", query=True, timeChange=True)
		# Check for frames
		if keysTranslate is not None:
			if len(keysTranslate) >= 1:
				cmds.select(bone, add=True)
		if keysRotate is not None:
			if len(keysRotate) >= 1:
				cmds.select(bone, add=True)
		if keysScale is not None:
			if len(keysScale) >= 1:
				cmds.select(bone, add=True)

# Cleans namespaces
def NamespaceClean():
	# Get a list of bones
	boneList = cmds.ls(type = 'joint')
	# Loop
	for bone in boneList:
		# Check if it has a namespace
		if bone.find(":") > -1:
			# We got one, prepare to clean
			resultSplit = bone.split(":")
			# Get the last one
			newName = resultSplit[len(resultSplit)-1]
			# Rename it
			try:
				# Do it
				cmds.rename(bone, newName)
			except:
				# Continue
				pass

def CleanNote(note):
	# Clean the note string
	RemovedLiterals = re.sub(INVALID_CHARS, "_", note)
	# Check for Maya reserved keywords, if matches, append _ beforehand
	if (RemovedLiterals == "switch" or RemovedLiterals == "for" or RemovedLiterals == "while"):
		# Found bad keyword
		RemovedLiterals = "_" + RemovedLiterals
	# Return it
	return RemovedLiterals

def MayaMatrixToQuat(mmat):
	# Converts a maya matrix (a retarded 4x4 array) to a quaternion (way faster than using maya objects)
	qx = 0.0
	qy = 0.0
	qz = 0.0
	qw = 1.0
	# Prepare to convert
	tr = mmat[0] + mmat[5] + mmat[10]
	# Check for divide by 0
	if tr > 0:
		# We're safe here
		divisor = math.sqrt(tr + 1.0) * 2.0
		# Calculate values
		qw = 0.25 * divisor
		qx = (mmat[6] - mmat[9]) / divisor
		qy = (mmat[8] - mmat[2]) / divisor
		qz = (mmat[1] - mmat[4]) / divisor
	elif (mmat[0] > mmat[5]) and (mmat[0] > mmat[10]):
		# Take from quat x
		divisor = math.sqrt(1.0 + mmat[0] - mmat[5] - mmat[10]) * 2.0
		# Calculate values
		qw = (mmat[6] - mmat[9]) / divisor
		qx = 0.25 * divisor
		qy = (mmat[4] + mmat[1]) / divisor
		qz = (mmat[8] + mmat[2]) / divisor
	elif (mmat[5] > mmat[10]):
		# Take from quat y 
		divisor = math.sqrt(1.0 + mmat[5] - mmat[0] - mmat[10]) * 2.0
		# Calculate values
		qw = (mmat[8] - mmat[2]) / divisor
		qx = (mmat[4] + mmat[1]) / divisor
		qy = 0.25 * divisor
		qz = (mmat[9] + mmat[6]) / divisor
	else:
		# Take from quat z 
		divisor = math.sqrt(1.0 + mmat[10] - mmat[0] - mmat[5]) * 2.0
		# Calculate values
		qw = (mmat[1] - mmat[4]) / divisor
		qx = (mmat[8] + mmat[2]) / divisor
		qy = (mmat[9] + mmat[6]) / divisor
		qz = 0.25 * divisor

	# Return the value
	return (qx, qy, qz, qw)

def ExportEntireSceneAnim():
	# Export everything that's selected, if none, export all
	exportTo = cmds.fileDialog2(fileMode = 0, fileFilter = "SEAnim Files (*.seanim)", caption = "Export SEAnim")
	# Check
	if exportTo == None or len(exportTo) == 0 or exportTo[0].strip() == "":
		# Was blank
		return None
	# Log
	print("Exporting SEAnim...")
	# Setup path
	exportPath = exportTo[0].strip()
	# An anim
	resultAnim = SEAnim.Anim()
	# Set default framerate
	resultAnim.header.framerate = 30
	# Used because we made this anim after the fact
	resultAnim.header.animType = SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE
	# Fetch the end frame count
	endSceneFrame = cmds.playbackOptions(query = True, aet = True)
	# Whether or not to save scale data (Found a scale that was not 1.0)
	saveScales = False
	# Setup progress
	gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')
	# Get bones
	allBones = cmds.ls(selection = True, type = 'joint')
	# If none, get all joints in scene
	if len(allBones) == 0:
		# Grab all
		allBones = cmds.ls(type = 'joint')
	# Get max length
	maxCount = len(allBones)
	# Show progress
	cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=False, status='Exporting SEAnim...', maxValue=maxCount)
	# Loop
	for bone in allBones:
		# Progress 
		cmds.progressBar(gMainProgressBar, edit=True, step=1)
		# Our bone
		boneUse = SEAnim.Bone()
		# Set name
		boneUse.name = bone
		# Loop from 0 to endSceneFrame and grab each translation and rotation we can find
		for frame in xrange(0, int(endSceneFrame)):
			# Grab translate, rotate, and scale keys from this frame
			transKey = cmds.getAttr(bone + ".translate", time = frame)[0]
			# Make and add key
			boneUse.posKeys.append(SEAnim.KeyFrame(frame, transKey))
			# Transformation matrix (4x4)
			rotMat = cmds.getAttr(bone + ".matrix", time = frame)
			# Convert to key
			rotKey = MayaMatrixToQuat(rotMat)
			# Make and add key
			boneUse.rotKeys.append(SEAnim.KeyFrame(frame, rotKey))
			# Grab scale (don't forget to check for != 1.0)
			scaleKey = cmds.getAttr(bone + ".scale", time = frame)[0]
			# Check, if all scales are default, don't bother saving the data (Only worth it for scales, since rotation and translation is common)
			if (scaleKey[0] != 1.0) or (scaleKey[1] != 1.0) or (scaleKey[2] != 1.0):
				# We need scales
				saveScales = True
			# Make and add key
			boneUse.scaleKeys.append(SEAnim.KeyFrame(frame, scaleKey))
			# Increase
			boneUse.locKeyCount = (boneUse.locKeyCount + 1)
			boneUse.rotKeyCount = (boneUse.rotKeyCount + 1)
			boneUse.scaleKeyCount = (boneUse.scaleKeyCount + 1)
		# Add the bone to the anim
		resultAnim.bones.append(boneUse)
	# Check whether or not to remove scale data
	if saveScales == False:
		# Loop and clear
		for boneUse in resultAnim.bones:
			# Clear the data
			boneUse.scaleKeys = []
			boneUse.scaleKeyCount = 0
	# End progress
	cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
	# Check for SENotes
	if (cmds.objExists("SENotes")):
		# Get children and loop
		noteTrackList = cmds.listRelatives("SENotes", type = "transform")
		# Loop
		if noteTrackList is not None:
			# Loop it
			for note in noteTrackList:
				# Get key'd values
				noteKeys = cmds.keyframe(note + ".translateX", query = True, timeChange = True)
				# Loop and add
				if noteKeys is not None:
					# Loop
					for keyNote in noteKeys:
						# Make and add
						seaNote = SEAnim.Note()
						# Set name
						seaNote.name = note
						# Set frame
						seaNote.frame = keyNote
						# Add
						resultAnim.notes.append(seaNote)
	# Save as file
	resultAnim.save(exportPath)
	# Done
	print("The SEAnim was exported")

# Loop through and reset scene bones
def ResetSceneAnim():
	# Loop through them all
	SceneJoints = cmds.ls(type="joint")
	# Loop
	for name in SceneJoints:
		# Purge keys
		cmds.cutKey(name, time=(0, MAX_FRAMELEN), option="keys")
		# Check for undo
		if (cmds.objExists(name + ".seanimUndoT")):
			# Reset to it
			ResetTranslation = cmds.getAttr(name + ".seanimUndoT")[0]
			ResetScale = cmds.getAttr(name + ".seanimUndoS")[0]
			ResetRotation = cmds.getAttr(name + ".seanimUndoR")[0]
			# Apply
			cmds.setAttr(name + ".t", ResetTranslation[0], ResetTranslation[1], ResetTranslation[2])
			cmds.setAttr(name + ".scale", ResetScale[0], ResetScale[1], ResetScale[2])
			cmds.setAttr(name + ".r", 0, 0, 0)
			cmds.setAttr(name + ".jo", ResetRotation[0], ResetRotation[1], ResetRotation[2])
	# Remove notetracks
	if cmds.objExists("SENotes"):
		# Delete
		cmds.delete("SENotes")

# Processes a joint, creating it's rest position, and returning a dag path
def DagPathFromJoint(name, needsRest=True):
	# Check for it
	if not cmds.objExists(name):
		# Not found in scene
		return False
	# Check to add
	if needsRest:
		# Check for the attr (to set rest pos)
		if not cmds.objExists(name + ".seanimUndoT"):
			# We need to setup the undo data
			ResetTranslation = cmds.getAttr(name + ".t")[0]
			ResetScale = cmds.getAttr(name + ".scale")[0]
			ResetRotation = cmds.getAttr(name + ".jo")[0]
			# Make the attributes
			cmds.addAttr(name, longName="seanimUndoT", dataType="double3", storable=True)
			cmds.addAttr(name, longName="seanimUndoS", dataType="double3", storable=True)
			cmds.addAttr(name, longName="seanimUndoR", dataType="double3", storable=True)
			# Set them
			cmds.setAttr(name + ".seanimUndoT", ResetTranslation[0], ResetTranslation[1], ResetTranslation[2], type="double3")
			cmds.setAttr(name + ".seanimUndoS", ResetScale[0], ResetScale[1], ResetScale[2], type="double3")
			cmds.setAttr(name + ".seanimUndoR", ResetRotation[0], ResetRotation[1], ResetRotation[2], type="double3")
	# Make selector
	sList = OpenMaya.MSelectionList()
	# Add it
	sList.add(name)
	# New Path
	dResult = OpenMaya.MDagPath()
	# Set it
	sList.getDagPath(0, dResult)
	# Return
	return dResult

# Sets an anim curve to a bone, returns resulting curve
def GetAnimCurve(joint, attr, curveType):
	# Get the plug
	attrPlug = OpenMaya.MFnDependencyNode(joint).findPlug(attr, False)
	# Make it keyable
	attrPlug.setKeyable(True)
	# Make it unlocked
	attrPlug.setLocked(False)
	# Check if we must detatch or remove an existing one
	if attrPlug.isConnected():
		# Attach to it (TODO reset this eventually, disconnect other shiz)
		return OpenMayaAnim.MFnAnimCurve(attrPlug)
	# Apply the curve to the bone
	animCurve = OpenMayaAnim.MFnAnimCurve()
	# Attach it
	animCurve.create(attrPlug, curveType)
	# Return the curve
	return animCurve

# Loads a .seanim file
def LoadSEAnimBuildCurve(filepath="", mergeOverride=False):
	# Load a seanim by building a curve
	print("Loading SEAnim file...")
	# Load the file using helper lib
	anim = SEAnim.Anim(filepath)
	# Starting frame
	start_frame = 0
	# End frame (Clamp to avoid blank animations)
	end_frame = max(1, anim.header.frameCount - 1)
	# Set scene start and end
	cmds.playbackOptions(ast=start_frame, minTime=start_frame)
	# Set end
	cmds.playbackOptions(maxTime=end_frame, aet=end_frame)
	# Turn off autoKey
	mel.eval("autoKeyframe -state off")
	# Make sure scene is in CM scale
	mel.eval("currentUnit -linear \"cm\"")
	# Reset scene if need be, todo, check anim type
	if not mergeOverride:
		# Reset it
		ResetSceneAnim()
	# Setup progress
	gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')
	# Count of bones (used for progress, clamped to at least 1)
	maxCount = max(1, len(anim.bones))
	# Create the bar
	cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=False, status='Loading SEAnim...', maxValue=maxCount)
	# Loop through bones
	for tag in anim.bones:
		# Progress
		cmds.progressBar(gMainProgressBar, edit=True, step=1)
		# Setup the tagname
		nsTag = tag.name.strip()
		# Make sure it's not blank
		if nsTag != "":
			# Check if it exists
			if cmds.objExists(nsTag + ".t") == False:
				# Set to new name
				nsTag = "*:" + nsTag
				# Check once more
				if cmds.objExists(nsTag + ".t") == False:
					# Go
					continue
		else:
			# Continue
			continue
		# Check for parent modifiers
		BoneAnimType = ResolvePotentialAnimTypeOverride(nsTag, anim.boneAnimModifiers)
		# Check if we need to use the anim's default type
		if BoneAnimType is None:
			# Use animation default
			BoneAnimType = anim.header.animType
		# Fetch the bone in the scene
		try:
			# Load it
			BoneDagPath = DagPathFromJoint(nsTag)
		except:
			# Log
			print("SEAnim -> WARN: Failed to get MDagPath for: " + nsTag)
		# Make a joint
		try:
			# Make joint
			BoneJoint = OpenMayaAnim.MFnIkJoint(BoneDagPath)
		except:
			# Log
			print("SEAnim -> WARN: Failed to get MFnIkJoint for: " + nsTag)
			# Go to next anim
			continue
		# Reset rotation values (If the animation is not additive)
		if len(tag.rotKeys) > 0 and BoneAnimType != SEAnim.SEANIM_TYPE.SEANIM_TYPE_ADDITIVE:
			# Set to rest rotation (if we have rotation keys!)
			BoneJoint.setOrientation(OpenMaya.MQuaternion(0, 0, 0, 1))
		# Grab rest transform
		BoneRestTransform = BoneJoint.getTranslation(OpenMaya.MSpace.kTransform)
		# Loop through translation keys (if we have any)
		if len(tag.posKeys) > 0:
			# We got them, create the curves first
			BoneCurveX = GetAnimCurve(BoneDagPath.transform(), "translateX", 1)
			BoneCurveY = GetAnimCurve(BoneDagPath.transform(), "translateY", 1)
			BoneCurveZ = GetAnimCurve(BoneDagPath.transform(), "translateZ", 1)
			# Get key
			key = tag.posKeys[0]
			# Set initial pose for the bone
			if BoneAnimType == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE:
				# We just set the position
				BoneJoint.setTranslation(OpenMaya.MVector(key.data[0], key.data[1], key.data[2]), OpenMaya.MSpace.kTransform)
			else:
				# It's relative, add rest transform
				BoneJoint.setTranslation(OpenMaya.MVector(key.data[0] + BoneRestTransform.x, key.data[1] + BoneRestTransform.y, key.data[2] + BoneRestTransform.z), OpenMaya.MSpace.kTransform)
			# Loop through keys
			for key in tag.posKeys:
				# Check animation type to see what data we need
				if BoneAnimType == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE:
					# Add absolute keyframe
					BoneCurveX.addKeyframe(OpenMaya.MTime(key.frame), key.data[0], 2, 2)
					BoneCurveY.addKeyframe(OpenMaya.MTime(key.frame), key.data[1], 2, 2)
					BoneCurveZ.addKeyframe(OpenMaya.MTime(key.frame), key.data[2], 2, 2)
				else:
					# Add relative keyframe
					BoneCurveX.addKeyframe(OpenMaya.MTime(key.frame), key.data[0] + BoneRestTransform.x, 2, 2)
					BoneCurveY.addKeyframe(OpenMaya.MTime(key.frame), key.data[1] + BoneRestTransform.y, 2, 2)
					BoneCurveZ.addKeyframe(OpenMaya.MTime(key.frame), key.data[2] + BoneRestTransform.z, 2, 2)
		# Loop through scale keys (if we have any)
		if len(tag.scaleKeys) > 0:
			# We got them, create the curves first
			BoneCurveX = GetAnimCurve(BoneDagPath.transform(), "scaleX", 1)
			BoneCurveY = GetAnimCurve(BoneDagPath.transform(), "scaleY", 1)
			BoneCurveZ = GetAnimCurve(BoneDagPath.transform(), "scaleZ", 1)
			# Get key
			key = tag.scaleKeys[0]
			# Set initial scale for the bone
			cmds.setAttr(nsTag + ".scale", key.data[0], key.data[1], key.data[2])
			# Loop through keys
			for key in tag.scaleKeys:
				# Add scale keyframe
				BoneCurveX.addKeyframe(OpenMaya.MTime(key.frame), key.data[0], 2, 2)
				BoneCurveY.addKeyframe(OpenMaya.MTime(key.frame), key.data[1], 2, 2)
				BoneCurveZ.addKeyframe(OpenMaya.MTime(key.frame), key.data[2], 2, 2)
		# Loop through rotation keys (if we have any)
		if len(tag.rotKeys) > 0:
			# We got them, create the curves first
			BoneCurveX = GetAnimCurve(BoneDagPath.transform(), "rotateX", 0)
			BoneCurveY = GetAnimCurve(BoneDagPath.transform(), "rotateY", 0)
			BoneCurveZ = GetAnimCurve(BoneDagPath.transform(), "rotateZ", 0)
			# Get key
			key = tag.rotKeys[0]
			# Set initial pose for the bone
			QuatData = OpenMaya.MQuaternion(key.data[0], key.data[1], key.data[2], key.data[3])
			# Convert to euler
			EularData = QuatData.asEulerRotation()
			# Set rotate values
			cmds.setAttr(nsTag + ".r", math.degrees(EularData.x), math.degrees(EularData.y), math.degrees(EularData.z))
			# Loop through keys
			for key in tag.rotKeys:
				# Add rotation keyframe (convert to eular)
				QuatData = OpenMaya.MQuaternion(key.data[0], key.data[1], key.data[2], key.data[3])
				# Convert to euler
				EularData = QuatData.asEulerRotation()
				# Add rotation keyframe
				BoneCurveX.addKeyframe(OpenMaya.MTime(key.frame), EularData.x, 2, 2)
				BoneCurveY.addKeyframe(OpenMaya.MTime(key.frame), EularData.y, 2, 2)
				BoneCurveZ.addKeyframe(OpenMaya.MTime(key.frame), EularData.z, 2, 2)
			# Set rotation interpolation (Why the fuck does the api not expose this...)
			mel.eval("catchQuiet(`rotationInterpolation -c quaternion \"" + nsTag + ".rotateX\" \"" + nsTag + ".rotateY\" \"" + nsTag + ".rotateZ\"`);")
	# End progress
	cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
	# Import notetracks (if any)
	if not cmds.objExists("SENotes"):
		# Make the base
		BaseNote = cmds.spaceLocator()
		# Rename
		cmds.rename(BaseNote, "SENotes")
	# Loop through the notes
	for note in anim.notes:
		# Try to key it
		try:
			# Clean the note name
			cleanNote = CleanNote(note.name)
			# Check if it exists
			if not cmds.objExists(cleanNote):
				# We must make it
				NewNote = cmds.spaceLocator()
				# Rename
				cmds.rename(NewNote, cleanNote)
				# Parent it
				mel.eval("parent " + cleanNote + " SENotes")
			# Now grab the curve, and add the key
			NoteCurve = GetAnimCurve(DagPathFromJoint(cleanNote, False).transform(), "translateX", 1)
			# Add the key
			NoteCurve.addKeyframe(OpenMaya.MTime(note.frame), 0, 2, 2)
		except:
			# Nothing
			pass
	# Reset time
	cmds.currentTime(start_frame)
	# End
	print("The animation has been loaded")

# Class to handle import / export
class SEAnimFileManager(OpenMayaMPx.MPxFileTranslator):
	def __init__(self):
		OpenMayaMPx.MPxFileTranslator.__init__(self)
	def haveWriteMethod(self):
		return False
	def haveReadMethod(self):
		return True
	def identifyFile(self, file, buf, size):
		return OpenMayaMPx.MPxFileTranslator.kCouldBeMyFileType
	def filter(self):
		return "*.seanim"
	def defaultExtension(self):
		return "seanim"
	def writer(self, fileObject, optionString, accessMode):
		print("TODO: Exporting")
	def reader(self, fileObject, optionString, accessMode):
		fileName = fileObject.fullName()
		LoadSEAnimBuildCurve(fileName)

# Proxy to the register object
def ProxySEAnimRegister():
	# Proxy to the handler
    return OpenMayaMPx.asMPxPtr(SEAnimFileManager())   

# Initialize plugin
def initializePlugin(mObject):
	# Register the plugin
	mPlugin = OpenMayaMPx.MFnPlugin(mObject, "DTZxPorter", "1.0", "Any")
	# Try and register the file translators
	try:
		# Register seanim
		mPlugin.registerFileTranslator("SEAnim", None, ProxySEAnimRegister)
	except:
		# Log the error
		print("Failed to register SETools!")
	# If we got here, setup the menu
	CreateMenu()

# Unload the plugin
def uninitializePlugin(mObject):
	# Get the plugin instance
	mPlugin = OpenMayaMPx.MFnPlugin(mObject)
	# Try and unregister the file translators
	try:
		# Unregister seanim
		mPlugin.deregisterFileTranslator("SEAnim")
	except:
		# Log error
		print("Failed to unload SETools!")
	# If we got here, clean up the menu
	DeleteMenu()