# Windows Setup Rebooted
The ultimate way to install Windows with the least amount of hassles!

## How to use
> [!WARNING]
> **This is currently a pre-release.** Stuff may not work properly.
> If you don't want to risk anything, just wait until the full release.

_Requires an existing copy of the Windows installation media._
Just plop it in into your drive, or, into a separate drive, then within Setup, select "Repair my PC" and then launch the command prompt. Navigate to the drive and do the requested steps.

> [!TIP]
> If you cannot determine what disk you actually need to use, do the following commands:
> Leave the script and type in ```diskpart```.
> Type in the command ```lis dis```.
> Select the disk you need using ```sel dis [your disk here]``` and then ```del dis```. This will show the details of that disk.
> If it's the wrong disk, select another disk and see its details. Search until you found the correct disk.
> Leave diskpart with ```exit```, then go back to setup and use that disk to continue.

> [!WARNING]
> **This will erase all of your data on the selected disk.** Make sure you have backed up all of the important information from it into another medium before continuing.

> [!CAUTION]
> ***Do NOT terminate setup if the script says so. Otherwise, you will brick your current install and will need a complete reinstall.***

## How to use unattended mode
The script includes unattended mode, which allows you to set up with no user input.

Unattended mode can be used with the ```/\``` parameter and uses ```setup.cfg``` to read the parameters for setup.

### Parameter definitions
- ```src``` (required): Defines source drive letter containing the Windows installation media.
- ```idx``` (required): Defines the specified image index to use.
- ```drv``` (required): Defines target drive number to install Windows on.
- ```name``` (required): Defines user name to use.
- ```pass```: Defines user name password to use.
- ```nomsr```: Specifies not to create Microsoft Reserved partition.
- ```nowre```: Specifies not to create Recovery partition.
- ```bl1```: Specifies to include common bloat.
- ```bl2```: Specifies to include Sound Recorder.
- ```bl3```: Specifies to include Camera.
- ```bl4```: Specifies to include Clock.
- ```bl5```: Specifies to include Calculator.
- ```bl6```: Specifies to include Dev Home.
- ```bl7```: Specifies to include Phone Link.
- ```bl8```: Specifies to include Snipping Tool.
- ```bl9```: Specifies to include Terminal.
- ```bl10```: Specifies to include Xbox App and gaming features.
- ```bl11```: Specifies to include Paint.
- ```bl12```: Specifies to include Microsoft Store.
- ```bl13```: Specifies to include Microsoft Edge (UWP stub).
- ```bl14```: Specifies to include Media Player.
- ```bl15```: Specifies to include Photos.
- ```bl16```: Specifies to include Notepad.
> [!CAUTION]
> ***Due to the constraints of Batch, every line of the ```setup.cfg``` file is executed, even if it does not make a valid parameter. This can introduce Arbitrary Code Execution (ACE), which allows the user to execute custom code and potentially cause harm to your computer.*** To prevent this risk, **please check the ```setup.cfg``` before using unattended mode** as ACE can be used to destroy data, install viruses and more.
## Changelog
- **2025-06-05: Released v0.1.0.** Initial public pre-release.
- **2025-06-21: Released v0.2.0.**
  - Added unattended mode.
  - Added Microsoft Reserved and Recovery partition support.
- **2025-07-08: Released v0.3.0.**
  - Added Standard setup mode, along with Advanced mode.
  - Added debloat support.
  - Fixed delimiter set for unattended mode.
  - Revamped user interface.
