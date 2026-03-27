# Copyright (C) 2026 Chuck Talk <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

import subprocess
import json
import logging
import shutil
import os
import re

class AuthManager:
    """
    Manages authentication with Google Drive via rclone.
    """
    REMOTE_NAME = "cyswllt_gdrive"

    def __init__(self):
        pass

    def is_rclone_installed(self):
        """Checks if rclone is installed/available in PATH."""
        rclone_path = shutil.which("rclone")
        if not rclone_path:
            return False
        try:
            subprocess.run([rclone_path, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def is_authenticated(self):
        """Checks if the remote is already configured."""
        rclone_path = shutil.which("rclone")
        if not rclone_path: return False
        try:
            result = subprocess.run(
                [rclone_path, "listremotes"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return f"{self.REMOTE_NAME}:" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def start_authentication(self):
        """
        Starts the authentication flow. 
        Note: This is a blocking call that might open a browser.
        In a real GTK app, this should run in a thread.
        """
        # We use 'config create' to create a new remote named cyswllt_gdrive of type 'drive'
        # config_is_local=false forces the headless flow or interactive flow depending on flags,
        # but for desktop we want the standard flow where it opens the browser.
        # However, running this from python and capturing input/output can be tricky if it's interactive.
        # A simpler way for a dedicated app might be to use 'rclone authorize drive' 
        # scanning the output for the token, then creating the config.
        
        # Let's try the 'authorize' approach as it gives us a JSON token blob
        # which we can then use to create the remote non-interactively.
        
        rclone_path = shutil.which("rclone")
        if not rclone_path:
            logging.error("Rclone not found in PATH")
            return False
            
        try:
            logging.info("Starting authorization...")
            # 'rclone authorize drive' opens browser and prints token to stdout
            # We capture stdout. Note: rclone might print instructions to stderr.
            result = subprocess.run(
                [rclone_path, "authorize", "drive"],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = result.stdout.strip()
            # The output generally ends with the JSON token
            # Example: ... {"access_token": ...}
            
            # Find the JSON part starting with { and ending with }
            # We look for the last occurrence of '}' and the matching '{'
            end_index = output.rfind('}')
            if end_index == -1:
                 raise Exception("Could not find closing brace in rclone output")
                 
            # Walk backwards to find start? iterating is safer or regex
            # Let's try regex searching for the JSON blob
            match = re.search(r'(\{.*\})', output, re.DOTALL)
            if not match:
                 # Fallback: try to just parse the whole output if it's clean
                 try:
                     json.loads(output)
                     token_json = output
                 except json.JSONDecodeError:
                     raise Exception("Could not find token JSON in rclone output")
            else:
                 token_json = match.group(0)

            # Validate it's valid JSON
            json.loads(token_json) 
            
            logging.info(f"Token received. Configuring remote '{self.REMOTE_NAME}'...")

            # Now create the remote with this token
            # rclone config create <name> <type> <key>=<value> ...
            # We pass the token as a string. rclone expects 'token={"access_token":...}'
            subprocess.run(
                [
                    rclone_path, "config", "create", 
                    self.REMOTE_NAME, "drive", 
                    f"token={token_json}",
                    "config_is_local=false" 
                ],
                check=True,
                capture_output=True # Silence output
            )
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Rclone error: {e}")
            if e.stderr:
                logging.error(f"Stderr: {e.stderr}")
            return False
        except Exception as e:
            logging.error(f"Auth error: {e}")
            return False

    def delete_remote(self):
        """Removes the remote configuration."""
        rclone_path = shutil.which("rclone")
        if not rclone_path: return False
        try:
            subprocess.run(
                [rclone_path, "config", "delete", self.REMOTE_NAME],
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
