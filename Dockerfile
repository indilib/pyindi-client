FROM ubuntu:latest

WORKDIR pyindi

RUN apt-get update -y
RUN apt-get install software-properties-common -y
RUN apt-add-repository -y ppa:mutlaqja/ppa
RUN apt-get -y install build-essential cmake git libstellarsolver-dev libeigen3-dev libcfitsio-dev zlib1g-dev libindi-dev extra-cmake-modules libkf5plotting-dev libqt5svg5-dev libkf5xmlgui-dev libkf5kio-dev kinit-dev libkf5newstuff-dev kdoctools-dev libkf5doctools-dev libkf5notifications-dev qtdeclarative5-dev libkf5crash-dev gettext libnova-dev libgsl-dev libraw-dev libkf5notifyconfig-dev wcslib-dev libqt5websockets5-dev xplanet xplanet-images qt5keychain-dev libsecret-1-dev breeze-icon-theme
RUN apt-get install python3 python3-dev python3-pip swig -y
RUN pip3 install -U pip

COPY . .
RUN python3 setup.py install
RUN pip3 install -r requirements-test.txt