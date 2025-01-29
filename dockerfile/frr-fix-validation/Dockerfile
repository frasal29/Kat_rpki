FROM kathara/base

ARG DEBIAN_FRONTEND="noninteractive"

# Aggiunge il repository sid per ottenere libc6 >= 2.38
RUN apt update && \
    apt install -y software-properties-common && \
    echo "deb http://deb.debian.org/debian sid main" > /etc/apt/sources.list.d/sid.list && \
    apt update && \
    apt install -y libc6

RUN apt update && \
    apt install -y git autoconf automake libtool make \
    libprotobuf-c-dev protobuf-c-compiler build-essential \
    python3-dev python3-pytest python3-sphinx libjson-c-dev \
    libelf-dev libreadline-dev cmake libcap-dev bison flex \
    pkg-config texinfo gdb libgrpc-dev python3-grpc-tools \
    libpcre2-dev

RUN curl "http://ftp.de.debian.org/debian/pool/main/liby/libyang2/libyang2t64_2.1.148-0.2_amd64.deb" --output libyang2.deb
RUN curl "https://ci1.netdef.org/artifact/FRR-PULLREQ3/shared/build-04863/Debian-12-(Bookworm)-x86_64-Packages/frr_10.2-dev-PR16781-ge160833-20240910.144548-1%7Edeb12u1_amd64.deb" \
    --output frr.deb
RUN curl "https://ci1.netdef.org/artifact/FRR-PULLREQ3/shared/build-04863/Debian-12-(Bookworm)-x86_64-Packages/frr-pythontools_10.2-dev-PR16781-ge160833-20240910.144548-1%7Edeb12u1_all.deb" \
    --output frr-pythontools.deb
RUN curl "https://ci1.netdef.org/artifact/FRR-PULLREQ3/shared/build-04863/Debian-12-(Bookworm)-x86_64-Packages/frr-rpki-rtrlib_10.2-dev-PR16781-ge160833-20240910.144548-1%7Edeb12u1_amd64.deb" \
    --output frr-rpki-rtr.deb

# Verifica la validità dei file scaricati
RUN file libyang2.deb && \
    file frr.deb && \
    file frr-pythontools.deb && \
    file frr-rpki-rtr.deb

RUN apt install ./libyang2.deb -y
RUN apt install ./frr.deb -y
RUN apt install ./frr-pythontools.deb -y
RUN apt install ./frr-rpki-rtr.deb -y

# Rimuove il repository sid per evitare ulteriori aggiornamenti instabili
RUN rm /etc/apt/sources.list.d/sid.list && apt update
