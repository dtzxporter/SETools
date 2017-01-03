# SEA formats import / export plugin for Maya
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

#TODO: A way to purge namespaces from menu
#TORO: Update check...?

MENU_DATA = {'menu' : ["SEAToolsPluginMenu", "SEA Tools", None, None, None]}

GUN_BASE_TAGS = ["j_gun", "j_gun1", "tag_weapon", "tag_weapon1"]
VIEW_HAND_TAGS = ["tag_weapon", "tag_weapon1", "tag_weapon_right", "tag_weapon_left"]

# About info
def AboutWindow():
	result = cmds.confirmDialog(message="---  SEA Tools plugin (v1.3.4)  ---\n\nDeveloped by DTZxPorter\n\nFormat design by SE2Dev", button=['OK'], defaultButton='OK', title="About SEA Tools")

# A list (in order of priority) of bone names to automatically search for when determining which bone to use as the root for delta anims
DeltaRootBones = ["tag_origin"]

# Compare two iterable objects
def first(a, b):
	for elem in a:
		if elem in b:
			return a
	return None

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
def ResolvePotentialAnimTypeOverride(bone, boneAnimModifiers):
	#Grab the parent tree
	try:
		parents = cmds.ls(bone.name, long=True)[0].split('|')[1:-1]
		# Check if we even had parents
		if len(parents) == 0 or len(boneAnimModifiers) == 0:
			return None

		for parent in parents:
			for modBone in boneAnimModifiers:
				if parent == modBone.name:
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
		pass
	else:
		LoadSEAnim(file_import)

# Create the menu
def CreateMenu():
	# Set the diplay's parent
	cmds.setParent(mel.eval("$temp1=$gMainWindow"))
	# Check for existing control, remove it if we can
	if cmds.control(MENU_DATA['menu'][0], exists=True):
		cmds.deleteUI(MENU_DATA['menu'][0], menu=True)
	
	# Recreate the base
	menu = cmds.menu(MENU_DATA['menu'][0], label=MENU_DATA["menu"][1], tearOff=True)
	
	# Import tools
	cmds.menuItem(label="Import SEAnim", command="SEAToolsPlugin.ImportSEAnim()")

	# Divide
	cmds.menuItem(divider=True)

	# Export tools
	cmds.menuItem(label="Export All -> SEAnim", command="SEAToolsPlugin.ExportEntireSceneAnim()")

	# Export selected
	cmds.menuItem(label="Export Selected -> SEAnim", command="SEAToolsPlugin.ExportSelectedAnim()")

	# Divide
	cmds.menuItem(divider=True)

	# Bind weapon to hand
	cmds.menuItem(label="Attach Weapon to Rig", command="SEAToolsPlugin.WeaponBinder()")

	# Divide
	cmds.menuItem(divider=True)

	# Debug stuff
	cmds.menuItem(label="Reload Plugin", command="reload(SEAToolsPlugin)")

	# About
	cmds.menuItem(label="About", command="SEAToolsPlugin.AboutWindow()")

# Bind the weapon to hands
def WeaponBinder():
	# This is currently COD specific, can implement into model / anim format later
	for x in xrange(0,len(GUN_BASE_TAGS)):
		try:
			# Select both tags and parent them
			cmds.select(GUN_BASE_TAGS[x], replace=True)
			cmds.select(VIEW_HAND_TAGS[x], toggle=True)
			# Connect
			cmds.connectJoint(connectMode=True)
			# Parent
			mel.eval("parent " + GUN_BASE_TAGS[x] + " " + VIEW_HAND_TAGS[x])
			# Remove
			cmds.select(clear=True)
		except:
			pass

def CleanNote(note):
	# Clean the note string
	return note.replace(" ", "_").replace("#", "_").replace("\"", "_").replace("'", "_").replace("=", "_")

def ExportEntireSceneAnim(selectedBones=False):
	# Export the whole scene
	print("Exporting SEAnim...")
	# Get file
	exportTo = cmds.fileDialog2(fileMode=0, fileFilter="SEAnim Files (*.seanim)", caption="Export SEAnim")
	# Check
	if exportTo == None or len(exportTo) == 0 or exportTo[0].strip() == "":
		# Was blank
		return None
	# Setup path
	exportPath = exportTo[0].strip()
	# An anim
	resultAnim = SEAnim.Anim()
	# Used because we made this anim after the fact
	resultAnim.header.animType = SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE
	# Loop through bones in scene
	allBones = cmds.ls(type='joint')
	# Check if we just want selected bones
	if selectedBones:
		# Only list selected bones (Joints)
		allBones = cmds.ls(selection=True, type='joint')
	# A list of frames
	framesList = []
	# Loop
	for bone in allBones:
		# Our bone
		boneUse = SEAnim.Bone()
		# Set name
		boneUse.name = bone
		# We had keys
		hadKeys = False
		# Check if bone has keys for .t or .r
		keysTranslate = cmds.keyframe(bone + ".translate", query=True, timeChange=True)
		# framesAddedTranslate
		framesAddedTranslate = []
		# Check
		if keysTranslate is not None:
			if len(keysTranslate) >= 1:
				# We got translation frames, loop and add
				hadKeys = True
				# Loop
				for frame in keysTranslate:
					# Add if need be
					if frame not in framesList:
						# Add
						framesList.append(frame)
					# Check
					if frame not in framesAddedTranslate:
						# Add
						framesAddedTranslate.append(frame)
						# Grab the XYZ
						transKey = cmds.getAttr(bone + ".translate", time=frame)[0]
						# Make and add key
						boneUse.posKeys.append( SEAnim.KeyFrame(frame, transKey) )
						# Increase
						boneUse.locKeyCount = (boneUse.locKeyCount + 1)
		# Get rotations
		keysRotate = cmds.keyframe(bone + ".rotate", query=True, timeChange=True)
		# framesAddedRotate
		framesAddedRotate = []
		# Check
		if keysRotate is not None:
			if len(keysRotate) >= 1:
				# We got rotations frames, loop and add
				hadKeys = True
				# Loop
				for frame in keysRotate:
					# Add if need be
					if frame not in framesList:
						# Add
						framesList.append(frame)
					# Check
					if frame not in framesAddedRotate:
						# Add
						framesAddedRotate.append(frame)
						# Grab the Eular and convert to quat
						eularKey = cmds.getAttr(bone + ".rotate", time=frame)[0]
						# Convert and add
						eularRot = OpenMaya.MEulerRotation(math.radians(eularKey[0]), math.radians(eularKey[1]), math.radians(eularKey[2]))
						# Result
						quatRot = eularRot.asQuaternion()
						# Make rot
						rotValue = (quatRot.x, quatRot.y, quatRot.z, quatRot.w)
						# Make and add key
						boneUse.rotKeys.append( SEAnim.KeyFrame(frame, rotValue) )
						# Increase
						boneUse.rotKeyCount = (boneUse.rotKeyCount + 1)
		# Check if we had any
		if hadKeys:
			# Add to anim
			resultAnim.bones.append(boneUse)
	# Check for SENotes
	if (cmds.objExists("SENotes")):
		# Get children and loop
		noteTrackList = cmds.listRelatives("SENotes",type="transform")
		# Loop
		if noteTrackList is not None:
			# Loop it
			for note in noteTrackList:
				# Get key'd values
				noteKeys = cmds.keyframe(note + ".translateX", query=True, timeChange=True)
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
	# Frame count ( Get biggest # from list )
	resultAnim.header.frameCount = len(framesList)
	# Save as file
	resultAnim.save(exportPath)
	# Done
	print("The SEAnim was exported.")

def ExportSelectedAnim():
	# Export selected bones only
	ExportEntireSceneAnim(True)


#Load a .seanim file
def LoadSEAnim(filepath=""):
	# Log
	print("Loading SEAnim file...")
	# Load the file using helper lib
	anim = SEAnim.Anim(filepath)
	# Starting frame
	start_frame = 0
	# End frame
	end_frame = start_frame + anim.header.frameCount - 1
	# Set scene start and end
	cmds.playbackOptions(ast=start_frame, minTime=start_frame)
	# Set end
	cmds.playbackOptions(maxTime=end_frame, aet=end_frame)
	# Turn off autoKey
	mel.eval("autoKeyframe -state off")
	# Import the actual keyframes
	i = 0
	# Loop through tag names
	for tag in anim.bones:
		try:
			# Check if the tag exist, otherwise don't waste time
			cmds.getAttr(tag.name + ".t")
		except:
			i += 1
		else:
			# Check for parent modifiers
			animType = ResolvePotentialAnimTypeOverride(tag, anim.boneAnimModifiers)
			# Check if we need to use the anim's default type
			if animType is None:
				# Use animation default
				animType = anim.header.animType

			# Generate the rest keyframes which are used as a base for the following frames (for only the bones that are used)
			try:
				if len(tag.rotKeys) > 1: # Has a lot of rotation
					# Reset bone orientation
					cmds.setAttr(tag.name + ".jo", 0, 0, 0)
					# Reset bone rotation
					cmds.setAttr(tag.name + ".rotate", 0, 0, 0)
				else: # Has no rotation but needs to be reset, should work..
 					# Reset bone orientation
 					cmds.setAttr(tag.name + ".jo", 0, 0, 0)
 					# Reset bone rotation
 					cmds.setAttr(tag.name + ".rotate", 0, 0, 0)
				# Set key
				cmds.setKeyframe(tag.name, time=start_frame)
			except:
				pass
			# Grab current position data
			bone_rest = cmds.getAttr(tag.name + ".t")[0]
			# Loop through positions
			for key in tag.posKeys:
				# Viewanims are SEANIM_TYPE_ABSOLUTE
				if animType == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE:
					# Set the absolute key
					cmds.setKeyframe(tag.name, v=key.data[0], at="translateX", time=key.frame)
					cmds.setKeyframe(tag.name, v=key.data[1], at="translateY", time=key.frame)
					cmds.setKeyframe(tag.name, v=key.data[2], at="translateZ", time=key.frame)
					# Check if it's static
					if len(tag.posKeys) == 1: # Single pos, change the value on the bone
						# Set it
						cmds.setAttr(tag.name + ".t", key.data[0], key.data[1], key.data[2])
				else: # Use DELTA / RELATIVE results (ADDITIVE is unknown)
					# Set the relative key
					cmds.setKeyframe(tag.name, v=(bone_rest[0] + key.data[0]), at="translateX", time=key.frame)
					cmds.setKeyframe(tag.name, v=(bone_rest[1] + key.data[1]), at="translateY", time=key.frame)
					cmds.setKeyframe(tag.name, v=(bone_rest[2] + key.data[2]), at="translateZ", time=key.frame)
					# Check if it's static
					if len(tag.posKeys) == 1: # Single pos, change the value on the bone
						# Set it
						cmds.setAttr(tag.name + ".t", (bone_rest[0] + key.data[0]), (bone_rest[1] + key.data[1]), (bone_rest[2] + key.data[2]))
			# Loop through rotations
			for key in tag.rotKeys:
				# Set the rotation
				quat = OpenMaya.MQuaternion(key.data[0], key.data[1], key.data[2], key.data[3])
				# Convert to euler
				euler_rot = quat.asEulerRotation();
				# Reset it's JO
				cmds.setAttr(tag.name + ".jo", 0, 0, 0)
				# Set the matrix
				cmds.setAttr(tag.name + ".r", math.degrees(euler_rot.x), math.degrees(euler_rot.y), math.degrees(euler_rot.z))
				# Key the frame
				cmds.setKeyframe(tag.name, at="rotate", time=key.frame)
			# Rotation interpolation (Only for eular angles)
			mel.eval("rotationInterpolation -c quaternion " + tag.name + ".rotateX " + tag.name + ".rotateY " + tag.name + ".rotateZ")
			# Try to interpol
			try:
				# Linear interpolation (Eular angles)
				cmds.select(tag.name)
				# Transform selection
				mel.eval("keyTangent -e -itt linear -ott linear")
			except:
				# Nothing
				pass
			# Clear selection
			cmds.select(clear=True)
			# Basic counter
			i += 1
	# Notetracks
	base_track = cmds.spaceLocator()
	# Rename
	cmds.rename(base_track, "SENotes")
	# Loop
	for note in anim.notes:
		# Clean the note name
		cleanNote = CleanNote(note.name)
		# Check if it exists
		if cmds.objExists(cleanNote):
			# We have it, key it
			cmds.setKeyframe(cleanNote, time=note.frame)
		else:
			# We need to make it
			notetrack = cmds.spaceLocator()
			# Rename
			cmds.rename(notetrack, cleanNote)
			# Parent it
			mel.eval("parent " + cleanNote + " SENotes")
			# Key it
			cmds.setKeyframe(cleanNote, time=note.frame)

	# Reset time
	cmds.currentTime(start_frame)
	# End
	print("The animation has been loaded.")

# Make the menu
CreateMenu()
