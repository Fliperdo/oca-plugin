## Installing the Plugin
Copy the oca-plugin folder here in the repo to the plugins folder of GIMP.

OR

Use the provided `install-and-update.ps1` script to automatically delete the old plugin and install the new one (you will need to change the script to point to your own environment):
```powershell
.\install-and-update.ps1
```

## Usage
Once the plugin is installed, you can export GIMP images to OCA format:
- Open an image in GIMP
- Go to File > Export As...
- Choose the .oca file format or just replace the name with .oca at the end
- The plugin will create a zip file with a .oca extension name and a blank.json manifest in that zip.
- You can rename the fileName.oca to fileName.zip and then extract it to see the contents.