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
        self.logger.info("new BLOB "+ bp.name.decode())
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
