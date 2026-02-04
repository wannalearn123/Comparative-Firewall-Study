FROM fedora:latest

RUN dnf -y update && \
    dnf -y install httpd-tools \
    curl \
    python3 python3-pip \
    net-tools \
    iputils
    
RUN dnf clean all 

USER root

WORKDIR /app