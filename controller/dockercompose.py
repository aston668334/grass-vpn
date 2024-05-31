import pandas as pd
import requests, json, sys, base64, tempfile, subprocess, time
import re
import os
import yaml
import shutil
from dotenv import load_dotenv

load_dotenv()

def copy_specific_files(source_dir, destination_dir, ip_list):
    # Ensure the destination directory exists
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    
    # Iterate over the directories and files
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            dir_name = os.path.basename(root)
            
            # Check if the directory name matches any IP in the ip_list
            if any(ip in dir_name for ip in ip_list):
                # Create destination directory if it doesn't exist
                dest_dir_path = os.path.join(destination_dir, dir_name)
                if not os.path.exists(dest_dir_path):
                    os.makedirs(dest_dir_path)
                
                # Copy the file to the destination directory
                shutil.copy(file_path, dest_dir_path)

# Function to recursively iterate over directories
def copy_testing_files(source_dir, destination_dir, ip_list):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            dir_name = os.path.basename(os.path.dirname(file_path))
            
            # Check conditions to determine if the file needs to be copied
            if not any(root in i for i in ip_list):
                # Create destination directory if it doesn't exist
                dest_dir_path = os.path.join(destination_dir, dir_name)
                if not os.path.exists(dest_dir_path):
                    os.makedirs(dest_dir_path)
                
                # Copy the file to the destination directory
                shutil.copy(file_path, dest_dir_path)

def extract_ip_port_protocol(contents):
    # Regular expression to match the IP address, port, and protocol
    ip_port_match = re.search(r'remote\s+([\d\.]+)\s+(\d+)', contents)
    proto_match = re.search(r'proto\s+(\w+)', contents)

    ip_address, port, protocol = None, None, None

    if ip_port_match:
        ip_address = ip_port_match.group(1)
        port = ip_port_match.group(2)

    if proto_match:
        protocol = proto_match.group(1)

    return ip_address, port, protocol



def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        # print(f"Directory '{directory}' created successfully.")
    else:
        pass
        # print(f"Directory '{directory}' already exists.")

# Replace 'your_directory_here' with the directory path you want to create

def create_docker_compose_file(directory_path,ip,port,protocol,open_port):

    grass_user = os.getenv("GRASS_USER")
    grass_pass = os.getenv("GRASS_PASS")

    create_directory_if_not_exists(directory_path)
    ip_directory_path = directory_path + '/' + ip
    create_directory_if_not_exists(ip_directory_path)
    docker_compose_data = add_services_to_compose(ip, port, protocol, grass_user, grass_pass, open_port)

    ip_directory_path_docker_compose = ip_directory_path + '/' + 'docker-compose.yml'
    write_docker_compose(ip_directory_path_docker_compose,docker_compose_data)


def write_docker_compose(file_path, compose_data):
    with open(file_path, 'w') as file:
        yaml.safe_dump(compose_data, file)



def add_services_to_compose(ip, port, protocol, grass_user, grass_pass, open_port):
    services = {}
    service_name = f"grass_{ip.replace('.', '_')}_{port}"
    services[service_name] = {
        "image": "aron666/aron.grassminer",
        "container_name": f"grass_{ip.replace('.', '_')}_{port}",
        "environment": [
            f"GRASS_USER={grass_user}",
            f"GRASS_PASS={grass_pass}",
            "ADMIN_USER=admin",
            "ADMIN_PASS=admin",
            "PROXY_ENABLE=true",
            "PROXY_HOST=http://" +  f"vpnclient_{ip.replace('.', '_')}_{port}" + ':3128'
            # "PROXY_USER=user"
            # "PROXY_PASS=pass"
        ],
        # "network_mode": f"service:vpnclient_{ip.replace('.', '_')}_{port}",
        "network_mode" : "vpn",
        "ports" : [str(open_port)+":8080"],
        "restart": "always"
    }
    
    # Add VPN client service
    services[f"vpnclient_{ip.replace('.', '_')}_{port}"] = generate_service(ip, port, protocol, grass_user, grass_pass)
        
    return {
        "version": "3",
        "services": services,
    }



def generate_service(ip, port, protocol, grass_user, grass_pass):
    service_template = {
        "image": "aron666/softether-vpnclient",
        "container_name": f"vpnclient_{ip.replace('.', '_')}_{port}",
        "environment": {
            "VPN_NAME": "vpn1",
            "VPN_HOST": ip,
            "VPN_PORT": port,
            "VPN_PORTOCOL": protocol,
            "VPN_HUB": "VPNGATE",
            "VPN_USER": "vpn",
            "VPN_PASSWORD": "vpn",
            "VPN_NIC_MAC": "db:e0:14:72:8f:69"
        },
        "volumes": [
            "/dev:/dev",
            "/lib/modules:/lib/modules"
        ],
        "network_mode" : "vpn",
        "privileged": True,
        "cap_add": ["ALL"],
        "stdin_open": True,
        "tty": True,
        "restart": "always"
    }
    
    return service_template


