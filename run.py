import requests
import json
import pandas as pd
import os
import shutil
import sys
import pydc_control
import subprocess
import docker
from dotenv import load_dotenv
import re

load_dotenv()

from controller import dockercompose, dockercontroler, getgrass, vpngate

# Define the CSV file name
vpn_ip_status = 'vpn_ip_status.csv'
csv_file = 'vpn_list.csv'
temp_path = './grass_vpn_testing_ip/'

df = getgrass.start(os.getenv("API_KEY"),vpn_ip_status,csv_file)
valid_df = getgrass.update_docker_status(vpn_ip_status,df)
valid_df_add = vpngate.add_vpngate(valid_df)
bad_ips = valid_df_add[(valid_df_add['TotalUptime'] > 60) & (valid_df_add['Score'] == 0)]
good_ips = valid_df_add[(valid_df_add['TotalUptime'] > 60) & (valid_df_add['Score'] > 0)]
testing_ips = valid_df_add[~(valid_df_add['IP'].isin(bad_ips['IP']))& ~(valid_df_add['IP'].isin(good_ips['IP']))]

# 遍歷 DataFrame 並檢查欄位是否為 NaN
for ind, i in good_ips.iterrows():
    if pd.notna(i["IP"]) and pd.notna(i["Port"]) and pd.notna(i["Protocol"]):
        dockercompose.create_docker_compose_file("temp_path", i["IP"], int(i["Port"]), i["Protocol"])


candidate_ip = testing_ips[testing_ips['TotalUptime'].isna()]
for ind, i in candidate_ip.iterrows():
    dockercompose.create_docker_compose_file(temp_path,i["IP"],int(i["Port"]),i["Protocol"])

dockercontroler.start_good_ips('./grass_vpn_good_ip/')

dockercontroler.start_good_ips('./grass_vpn_testing_ip/')