# -*- coding: utf-8 -*-
# @Time     :2023/12/26 17:00
# @Author   :ym
# @File     :main.py
# @Software :PyCharm

import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
import docker
import os

# Function to get list of container IPs with names starting with "vpnclient_"
def get_vpnclient_proxies():
    client = docker.from_env()
    containers = client.containers.list(filters={"name": "vpnclient_"})
    proxies = []
    for container in containers:
        networks = container.attrs['NetworkSettings']['Networks']
        for network_name, network_info in networks.items():
            ip_address = network_info.get('IPAddress')
            if ip_address:
                proxies.append(f"http://{ip_address}:3128")
    return proxies

# Async function to connect to WebSocket server
async def connect_to_wss(http_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, http_proxy))
    logger.info(device_id)
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            uri = "wss://proxy.wynd.network:4650/"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(http_proxy)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send(send_message)
                        await asyncio.sleep(20)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(message)
                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "2.5.0"
                            }
                        }
                        logger.debug(auth_response)
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send(json.dumps(pong_response))
        except asyncio.CancelledError:
            logger.info(f"Task for proxy {http_proxy} cancelled")
            break
        except Exception as e:
            logger.error(e)
            logger.error(http_proxy)

# Function to update proxy list and manage tasks
async def update_proxies(user_id, tasks, current_proxies):
    while True:
        new_proxies = get_vpnclient_proxies()
        logger.info(f"Updating proxy list: {new_proxies}")

        # Cancel and remove tasks for proxies that are no longer valid
        for proxy, task in list(current_proxies.items()):
            if proxy not in new_proxies:
                task.cancel()
                del current_proxies[proxy]

        # Add new tasks for new proxies
        for proxy in new_proxies:
            if proxy not in current_proxies:
                task = asyncio.create_task(connect_to_wss(proxy, user_id))
                current_proxies[proxy] = task

        await asyncio.sleep(300)  # Wait for 5 minutes

# Main function
async def main():
    grass_userid = os.getenv("GRASS_USERID")
    initial_proxies = get_vpnclient_proxies()
    current_proxies = {}
    
    # Create initial tasks
    for proxy in initial_proxies:
        task = asyncio.create_task(connect_to_wss(proxy, grass_userid))
        current_proxies[proxy] = task
    
    # Schedule the update of proxies
    asyncio.create_task(update_proxies(grass_userid, current_proxies, current_proxies))
    
    await asyncio.gather(*current_proxies.values())

if __name__ == '__main__':
    # Run main function
    asyncio.run(main())
