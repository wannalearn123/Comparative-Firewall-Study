FROM fedora:43

RUN dnf -y update && \
    dnf -y install httpd-tools \
    curl \
    python3 python3-pip \
    net-tools \
    iputils \
    hping3 \
    file
    
RUN dnf clean all 

USER root

WORKDIR /app