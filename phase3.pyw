import sys
import os
import subprocess
import json
import winreg
import time
import shutil
import ctypes

class HiddenProcess:
    """
    Context manager to run subprocesses without a console window.
    Uses CREATE_NO_WINDOW flag.
    """
    def __enter__(self):
        self.startupinfo = subprocess.STARTUPINFO()
        self.startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        self.startupinfo.wShowWindow = subprocess.SW_HIDE
        self.creationflags = subprocess.CREATE_NO_WINDOW
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def is_admin():
    """Check if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def execute_command(command):
    """Executes a command without a window and logs it."""
    try:
        with HiddenProcess() as hp:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=hp.startupinfo,
                creationflags=hp.creationflags
            )
            result.wait()
        return result
    except Exception as e:
        return None

def set_registry_value(hive, key_path, value_name, value_type, value_data):
    """Sets a registry value. 'hive' is 'HKLM' or 'HKCU'."""
    try:
        root_key = winreg.HKEY_LOCAL_MACHINE if hive == "HKLM" else winreg.HKEY_CURRENT_USER
        
        with winreg.OpenKey(root_key, key_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, value_name, 0, value_type, value_data)
        return True
    except FileNotFoundError:
        try:
            # Key might not exist, try creating it
            with winreg.CreateKey(root_key, key_path) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, value_data)
            return True
        except Exception as e:
            return False
    except Exception as e:
        return False

def check_oobe_status():
    """
    Checks if OOBE is in progress.
    Per user request, returns True (run) if keys are NOT 0.
    Returns False (don't run) if they are 0 (completed).
    """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\Setup", 0, winreg.KEY_READ) as key:
            oobe_in_progress, _ = winreg.QueryValueEx(key, "OOBEInProgress")
            setup_in_progress, _ = winreg.QueryValueEx(key, "SystemSetupInProgress")
            
            # If both are 0, setup is "complete", so we should not run.
            if oobe_in_progress == 0 and setup_in_progress == 0:
                return False
            
            # Otherwise, one or both are non-zero, meaning setup is active.
            return True
            
    except FileNotFoundError:
        return True
    except Exception as e:
        return True

def create_user(username, password):
    """Creates a user account and adds it to Administrators."""
    if password:
        execute_command(f'net user "{username}" "{password}" /add')
    else:
        execute_command(f'net user "{username}" /add')
    
    execute_command(f'net localgroup Users "{username}" /add')
    execute_command(f'net localgroup Administrators "{username}" /add')

def remove_bloat(bloat_list):
    """Removes provisioned AppX packages based on the list."""   
    # Map of IDs from config to package names
    BLOAT_MAP = {
        # Common
        "bl_common": [
            "Clipchamp.Clipchamp", "Microsoft.BingNews", "Microsoft.BingSearch",
            "Microsoft.BingWeather", "Microsoft.Edge.GameAssist", "Microsoft.GetHelp",
            "Microsoft.MicrosoftOfficeHub", "Microsoft.MicrosoftSolitaireCollection",
            "Microsoft.MicrosoftStickyNotes", "Microsoft.OutlookForWindows",
            "Microsoft.PowerAutomateDesktop", "Microsoft.Todos",
            "Microsoft.WindowsFeedbackHub", "MSTeams", "MicrosoftCorporationII.QuickAssist",
            "MicrosoftWindows.Client.WebExperience", "MicrosoftWindows.CrossDevice"
        ],
        "bl_soundrec": ["Microsoft.WindowsSoundRecorder"],
        "bl_camera": ["Microsoft.WindowsCamera"],
        "bl_clock": ["Microsoft.WindowsAlarms"],
        "bl_calc": ["Microsoft.WindowsCalculator"],
        "bl_devhome": ["Microsoft.Windows.DevHome"],
        "bl_phonelink": ["Microsoft.YourPhone"],
        "bl_snip": ["Microsoft.ScreenSketch"],
        "bl_terminal": ["Microsoft.WindowsTerminal"],
        "bl_xbox": [
            "Microsoft.GamingApp", "Microsoft.XboxGamingOverlay",
            "Microsoft.XboxIdentityProvider", "Microsoft.XboxSpeechToTextOverlay",
            "Microsoft.Xbox.TCUI"
        ],
        "bl_paint": ["Microsoft.Paint"],
        "bl_store": ["Microsoft.WindowsStore", "Microsoft.StorePurchaseApp"],
        "bl_edge": ["Microsoft.MicrosoftEdge.Stable"],
        "bl_media": ["Microsoft.ZuneMusic"],
        "bl_photos": ["Microsoft.Windows.Photos"],
        "bl_notepad": ["Microsoft.WindowsNotepad"],
    }
    
    packages_to_remove = set()
    for bloat_id in bloat_list:
        packages = BLOAT_MAP.get(bloat_id, [])
        for pkg in packages:
            packages_to_remove.add(pkg)
            
    for pkg_name in packages_to_remove:
        ps_command = f"Get-AppProvisionedPackage -Online | Where-Object DisplayName -Like '*{pkg_name}*' | Remove-AppProvisionedPackage -Online -AllUsers"
        execute_command(f'PowerShell -Command "& {{{ps_command}}}"')

def create_scheduled_task(task_name, command, user="SYSTEM", run_level="HighestAvailable", trigger="OnLogon"):
    """Creates a simple scheduled task to run a command."""
    # Use schtasks.exe to create the task
    # This is simpler than XML for this purpose
    # /sc onlogon
    # /sc onstart
    
    if trigger == "OnLogon":
        trigger_cmd = "/sc ONLOGON"
    else: # OnStart
        trigger_cmd = "/sc ONSTART"

    schtasks_cmd = (
        f'schtasks /create /tn "{task_name}" /tr "{command}" '
        f'{trigger_cmd} /ru {user} '
    )
    
    if run_level == "HighestAvailable":
        schtasks_cmd += "/rl HIGHEST "
        
    schtasks_cmd += "/f" # Force create
    
    execute_command(schtasks_cmd)

def main():
    """Main entry point for Phase 3."""
    
    # Get path to self and config file
    exe_path = os.path.dirname(sys.executable)
        
    config_path = os.path.join(exe_path, "phase3.cfg")
    
    # 1. Check OOBE status
    if not check_oobe_status():
        sys.exit(1) # Not an error, just already done
        
    # 2. Check for config file
    if not os.path.exists(config_path):
        sys.exit(2)
        
    # 3. Load Config
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        sys.exit(2)
    
    # --- 4. Run Setup Tasks ---

    # Run windeploy to setup Windows
    execute_command(r"C:\Windows\System32\oobe\windeploy.exe")
    
    # Create User
    user_info = config.get("user_account")
    if user_info and user_info.get("username"):
        create_user(user_info["username"], user_info.get("password"))
        username = user_info["username"] # For scheduled tasks
    else:
        username = "SYSTEM" # Fallback for tasks
        
    # Remove Bloat
    bloat_list = config.get("bloat_remove", [])
    if bloat_list:
        remove_bloat(bloat_list)
        
    # Install Local Apps (if selected)
    software_ops = config.get("software_install", [])
    if "local_apps" in software_ops:
        local_apps_dir = r"C:\Apps"
        if os.path.exists(local_apps_dir) and any(os.scandir(local_apps_dir)):
            
            # Grant user permissions to the folder
            execute_command(f'icacls "{local_apps_dir}" /grant "{username}":(OI)(CI)F /T')
            
            # Create a batch file to run all installers
            command = 'PowerShell -WindowStyle Hidden -Command "& {Start-Process -FilePath \'cmd\' -ArgumentList \'/c schtasks/delete /tn InstallApps /f&for %%f in (C:\\Apps\\*) do start/wait %%f&del %%f&rd C:\\Apps\' -WindowStyle Hidden}'
            
            # Create task to run the batch file
            create_scheduled_task(
                "InstallApps",
                command,
                user=username,
                trigger="OnLogon"
            )

    # --- 5. Finalize Setup ---
    # Set OOBE keys to 0 (complete)
    set_registry_value("HKLM", r"SYSTEM\Setup", "OOBEInProgress", winreg.REG_DWORD, 0)
    set_registry_value("HKLM", r"SYSTEM\Setup", "SetupType", winreg.REG_DWORD, 0)
    set_registry_value("HKLM", r"SYSTEM\Setup", "SystemSetupInProgress", winreg.REG_DWORD, 0)
    
    # Clean up config file
    try:
        os.remove(config_path)
    except Exception as e:
        pass
        
    # Schedule self-destruct for this executable and log file
    del_self_cmd = f'cmd.exe /c del "{exe_path}\\phase3.exe"'
    create_scheduled_task(
        "DeletePhase3Script",
        del_self_cmd,
        user="SYSTEM",
        trigger="OnStart"
    )
    
    # Don't reboot here, the batch file logic just lets OOBE finish
    # and reboot at the end. We've set the keys, so Windows will proceed.
    # The original script does `shutdown -r -t 0` inside its generated
    # OOBE\setup.bat. We can add that here for consistency.
    execute_command("shutdown -r -t 0")

if __name__ == "__main__":
    main()
