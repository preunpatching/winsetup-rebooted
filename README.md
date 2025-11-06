# Windows Setup Rebooted
The ultimate way to install Windows with the least amount of hassles!

![An operating system installer flying over the sky.](logo.jpg)
_Image generated using Flux model with prompt "An operating system installer flying over the sky"._

# What it can do
A lot of things! Includes:
- Not just **operating system installation**, but **full system provision**! You can install your selection of apps and let it rip!
- **Bypasses the OOBE (Out Of Box Experience) and other prompts**! No need to do things Microsoft forces you to do!
- **Includes 2 setup modes** - _Standard_ and _Advanced_. Even people who know nothing about this crazy stuff can use it!
- **Debloating**! Yes, you can uninstall your most hated apps, including Microsoft Store!
- **Unattended mode**! You can make a configuration file that contains your settings, then launch it and let it do the job for you!
- **BIOS/UEFI-CSM support**! Even your ancient x64 PC with a BIOS can run Windows 11!
- And all of this is in **one file**! No external components required.

# Minimum system requirements using this tool
- x64 capable CPU
- ~~4GB~~ 2GB of RAM (DISM will throw an OOM error if with roughly less than 2GB of RAM)
- ~~UEFI only with Secure Boot~~ BIOS or UEFI
- ~~TPM 2.0~~

# How to use
_Requires an existing copy of Windows installation media._
Just place Setup into your Windows installation media or into a separate drive, then within Setup, select _Repair my PC_ and then launch the command prompt and then run Setup. **The binaries are for Windows 8 and later only.**

> [!WARNING]
> **This will erase all of your data on the selected disk.** Make sure you have backed up all of the important information from it into another medium before continuing.

> [!CAUTION]
> ***Do NOT terminate setup if the script says so. Otherwise, you will brick your current install and will need a complete reinstall.***

## How to use unattended mode
Setup includes unattended mode, which allows you to set up Windows without any user input.

First, run Setup with the ```--generate <config.json>``` parameter. This will run Setup, but instead of starting Phase 2 upon finishing, it will generate a config file as ```config.json```. Then, you can run Setup with the ```--unattend <unattend.json>``` parameter, which will read the configuration from ```unattend.json```, verify the parameters, then immediately start installation. If any value is invalid, Setup will not run.

> [!NOTE]
> You cannot combine the ```--generate``` and ```--unattend``` parameters together.

# How to build
In a folder containing ```setup.pyw``` and ```phase3.pyw```, run ```pyinstaller -F --optimize 2 phase3.pyw&&pyinstaller -F --optimize 2 --add-binary "dist\phase3.exe:." setup.pyw```. The binaries will be produced in the dist folder. It has been confirmed to compile under Python 3.13.7 and 3.14.0.

## Test mode
To run Setup in test mode, run Setup with the ```--test``` parameter. This will run Setup, but the OS checks will be bypassed, no Terminal or Verifier functions will run, and Phase 2 will not run. It is used purely for testing the GUI to ensure it does not produce any errors.

# Planned features
- [ ] Bring back Ninite app installation support (removed in v1.0.0)
- [x] ~~Transition into Windows GUI binary~~ (implemented in v1.0.0)
- [x] ~~More robust error checking~~ (implemented in v1.0.0)
- [x] ~~More secure password input field~~ (implemented in v1.0.0)

# FAQ
## What about Python 3.15?
It is still **an early developer preview** - I will not maintain support for Python 3.15, likely until it reaches the **release candidate** phase (expected to start at 2026-07-28).

## What about Windows Vista and 7 support?
This requires **Python 3.8 or earlier**, which is long since the last bugfix update (2021-05-03) and the last security update without binaries (2024-09-06). It may be possible to get binaries working in Python 3.8, but some features that weren't present in Python 3.8 (which may be plenty) may not work at all, requiring a rewrite.
