# Ripchord2ChordTrigger
A simple Python script converting ripchord presets to Logic Pro's Chord Trigger preset. For those having trouble with ripchord in Logic Pro.

## Reason for creating this
In some M-series Mac, using ripchord with Logic Pro or MainStage will cause random notes being pressed without any way to stop them when adding or initializing the plugin to the track. This is most likely cause by a bug in Logic Pro and MainStage's MIDI processing. You can of course enable MIDI 2.0 in Logic's setting to get rid of this issue but MainStage does not have such option. Since Logic's built-in Chord Trigger plugin behaves basically the same as ripchord, ripchord users suffering from this issue can easily convert their ripchord presets that they found (or bought with real money 💸) to Chord Trigger-usable presets. 

## Usage
Run the script under where the presets are located, and it will automatically convert all ripchord presets into `Chord Trigger Presets` subfolder by default.
After running the script, it's better to drag the output folder into Chord Trigger's preset folder to access it using Chord Trigger's preset dropdown. You may open a Finder window, press shift + command + G and copy paste this to enter the Chord Trigger preset folder:
``` 
/Users/[YOUR_USERNAME]/Music/Audio Music Apps/Plug-In Settings/Chord Trigger
```

### Default
``` bash
# inside the preset folder
python3 ripchord2chordtrigger.py
```

### Designate output folder
``` bash
# inside the preset folder
python3 ripchord2chordtrigger.py --output "Folder Name"
```

### Convert selected preset(s)
``` bash
# inside the preset folder
python3 ripchord2chordtrigger.py "this_preset.rpc" "that_preset.rpc" "etc.rpc"
```

### Replace existing conversion
``` bash
# inside the preset folder
python3 ripchord2chordtrigger.py --force
```

### Show options
``` bash
# inside the preset folder
python3 ripchord2chordtrigger.py --help
```
