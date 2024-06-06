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
from controller import getgrass_proxy
import asyncio
import time

load_dotenv()

from controller import dockercompose, dockercontroler, getgrass, vpngate

def start():
    vpn_ip_status = 'vpn_ip_status.csv'
    csv_file = 'vpn_list.csv'
    temp_path_testing = './grass_vpn_testing_ip/'
    temp_path_good = './grass_vpn_good_ip/'
    temp_path_bad = './grass_vpn_bad_ip/'
    temp_path_unstable = './grass_vpn_unstable_ip/'
    max_container = int(os.getenv("MAX_CONTAINER"))

    df = getgrass.start(os.getenv("API_KEY"), vpn_ip_status, csv_file)
    valid_df = getgrass.update_docker_status(vpn_ip_status, df)
    valid_df_add = vpngate.add_vpngate(valid_df)

    bad_ips = valid_df_add[(valid_df_add['TotalUptime'] > 60) & (valid_df_add['Score'] == 0)]
    good_ips = valid_df_add[(valid_df_add['TotalUptime'] > 60) & (valid_df_add['Score'] > 0)]
    testing_ips = valid_df_add[~(valid_df_add['IP'].isin(bad_ips['IP'])) & ~(valid_df_add['IP'].isin(good_ips['IP']))]

    for ind, i in good_ips.iterrows():
        if pd.notna(i["IP"]) and pd.notna(i["Port"]) and pd.notna(i["Protocol"]):
            dockercompose.create_docker_compose_file(temp_path_good, i["IP"], int(i["Port"]), i["Protocol"])

    candidate_ip = testing_ips[testing_ips['TotalUptime'].isna()]
    for ind, i in candidate_ip[:max_container].iterrows():
        dockercompose.create_docker_compose_file(temp_path_testing, i["IP"], int(i["Port"]), i["Protocol"])

    dockercontroler.start_good_ips(temp_path_good)
    dockercontroler.start_good_ips(temp_path_testing)

    # Move bad IPs to bad directory and remove
    for ind, i in bad_ips.iterrows():
        if pd.notna(i["IP"]) and pd.notna(i["Port"]) and pd.notna(i["Protocol"]):
            dockercompose.create_docker_compose_file(temp_path_bad, i["IP"], int(i["Port"]), i["Protocol"])
            dockercontroler.stop_remove_ip(temp_path_bad, i["IP"])

    # Check and move unstable IPs
    dockercontroler.check_unstable_ips(temp_path_unstable)

def stop():
    dockercontroler.stop_good_ips('./grass_vpn_testing_ip/')

def stop_and_remove_all_docker_containers():
    try:
        # Stop all running containers
        subprocess.run(['docker', 'stop', '$(docker', 'ps', '-aq)'], shell=True, check=True)
        # Remove all containers
        subprocess.run(['docker', 'rm', '$(docker', 'ps', '-aq)'], shell=True, check=True)
        # Remove all networks
        subprocess.run(['docker', 'network', 'prune', '-f'], check=True)
        print("All Docker containers and networks have been stopped and removed.")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def signal_handler(sig, frame):
    print("Caught signal", sig)
    stop_and_remove_all_docker_containers()
    sys.exit(0)

async def main_loop():
    while True:
        try:
            print("Starting services...")
            start()
            print("Services started. Waiting for 12 hours...")
            await asyncio.sleep(3 * 60 * 60)  # Sleep for 3 hours
            print("Stopping services...")
            stop()
            print("Services stopped. Restarting loop...")
        except Exception as e:
            print("An error occurred:", e)
            stop()
            sys.exit(1)

async def run_main():
    await getgrass_proxy.main()
    await main_loop()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(run_main())
    except asyncio.CancelledError:
        pass
    finally:
        stop()
        loop.close()
