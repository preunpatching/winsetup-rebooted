import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
from platform import system
import subprocess
import threading
import json
import shutil
import argparse # For command-line argument parsing

# --- Configuration & Constants ---

# Define the steps for the Phase 1 Wizard
# This is where you translate your batch file's logic into a structured wizard.
# 'Terminal' and 'Verifier' functions are defined below and linked here by name.
PHASE_1_STEPS = [
    {
        "Name": "Welcome",
        "Description": "Welcome to Microsoft Windows Setup.\nPress the Next button to continue.",
        "Type": "info", # A custom type just for showing info
        "Terminal": "welcome",
    },
    {
        "Name": "Source Drive",
        "Description": "Select your Windows installation source drive (e.g., 'D').",
        "Type": "string",
        "Id": "src_drive",
        "Terminal": "list_volumes",
        "Verifier": "verify_source_drive",
    },
    {
        "Name": "Image Index",
        "Description": "Select the Windows image index to install (e.g., '6').",
        "Type": "integer",
        "Id": "img_index",
        "Terminal": "list_image_indexes", # This will need src_drive from previous step
        "Verifier": "verify_image_index",
    },
    {
        "Name": "Target Drive",
        "Description": "Select the target drive number to install Windows on (e.g., '0').",
        "Type": "integer",
        "Id": "target_disk",
        "Terminal": "list_disks",
        "Verifier": "verify_target_disk",
    },
    {
        "Name": "User Account",
        "Description": "Specify the primary user account and an optional password.",
        "Type": "user_pass", # Custom type
        "Id": "user_account", # Will store as {"username": "...", "password": "..."}
        "Verifier": "verify_user_account",
    },
    {
        "Name": "Partitioning",
        "Description": "Select partitioning options.",
        "Type": "multichoice",
        "Id": "partition_options",
        "Choices": [
            {"Id": "no_msr", "Name": "Do NOT create Microsoft Reserved (MSR) partition"},
            {"Id": "no_wre", "Name": "Do NOT create Windows Recovery (WinRE) partition (not recommended)"},
        ]
    },
    {
        "Name": "Boot Mode",
        "Description": "Select the boot mode for the target system. This must match your current boot mode.",
        "Type": "singlechoice",
        "Id": "bios_mode",
        "Choices": [
            {"Id": "uefi", "Name": "UEFI (default)"},
            {"Id": "bios", "Name": "BIOS / UEFI-CSM"},
        ]
    },
    {
        "Name": "Bloat Removal",
        "Description": "Select which built-in apps to remove (Advanced).",
        "Type": "multichoice",
        "Id": "bloat_remove",
        "Choices": [
            {"Id": "bl_common", "Name": "Common Bloat"},
            {"Id": "bl_soundrec", "Name": "Sound Recorder"},
            {"Id": "bl_camera", "Name": "Camera"},
            {"Id": "bl_clock", "Name": "Alarms & Clock"},
            {"Id": "bl_calc", "Name": "Calculator"},
            {"Id": "bl_devhome", "Name": "Dev Home"},
            {"Id": "bl_phonelink", "Name": "Phone Link"},
            {"Id": "bl_snip", "Name": "Snipping Tool"},
            {"Id": "bl_terminal", "Name": "Terminal"},
            {"Id": "bl_xbox", "Name": "Xbox & Gaming Features"},
            {"Id": "bl_paint", "Name": "Paint"},
            {"Id": "bl_store", "Name": "Microsoft Store"},
            {"Id": "bl_edge", "Name": "Edge (UWP Stub)"},
            {"Id": "bl_media", "Name": "Media Player"},
            {"Id": "bl_photos", "Name": "Photos"},
            {"Id": "bl_notepad", "Name": "Notepad"},
        ]
    },
    {
        "Name": "Additional Software",
        "Description": "Select additional software to install.",
        "Type": "multichoice",
        "Id": "software_install",
        "Choices": [
            {"Id": "local_apps", "Name": "Install apps from 'Apps' folder"},
            {"Id": "local_drivers", "Name": "Install drivers from 'Drivers' folder"},
        ]
    },
    {
        "Name": "Confirmation",
        "Description": "Please review your choices below.",
        "Type": "summary", # Custom type
        "Id": "summary",
    },
]
PHASE_1_STEP_NAMES = {"src_drive": "Source Drive", "img_index": "Image Index", "target_disk": "Target Drive", "user_account": "User Account", "partition_options": "Partitioning", "bios_mode": "Boot mode", "bloat_remove": "Bloat Removal", "software_install": "Additional Software"}

# --- Helper Functions (Low-Level) ---

def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This is CRITICAL for finding 'phase3_setup.exe' when bundled.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Not in a PyInstaller bundle, use relative path
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def run_command_in_thread(command, terminal_widget, on_completion=None):
    """Runs a command in a separate thread to avoid blocking the GUI."""
    def target():
        terminal_widget.config(state=tk.NORMAL)
        
        try:
            # Use Popen to capture output in real-time
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW # Hide console window
            )

            # Read line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    terminal_widget.insert(tk.END, line)
                    terminal_widget.see(tk.END)
            
            process.stdout.close()
            process.wait()
            
        except Exception as e:
            terminal_widget.insert(tk.END, f"Something went wrong: {e}")
        
        finally:
            terminal_widget.see(tk.END)
            terminal_widget.config(state=tk.DISABLED)
            if on_completion:
                on_completion() # Call callback

    # Start the thread
    threading.Thread(target=target, daemon=True).start()

def write_to_file(filepath, content, append=False):
    """
    Writes content to a file.
    Returns True on success, False on error.
    """
    mode = 'a' if append else 'w'
    try:
        with open(filepath, mode, encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        self.app.log_to_terminal(f"ERROR writing to file {filepath}: {e}")
        return False

# --- Terminal & Verifier Functions (Phase 1) ---

class StepHelpers:
    """
    Container for Terminal and Verifier functions.
    'app' (the SetupGUI instance) is passed during init.
    """
    def __init__(self, app):
        self.app = app
        self.wim_info_cache = "" # Cache for DISM output
        self.disk_info_cache = "" # Cache for Diskpart output

    def get_function(self, name):
        """Utility to get a helper function by its name string."""
        return getattr(self, name, self.default_helper)

    def default_helper(self, *args, **kwargs):
        """Fallback for missing helpers."""
        log_msg = f"WARN: Helper function '{args[0] if args else ''}' not found."
        if "terminal_widget" in kwargs:
            kwargs["terminal_widget"].config(state=tk.NORMAL)
            kwargs["terminal_widget"].insert(tk.END, f"{log_msg}\n")
            kwargs["terminal_widget"].config(state=tk.DISABLED)
        return None # Verifiers return None for success

    # --- Synchronous Helpers (for Unattended Mode) ---

    def load_wim_info_sync(self, src_drive):
        """Synchronously runs DISM and populates cache."""
        if not src_drive:
            self.app.log_to_terminal("FATAL: Source drive is not set.")
            return False
        
        wim_path = ""
        if os.path.exists(f"{src_drive}:\\sources\\install.wim"):
            wim_path = f"{src_drive}:\\sources\\install.wim"
        elif os.path.exists(f"{src_drive}:\\sources\\install.esd"):
            wim_path = f"{src_drive}:\\sources\\install.esd"
        else:
            self.app.log_to_terminal(f"FATAL: Could not find install.wim or install.esd on {src_drive}:\\sources.\n")
            return False
            
        self.app.setup_data["wim_path"] = wim_path
        command = f"dism /get-wiminfo /wimfile:\"{wim_path}\""
        
        self.wim_info_cache = self.app.run_command_sync(command)
        return True

    def load_disk_info_sync(self):
        """Synchronously runs Diskpart and populates cache."""
        script = "lis dis"
        if not write_to_file("X:\\temp.txt", script):
            self.app.log_to_terminal("FATAL: Failed to write diskpart script.")
            return False
            
        command = "diskpart /s X:\\temp.txt"
        self.disk_info_cache = self.app.run_command_sync(command)
        
        return True

    # --- Terminal Functions (Async for GUI) ---

    def welcome(self, terminal_widget):
        run_command_in_thread("echo Windows Setup Rebooted v1.0.0 by preunpatching (https://github.com/preunpatching/winsetup-rebooted)", terminal_widget)

    def list_volumes(self, terminal_widget):
        """Runs 'diskpart lis vol' and outputs to terminal."""
        script = "lis vol"
        write_to_file("X:\\temp.txt", script)
        run_command_in_thread("diskpart /s X:\\temp.txt", terminal_widget)

    def list_disks(self, terminal_widget):
        """Runs 'diskpart lis dis' and outputs to terminal."""
        script = "lis dis"
        write_to_file("X:\\temp.txt", script)
        def target():
            terminal_widget.config(state=tk.NORMAL)
            terminal_widget.see(tk.END)
            self.disk_info_cache = "" # Clear cache
            try:
                process = subprocess.Popen(
                    "diskpart /s X:\\temp.txt", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.disk_info_cache += line # Add to cache
                        terminal_widget.insert(tk.END, line)
                        terminal_widget.see(tk.END)
                process.stdout.close()
                process.wait()
            except Exception as e:
                terminal_widget.insert(tk.END, f"Something went wrong: {e}")
            finally:
                terminal_widget.see(tk.END)
                terminal_widget.config(state=tk.DISABLED)
        
        threading.Thread(target=target, daemon=True).start()

    def list_image_indexes(self, terminal_widget):
        """Runs 'dism /get-wiminfo' based on selected source drive."""
        src_drive = self.app.setup_data.get("src_drive", {})

        # Find install.wim or install.esd
        wim_path = ""
        if os.path.exists(f"{src_drive}:\\sources\\install.wim"):
            wim_path = f"{src_drive}:\\sources\\install.wim"
        elif os.path.exists(f"{src_drive}:\\sources\\install.esd"):
            wim_path = f"{src_drive}:\\sources\\install.esd"
        
        # Cache the WIM path for the verifier
        self.app.setup_data["wim_path"] = wim_path
        
        def target():
            terminal_widget.config(state=tk.NORMAL)
            terminal_widget.see(tk.END)
            self.wim_info_cache = "" # Clear cache
            try:
                process = subprocess.Popen(
                    f"dism /get-wiminfo /wimfile:\"{wim_path}\"", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.wim_info_cache += line # Add to cache
                        terminal_widget.insert(tk.END, line)
                        terminal_widget.see(tk.END)
                process.stdout.close()
                process.wait()
            except Exception as e:
                terminal_widget.insert(tk.END, f"Something went wrong: {e}")
            finally:
                terminal_widget.see(tk.END)
                terminal_widget.config(state=tk.DISABLED)
        
        threading.Thread(target=target, daemon=True).start()

    # --- Verifier Functions ---
    
    def verify_source_drive(self, value):
        """Checks if the selected source drive is valid."""
        if not value:
            return "Source drive cannot be empty."
        drive = value.strip().upper()
        if not os.path.exists(f"{drive}:\\sources"):
            return f"Path '{drive}:\\sources' not found."
        if not (os.path.exists(f"{drive}:\\sources\\install.wim") or os.path.exists(f"{drive}:\\sources\\install.esd")):
            return f"No 'install.wim' or 'install.esd' found in '{drive}:\\sources'."
        return None # Success

    def verify_image_index(self, value):
        """Checks if the index exists in the cached DISM output."""
        if not value:
            return "Image index cannot be empty."
        try:
            index_num = int(value)
            if index_num <= 0:
                return "Index must be a positive number."
            
            if not self.wim_info_cache:
                # This can happen if user clicks Next before command finishes
                return "WIM info is still loading. Please wait."
            
            # Check if "Index : [value]" exists in the cached output
            if f"Index : {index_num}" not in self.wim_info_cache:
                return f"Index {index_num} not found in the WIM file."
            
        except ValueError:
            return "Index must be a valid number."
        except Exception as e:
            return f"Verification error: {e}"
        return None # Success

    def verify_target_disk(self, value):
        """Checks if the target disk number exists in the cached DiskPart output."""
        if not value:
            return "Target disk cannot be empty."
        try:
            disk_num = int(value)
            if disk_num < 0:
                return "Disk number must be 0 or greater."
            if not self.disk_info_cache:
                return "Disk info is still loading. Please wait."
            
            # Search for "Disk [num]" at the start of a line
            # This is more robust than `in self.disk_info_cache`
            found = False
            for line in self.disk_info_cache.splitlines():
                if line.strip().startswith(f"Disk {disk_num}"):
                    found = True
                    break
            if not found:
                 return f"Disk {disk_num} not found."
        except ValueError:
            return "Disk number must be a valid integer."
        return None # Success

    def verify_user_account(self, value):
        """Value is a dict {"username": "...", "password": "..."}"""
        if not value.get("username"):
            return "Username cannot be empty."
        return None # Success

# --- Main Application GUI ---

class SetupGUI(tk.Tk):
    def __init__(self, args):
        self.terminated = False
        self.args = args # Store parsed arguments
        self.helper = StepHelpers(self)
        self.unattended_mode = bool(self.args.unattend)
        self.generate_mode = bool(self.args.generate)

        if self.unattended_mode and self.generate_mode:
            messagebox.showerror(
                "Setup Error",
                "Specifying unattended and generate modes together is not allowed."
            )
            self.terminated = True
            return

        # Check if running under Windows
        if not system() == "Windows" and not self.args.test:
            messagebox.showerror(
                "Environment Error",
                "Setup will only run under Windows systems.\n"
                "Running under any other system is unsupported.\n"
                "To bypass for testing the GUI, use the --test flag."
            )
            self.terminated = True
            return

        # Check for Windows PE
        if not os.path.exists("X:\\Windows\\System32\\wpeutil.exe") and not self.args.test:
            messagebox.showerror(
                "Environment Error",
                "Setup will only run under Windows PE.\n"
                "Running under the full Windows OS is unsupported.\n"
                "To bypass for testing the GUI, use the --test flag."
            )
            self.terminated = True
            return

        super().__init__()
        
        # --- App State ---
        self.current_step = 0
        self.setup_data = {} # To store all collected choices
        self.step_widgets = {} # To store widgets for data retrieval

        # --- Styles ---
        style = ttk.Style(self)
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 16))
        style.configure("Description.TLabel", font=("Segoe UI", 11), wraplength=750)
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TRadiobutton", font=("Segoe UI", 10))
        style.configure("TCheckbutton", font=("Segoe UI", 10))

        # --- Main Layout ---
        self.title("Windows Setup Rebooted")
        if self.unattended_mode:
            self.setup_unattended_gui()
            # Start verification in a thread to allow GUI to render
            threading.Thread(target=self.run_unattended_verification, daemon=True).start()
        else:
            self.setup_interactive_gui()
            # Start Wizard
            self.show_step()

    def setup_unattended_gui(self):
        """Configures the GUI for unattended mode (log only)."""
        self.geometry("800x600")
        self.minsize(640, 480)
            
        # Root grid configuration
        self.grid_rowconfigure(0, weight=3) # Step frame
        self.grid_rowconfigure(1, weight=1) # Terminal
        self.grid_rowconfigure(2, weight=0) # Navigation
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Step Frame (where wizard steps appear)
        self.step_frame = ttk.Frame(self, padding="10 10 10 0") # No bottom padding
        self.step_frame.grid(row=0, column=0, sticky="nsew")
        self.step_frame.grid_rowconfigure(2, weight=1) # Row 2 (scroll area) will expand
        self.step_frame.grid_columnconfigure(0, weight=1)

        # 2. Terminal Frame (for command output)
        terminal_frame = ttk.LabelFrame(self, text="Terminal Output")
        terminal_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        terminal_frame.grid_rowconfigure(0, weight=1)
        terminal_frame.grid_columnconfigure(0, weight=1)
        
        self.terminal = scrolledtext.ScrolledText(
            terminal_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#2b2b2b",
            fg="#cccccc",
            state=tk.DISABLED,
            relief=tk.FLAT
        )
        self.terminal.grid(row=0, column=0, sticky="nsew")

        # 3. Navigation Frame (for buttons)
        nav_frame = ttk.Frame(self, padding="10 5 10 5")
        nav_frame.grid(row=2, column=0, sticky="ew")
        nav_frame.grid_columnconfigure(0, weight=1) # Left button
        nav_frame.grid_columnconfigure(1, weight=1) # Right button
        
        self.prev_button = ttk.Button(
            nav_frame,
            text="< Previous",
            command=None,
            state=tk.DISABLED
        )
        self.prev_button.grid(row=0, column=0, sticky="w")
        
        self.next_button = ttk.Button(
            nav_frame,
            text="Next >",
            command=None,
            state=tk.DISABLED
        )
        self.next_button.grid(row=0, column=1, sticky="e")

        # 1. Title
        title_label = ttk.Label(self.step_frame, text="Phase 1: Verifying options", style="Header.TLabel", justify=tk.CENTER, anchor="center")
        title_label.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        
        # 2. Description
        desc_label = ttk.Label(self.step_frame, text="The options are being verified. Please wait.", style="Description.TLabel", justify=tk.CENTER, anchor="center")
        desc_label.grid(row=1, column=0, pady=(0, 20), sticky="new")

    def setup_interactive_gui(self):
        """Configures the GUI for the interactive wizard."""
        self.geometry("800x600")
        self.minsize(640, 480)
            
        # Root grid configuration
        self.grid_rowconfigure(0, weight=3) # Step frame
        self.grid_rowconfigure(1, weight=1) # Terminal
        self.grid_rowconfigure(2, weight=0) # Navigation
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Step Frame (where wizard steps appear)
        self.step_frame = ttk.Frame(self, padding="10 10 10 0") # No bottom padding
        self.step_frame.grid(row=0, column=0, sticky="nsew")
        self.step_frame.grid_rowconfigure(2, weight=1) # Row 2 (scroll area) will expand
        self.step_frame.grid_columnconfigure(0, weight=1)

        # 2. Terminal Frame (for command output)
        terminal_frame = ttk.LabelFrame(self, text="Terminal Output")
        terminal_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        terminal_frame.grid_rowconfigure(0, weight=1)
        terminal_frame.grid_columnconfigure(0, weight=1)
        
        self.terminal = scrolledtext.ScrolledText(
            terminal_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#2b2b2b",
            fg="#cccccc",
            state=tk.DISABLED,
            relief=tk.FLAT
        )
        self.terminal.grid(row=0, column=0, sticky="nsew")

        # 3. Navigation Frame (for buttons)
        nav_frame = ttk.Frame(self, padding="10 5 10 5")
        nav_frame.grid(row=2, column=0, sticky="ew")
        nav_frame.grid_columnconfigure(0, weight=1) # Left button
        nav_frame.grid_columnconfigure(1, weight=1) # Right button
        
        self.prev_button = ttk.Button(
            nav_frame,
            text="< Previous",
            command=self.prev_step
        )
        self.prev_button.grid(row=0, column=0, sticky="w")
        
        self.next_button = ttk.Button(
            nav_frame,
            text="Next >",
            command=self.next_step
        )
        self.next_button.grid(row=0, column=1, sticky="e")

    def clear_step_frame(self):
        """Destroys all widgets in the step frame."""
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")
        for widget in self.step_frame.winfo_children():
            widget.destroy()
        self.step_widgets = {} # Clear widget cache

    def generate_summary_text(self):
        """Creates a user-friendly summary of all selected options."""
        text = ""

        # Build a map of all choice names from PHASE_1_STEPS
        choice_name_map = {}
        for step in PHASE_1_STEPS:
            for choice in step.get("Choices", []):
                choice_name_map[choice["Id"]] = choice["Name"]

        # Iterate through steps in order to display summary
        for step in PHASE_1_STEPS:
            step_id = step.get("Id")
            if not step_id or step_id == "summary":
                continue
                
            data = self.setup_data.get(step_id)
            if not data:
                continue # Skip if no data (e.g., info step)

            name = PHASE_1_STEP_NAMES.get(step_id)
            
            text += f"{name}: "
            
            if step_id == "user_account":
                text += f"Username: '{data.get('username')}', Password: {'(set)' if data.get('password') else '(not set)'}\n"
            elif isinstance(data, str):
                # For single choice, try to map ID to friendly name
                text += f"{choice_name_map.get(data, data)}\n"
            elif isinstance(data, list): # Multichoice
                if not data:
                    text += "(none selected)\n"
                else:
                    # Map all choice IDs to their friendly names
                    choice_strings = [choice_name_map.get(v, v) for v in data]
                    text += f"\n    - " + "\n    - ".join(choice_strings) + "\n"
            elif data is None:
                text += "(not set)\n"
            else:
                # Fallback for integers or other types
                text += f"{str(data)}\n"
        
        return text

    def show_step(self):
        """Renders the widgets for the current step."""
        self.clear_step_frame()
        
        if self.current_step >= len(PHASE_1_STEPS):
            self.start_phase_2() # Should be triggered by button, but as a fallback
            return
            
        step = PHASE_1_STEPS[self.current_step]
        name = step.get("Name", "Unnamed Step")
        desc = step.get("Description", "")
        step_type = step.get("Type", "info")
        step_id = step.get("Id", name) # Use Name as fallback ID
        
        # Store variables for this step's widgets
        self.step_widgets['vars'] = {}
        
        # --- Create Widgets ---
        
        # 1. Title
        title_label = ttk.Label(self.step_frame, text=name, style="Header.TLabel", justify=tk.CENTER, anchor="center")
        title_label.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        
        # 2. Description
        desc_label = ttk.Label(self.step_frame, text=desc, style="Description.TLabel", justify=tk.LEFT)
        desc_label.grid(row=1, column=0, pady=(0, 20), sticky="new")

        # 3. Step-specific widgets
        
        # This is the parent for the widgets.
        # It will either be a simple frame (for summary) or a scrollable frame (for others)
        widget_parent_frame = None
        
        if step_type == "summary":
            content_frame = ttk.Frame(self.step_frame)
            content_frame.grid(row=2, column=0, sticky="nsew")
            content_frame.grid_rowconfigure(0, weight=1)
            content_frame.grid_columnconfigure(0, weight=1)
            
            summary_text = scrolledtext.ScrolledText(
                content_frame, wrap=tk.WORD, width=80, height=10,
                font=("Consolas", 10), relief=tk.FLAT, bg=self.cget('bg'),
                padx=10, pady=10
            )
            summary_text.grid(row=0, column=0, sticky="nsew")
            
            try:
                # Use the new summary generator
                summary = self.generate_summary_text()
                summary_text.insert(tk.END, summary)
            except Exception as e:
                summary_text.insert(tk.END, f"Error generating summary: {e}")
            
            summary_text.config(state=tk.DISABLED)
            widget_parent_frame = content_frame

        else:
            # --- All other steps get the NEW Scrollable Area ---
            
            # This outer_frame holds the canvas and scrollbar
            outer_frame = ttk.Frame(self.step_frame)
            outer_frame.grid(row=2, column=0, sticky="nsew")
            outer_frame.grid_rowconfigure(0, weight=1)
            outer_frame.grid_columnconfigure(0, weight=1)
            
            canvas = tk.Canvas(outer_frame, borderwidth=0, highlightthickness=0)
            scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
            
            # This is the frame that will hold the widgets and be scrolled
            scrollable_widget_frame = ttk.Frame(canvas, style="Inner.TFrame")
            widget_parent_frame = scrollable_widget_frame # This is where widgets will be built
            
            # Bind inner frame's configure event to update canvas scroll region
            scrollable_widget_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(
                    scrollregion=canvas.bbox("all")
                )
            )

            # Create the window inside the canvas
            canvas.create_window((0, 0), window=scrollable_widget_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")

            # --- Bind mouse wheel scrolling ---
            def on_mousewheel(event):
                # Handle cross-platform mouse wheel delta
                delta = 0
                if event.num == 4: # Linux scroll up
                    delta = -1
                elif event.num == 5: # Linux scroll down
                    delta = 1
                elif event.delta: # Windows/macOS
                    delta = -1 * (event.delta / 120)
                
                canvas.yview_scroll(int(delta), "units")

            # Bind all relevant widgets to mouse wheel
            self.bind_all("<MouseWheel>", on_mousewheel)
            self.bind_all("<Button-4>", on_mousewheel) # Linux
            self.bind_all("<Button-5>", on_mousewheel) # Linux
            
            # --- Populate the scrollable_widget_frame ---
            
            if step_type == "string" or step_type == "integer":
                var = tk.StringVar()
                prev_val = self.setup_data.get(step_id, "")
                var.set(prev_val)
                
                entry = ttk.Entry(scrollable_widget_frame, textvariable=var, width=60)
                entry.pack(pady=5, padx=10)
                self.step_widgets['vars'][step_id] = var
                
            elif step_type == "user_pass":
                user_frame = ttk.Frame(scrollable_widget_frame, style="Inner.TFrame")
                user_frame.pack(pady=5, padx=10)
                user_frame.grid_columnconfigure(1, weight=1)
                
                ttk.Label(user_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
                user_var = tk.StringVar()
                user_entry = ttk.Entry(user_frame, textvariable=user_var, width=40)
                user_entry.grid(row=0, column=1, sticky="ew", pady=2)
                
                ttk.Label(user_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
                pass_var = tk.StringVar()
                pass_entry = ttk.Entry(user_frame, textvariable=pass_var, width=40, show="*")
                pass_entry.grid(row=1, column=1, sticky="ew", pady=2)
                
                prev_val = self.setup_data.get(step_id, {})
                user_var.set(prev_val.get("username", ""))
                pass_var.set(prev_val.get("password", ""))
                
                self.step_widgets['vars'][step_id] = {"username": user_var, "password": pass_var}
                
            elif step_type == "singlechoice":
                var = tk.StringVar()
                self.step_widgets['vars'][step_id] = var
                
                prev_val = self.setup_data.get(step_id, {})
                var.set(prev_val)
                
                for choice in step.get("Choices", []):
                    rb = ttk.Radiobutton(
                        scrollable_widget_frame,
                        text=choice["Name"],
                        value=choice["Id"],
                        variable=var
                    )
                    rb.pack(anchor="w", padx=20, pady=2)

            elif step_type == "multichoice":
                vars_dict = {}
                prev_val_list = self.setup_data.get(step_id, {})
                
                for choice in step.get("Choices", []):
                    var = tk.BooleanVar()
                    if choice["Id"] in prev_val_list:
                        var.set(True)
                    
                    cb = ttk.Checkbutton(
                        scrollable_widget_frame,
                        text=choice["Name"],
                        variable=var
                    )
                    cb.pack(anchor="w", padx=20, pady=2)
                    vars_dict[choice["Id"]] = var
                self.step_widgets['vars'][step_id] = vars_dict
            
            elif step_type == "info":
                # 'info' steps just show text, no widgets to add here.
                pass

        # 4. Run Terminal function if specified
        try:
            if step.get("Terminal") and not self.args.test:
               func = self.helper.get_function(step["Terminal"])
               if func: func(terminal_widget=self.terminal)
        except Exception as e:
            self.log_to_terminal(f"Something went wrong: {e}")

        # 5. Update Navigation Buttons
        self.prev_button.config(state=tk.NORMAL if self.current_step > 0 else tk.DISABLED)
        
        if self.current_step == len(PHASE_1_STEPS) - 1: # Last step
            if self.generate_mode:
                self.next_button.config(text="Generate Script >", command=self.confirm_and_start)
            else:
                self.next_button.config(text="Start Setup >", command=self.confirm_and_start)
        else:
            self.next_button.config(text="Next >", command=self.next_step)

    def save_step_data(self):
        """Saves the data from the current step's widgets into self.setup_data."""
        step = PHASE_1_STEPS[self.current_step]
        step_id = step.get("Id")
        step_type = step.get("Type")
        
        if not step_id or not self.step_widgets.get('vars'):
            return True # No data to save
            
        data = None
        vars = self.step_widgets['vars'].get(step_id)

        try:
            if step_type == "string" or step_type == "integer" or step_type == "singlechoice":
                data = vars.get()
                if step_type == "integer":
                    if not data: # Allow 0 but not empty string
                         messagebox.showwarning("Invalid Input", "Input must not be empty.")
                         return False
                    try:
                        int(data)
                    except ValueError:
                        messagebox.showwarning("Invalid Input", "Input must be a valid integer.")
                        return False # Verification failed
                elif not data:
                    messagebox.showwarning("Invalid Input", "Input must not be empty.")
                    return False # Verification failed
            
            elif step_type == "user_pass":
                data = {
                    "username": vars["username"].get(),
                    "password": vars["password"].get()
                }
                if not data["username"]:
                    messagebox.showwarning("Invalid Input", "Username cannot be empty.")
                    return False # Verification failed
                
            elif step_type == "multichoice":
                data = [choice_id for choice_id, var in vars.items() if var.get() is True]
            
            else:
                return True # No data to save for this type
                
            # Run verifier if it exists
            if step.get("Verifier") and not self.args.test:
                func = self.helper.get_function(step["Verifier"])
                if func:
                    error_msg = func(data)
                    if error_msg:
                        messagebox.showwarning("Invalid Input", error_msg)
                        return False # Verification failed
            
            # Save data
            self.setup_data[step_id] = data
            return True # Success
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save data for this step: {e}")
            return False

    def next_step(self):
        """Saves data, verifies, and moves to the next step."""
        if not self.save_step_data():
            return # Don't advance if save/verify failed
            
        if self.current_step < len(PHASE_1_STEPS) - 1:
            self.current_step += 1
            self.show_step()

    def prev_step(self):
        """Moves to the previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step()

    def confirm_and_start(self):
        """Shows final confirmation dialog before starting Phase 2."""
        if not self.save_step_data():
            return # Final save failed
            
        if self.generate_mode:
            self.start_phase_2()
        else:
            if messagebox.askyesno(
                "Final Confirmation",
                "You are about to start the Windows installation.\n"
                "ALL DATA on the target disk will be permanently erased.\n\n"
                "Are you absolutely sure you want to continue?",
                icon='warning'
            ):
                self.start_phase_2()

    def start_phase_2(self):
        """Disables UI and hands off to the main setup logic function."""
        if self.generate_mode:
            # Write the config
            write_to_file(self.args.generate, json.dumps(self.setup_data))
            messagebox.showinfo("Config Generated", f"Configuration file '{self.args.generate}' has been generated.")
            self.destroy()
            return

        # Clear interactive frame or configure unattended frame
        self.clear_step_frame() 
        title_label = ttk.Label(self.step_frame, text="Phase 2: Installing Windows", style="Header.TLabel", anchor="center")
        title_label.grid(row=0, column=0, pady=(10, 10), sticky="ew")
            
        desc_label = ttk.Label(
            self.step_frame, 
            text="Installation is in progress. Please wait.\nDo NOT close this window.", 
            style="Description.TLabel", 
            justify=tk.CENTER,
            anchor="center"
        )
        desc_label.grid(row=1, column=0, pady=(0, 20), sticky="new")
        self.terminal.config(state=tk.NORMAL)
        self.terminal.delete('1.0', tk.END)
        self.terminal.config(state=tk.DISABLED)
            
        # Disable nav buttons
        self.prev_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.DISABLED)

        # Start the actual setup process in a new thread
        if self.args.test:
            self.log_to_terminal("TEST MODE: Phase 2 will not run.")
        else:
            threading.Thread(
                target=system_setup,
                args=(self.setup_data, self.log_to_terminal), # Pass log function
                daemon=True
            ).start()

    # --- Unattended Mode Methods ---

    def log_to_terminal(self, message):
        """Thread-safe method to log to the terminal widget."""
        if not hasattr(self, 'terminal'): return
        try:
            self.terminal.config(state=tk.NORMAL)
            self.terminal.insert(tk.END, f"{message}\n")
            self.terminal.see(tk.END)
            self.terminal.config(state=tk.DISABLED)
        except tk.TclError:
            pass # App may be closing

    def run_command_sync(self, command):
        """Runs a command synchronously and returns its stdout."""
        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if process.stderr:
                self.log_to_terminal(f"STDERR: {process.stderr}")
            return process.stdout
        except Exception as e:
            self.log_to_terminal(f"ERROR: {e}")
            return f"Error: {e}"

    def verify_all_steps_sync(self):
        """Runs all verifiers in sequence for unattended mode."""
        for step in PHASE_1_STEPS:
            step_id = step.get("Id")
            if not step_id or step_id == "summary":
                continue
            
            self.log_to_terminal(f"Verifying: {step.get('Name')}")
            
            data_entry = self.setup_data.get(step_id)
            if data_entry is None and step.get("Type") not in ["info"]:
                # Check if it's a non-required, non-data step
                if step.get("Verifier"):
                     messagebox.showerror("Invalid Input", f"Missing input '{step_id}'.")
                     return False
                continue # Skip steps not in JSON (e.g., partitioning if default is ok)

            # Some steps might not be in the JSON (like multichoice)
            # but have a verifier. We assume the JSON is the source of truth.
            if data_entry is None:
                continue

            # We need to populate caches *before* running verifiers.
            try:
                if step_id == "img_index":
                    src_drive_val = self.setup_data.get("src_drive", {})
                    if not self.helper.load_wim_info_sync(src_drive_val):
                        messagebox.showerror("Verification Error", "Failed to load WIM info for verification.")
                        return False
                elif step_id == "target_disk":
                    if not self.helper.load_disk_info_sync():
                        messagebox.showerror("Verification Error", "Failed to load disk info for verification.")
                        return False
            except Exception as e:
                 messagebox.showerror("Verification Error", f"Something went wrong:\n{e}")
                 return False

            # Now run the verifier
            if step.get("Verifier"):
                func = self.helper.get_function(step["Verifier"])
                error_msg = func(data_entry)
                if error_msg:
                    messagebox.showerror("Invalid Input", f"{step.get('Name')}: {error_msg}")
                    return False
                    
        return True # All steps passed

    def run_unattended_verification(self):
        """Main logic thread for unattended mode."""
        filepath = self.args.unattend
        self.log_to_terminal(f"Loading config from {filepath}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            # We must merge this with the step names from PHASE_1_STEPS
            # The loaded JSON is *just* the data, not the friendly names
            
            loaded_data = config_data
            
            # Re-structure loaded data to match self.setup_data format
            self.setup_data = {}
            for step in PHASE_1_STEPS:
                step_id = step.get("Id")
                if step_id in loaded_data:
                    self.setup_data[step_id] = loaded_data[step_id]
            
            # Manually add wim_path from src_drive (will be verified)
            src_drive = loaded_data.get("src_drive")
            if src_drive:
                 wim_path = ""
                 if os.path.exists(f"{src_drive}:\\sources\\install.wim"):
                     wim_path = f"{src_drive}:\\sources\\install.wim"
                 elif os.path.exists(f"{src_drive}:\\sources\\install.esd"):
                     wim_path = f"{src_drive}:\\sources\\install.esd"
                 
                 if wim_path:
                      self.setup_data["wim_path"] = wim_path

        except Exception as e:
            messagebox.showerror("Verification Error", f"Failed to load config file:\n{e}")
            self.destroy()
            return

        # Verification Loop
        if self.args.test:
            self.log_to_terminal("TEST MODE: Verification will not run.")
        else:
            try:
                verified = self.verify_all_steps_sync()
                if not verified:
                    self.destroy()
                    return
            except Exception as e:
                messagebox.showerror("Fatal Error", f"Something went wrong:\n{e}")
                self.destroy()
                return

        # Proceed to Phase 2
        self.start_phase_2()

# --- Phase 2: System Setup Logic ---

def system_setup(data, log_func):
    """
    Main function for Phase 2. Runs Diskpart, DISM, etc.
    This runs in a separate thread.
    
    'data' is the self.setup_data dictionary.
    'log_func' is the app.log_to_terminal method.
    """
    
    def run_sync(command):
        """
        Runs a command synchronously and logs its output.
        Returns True on success (code 0), False otherwise.
        """
        try:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in iter(process.stdout.readline, ''):
                if line:
                    log_func(f"  {line.strip()}")
            
            process.stdout.close()
            return_code = process.wait()
            
            return True
            
        except Exception as e:
            log_func(f"FATAL: {e}")
            return False

    try:
        # --- 1. Extract Data ---
        log_func("Extracting setup choices...")
        target_disk = data.get("target_disk", {})
        wim_path = data.get("wim_path", {})
        img_index = data.get("img_index", {})
        bios_mode = data.get("bios_mode", {})
        part_ops = data.get("partition_options", {})
        
        no_msr = "no_msr" in part_ops
        no_wre = "no_wre" in part_ops

        # --- 2. Partition Disk ---
        log_func("Generating diskpart script...")
        script = f"sel dis {target_disk}\n"
        script += "cle\n"
        
        if bios_mode == "uefi":
            script += "con gpt\n"
            # EFI partition
            script += "cre par efi size=512\n"
            script += "for fs=fat32 quick\n"
            script += "ass letter=W\n" # System partition
            # MSR partition
            if not no_msr:
                script += "cre par msr size=16\n"
            # Windows partition
            script += "cre par pri\n"
            if not no_wre:
                script += "shr minimum=700\n" # Shrink for WinRE
            script += "for fs=ntfs quick\n"
            script += "ass letter=Z\n" # Windows partition
            # WinRE partition
            if not no_wre:
                script += "cre par pri\n"
                script += "for fs=ntfs quick\n"
                script += "ass letter=R\n" # Recovery partition
                script += "set id=\"de94bba4-06d1-4d40-a16a-bfd50179d6ac\"\n"
                script += "gpt attributes=0x8000000000000001\n"
        else: # bios_mode == "bios"
            script += "con mbr\n"
            # Windows partition
            script += "cre par pri\n"
            if not no_wre:
                script += "shr minimum=700\n"
            script += "for fs=ntfs quick\n"
            script += "ass letter=Z\n"
            script += "act\n" # Set active
            # WinRE partition
            if not no_wre:
                script += "cre par pri\n"
                script += "for fs=ntfs quick\n"
                script += "ass letter=R\n"
                script += "set id=27\n"
        
        write_to_file(r"X:\temp.txt", script)
        run_sync("diskpart /s X:\\temp.txt")

        # --- 3. Apply Image ---
        log_func("Applying Windows image...")
        dism_cmd = f"dism /apply-image /imagefile:\"{wim_path}\" /index:{img_index} /applydir:Z:\\"
        if not run_sync(dism_cmd):
            log_func("FATAL: Could not apply image.")
            log_func("FATAL: Setup failed.")
            return
            
        # --- 4. Install Drivers (if selected) ---
        if "local_drivers" in data.get("software_install", {}):
            driver_dir = "Drivers" # Assuming relative to script
            if os.path.exists(driver_dir) and any(os.scandir(driver_dir)):
                log_func("Installing drivers from 'Drivers' folder...")
                driver_cmd = f"dism /image:Z:\\ /add-driver /driver:\"{driver_dir}\" /recurse /forceunsigned"
                if not run_sync(driver_cmd):
                    log_func("ERROR: Driver installation failed.")
            else:
                log_func("WARN: Folder not found or is empty.")

        # --- 5. Write Boot Files ---
        log_func("Writing boot files...")
        if bios_mode == "uefi":
            boot_cmd = "bcdboot Z:\\Windows /s W:"
        else: # uefi
            boot_cmd = "bcdboot Z:\\Windows /s Z:"
        run_sync(boot_cmd)

        # --- 6. Prepare Phase 3 ---
        log_func("Preparing Phase 3...")
        
        # Create OOBE directory
        oobe_dir = r"Z:\Windows\System32\OOBE"
        if not os.path.exists(oobe_dir):
            os.makedirs(oobe_dir)
        
        # Copy embedded 'phase3.exe'
        try:
            phase3_exe_source_path = get_resource_path("phase3.exe")
            phase3_exe_dest_path = os.path.join(oobe_dir, "phase3.exe")
            log_func(f"Copying '{phase3_exe_source_path}' to '{phase3_exe_dest_path}'")
            shutil.copy2(phase3_exe_source_path, phase3_exe_dest_path)
        except Exception as e:
            log_func(f"FATAL: {e}")
            log_func("FATAL: Setup failed.")
            return
            
        # Create Phase 3 config data
        log_func("Generating Phase 3 config file...")
        phase3_config = {
            "user_account": data.get("user_account", {}),
            "bloat_remove": data.get("bloat_remove", {}),
            "software_install": data.get("software_install", {}),
        }
        
        config_path = os.path.join(oobe_dir, "phase3.cfg")
        if not write_to_file(config_path, json.dumps(phase3_config, indent=4)):
            log_func("FATAL: Could not write config file.")
            log_func("FATAL: Setup failed.")
            return

        # Copy local 'Apps' folder if selected
        if "local_apps" in phase3_config["software_install"]:
            apps_dir = "Apps"
            if os.path.exists(apps_dir) and any(os.scandir(apps_dir)):
                log_func("Copying 'Apps' folder to Z:\\Apps...")
                try:
                    shutil.copytree(apps_dir, "Z:\\Apps")
                except Exception as e:
                    log_func(f"ERROR: Could not copy local apps.")
            else:
                log_func("WARN: Folder not found or is empty.")
        
        # Set up WinRE (if not disabled)
        if not no_wre:
            log_func("Configuring Windows Recovery Environment...")
            re_dir = r"R:\Recovery\WindowsRE"
            if not os.path.exists(re_dir):
                os.makedirs(re_dir)
            run_sync(f"xcopy Z:\\Windows\\System32\\Recovery\\Winre.wim {re_dir}")
            run_sync(f"Z:\\Windows\\System32\\ReAgentc /setreimage /path {re_dir} /target Z:\\Windows")

        # --- 7. Set up Registry for Phase 3 ---
        log_func("Modifying registry to run Phase 3 on boot...")
        try:
            # Load SYSTEM hive
            run_sync("reg load HKLM\\SYS Z:\\Windows\\System32\\config\\SYSTEM")
            
            # Set CmdLine to run our Phase 3 exe.
            # After reboot, Z: becomes C:
            key_path = r"HKLM\SYS\Setup"
            cmd_line = r"C:\Windows\System32\OOBE\phase3.exe"
            
            run_sync(f'reg add "{key_path}" /v CmdLine /d "{cmd_line}" /f')
            
            # Unload hive
            run_sync("reg unload HKLM\\SYS")
            
            # Load SOFTWARE hive to disable privacy experience
            run_sync("reg load HKLM\\SOFT Z:\\Windows\\System32\\config\\SOFTWARE")
            key_path = r"HKLM\SOFT\Policies\Microsoft\Windows\OOBE"
            run_sync(f'reg add "{key_path}" /v DisablePrivacyExperience /t REG_DWORD /d 1 /f')
            run_sync("reg unload HKLM\\SOFT")
            
        except Exception as e:
            log_func(f"FATAL: {e}")
            log_func("FATAL: Setup failed.")
            return
            
        # --- 8. Reboot ---
        log_func("Phase 2 complete. The system will now reboot.")
        run_sync("wpeutil reboot")

    except Exception as e:
        log_func(f"FATAL: {e}")
        log_func("FATAL: Setup failed.")

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Windows Setup Rebooted: A script to install Windows with ease.")
    parser.add_argument(
        "--unattend",
        type=str,
        metavar="<unattend.json>",
        help="run in unattended mode with specified JSON config file"
    )
    parser.add_argument(
        "--generate",
        type=str,
        metavar="<config.json>",
        help="generated specified JSON config file for unattended mode"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="GUI test mode: bypass OS checks and skip verifiers and setup actions"
    )
    args = parser.parse_args()
      
    app = SetupGUI(args=args) # Pass args to the app
    if not app.terminated: # Check if init failed (e.g., PE check)
        app.mainloop()