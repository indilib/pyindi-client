FROM ubuntu:noble

WORKDIR /pyindi-client

ENV DEBIAN_FRONTEND="noninteractive" TZ=Etc/UTC

### install dependencies
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y build-essential software-properties-common libcfitsio-dev libnova-dev \
    pkg-config cmake libdbus-1-dev libglib2.0-dev

### install python and swig
RUN apt-get install -y python3-dev python3-pip python3-venv virtualenv swig

### install indi from PPA
RUN add-apt-repository -y ppa:mutlaqja/ppa
RUN apt-get -y install \
    libindi-dev \
    indi-bin

### setup virtualenv
RUN python3 -m venv /pyindi-client/venv
# We still need setuptools as it's the build backend specified in pyproject.toml
RUN /pyindi-client/venv/bin/pip3 install -U pip setuptools wheel build

### build and install pyindi-client package
COPY indiclientpython.i .
COPY pyproject.toml .
COPY README.md .
COPY setup.py .
COPY setup.cfg .

### Generate the SWIG wrapper (including header file)
RUN swig -python -c++ -threads -I/usr/include -I/usr/include/libindi -I/usr/local/include/libindi indiclientpython.i

RUN /pyindi-client/venv/bin/python3 -m build
RUN /pyindi-client/venv/bin/pip3 install dist/*.whl

### install test requirements and setup test environment
COPY requirements-test.txt .
RUN /pyindi-client/venv/bin/pip3 install -r requirements-test.txt
COPY tox.ini .
COPY tests/ tests/
COPY examples/ examples/

CMD /bin/bash -c "indiserver indi_simulator_ccd indi_simulator_focus indi_simulator_gps indi_simulator_guide indi_simulator_wheel indi_simulator_telescope & /pyindi-client/venv/bin/tox"
