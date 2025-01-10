FROM ubuntu:noble

WORKDIR /pyindi-client

ENV DEBIAN_FRONTEND="noninteractive" TZ=Etc/UTC

### install dependencies
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y build-essential software-properties-common libcfitsio-dev libnova-dev

### indi source build packages
#RUN apt-get install -y git cdbs dkms cmake fxload libgps-dev libgsl-dev libraw-dev libusb-dev zlib1g-dev libftdi-dev libgsl0-dev libjpeg-dev libkrb5-dev libnova-dev libtiff-dev libfftw3-dev librtlsdr-dev libcfitsio-dev libgphoto2-dev build-essential libusb-1.0-0-dev libboost-regex-dev libcurl4-gnutls-dev libev-dev

RUN apt-get install -y python3-dev python3-pip python3-venv virtualenv swig

### install indi from PPA
RUN add-apt-repository -y ppa:mutlaqja/ppa
RUN apt-get -y install \
    libindi-dev \
    indi-bin

### build and install latest indi release
#RUN git clone --depth 1 https://github.com/indilib/indi.git
#RUN cd indi && git checkout `git describe --tags \`git rev-list --tags --max-count=1\``
#RUN mkdir indi/build && cd indi/build && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug .. && make -j4 && make install


### setup virtualenv
RUN python3 -m venv /pyindi-client/venv
RUN /pyindi-client/venv/bin/pip3 install -U pip setuptools wheel

### install pyindi-client package
COPY indiclientpython.i .
COPY setup.py .
COPY setup.cfg .
RUN /pyindi-client/venv/bin/python3 setup.py install

### start indiserver & run tests
COPY requirements-test.txt .
RUN /pyindi-client/venv/bin/pip3 install -r requirements-test.txt
COPY tox.ini .
COPY tests/ tests/
COPY examples/ examples/
CMD /bin/bash -c "indiserver indi_simulator_ccd indi_simulator_focus indi_simulator_gps indi_simulator_guide indi_simulator_wheel indi_simulator_telescope & /pyindi-client/venv/bin/tox"
