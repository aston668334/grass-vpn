import requests
import json
import pandas as pd
import os
import shutil
import sys
import subprocess
import docker
from dotenv import load_dotenv
import re
import signal
import asyncio
import time
import schedule
from controller import getgrass_proxy, dockercompose, dockercontroler, getgrass, vpngate, nodepay_proxy

load_dotenv()

def manage_docker_network():
    network_name = "vpn"
    subnet = "172.2.0.0/16"

    # Check if the network exists
    existing_networks = subprocess.check_output(['docker', 'network', 'ls', '--filter', f'name={network_name}', '--format', '{{.Name}}']).decode().strip().split('\n')

    if network_name in existing_networks:
        print(f"Network {network_name} exists. Removing it...")
        subprocess.run(['docker', 'network', 'rm', network_name], check=True)

    print(f"Creating network {network_name} with subnet {subnet}...")
    subprocess.run(['docker', 'network', 'create', '--driver', 'bridge', '--subnet', subnet, network_name], check=True)

def remove_docker_network():
    network_name = "vpn"
    print(f"Removing network {network_name}...")
    subprocess.run(['docker', 'network', 'rm', network_name], check=True)

def count_running_vpnclient_containers():
    output = subprocess.check_output(['docker', 'ps', '-q', '--filter', 'name=vpnclient*']).decode().strip()
    if output:
        return len(output.split('\n'))
    return 0

def start_vpn_services(df):
    for ind, i in df.iterrows():
        if pd.notna(i["IP"]) and pd.notna(i["Port"]) and pd.notna(i["Protocol"]):
            dockercompose.start_vpn_container(i["IP"], int(i["Port"]), i["Protocol"])

def stop_vpn_services(df):
    for ind, i in df.iterrows():
        if pd.notna(i["IP"]) and pd.notna(i["Port"]) and pd.notna(i["Protocol"]):
            dockercompose.stop_vpn_container(i["IP"], int(i["Port"]), i["Protocol"])

def manage_vpn_services():
    vpn_ip_status = 'vpn_ip_status.csv'
    max_container = int(os.getenv("MAX_CONTAINER"))

    df = getgrass.start(os.getenv("API_KEY"), vpn_ip_status)
    valid_df = getgrass.update_docker_status(vpn_ip_status, df)
    valid_df_add = vpngate.add_vpngate(valid_df)

    valid_df_add.to_csv("vpn_ip_status.csv", index=False)

    bad_ips = valid_df_add[(valid_df_add['TotalUptime'] > 60) & (valid_df_add['Score'] == 0)]
    good_ips = valid_df_add[(valid_df_add['TotalUptime'] > 60) & (valid_df_add['Score'] > 0)]
    testing_ips = valid_df_add[~(valid_df_add['IP'].isin(bad_ips['IP'])) & ~(valid_df_add['IP'].isin(good_ips['IP']))]

    # Start VPN services for good IPs
    start_vpn_services(good_ips)

    candidate_ip = testing_ips[testing_ips['TotalUptime'].isna()]

    current_vpnclient_count = count_running_vpnclient_containers()
    for ind, i in candidate_ip.iterrows():
        if current_vpnclient_count < max_container:
            dockercompose.start_vpn_container(i["IP"], int(i["Port"]), i["Protocol"])
            current_vpnclient_count += 1
        else:
            break

    # Stop VPN services for bad IPs
    stop_vpn_services(bad_ips)

    # Check and move unstable IPs
    dockercompose.check_all_containers()

def start():
    manage_vpn_services()
    asyncio.run(getgrass_proxy.main())  # Start WebSocket connections and proxy management
    asyncio.run(nodepay_proxy.main())  # Start WebSocket connections and proxy management


def stop():
    client = docker.from_env()
    containers = client.containers.list(all=True)
    for container in containers:
        if container.name.startswith('vpnclient_'):
            print(f'Stopping and removing container {container.name}...')
            container.stop()
            container.remove()
    remove_docker_network()

def auto_restart_docker():
    print("Restarting VPN services...")
    stop()
    time.sleep(10)  # Give some time for the services to stop completely
    start()

def auto_restart_proxy():
    print("Restarting grass and nodepay services...")
    asyncio.run(getgrass_proxy.main())  # Start WebSocket connections and proxy management
    asyncio.run(nodepay_proxy.main())  # Start WebSocket connections and proxy management


if __name__ == "__main__":
    start()
    schedule.every(12).hours.do(auto_restart_proxy)
    schedule.every(10).minutes.do(auto_restart_docker)  # Schedule auto_restart every 10 minutes
    while True:
        schedule.run_pending()