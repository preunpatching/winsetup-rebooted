# Windows Setup Batch Script
A Windows Batch script designed to install Windows with the least amount of hassles.

It manually installs Windows with no extra applications needed, while bypassing the OOBE and telemetry prompts too.

## How to use
> [!WARNING]
> ***This is currently a pre-release. Stuff may not work properly.***
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
> ***This will erase all of your data on the selected disk. Make sure you have backed up all of the important information from it into another medium before continuing.***

> [!CAUTION]
> ***Do NOT terminate setup if the script says so. Otherwise, you will brick your current install and will need a complete reinstall.***

## Changelog
- **2025-06-05: Released public pre-release.**
