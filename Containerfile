FROM fedora:41

RUN dnf install -y \
    bash \
    python3 \
    python3-pip \
    git \
    && dnf clean all

WORKDIR /opt/project-zenith
COPY . /opt/project-zenith
RUN python3 -m pip install --no-cache-dir .

ENTRYPOINT ["zen"]
CMD ["status", "--json"]
