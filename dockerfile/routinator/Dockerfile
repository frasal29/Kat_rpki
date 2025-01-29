FROM kathara/frr3
RUN apt update
RUN apt upgrade -y
RUN apt install -y rsync curl build-essential libssl-dev openssl pkg-config
RUN curl -fsSL https://packages.nlnetlabs.nl/aptkey.asc | gpg --dearmor -o /usr/share/keyrings/nlnetlabs-archive-keyring.gpg
RUN echo "deb [trusted=yes arch=$(dpkg --print-architecture)] https://packages.nlnetlabs.nl/linux/debian bookworm main" | tee /etc/apt/sources.list.d/nlnetlabs.list > /dev/null
RUN apt update
RUN apt install -y routinator

RUN pip install rpki-rtr-client --break-system-packages