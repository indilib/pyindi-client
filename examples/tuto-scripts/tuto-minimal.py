import PyIndi


class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()

    def newDevice(self, d):
        pass

    def newProperty(self, p):
        pass

    def removeProperty(self, p):
        pass

    def newBLOB(self, bp):
        pass

    def newSwitch(self, svp):
        pass

    def newNumber(self, nvp):
        pass

    def newText(self, tvp):
        pass

    def newLight(self, lvp):
        pass

    def newMessage(self, d, m):
        pass

    def serverConnected(self):
        pass

    def serverDisconnected(self, code):
        pass


indiclient = IndiClient()
indiclient.setServer("localhost", 7624)

indiclient.connectServer()
while 1:
    pass
