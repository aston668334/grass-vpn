import docker
from docker.types import Mount

def start_vpn_container(ip, port, protocol):
    client = docker.from_env()
    container_name = f'vpnclient_{ip.replace(".", "_")}_{port}'
    
    # Check if container already exists
    try:
        container = client.containers.get(container_name)
        print(f'Container {container.name} already exists.')
    except docker.errors.NotFound:
        container = client.containers.run(
            image='aron666/softether-vpnclient',
            name=container_name,
            environment={
                'VPN_HOST': str(ip),
                'VPN_HUB': 'VPNGATE',
                'VPN_NAME': 'vpn1',
                'VPN_NIC_MAC': 'db:e0:14:72:8f:69',
                'VPN_PASSWORD': 'vpn',
                'VPN_PORT': str(port),
                'VPN_PORTOCOL': protocol,
                'VPN_USER': 'vpn'
            },
            cap_add=['ALL'],
            network_mode='vpn',
            privileged=True,
            restart_policy={'Name': 'always'},
            stdin_open=True,
            tty=True,
            mounts=[
                Mount(target='/dev', source='/dev', type='bind'),
                Mount(target='/lib/modules', source='/lib/modules', type='bind')
            ],
            detach=True  # Run in detached mode
        )
        print(f'Container {container.name} started with ID {container.id}')

def stop_vpn_container(ip, port, protocol):
    client = docker.from_env()
    container_name = f'vpnclient_{ip.replace(".", "_")}_{port}'

    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        print(f'Container {container.name} stopped and removed.')
    except docker.errors.NotFound:
        print(f'Container {container_name} not found.')

def check_container_restarts(ip, port, max_restarts=20):
    client = docker.from_env()
    container_name = f'vpnclient_{ip.replace(".", "_")}_{port}'

    try:
        container = client.containers.get(container_name)
        restart_count = container.attrs['RestartCount']
        print(f'Container {container.name} has restarted {restart_count} times.')
        
        if restart_count > max_restarts:
            print(f'Container {container.name} has exceeded {max_restarts} restarts. Stopping and removing...')
            stop_vpn_container(ip, port)
        else:
            print(f'Container {container.name} is within the restart limit.')
    except docker.errors.NotFound:
        print(f'Container {container_name} not found.')

def check_all_containers(max_restarts=20):
    client = docker.from_env()

    for container in client.containers.list(all=True):
        if container.name.startswith('vpnclient_'):
            restart_count = container.attrs['RestartCount']
            print(f'Container {container.name} has restarted {restart_count} times.')
            
            if restart_count > max_restarts:
                print(f'Container {container.name} has exceeded {max_restarts} restarts. Stopping and removing...')
                container.stop()
                container.remove()
                print(f'Container {container.name} stopped and removed.')
            else:
                print(f'Container {container.name} is within the restart limit.')

if __name__ == "__main__":
    # Example usage: start_vpn_container('219.100.37.3', 443, 'tcp')
    start_vpn_container('219.100.37.3', 443, 'tcp')

    # Check container restart count and stop if exceeds limit
    check_container_restarts('219.100.37.3', 443, max_restarts=20)

    # Check all containers managed by this script
    check_all_containers(max_restarts=20)