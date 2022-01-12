import PyIndi
import pytest
import time


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


@pytest.fixture()
def client():
    client = IndiClient()
    client.setServer("localhost", 7624)
    client.connectServer()

    for _ in range(15):
        if client.isServerConnected() and len(client.getDevices()) > 0:
            break
        time.sleep(1)

    yield client


def test_connect(client):
    assert client.isServerConnected()


def test_list_devices(client):
    device_names = [x.getDeviceName() for x in client.getDevices()]
    expected_device_names = [
        "Telescope Simulator",
        "Filter Simulator",
        "Guide Simulator",
        "GPS Simulator",
        "Focuser Simulator",
        "CCD Simulator",
    ]
    assert set(device_names) == set(expected_device_names)


def test_one(client):
    pass
