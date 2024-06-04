

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

def get_ips():
        # Step 1: Get all container IDs with names starting with "vpnclient_"
    container_ids = subprocess.check_output(
        "docker ps -aqf 'name=vpnclient_*'", shell=True).decode().strip().split('\n')

    # Step 2: Use docker inspect to get IP addresses of these containers
    ip_list = []
    for container_id in container_ids:
        if container_id:  # Check if container_id is not an empty string
            ip_address = subprocess.check_output(
                f"docker inspect -f '{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}' {container_id}",
                shell=True).decode().strip()
            ip_list.append(ip_address)

    return ip_list