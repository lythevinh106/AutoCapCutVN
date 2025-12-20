"""
pyCapCut API Server - Local Configuration
"""

import os
import json

# Configuration file path
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Default configuration
PORT = 8000
DEBUG = True

# Default CapCut drafts folder - Update this to your CapCut drafts location
DRAFT_FOLDER = r"C:\Users\VINH\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft"

# Try to load local configuration file
if os.path.exists(CONFIG_FILE_PATH):
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            local_config = json.load(f)
            
            # Update port
            if "port" in local_config:
                PORT = local_config["port"]
            
            # Update debug mode
            if "debug" in local_config:
                DEBUG = local_config["debug"]
            
            # Update draft folder
            if "draft_folder" in local_config:
                DRAFT_FOLDER = local_config["draft_folder"]
                
    except Exception as e:
        # Config file load failed, use defaults
        print(f"Warning: Could not load config.json: {e}")
        pass
