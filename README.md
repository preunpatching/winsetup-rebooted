# Windows Setup Rebooted
The ultimate way to install Windows with the least amount of hassles!

![An operating system installer flying over the sky.](logo.jpg)
_Image generated using Flux model with prompt "An operating system installer flying over the sky"._

> [!WARNING]
> **This is currently a pre-release.** Stuff may not work properly.
> If you don't want to risk anything, just wait until the full release.

## What it can do
A lot of things! Includes:
- Not just **operating system installation**, but **full system provision**! You can install your selection of apps and let it rip!
- **Bypasses the OOBE (Out Of Box Experience) and other prompts**! No need to do things Microsoft forces you to do!
- **Includes 2 setup modes** - _Standard_ and _Advanced_. Even people who know nothing about this crazy stuff can use it!
- **Debloating**! Yes, you can uninstall your most hated apps, including Microsoft Store!
- **Unattended mode**! You can make a configuration file that contains your settings, then launch it and let it do the job for you!
- And all of this is in **one file**! No external components required.

## How to use
_Requires an existing copy of Windows installation media._
Just place this script into your Windows installation media or into a separate drive, then within Setup, select _Repair my PC_ and then launch the command prompt and then the script.

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
- ```bl1```: Specifies to remove common bloat.
- ```bl2```: Specifies to remove Sound Recorder.
- ```bl3```: Specifies to remove Camera.
- ```bl4```: Specifies to remove Clock.
- ```bl5```: Specifies to remove Calculator.
- ```bl6```: Specifies to remove Dev Home.
- ```bl7```: Specifies to remove Phone Link.
- ```bl8```: Specifies to remove Snipping Tool.
- ```bl9```: Specifies to remove Terminal.
- ```bl10```: Specifies to remove Xbox App and gaming features.
- ```bl11```: Specifies to remove Paint.
- ```bl12```: Specifies to remove Microsoft Store.
- ```bl13```: Specifies to remove Microsoft Edge (UWP stub).
- ```bl14```: Specifies to remove Media Player.
- ```bl15```: Specifies to remove Photos.
- ```bl16```: Specifies to remove Notepad.
- ```dia```: Specifies to download and install apps specified in ```app```.
- ```app```: Specifies which apps to install. The best way to get it is to go to [Ninite](https://ninite.com/), select your apps, and copy everything between the 2 last forward slashes.
- ```iapp```: Specifies to install apps in the Apps folder.
- ```idrv```: Specifies to install drivers in the Drivers folder.
> [!CAUTION]
> ***Due to the constraints of Batch, every line of the ```setup.cfg``` file is executed, even if it does not make a valid parameter. This can introduce Arbitrary Code Execution (ACE), which allows the user to execute custom code and potentially cause harm to your computer.*** To prevent this risk, **please check the ```setup.cfg``` before using unattended mode** as ACE can be used to destroy data, install viruses and more.

## Changelog
- **2025-09-09: Released v0.5.0.**
  - Added local apps and drivers installation support.
  - Fixed permission errors.
- **2025-07-16: Released v0.4.0.**
  - Changed the name from _Windows Setup Batch Script_ to _Windows Setup Rebooted_.
  - Added download and install apps feature.
- **2025-07-08: Released v0.3.0.**
  - Added Standard setup mode, along with Advanced mode.
  - Added debloat support.
  - Fixed delimiter set for unattended mode.
  - Revamped user interface.
- **2025-06-21: Released v0.2.0.**
  - Added unattended mode.
  - Added Microsoft Reserved and Recovery partition support.
- **2025-06-05: Released v0.1.0.** Initial public pre-release.
