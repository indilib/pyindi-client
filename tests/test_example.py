import PyIndi
import logging
import pytest
import time


logging.basicConfig(level=logging.INFO)
logger = logging


class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()

        self._blob_data = None

    @property
    def blob_data(self):
        return self._blob_data

    def updateProperty(self, p):
        # INDI 2.x.x code path

        if p.getType() == PyIndi.INDI_BLOB:
            p_blob = PyIndi.PropertyBlob(p)
            self.processBlob(p_blob[0])
        elif p.getType() == PyIndi.INDI_NUMBER:
            pass
        elif p.getType() == PyIndi.INDI_SWITCH:
            pass
        elif p.getType() == PyIndi.INDI_TEXT:
            pass
        elif p.getType() == PyIndi.INDI_LIGHT:
            pass
        else:
            logger.warning("Property type not matched: %d", p.getType())

    def processBlob(self, blob):
        self._blob_data = blob.getblobdata()


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
        "CCD Simulator"
    ]
    assert set(device_names) == set(expected_device_names)


def test_connecting_devices(client):
    for device in client.getDevices():
        if not device.isConnected():
            connection = device.getSwitch("CONNECTION")
            time.sleep(1.0)

            connection[0].setState(PyIndi.ISS_ON)  # CONNECT
            connection[1].setState(PyIndi.ISS_OFF)  # DISCONNECT
            client.sendNewSwitch(connection)

            time.sleep(1.0)

        assert device.isConnected()


def test_getting_properties(client):
    for device in client.getDevices():
        if not device.isConnected():
            connection = device.getSwitch("CONNECTION")
            time.sleep(1.0)

            connection[0].setState(PyIndi.ISS_ON)  # CONNECT
            connection[1].setState(PyIndi.ISS_OFF)  # DISCONNECT
            client.sendNewSwitch(connection)

            time.sleep(1.0)

        for prop in device.getProperties():
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


def test_exposure(client):
    device_ccd = client.getDevice("CCD Simulator")
    time.sleep(1.0)

    connection = device_ccd.getSwitch("CONNECTION")
    time.sleep(1.0)

    if not device_ccd.isConnected():
        connection[0].setState(PyIndi.IIS_ON)  # CONNECT
        connection[1].setState(PyIndi.ISS_OFF)  # DISCONNECT
        client.sendNewSwitch(connection)

        time.sleep(1.0)

    client.setBLOBMode(PyIndi.B_ALSO, device_ccd.getDeviceName(), None)

    EXPOSURE = device_ccd.getNumber("CCD_EXPOSURE")
    time.sleep(1.0)

    # take 0.1 second exposure
    EXPOSURE[0].setValue(0.1)  # CCD_EXPOSURE_VALUE
    client.sendNewNumber(EXPOSURE)

    time.sleep(3.0)

    assert not isinstance(client.blob_data, type(None))


def test_slew(client):
    device_telescope = client.getDevice("Telescope Simulator")
    time.sleep(1)

    if not device_telescope.isConnected():
        connection = device_telescope.getSwitch("CONNECTION")
        time.sleep(1)

        connection[0].setState(PyIndi.ISS_ON)  # CONNECT
        connection[1].setState(PyIndi.ISS_OFF)  # DISCONNECT
        client.sendNewSwitch(connection)

        time.sleep(1.0)

    device_ccd = client.getDevice("CCD Simulator")
    time.sleep(1)

    if not device_ccd.isConnected():
        connection = device_ccd.getSwitch("CONNECTION")
        time.sleep(1)

        connection[0].setState(PyIndi.ISS_ON)  # CONNECT
        connection[1].setState(PyIndi.ISS_OFF)  # DISCONNECT
        client.sendNewSwitch(connection)

        time.sleep(1.0)

    ON_COORD_SET = device_telescope.getSwitch("ON_COORD_SET")
    time.sleep(1.0)

    ON_COORD_SET[0].setState(PyIndi.ISS_ON)  # TRACK
    ON_COORD_SET[1].setState(PyIndi.ISS_OFF)  # SLEW
    ON_COORD_SET[2].setState(PyIndi.ISS_OFF)  # SYNC
    client.sendNewSwitch(ON_COORD_SET)

    EQUATORIAL_EOD_COORD = device_telescope.getNumber("EQUATORIAL_EOD_COORD")
    time.sleep(1.0)

    # slew to M13
    EQUATORIAL_EOD_COORD[0].setValue(16.7175)  # RA_PE
    EQUATORIAL_EOD_COORD[1].setValue(36.4233)  # DEC_PE
    client.sendNewNumber(EQUATORIAL_EOD_COORD)
