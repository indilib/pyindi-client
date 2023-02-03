import PyIndi
import time


class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()

    def newDevice(self, d):
        global dmonitor
        # We catch the monitored device
        dmonitor = d
        print("New device ", d.getDeviceName())

    def newProperty(self, p):
        global monitored
        global cmonitor
        # we catch the "CONNECTION" property of the monitored device
        if p.getDeviceName() == monitored and p.isNameMatch("CONNECTION"):
            cmonitor = PyIndi.PropertySwitch(p)
        print("New property ", p.getName(), " for device ", p.getDeviceName())

    def updateProperty(self, p):
        global newval
        global prop
        nvp = PyIndi.PropertyNumber(p)
        if nvp.isValid():
            # We only monitor Number properties of the monitored device
            prop = nvp
            newval = True


monitored = "Telescope Simulator"
dmonitor = None
cmonitor = None

indiclient = IndiClient()
indiclient.setServer("localhost", 7624)

# we are only interested in the telescope device properties
indiclient.watchDevice(monitored)
indiclient.connectServer()

# wait CONNECTION property be defined
while not (cmonitor):
    time.sleep(0.5)

# if the monitored device is not connected, we do connect it
if not (dmonitor.isConnected()):
    # Property vectors are mapped to iterable Python objects
    # Hence we can access each element of the vector using Python indexing
    # each element of the "CONNECTION" vector is a ISwitch
    cmonitor[0].setState(PyIndi.ISS_ON)  # the "CONNECT" switch
    cmonitor[1].setState(PyIndi.ISS_OFF)  # the "DISCONNECT" switch
    indiclient.sendNewProperty(cmonitor)  # send this new value to the device

newval = False
prop = None
nrecv = 0
while nrecv < 10:
    # we poll the newval global variable
    if newval:
        print(
            "newval for property", prop.getName(), " of device ", prop.getDeviceName()
        )
        # prop is a property vector, mapped to an iterable Python object
        for n in prop:
            # n is a INumber as we only monitor number vectors
            print(n.getName(), " = ", n.getValue())
        nrecv += 1
        newval = False
