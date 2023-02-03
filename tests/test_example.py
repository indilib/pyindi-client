import PyIndi
import pytest
import time


class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()


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


def test_getting_properties(client):
    for d in client.getDevices():
        for prop in d.getProperties():
            prop_name = prop.getName()
            prop_type = prop.getType()
            if prop_type == PyIndi.INDI_TEXT:
                prop_text = prop.getText()
            elif prop_type == PyIndi.INDI_NUMBER:
                prop_number = prop.getNumber()
            elif prop_type == PyIndi.INDI_SWITCH:
                prop_switch = prop.getSwitch()
            elif prop_type == PyIndi.INDI_LIGHT:
                prop_light = prop.getLight()
            elif prop_type == PyIndi.INDI_BLOB:
                prop_blob = prop.getBLOB()
