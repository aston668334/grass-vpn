

import requests
import json
import pandas as pd
import os
import shutil
import sys
import pydc_control
import subprocess
import docker



# Function to recursively iterate over directories
def stop_good_ips(source_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if '.yml' in file:
                file_path = os.path.join(root, file)
                command = ['docker','compose', '-f', file_path, 'down']
                # Execute the command
                try:
                    subprocess.run(command, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")


# Function to recursively iterate over directories
def start_good_ips(source_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if '.yml' in file:
                file_path = os.path.join(root, file)
                command = ['docker','compose', '-f', file_path, 'up', '-d']
                # Execute the command
                try:
                    subprocess.run(command, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")

# Function to recursively iterate over directories
def start_testing_ips(source_dir):
    count = 0
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if '.yml' in file:
                file_path = os.path.join(root, file)
                command = ['docker','compose', '-f', file_path, 'up', '-d']
                # Execute the command
                try:
                    subprocess.run(command, check=True)
                    count += 1
                    print(count)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")
        if count >= 10:
            break
