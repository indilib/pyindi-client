"""
This script is a tutorial example demonstrating how to connect to an INDI server
and monitor properties of a specific device using the PyIndi library.

It shows how to use the `watchDevice` method to filter events and how to handle
property updates, specifically focusing on monitoring Number properties.
"""
import PyIndi
import time


class IndiClient(PyIndi.BaseClient):
    """
    Custom INDI client class inheriting from PyIndi.BaseClient.

    This class overrides callback methods to monitor specific device and property
    events from the INDI server.
    """
    def __init__(self):
        """
        Initializes a new IndiClient instance.
        """
        super(IndiClient, self).__init__()

    def newDevice(self, d):
        """
        Callback method emitted when a new device is created on the INDI server.

        This overridden method catches and stores the monitored device instance.

        Args:
            d (PyIndi.Device): The newly created INDI device.
        """
        global dmonitor
        # We catch the monitored device
        dmonitor = d
        print("New device ", d.getDeviceName())

    def newProperty(self, p):
        """
        Callback method emitted when a new property is created for an INDI driver.

        This overridden method catches and stores the CONNECTION property
        of the monitored device.

        Args:
            p (PyIndi.Property): The newly created INDI property.
        """
        global monitored
        global cmonitor
        # we catch the "CONNECTION" property of the monitored device
        if p.getDeviceName() == monitored and p.isNameMatch("CONNECTION"):
            cmonitor = PyIndi.PropertySwitch(p)
        print("New property ", p.getName(), " for device ", p.getDeviceName())

    def updateProperty(self, p):
        """
        Callback method emitted when a property value is updated on the INDI server.

        This overridden method checks if the updated property is a Number property
        of the monitored device and signals that a new value is available.

        Args:
            p (PyIndi.Property): The updated INDI property.
        """
        global newval
        global prop
        # Cast the generic property to a Number property
        nvp = PyIndi.PropertyNumber(p)
        # Check if the cast was successful (i.e., it's a Number property)
        if nvp.isValid():
            # We only monitor Number properties of the monitored device
            prop = nvp
            newval = True


# --- Global Variables for Monitoring ---

# The name of the device to monitor
monitored = "Telescope Simulator"
# Variable to hold the monitored device instance
dmonitor = None
# Variable to hold the CONNECTION property of the monitored device
cmonitor = None

# --- Main Execution ---

# Create an instance of the IndiClient class and set the server host/port
indiclient = IndiClient()
indiclient.setServer("localhost", 7624)

# Tell the INDI client to only watch properties for the specified device.
# This filters out events from other devices on the server.
indiclient.watchDevice(monitored)
# Connect to the INDI server
indiclient.connectServer()

# Wait for the CONNECTION property of the monitored device to be defined
while not (cmonitor):
    time.sleep(0.5)

# If the monitored device is not connected, attempt to connect it
if not (dmonitor.isConnected()):
    # Property vectors are mapped to iterable Python objects
    # Hence we can access each element of the vector using Python indexing
    # each element of the "CONNECTION" vector is a ISwitch
    # Set the "CONNECT" switch to ON
    cmonitor[0].setState(PyIndi.ISS_ON)  # the "CONNECT" switch
    # Set the "DISCONNECT" switch to OFF
    cmonitor[1].setState(PyIndi.ISS_OFF)  # the "DISCONNECT" switch
    # Send this new value to the device to initiate connection
    indiclient.sendNewProperty(cmonitor)

# --- Monitoring Loop ---

# Flag to indicate if a new Number property value has been received
newval = False
# Variable to hold the updated Number property
prop = None
# Counter for the number of received updates (loop runs 10 times)
nrecv = 0
while nrecv < 10:
    # We poll the newval global variable to check for updates.
    # A more efficient approach in a real application might use threading events
    # or a queue to handle updates asynchronously.
    if newval:
        print(
            "newval for property", prop.getName(), " of device ", prop.getDeviceName()
        )
        # prop is a property vector, mapped to an iterable Python object
        # Iterate through the elements of the updated Number property
        for n in prop:
            # n is a INumber as we only monitor number vectors
            print(n.getName(), " = ", n.getValue())
        # Increment the received updates counter
        nrecv += 1
        # Reset the flag
        newval = False
