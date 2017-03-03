# SEToolsMaya (v1.5.6)

A .SE format import / export plugin for maya (2012+)

*.SE formats are open-sourced formats optimized for next-generation modeling and animation. They are free to be used in any project, game, software, etc with the hopes that people will adapt the standard unlike other formats available.*

- Animation format documentation: [Specification](https://github.com/SE2Dev/SEAnim-Docs)
- Model format documentation: [Coming soon](#)

## Installation:

Download the latest [seanim.py](https://raw.githubusercontent.com/dtzxporter/SEATools/master/seanim.py) and [SEAToolsPlugin.py](https://raw.githubusercontent.com/dtzxporter/SEATools/master/SEAToolsPlugin.py) from the repo and save them in `Documents\maya\<mayaversion>\scripts`

If you have a usersetup.mel edit it and put `python("import SEAToolsPlugin");` on it's own line, otherwise create this file and add the line to it. Close and reopen maya to see the new SEA Tools menu.

## Updating:

Replace the files in the `Documents\maya\<mayaversion>\scripts` folder with the new ones AND delete all of the `.pyc` files. Go to "SE Tools->Reload" Plugin to finish.

## Usage:

*Animations:*
- To import an anim use "SE Tools -> Import SEAnim" this will import an anim onto an already binded scene.
- To export, either select the bones to use (or select none for all), set the end scene time to the animation end time, then use "SE Tools -> Export SEAnim" this will export the animation to a .seanim file.
- To place a notetrack use "SE Tools -> Place Notetrack" this will place a notetrack named "new_notetrack" at the current scene time, you can rename it using the object browser on the left.

*Models:*
- Coming soon

## Changelog:

*v1.5.6:*
- Fix in seanim.py for scale export!

*v1.5.5:*
- Simplified import and export
- Fixed framerate and end scene time when exporting anims
- Fixed another bug on import
- Added place notetrack feature
- Cleaned up codebase
- Added support for bone scale keys
- Exporting progress bar
- Ensured that the scene is in se format units (CM)
- Requires updated seanim.py!