FROM ubuntu:jammy-20240416 AS base

USER root

RUN apt update && apt install -y gcc make squid
RUN apt-get install -y isc-dhcp-client nano curl net-tools iputils-ping
RUN apt-get update && apt-get install -y libicu-dev

COPY softether-vpnclient.tar.gz /tmp/softether-vpnclient.tar.gz

RUN tar -xvf /tmp/softether-vpnclient.tar.gz -C /opt

RUN rm /tmp/softether-vpnclient.tar.gz

WORKDIR /opt/vpnclient

COPY run.sh ./run.sh

RUN mkdir app

COPY app/* app

RUN sh .install.sh

RUN ./vpnclient start

WORKDIR /opt/vpnclient/app

COPY conf/squid.conf /etc/squid/squid.conf

# CMD ["/bin/sh", "run.sh"]

RUN chmod +x ./Aron.VPN.Controller
CMD ["sh", "-c", "squid && ./Aron.VPN.Controller"]
# ENTRYPOINT ["./Aron.VPN.Controller"]

