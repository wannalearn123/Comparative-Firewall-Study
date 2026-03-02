FROM fedora:43

RUN dnf -y update && \
    dnf -y install httpd-tools \
    curl \
    python3 python3-pip \
    net-tools \
    iputils \
    file
    
RUN dnf clean all 

RUN pip3 install requests urllib3

USER root

WORKDIR /app
