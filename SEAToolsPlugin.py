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

MENU_DATA = {'menu' : ["SEAToolsPluginMenu", "SE Tools", None, None, None]}

GUN_BASE_TAGS = ["j_gun", "j_gun1", "tag_weapon", "tag_weapon1"]
VIEW_HAND_TAGS = ["tag_weapon", "tag_weapon1", "tag_weapon_right", "tag_weapon_left"]

# About info
def AboutWindow():
	result = cmds.confirmDialog(message="---  SE Tools plugin (v1.5.5)  ---\n\nDeveloped by DTZxPorter", button=['OK'], defaultButton='OK', title="About SE Tools")

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
				if partag == modBone.name:
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
	cmds.menuItem(label="Import <- SEAnim", command="SEAToolsPlugin.ImportSEAnim()")

	# Divide
	cmds.menuItem(divider=True)

	# Export tools
	cmds.menuItem(label="Export -> SEAnim", command="SEAToolsPlugin.ExportEntireSceneAnim()")

	# Divide
	cmds.menuItem(divider=True)

	# Clean namespaces
	cmds.menuItem(label="Clean Namespaces", command="SEAToolsPlugin.NamespaceClean()")

	# Place notetrack
	cmds.menuItem(label="Place Notetrack", command="SEAToolsPlugin.PlaceNote()")

	# Divide
	cmds.menuItem(divider=True)

	# Make game specific submenu
	game_menu = cmds.menuItem(label="Game Specific Tools", subMenu=True)

	# Call of duty menu
	cmds.menuItem(label="Call of Duty", subMenu=True)

	# Bind weapon to hand
	cmds.menuItem(label="Attach Weapon to Rig", command="SEAToolsPlugin.WeaponBinder()")

	# Close out menu (Call of Duty)
	cmds.setParent(game_menu, menu=True)

	# Close out menu (Game tools)
	cmds.setParent(menu, menu=True)

	# Divide
	cmds.menuItem(divider=True)

	# Debug stuff
	cmds.menuItem(label="Reload Plugin", command="reload(SEAToolsPlugin)")

	# About
	cmds.menuItem(label="About", command="SEAToolsPlugin.AboutWindow()")

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
	# Now we can make the child
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
	return note.replace(" ", "_").replace("#", "_").replace("\"", "_").replace("'", "_").replace("=", "_").replace("/", "_")

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

# Reference values for a maya matrix
"""
m00 = mmat[0]
m01 = mmat[4]
m02 = mmat[8]
m03 = mmat[12]
m10 = mmat[1]
m11 = mmat[5]
m12 = mmat[9]
m13 = mmat[13]
m20 = mmat[2]
m21 = mmat[6]
m22 = mmat[10]
m23 = mmat[14]
m30 = mmat[3]
m31 = mmat[7]
m32 = mmat[11]
m33 = mmat[15]
"""

def ExportEntireSceneAnim():
	# Export everything that's selected, if none, export all
	print("Exporting SEAnim...")
	# Get file
	exportTo = cmds.fileDialog2(fileMode = 0, fileFilter = "SEAnim Files (*.seanim)", caption = "Export SEAnim")
	# Check
	if exportTo == None or len(exportTo) == 0 or exportTo[0].strip() == "":
		# Was blank
		return None
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
	print("The SEAnim was exported.")


#Load a .seanim file
def LoadSEAnim(filepath=""):
	# Log
	print("Loading SEAnim file...")
	# Load the file using helper lib
	anim = SEAnim.Anim(filepath)
	# Starting frame
	start_frame = 0
	# End frame
	end_frame = anim.header.frameCount - 1
	# Set scene start and end
	cmds.playbackOptions(ast=start_frame, minTime=start_frame)
	# Set end
	cmds.playbackOptions(maxTime=end_frame, aet=end_frame)
	# Turn off autoKey
	mel.eval("autoKeyframe -state off")
	# Make sure scene is in CM measurment
	mel.eval("currentUnit -linear \"cm\"")
	# Setup progress
	gMainProgressBar = mel.eval('$tmp = $gMainProgressBar')
	# Count
	maxCount = len(anim.bones)
	# Create the bar
	cmds.progressBar(gMainProgressBar, edit=True, beginProgress=True, isInterruptable=False, status='Loading SEAnim...', maxValue=maxCount)
	# Import the actual keyframes
	i = 0
	# Loop through tag names
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
					# Continue the loop
					i += 1
					# Go
					continue
		else:
			# Continue
			continue
		# Check for parent modifiers
		animType = ResolvePotentialAnimTypeOverride(nsTag, anim.boneAnimModifiers)
		# Check if we need to use the anim's default type
		if animType is None:
			# Use animation default
			animType = anim.header.animType

		# Generate the rest keyframes which are used as a base for the following frames (for only the bones that are used)
		try:
			if len(tag.rotKeys) > 1: # Has a lot of rotation
				# Reset bone orientation
				cmds.setAttr(nsTag + ".jo", 0, 0, 0)
				# Reset bone rotation
				cmds.setAttr(nsTag + ".rotate", 0, 0, 0)
			else: # Has no rotation but needs to be reset, should work..
					# Reset bone orientation
					cmds.setAttr(nsTag + ".jo", 0, 0, 0)
					# Reset bone rotation
					cmds.setAttr(nsTag + ".rotate", 0, 0, 0)
			# Set key
			cmds.setKeyframe(nsTag, time=start_frame)
		except:
			pass
		# Grab current position data
		bone_rest = cmds.getAttr(nsTag + ".t")[0]
		# Loop through positions
		for key in tag.posKeys:
			# Viewanims are SEANIM_TYPE_ABSOLUTE
			if animType == SEAnim.SEANIM_TYPE.SEANIM_TYPE_ABSOLUTE:
				# Set the absolute key
				cmds.setKeyframe(nsTag, v=key.data[0], at="translateX", time=key.frame)
				cmds.setKeyframe(nsTag, v=key.data[1], at="translateY", time=key.frame)
				cmds.setKeyframe(nsTag, v=key.data[2], at="translateZ", time=key.frame)
				# Check if it's static
				if len(tag.posKeys) == 1: # Single pos, change the value on the bone
					# Set it
					cmds.setAttr(nsTag + ".t", key.data[0], key.data[0], key.data[0])
			else: # Use DELTA / RELATIVE results (ADDITIVE is unknown)
				# Set the relative key
				cmds.setKeyframe(nsTag, v=(bone_rest[0] + key.data[0]), at="translateX", time=key.frame)
				cmds.setKeyframe(nsTag, v=(bone_rest[1] + key.data[1]), at="translateY", time=key.frame)
				cmds.setKeyframe(nsTag, v=(bone_rest[2] + key.data[2]), at="translateZ", time=key.frame)
				# Check if it's static
				if len(tag.posKeys) == 1: # Single pos, change the value on the bone
					# Set it
					cmds.setAttr(nsTag + ".t", (bone_rest[0] + key.data[0]), (bone_rest[1] + key.data[1]), (bone_rest[2] + key.data[2]))
		# Loop through rotations
		for key in tag.rotKeys:
			# Set the rotation
			quat = OpenMaya.MQuaternion(key.data[0], key.data[1], key.data[2], key.data[3])
			# Convert to euler
			euler_rot = quat.asEulerRotation()
			# Reset it's JO
			cmds.setAttr(nsTag + ".jo", 0, 0, 0)
			# Set the matrix
			cmds.setAttr(nsTag + ".r", math.degrees(euler_rot.x), math.degrees(euler_rot.y), math.degrees(euler_rot.z))
			# Key the frame
			cmds.setKeyframe(nsTag, at="rotate", time=key.frame)
		# Loop through scales
		for key in tag.scaleKeys:
			# Set the scale keys
			cmds.setKeyframe(nsTag, v=key.data[0], at="scaleX", time=key.frame)
			cmds.setKeyframe(nsTag, v=key.data[1], at="scaleY", time=key.frame)
			cmds.setKeyframe(nsTag, v=key.data[2], at="scaleZ", time=key.frame)
			# Check if it's static
			if len(tag.scaleKeys) == 1: # Single scale, change the value on the bone
				# Set it
				cmds.setAttr(nsTag + ".scale", key.data[0], key.data[1], key.data[2])
		# Rotation interpolation (Only for eular angles)
		mel.eval("rotationInterpolation -c quaternion \"" + nsTag + ".rotateX\" \"" + nsTag + ".rotateY\" \"" + nsTag + ".rotateZ\"")
		# Try to interpol
		try:
			# Linear interpolation (Eular angles)
			cmds.select(nsTag)
			# Transform selection
			mel.eval("keyTangent -e -itt linear -ott linear")
		except:
			# Nothing
			pass
		# Clear selection
		cmds.select(clear=True)
		# Basic counter
		i += 1
	# End progress
	cmds.progressBar(gMainProgressBar, edit=True, endProgress=True)
	# Notetracks
	base_track = cmds.spaceLocator()
	# Rename
	cmds.rename(base_track, "SENotes")
	# Loop
	for note in anim.notes:
		# Try to key it
		try:
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
		except:
			# Nothing
			pass

	# Reset time
	cmds.currentTime(start_frame)
	# End
	print("The animation has been loaded.")

# Make the menu
CreateMenu()