import PyIndi
import pytest


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


@pytest.fixture(scope="function")
def client():
    client = IndiClient()
    client.setServer("localhost", 7624)
    client.connectServer()
    yield client
    client.disconnectServer()

def test_connect(client):
    assert(client.isServerConnected())

def test_connect_device(client):
    telescope = "Telescope Simulator"
    device_telescope = client.getDevice(telescope)
    # assert(device_telescope.isConnected())


