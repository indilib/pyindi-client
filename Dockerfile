FROM ubuntu:latest

WORKDIR /pyindi-client

ENV DEBIAN_FRONTEND="noninteractive" TZ=Etc/UTC

#install dependencies
RUN apt-get update -y
RUN apt-get install -y  git  cdbs  dkms  cmake  fxload  libgps-dev  libgsl-dev  libraw-dev  libusb-dev  zlib1g-dev  libftdi-dev  libgsl0-dev  libjpeg-dev  libkrb5-dev  libnova-dev  libtiff-dev  libfftw3-dev  librtlsdr-dev  libcfitsio-dev  libgphoto2-dev  build-essential  libusb-1.0-0-dev  libboost-regex-dev  libcurl4-gnutls-dev
RUN apt-get install python3 python3-dev python3-pip swig -y
RUN pip3 install -U pip

#build and install latest indi release
RUN git clone https://github.com/indilib/indi.git
RUN cd indi && git checkout `git describe --tags \`git rev-list --tags --max-count=1\``
RUN mkdir indi/build && cd indi/build && cmake -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Debug .. && make -j4 && make install

#install pyindi-client package
COPY indiclientpython.i .
COPY setup.py .
COPY setup.cfg .
RUN python3 setup.py install

#start indiserver & run tests
COPY requirements-test.txt .
RUN pip3 install -r requirements-test.txt
COPY tox.ini .
COPY tests/ tests/
COPY examples/ examples/
CMD /bin/bash -c "indiserver indi_simulator_ccd indi_simulator_focus indi_simulator_gps indi_simulator_guide indi_simulator_wheel indi_simulator_telescope & tox ."
