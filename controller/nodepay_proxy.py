import asyncio
import signal
import requests
import json
import time
import ssl
import uuid
import websockets
from loguru import logger
import os
from websockets_proxy import Proxy, proxy_connect
from dotenv import load_dotenv
import docker

load_dotenv()

WEBSOCKET_URL = "wss://nw.nodepay.ai:4576/websocket"
SERVER_HOSTNAME = "nw.nodepay.ai"

RETRY_INTERVAL = 60  # in seconds (reduced for testing purposes)
PING_INTERVAL = 10  # in seconds
MAX_RETRIES = 5

NP_TOKEN = os.getenv("NP_TOKEN")

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + NP_TOKEN
}

response = requests.get("https://api.nodepay.ai/api/network/device-networks?page=0&size=10&active=false", headers=headers)
out = response.json()
USER_ID = out['data'][0]['user_id']

def get_vpnclient_proxies():
    client = docker.from_env()
    containers = client.containers.list(filters={"name": "vpnclient_"})
    proxies = []
    for container in containers:
        networks = container.attrs['NetworkSettings']['Networks']
        for network_name, network_info in networks.items():
            ip_address = network_info.get('IPAddress')
            if ip_address:
                proxy = f"http://{ip_address}:3128"
                logger.info(f"Found proxy: {proxy}")
                proxies.append(proxy)
    return proxies

async def call_api_info(token):
    return {
        "code": 0,
        "data": {
            "uid": USER_ID,
        }
    }

async def connect_socket_proxy(http_proxy, reconnect_interval=RETRY_INTERVAL, ping_interval=PING_INTERVAL, max_retries=MAX_RETRIES):
    browser_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, http_proxy))
    logger.info(f"Browser ID: {browser_id}")
    retries = 0
    while retries < max_retries:
        try:
            proxy = Proxy.from_url(http_proxy)
            custom_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            async with proxy_connect(WEBSOCKET_URL, proxy=proxy, ssl=ssl_context, server_hostname=SERVER_HOSTNAME,
                                     extra_headers=custom_headers) as websocket:
                logger.info("Connected to WebSocket")
                async def send_ping(guid, options={}):
                    payload = {
                        "id": guid,
                        "action": "PING",
                        **options,
                    }
                    await websocket.send(json.dumps(payload))

                async def send_pong(guid):
                    payload = {
                        "id": guid,
                        "origin_action": "PONG",
                    }
                    await websocket.send(json.dumps(payload))

                async for message in websocket:
                    data = json.loads(message)

                    if data["action"] == "PONG":
                        await send_pong(data["id"])
                        await asyncio.sleep(ping_interval)
                        await send_ping(data["id"])

                    elif data["action"] == "AUTH":
                        api_response = await call_api_info(NP_TOKEN)
                        if api_response["code"] == 0 and api_response["data"]["uid"]:
                            user_info = api_response["data"]
                            auth_info = {
                                "user_id": user_info["uid"],
                                "browser_id": browser_id,
                                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                                "timestamp": int(time.time()),
                                "device_type": "extension",
                                "version": "extension_version",
                                "token": NP_TOKEN,
                                "origin_action": "AUTH",
                            }
                            await send_ping(data["id"], auth_info)
                        else:
                            logger.error("Failed to authenticate")
                            break

        except asyncio.CancelledError:
            logger.info("Task was cancelled")
            break
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Connection closed with error: {e.code} - {e.reason}")
        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Connection closed normally")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            retries += 1
            if retries < max_retries:
                logger.info(f"Retrying in {reconnect_interval} seconds... (Attempt {retries}/{max_retries})")
                await asyncio.sleep(reconnect_interval)
            else:
                logger.error("Max retries reached. Giving up.")
                break

async def update_proxies(current_proxies):
    while True:
        new_proxies = get_vpnclient_proxies()
        logger.info(f"Updating proxy list: {new_proxies}")

        for proxy, task in list(current_proxies.items()):
            if proxy not in new_proxies:
                task.cancel()
                del current_proxies[proxy]

        for proxy in new_proxies:
            if proxy not in current_proxies:
                task = asyncio.create_task(connect_socket_proxy(proxy))
                current_proxies[proxy] = task

        await asyncio.sleep(300)

async def main():
    initial_proxies = get_vpnclient_proxies()
    current_proxies = {}

    for proxy in initial_proxies:
        task = asyncio.create_task(connect_socket_proxy(proxy))
        current_proxies[proxy] = task

    asyncio.create_task(update_proxies(current_proxies))

    await asyncio.gather(*current_proxies.values(), return_exceptions=True)

if __name__ == '__main__':
    asyncio.run(main())
