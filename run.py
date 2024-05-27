import pandas as pd
import requests, base64
import re
import os
import yaml
from dotenv import load_dotenv

load_dotenv()


def extract_ip_port(contents):

    # Regular expression to match the IP address and port
    match = re.search(r'remote\s+([\d\.]+)\s+(\d+)', contents)
    if match:
        ip_address = match.group(1)
        port = match.group(2)
        return ip_address, port
    else:
        return None, None

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
    docker_compose_file_path = './docker-compose_template.yml'

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

    ip_and_port = []
    for i in df['OpenVPN_ConfigData_Base64']:
        aa = base64.b64decode(i)
        # Decode the byte string
        decoded_string = aa.decode("utf-8")
        ip, port = extract_ip_port(decoded_string)
        ip_and_port.append((ip, port))

    for i in range(len(ip_and_port)):
        ip = ip_and_port[i][0]
        port = ip_and_port[i][1]
        ip_directory_path = directory_path + '/' + ip
        create_directory_if_not_exists(ip_directory_path)
        docker_compose_data = read_docker_compose(docker_compose_file_path)
        docker_compose_data['services']['grass1']['container_name'] = 'grass' + str(i)
        docker_compose_data['services']['vpnclient1']['container_name'] = 'vpnclient' + str(i)
        docker_compose_data['services']['vpnclient1']['environment']['VPN_HOST'] = ip
        docker_compose_data['services']['vpnclient1']['environment']['VPN_PORT'] = port
        docker_compose_data['services']['grass1']['environment'][0] = 'GRASS_USER=' + grass_user
        docker_compose_data['services']['grass1']['environment'][1] = 'GRASS_PASS=' + grass_pass
        ip_directory_path_docker_compose = ip_directory_path + '/' + 'docker-compose.yml'
        write_docker_compose(ip_directory_path_docker_compose,docker_compose_data)
    

        




