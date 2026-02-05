FROM fedora:43

RUN dnf -y update && \
    dnf -y install iptables \
    nginx \
    python3 python3-pip \
    curl \
    net-tools \
    iputils \
    procps \
    file

RUN dnf clean all 
    
RUN pip3 install psutil numpy matplotlib

USER root

WORKDIR /app
