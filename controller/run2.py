import pandas as pd
import requests, base64
import re
import os
import yaml
from dotenv import load_dotenv
import subprocess

load_dotenv()


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


def read_docker_compose(file_path):
    with open(file_path, 'r') as file:
        compose_data = yaml.safe_load(file)
    return compose_data

def write_docker_compose(file_path, compose_data):
    with open(file_path, 'w') as file:
        yaml.safe_dump(compose_data, file)




if __name__ == "__main__":
    grass_user = os.getenv("GRASS_USER")
    grass_pass = os.getenv("GRASS_PASS")

    directory_path = './vpn_grass'

    # Replace 'your_directory_here' with the directory path you want to create
    create_directory_if_not_exists(directory_path)


    # Define the API endpoint
    url = "https://www.vpngate.net/api/iphone/"

    # Make a GET request to the API
    response = requests.get(url)


    out = response.text[15:]
    # Split the string by commas and newline characters
    rows = out.split("\r\n")
    col_name = rows[0].split(",")
    rows_data = rows[1:]
    data = [row.split(",") for row in rows_data]
    # Create a DataFrame
    df = pd.DataFrame(data)
    df.columns = col_name
    df = df[:-2]
    df.to_csv('./vpn_list.csv',sep = ',', index =False)

    ip_and_port = []
    for i in df['OpenVPN_ConfigData_Base64']:
        aa = base64.b64decode(i)
        # Decode the byte string
        decoded_string = aa.decode("utf-8")
        ip, port, protocol = extract_ip_port_protocol(decoded_string)
        ip_and_port.append((ip, port,protocol))

    # for i in range(len(ip_and_port)):
    #     ip = ip_and_port[i][0]
    #     port = ip_and_port[i][1]
    #     ip_directory_path = directory_path + '/' + ip
    #     create_directory_if_not_exists(ip_directory_path)
    #     docker_compose_data = read_docker_compose(docker_compose_file_path)
    #     docker_compose_data['services']['grass1']['container_name'] = 'grass' + str(i)
    #     docker_compose_data['services']['vpnclient1']['container_name'] = 'vpnclient' + str(i)
    #     docker_compose_data['services']['vpnclient1']['environment']['VPN_HOST'] = ip
    #     docker_compose_data['services']['vpnclient1']['environment']['VPN_PORT'] = port
    #     docker_compose_data['services']['grass1']['environment'][0] = 'GRASS_USER=' + grass_user
    #     docker_compose_data['services']['grass1']['environment'][1] = 'GRASS_PASS=' + grass_pass
    #     ip_directory_path_docker_compose = ip_directory_path + '/' + 'docker-compose.yml'
    #     write_docker_compose(ip_directory_path_docker_compose,docker_compose_data)
    


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
        "networks" : ["vpn"],
        "privileged": True,
        "cap_add": ["ALL"],
        "stdin_open": True,
        "tty": True,
        "restart": "always"
    }
    
    return service_template

def add_services_to_compose(ip_and_port_list, grass_user, grass_pass):
    services = {}
    for ip, port, protocol in ip_and_port_list:
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
            "networks" : ["vpn"],
            "restart": "always"
        }
        
        # Add VPN client service
        services[f"vpnclient_{ip.replace('.', '_')}_{port}"] = generate_service(ip, port, protocol, grass_user, grass_pass)
        
    return {
        "version": "3",
        "services": services,
        "networks": {
            "vpn": {
                "driver": "bridge",
                "ipam": {
                    "config": [
                        {"subnet": "172.2.0.0/16"}
                    ]
                }
            }
        }
    }
    
split = 10
for i in range(0, len(ip_and_port), split):
    file_name = f"docker-compose_{i//split}.yml"
    # Generate Docker Compose data
    docker_compose_data = add_services_to_compose(ip_and_port[i:i+split], grass_user, grass_pass)
    # Write Docker Compose file
    with open(file_name, "w") as f:
        yaml.dump(docker_compose_data, f)

    print("Docker Compose file generated successfully.")

