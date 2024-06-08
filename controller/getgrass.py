import requests
import json
import pandas as pd
import os
import shutil
import sys
import pydc_control
import subprocess
import docker


def start(API_KEY,csv_file):

    url = "https://api.getgrass.io/activeIps"
        # Define the CSV file name

    payload = {}
    headers = {
    'Authorization': str(API_KEY)
    }

    # Check if the CSV file exists
    if os.path.exists(csv_file):
        # Read the existing CSV file into a DataFrame
        df = pd.read_csv(csv_file)
        print("CSV file exists. Here is the data:")
    else:
        # Create a new DataFrame
        data = {
            'IP': [],
            'Port': [],
            'Protocol': [],
            'Status': [],
            'Timestamp': [],
            'TotalUptime': [],
            'Restart_times': [],
            'Score': [],
            # 'Open_Port': []
        }
        df = pd.DataFrame(data)

        # Save the DataFrame to a new CSV file
        df.to_csv(csv_file, index=False)
        print("CSV file did not exist. A new CSV file has been created.")

    df['Protocol'] = df['Protocol'].astype(str)


    response = requests.request("GET", url, headers=headers, data=payload, verify=False)
    rqs = json.loads(response.text)
    grass_score_data = rqs['result']['data']

    ips_data = []
    for i in grass_score_data:
        ipAddress = i['ipAddress']
        ipScore = i['ipScore']
        totalUptime = i['totalUptime']
        ips_data.append({'IP': ipAddress, 'Score': ipScore, 'TotalUptime': totalUptime})


    ips = pd.DataFrame(ips_data)
    df = pd.concat([df, ips])
    df = df.sort_values(by=['Score'])
    df = df.drop_duplicates(subset=["IP"], keep = "last")
    df = df.reset_index(drop = True)



    # Check if the CSV file exists
    if os.path.exists(csv_file):
        # Read the existing CSV file into a DataFrame
        vpn_list = pd.read_csv(csv_file)
        print("Success read vpn_list.csv")
    else:
        print("Error in read vpn_list.csv")


    valid_df = df
    for i in range(len(vpn_list)):
        slice_data = vpn_list.iloc[i]
        if slice_data["IP"] in valid_df["IP"]:
            # Update the 'Port' and 'Protocol' columns in df with values from vpn_list
            valid_df['Port'] = slice_data['Port']
            valid_df['Protocol'] = slice_data['Protocol']
        else:
            new_data = pd.DataFrame(vpn_list.iloc[[i]])
            valid_df =pd.concat([valid_df, new_data], ignore_index=True)

    valid_df.to_csv(csv_file, index = False)


    return df




def extract_ip_and_port(input_string):
    # Split the string by underscores
    parts = input_string.split('_')
    # Extract the IP address parts (parts[1] to parts[4]) and join them with dots
    ip_address = '.'.join(parts[1:5])
    # The last part is the port
    port = parts[5]
    return ip_address, port


def update_docker_status(csv_file, valid_df):
    # Create a Docker client
    client = docker.from_env()

    # Get the list of running containers
    all_containers = client.containers.list(all=True)

    # Filter containers with the name 'vpnclient'
    vpnclient_containers = [container for container in all_containers if 'vpnclient' in container.name]

    # Get the number of 'vpnclient' containers
    number_of_vpnclient_containers = len(vpnclient_containers)

    print(f"Number of Docker containers named 'vpnclient': {number_of_vpnclient_containers}")

    # Get the status and restart count of 'vpnclient' containers
    for container in vpnclient_containers:
        container_info = client.api.inspect_container(container.id)
        status = container_info['State']['Status']
        restart_count = container_info['RestartCount']
        name = container.name
        ip, port = extract_ip_and_port(name)
        if ip in valid_df['IP'].values:
            valid_df.loc[valid_df['IP'] == ip, 'Restart_times'] = restart_count
        print(f"Container Name: {container.name}, Status: {status}, Restart Count: {restart_count}")
    
    valid_df.to_csv(csv_file, index = False)
    

    return valid_df

