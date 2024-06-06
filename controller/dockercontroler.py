import os
import subprocess
import shutil
import docker

client = docker.from_env()

def stop_good_ips(source_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.yml'):
                file_path = os.path.join(root, file)
                command = ['docker', 'compose', '-f', file_path, 'down']
                try:
                    subprocess.run(command, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")

def start_good_ips(source_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.yml'):
                file_path = os.path.join(root, file)
                command = ['docker', 'compose', '-f', file_path, 'up', '-d']
                try:
                    subprocess.run(command, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")

def stop_remove_ip(path, ip):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.yml') and ip in file:
                file_path = os.path.join(root, file)
                command = ['docker', 'compose', '-f', file_path, 'down']
                try:
                    subprocess.run(command, check=True)
                    shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error: {e}")

def check_unstable_ips(unstable_path):
    for container in client.containers.list():
        if container.attrs['RestartCount'] > 20:
            ip = container.attrs['Config']['Labels']['com.docker.compose.service']
            stop_remove_ip(unstable_path, ip)

def get_ips():
    container_ids = subprocess.check_output("docker ps -aqf 'name=vpnclient_*'", shell=True).decode().strip().split('\n')
    ip_list = []
    for container_id in container_ids:
        if container_id:
            ip_address = subprocess.check_output(
                f"docker inspect -f '{{{{range .NetworkSettings.Networks}}}}{{{{.IPAddress}}}}{{{{end}}}}' {container_id}",
                shell=True).decode().strip()
            ip_list.append(ip_address)
    return ip_list
