import pandas as pd
import requests, base64
import re
import os
import yaml
from dotenv import load_dotenv
import subprocess
import shutil
from controller import dockercompose

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
        shutil.rmtree(directory, ignore_errors=True)
        os.makedirs(directory)
        # print(f"Directory '{directory}' already exists.")


def read_docker_compose(file_path):
    with open(file_path, 'r') as file:
        compose_data = yaml.safe_load(file)
    return compose_data

def write_docker_compose(file_path, compose_data):
    with open(file_path, 'w') as file:
        yaml.safe_dump(compose_data, file)


def get_ip_port_list():
    grass_user = os.getenv("GRASS_USER")
    grass_pass = os.getenv("GRASS_PASS")
    docker_compose_file_path = './docker-compose_template.yml'

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
        ip, port, protocol = extract_ip_port_protocol(decoded_string)
        ip_and_port.append((ip, port,protocol))

    return ip_and_port

def write_csv(ip_and_port):
    # Create a DataFrame from the ip_and_port list
    vpn_list_df = pd.DataFrame(ip_and_port, columns=['IP', 'Port', 'Protocol'])

    # Write the DataFrame to the CSV file (creating it if it does not exist)
    if os.path.exists(csv_file):
        # If the file exists, append without headers
        vpn_list_df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        # If the file does not exist, create it with headers
        vpn_list_df.to_csv(csv_file, mode='w', header=True, index=False)



def add_vpngate(df):
    ip_port_list = get_ip_port_list()
    # Open_Port = int(df.Open_Port.max(skipna=True) + 1)
    for container in ip_port_list:
        IP, Port, Protocol = container
        if IP in df['IP'].values:
            df.loc[df['IP'] == IP, 'Port'] = Port
            df.loc[df['IP'] == IP, 'Protocol'] = Protocol
        else:
            # new_data = pd.DataFrame({'IP': [IP], 'Port': [Port], 'Protocol': [Protocol],'Open_Port':[Open_Port]})
            new_data = pd.DataFrame({'IP': [IP], 'Port': [Port], 'Protocol': [Protocol]})
            # Open_Port += 1
            df = pd.concat([df, new_data], ignore_index=True)
    return df


    


if __name__ == "__main__":
    grass_user = os.getenv("GRASS_USER")
    grass_pass = os.getenv("GRASS_PASS")
    docker_compose_file_path = './docker-compose_template.yml'
    # Define the CSV file name
    csv_file = 'vpn_list.csv'

    directory_path = './grass_vpn_pool'

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
        ip, port, protocol = extract_ip_port_protocol(decoded_string)
        ip_and_port.append((ip, port,protocol))


    # Create a DataFrame from the ip_and_port list
    vpn_list_df = pd.DataFrame(ip_and_port, columns=['IP', 'Port', 'Protocol'])

    # Write the DataFrame to the CSV file (creating it if it does not exist)
    if os.path.exists(csv_file):
        # If the file exists, append without headers
        vpn_list_df.to_csv(csv_file, mode='a', header=False, index=False)
    else:
        # If the file does not exist, create it with headers
        vpn_list_df.to_csv(csv_file, mode='w', header=True, index=False)

    open_port = 5001
    for i in range(len(ip_and_port)):
        ip = ip_and_port[i][0]
        port = ip_and_port[i][1]
        ip_directory_path = directory_path + '/' + ip
        create_directory_if_not_exists(ip_directory_path)
        docker_compose_data = read_docker_compose(docker_compose_file_path)
        docker_compose_data = dockercompose.add_services_to_compose(ip, port, protocol, grass_user, grass_pass, open_port)

        ip_directory_path_docker_compose = ip_directory_path + '/' + 'docker-compose.yml'
        write_docker_compose(ip_directory_path_docker_compose,docker_compose_data)
        open_port += 1

        





