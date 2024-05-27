#!/bin/bash

# 遍历目录及其子目录下的所有docker-compose.yml文件
find /path/to/your/directory -type f -name "docker-compose.yml" |
while read file; do
    # 提取目录路径
    dir=$(dirname "$file")
    
    # 进入目录并执行docker-compose命令
    cd "$dir" || exit
    docker-compose up -d
done
