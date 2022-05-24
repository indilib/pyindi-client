pyindi-client ![tests](https://github.com/indilib/pyindi-client/actions/workflows/main.yml/badge.svg)
=============


version : v1.9.1

An [INDI](http://indilib.org/) Client Python API, auto-generated from
the official C++ API using [SWIG](http://www.swig.org/).

Installation
============

Use pip

``` {.sourceCode .sh}
pip install pyindi-client
```

Alternatively download a zip archive (use commits history to get a
previous release), extract it and run

``` {.sourceCode .sh}
python setup.py install
```

The file [setup.cfg]{.title-ref} contains configuration options (mainly
concerning [libindi]{.title-ref} installation path). Edit
[setup.cfg]{.title-ref} if you use a libindi version \< 1.4.1 (02/2017).
The file setup.py searchs for the libindiclient.a library in some
predefined directories. If not found, the script fails. Locate this
library (try [locate lindiclient.a]{.title-ref} from the command line)
and add its path to the [libindisearchpaths]{.title-ref} variable in the
setup script.

Dependencies
============

For the above installation to work, you need to have installed from your
distribution repositories the following packages: Python setup tools,
Python development files, libindi development files and swig.

-   On an Ubuntu-like distribution, you may use

    ``` {.sourceCode .sh}
    apt-get install python-setuptools
    apt-get install python-dev
    apt-get install libindi-dev
    apt-get install swig
    apt-get install libcfitsio-dev
    apt-get install libnova-dev
    ```

-   On a Fedora-like distribution, you may use

    ``` {.sourceCode .sh}
    dnf install python-setuptools
    dnf install python-devel
    dnf install libindi-devel
    dnf install swig
    dnf install libcfitsio-dev
    dnf install libnova-dev
    ```

Getting Started
===============

In the following simple example, an INDI client class is defined giving
the implementation of the pure virtual INDI client functions. This is
mandatory. This class is instantiated once, and after defining server
host and port in this object, a list of devices together with their
properties is printed on the console.

``` {.sourceCode .python}
# for logging
import sys
import time
import logging
# import the PyIndi module
import PyIndi

# Fancy printing of INDI states
# Note that all INDI constants are accessible from the module as PyIndi.CONSTANTNAME
def strISState(s):
    if (s == PyIndi.ISS_OFF):
        return "Off"
    else:
        return "On"  
def strIPState(s):
    if (s == PyIndi.IPS_IDLE):
        return "Idle"
    elif (s == PyIndi.IPS_OK):
        return "Ok"
    elif (s == PyIndi.IPS_BUSY):
        return "Busy"
    elif (s == PyIndi.IPS_ALERT):
        return "Alert"

# The IndiClient class which inherits from the module PyIndi.BaseClient class
# It should implement all the new* pure virtual functions.
class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()
        self.logger = logging.getLogger('IndiClient')
        self.logger.info('creating an instance of IndiClient')
    def newDevice(self, d):
        self.logger.info("new device " + d.getDeviceName())
    def newProperty(self, p):
        self.logger.info("new property "+ p.getName() + " for device "+ p.getDeviceName())
    def removeProperty(self, p):
        self.logger.info("remove property "+ p.getName() + " for device "+ p.getDeviceName())
    def newBLOB(self, bp):
        self.logger.info("new BLOB "+ bp.name)
    def newSwitch(self, svp):
        self.logger.info ("new Switch "+ svp.name + " for device "+ svp.device)
    def newNumber(self, nvp):
        self.logger.info("new Number "+ nvp.name + " for device "+ nvp.device)
    def newText(self, tvp):
        self.logger.info("new Text "+ tvp.name + " for device "+ tvp.device)
    def newLight(self, lvp):
        self.logger.info("new Light "+ lvp.name + " for device "+ lvp.device)
    def newMessage(self, d, m):
        self.logger.info("new Message "+ d.messageQueue(m))
    def serverConnected(self):
        self.logger.info("Server connected ("+self.getHost()+":"+str(self.getPort())+")")
    def serverDisconnected(self, code):
        self.logger.info("Server disconnected (exit code = "+str(code)+","+str(self.getHost())+":"+str(self.getPort())+")")

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

# Create an instance of the IndiClient class and initialize its host/port members
indiclient=IndiClient()
indiclient.setServer("localhost",7624)

# Connect to server
print("Connecting and waiting 1 sec")
if (not(indiclient.connectServer())):
     print("No indiserver running on "+indiclient.getHost()+":"+str(indiclient.getPort())+" - Try to run")
     print("  indiserver indi_simulator_telescope indi_simulator_ccd")
     sys.exit(1)
time.sleep(1)

# Print list of devices. The list is obtained from the wrapper function getDevices as indiclient is an instance
# of PyIndi.BaseClient and the original C++ array is mapped to a Python List. Each device in this list is an
# instance of PyIndi.BaseDevice, so we use getDeviceName to print its actual name.
print("List of devices")
dl=indiclient.getDevices()
for dev in dl:
    print(dev.getDeviceName())

# Print all properties and their associated values.
print("List of Device Properties")
for d in dl:
    print("-- "+d.getDeviceName())
    lp=d.getProperties()
    for p in lp:
        print("   > "+p.getName())
        if p.getType()==PyIndi.INDI_TEXT:
            tpy=p.getText()
            for t in tpy:
                print("       "+t.name+"("+t.label+")= "+t.text)
        elif p.getType()==PyIndi.INDI_NUMBER:
            tpy=p.getNumber()
            for t in tpy:
                print("       "+t.name+"("+t.label+")= "+str(t.value))
        elif p.getType()==PyIndi.INDI_SWITCH:
            tpy=p.getSwitch()
            for t in tpy:
                print("       "+t.name+"("+t.label+")= "+strISState(t.s))
        elif p.getType()==PyIndi.INDI_LIGHT:
            tpy=p.getLight()
            for t in tpy:
                print("       "+t.name+"("+t.label+")= "+strIPState(t.s))
        elif p.getType()==PyIndi.INDI_BLOB:
            tpy=p.getBLOB()
            for t in tpy:
                print("       "+t.name+"("+t.label+")= <blob "+str(t.size)+" bytes>")

# Disconnect from the indiserver
print("Disconnecting")
indiclient.disconnectServer()
```

See the
[examples](https://github.com/indilib/pyindi-client/tree/master/examples)
for more simple demos of using **pyindi-client**.

See the [interface
file](https://github.com/indilib/pyindi-client/blob/master/indiclientpython.i)
for an insight of what is wrapped and how.

For documentation on the methods of INDI Client API, refer to the [INDI
C++ API documentation](http://www.indilib.org/api/index.html).

Notes
-----

License
=======

**pyindi-client** code is free software under the [GNU General Public
License v3 or later (GPLv3+)](http://www.gnu.org/licenses/gpl.html).

------------------------------------------------------------------------
