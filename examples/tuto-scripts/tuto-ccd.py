"""
This script is a tutorial example demonstrating how to control a telescope
and a CCD camera simulator using the PyIndi library.

It connects to an INDI server, points the telescope to the star Vega,
takes exposures using the CCD simulator, and processes the received image data (BLOBs).
This example specifically shows the usage of the more specific `sendNewSwitch`,
`sendNewNumber`, and `sendNewText` methods for sending property updates.
"""

import PyIndi
import time
import sys
import threading


class IndiClient(PyIndi.BaseClient):
    """
    Custom INDI client class inheriting from PyIndi.BaseClient.

    This class overrides the updateProperty callback to handle new BLOB data.
    """

    def __init__(self):
        """
        Initializes a new IndiClient instance.
        """
        super(IndiClient, self).__init__()

    def updateProperty(self, prop):
        """
        Callback method emitted when a property value is updated on the INDI server.

        This overridden method specifically checks for and handles BLOB properties
        by setting a threading event.

        Args:
            prop (PyIndi.Property): The updated INDI property.
        """
        global blobEvent
        if prop.getType() == PyIndi.INDI_BLOB:
            print("new BLOB ", prop.getName())
            # Set the event to signal that a new BLOB has been received
            blobEvent.set()


# --- Main Execution ---

# Create an instance of the IndiClient class and initialize its host/port members
indiclient = IndiClient()
indiclient.setServer("localhost", 7624)

# Connect to the INDI server
if not indiclient.connectServer():
    print(
        "No indiserver running on "
        + indiclient.getHost()
        + ":"
        + str(indiclient.getPort())
        + " - Try to run"
    )
    print("  indiserver indi_simulator_telescope indi_simulator_ccd")
    sys.exit(1)

# --- Telescope Control ---

# Define the name of the telescope device
telescope = "Telescope Simulator"
device_telescope = None
telescope_connect = None

# Get the telescope device object, waiting until it's available
device_telescope = indiclient.getDevice(telescope)
while not device_telescope:
    time.sleep(0.5)
    device_telescope = indiclient.getDevice(telescope)

# Wait for the CONNECTION property to be defined for the telescope
telescope_connect = device_telescope.getSwitch("CONNECTION")
while not telescope_connect:
    time.sleep(0.5)
    telescope_connect = device_telescope.getSwitch("CONNECTION")

# If the telescope device is not connected, connect it
if not device_telescope.isConnected():
    # Property vectors are mapped to iterable Python objects
    # Hence we can access each element of the vector using Python indexing
    # each element of the "CONNECTION" vector is a ISwitch
    telescope_connect.reset()
    telescope_connect[0].setState(PyIndi.ISS_ON)  # the "CONNECT" switch
    # Send this new switch property value to the device
    indiclient.sendNewSwitch(telescope_connect)

# Define the coordinates for Vega (RA in hours, DEC in degrees)
# Beware that ra/dec are in decimal hours/degrees
vega = {"ra": (279.23473479 * 24.0) / 360.0, "dec": +38.78368896}

# Set the ON_COORD_SET switch to engage tracking after goto
# device.getSwitch is a helper to retrieve a property vector
telescope_on_coord_set = device_telescope.getSwitch("ON_COORD_SET")
while not telescope_on_coord_set:
    time.sleep(0.5)
    telescope_on_coord_set = device_telescope.getSwitch("ON_COORD_SET")
# the order below is defined in the property vector, look at the standard Properties page
# or enumerate them in the Python shell when you're developing your program
telescope_on_coord_set.reset()
# Set the switch to engage tracking after the goto completes (index 0)
telescope_on_coord_set[0].setState(PyIndi.ISS_ON)  # index 0-TRACK, 1-SLEW, 2-SYNC
# Send the updated switch property to the device
indiclient.sendNewSwitch(telescope_on_coord_set)

# We set the desired coordinates
telescope_radec = device_telescope.getNumber("EQUATORIAL_EOD_COORD")
while not telescope_radec:
    time.sleep(0.5)
    telescope_radec = device_telescope.getNumber("EQUATORIAL_EOD_COORD")
# Set the RA and DEC values
telescope_radec[0].setValue(vega["ra"])
telescope_radec[1].setValue(vega["dec"])
# Send the updated number property to the device to start the goto
indiclient.sendNewNumber(telescope_radec)

# and wait for the scope has finished moving
while telescope_radec.getState() == PyIndi.IPS_BUSY:
    print("Scope Moving ", telescope_radec[0].value, telescope_radec[1].value)
    time.sleep(2)

# --- CCD Control ---

# Define the name of the CCD device
ccd = "CCD Simulator"
device_ccd = indiclient.getDevice(ccd)
while not (device_ccd):
    time.sleep(0.5)
    device_ccd = indiclient.getDevice(ccd)

# Wait for the CONNECTION property to be defined for the CCD
ccd_connect = device_ccd.getSwitch("CONNECTION")
while not (ccd_connect):
    time.sleep(0.5)
    ccd_connect = device_ccd.getSwitch("CONNECTION")
# If the CCD device is not connected, connect it
if not (device_ccd.isConnected()):
    ccd_connect.reset()
    ccd_connect[0].setState(PyIndi.ISS_ON)  # the "CONNECT" switch
    # Send the updated switch property to the device
    indiclient.sendNewSwitch(ccd_connect)

# Wait for the CCD_EXPOSURE property to be defined
ccd_exposure = device_ccd.getNumber("CCD_EXPOSURE")
while not (ccd_exposure):
    time.sleep(0.5)
    ccd_exposure = device_ccd.getNumber("CCD_EXPOSURE")

# Ensure the CCD simulator snoops the telescope simulator
# otherwise you may not have a picture of vega
ccd_active_devices = device_ccd.getText("ACTIVE_DEVICES")
while not (ccd_active_devices):
    time.sleep(0.5)
    ccd_active_devices = device_ccd.getText("ACTIVE_DEVICES")
# Set the active device for the CCD simulator to the telescope simulator
ccd_active_devices[0].setText("Telescope Simulator")
# Send the updated text property to the device
indiclient.sendNewText(ccd_active_devices)

# Inform the INDI server that we want to receive the "CCD1" blob from this device
indiclient.setBLOBMode(PyIndi.B_ALSO, ccd, "CCD1")

# Get the CCD1 BLOB property
ccd_ccd1 = device_ccd.getBLOB("CCD1")
while not ccd_ccd1:
    time.sleep(0.5)
    ccd_ccd1 = device_ccd.getBLOB("CCD1")

# Define a list of exposure times
exposures = [1.0, 5.0]

# Use a threading.Event to signal when a new BLOB (image) is received
blobEvent = threading.Event()
blobEvent.clear()  # Clear the event initially

# Start the first exposure
i = 0
ccd_exposure[0].setValue(exposures[i])
# Send the new exposure time (number property) to the device
indiclient.sendNewNumber(ccd_exposure)

# Loop through the exposure times
while i < len(exposures):
    # Wait for the blobEvent to be set, indicating a new BLOB has arrived
    blobEvent.wait()
    # If there are more exposures in the list, start the next one immediately
    if i + 1 < len(exposures):
        ccd_exposure[0].setValue(exposures[i + 1])
        blobEvent.clear()  # Clear the event for the next exposure
        # Send the new exposure time (number property) for the next exposure
        indiclient.sendNewNumber(ccd_exposure)
    # and meanwhile process the received one
    for blob in ccd_ccd1:
        print(
            "name: ",
            blob.getName(),
            " size: ",
            blob.getSize(),
            " format: ",
            blob.getFormat(),
        )
        # pyindi-client adds a getblobdata() method to IBLOB item
        # for accessing the contents of the blob, which is a bytearray in Python
        fits = blob.getblobdata()
        print("fits data type: ", type(fits))
        # here you may use astropy.io.fits to access the fits data
    # and perform some computations while the ccd is exposing
    # but this is outside the scope of this tutorial
    # Move to the next exposure in the list
    i += 1
