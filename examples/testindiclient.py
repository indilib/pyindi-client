"""
This script demonstrates basic usage of the PyIndi library to connect to an INDI server,
list available devices, and inspect their properties and values.

It defines a custom client class inheriting from PyIndi.BaseClient to handle INDI events
such as device and property creation/updates/removal, and server connection status.
"""

# for logging
import sys
import time
import logging

# import the PyIndi module
import PyIndi


# The IndiClient class which inherits from the module PyIndi.BaseClient class
# Note that all INDI constants are accessible from the module as PyIndi.CONSTANTNAME
class IndiClient(PyIndi.BaseClient):
    """
    Custom INDI client class inheriting from PyIndi.BaseClient.

    This class overrides various callback methods to handle events from the INDI server.
    """

    def __init__(self):
        """
        Initializes a new IndiClient instance and sets up logging.
        """
        super(IndiClient, self).__init__()
        self.logger = logging.getLogger("IndiClient")
        self.logger.info("creating an instance of IndiClient")

    def newDevice(self, d):
        """
        Callback method emitted when a new device is created on the INDI server.

        Args:
            d (PyIndi.Device): The newly created INDI device.
        """
        self.logger.info(f"new device {d.getDeviceName()}")

    def removeDevice(self, d):
        """
        Callback method emitted when a device is deleted from the INDI server.

        Args:
            d (PyIndi.Device): The INDI device that was removed.
        """
        self.logger.info(f"remove device {d.getDeviceName()}")

    def newProperty(self, p):
        """
        Callback method emitted when a new property is created for an INDI driver.

        Args:
            p (PyIndi.Property): The newly created INDI property.
        """
        self.logger.info(
            f"new property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}"
        )

    def updateProperty(self, p):
        """
        Callback method emitted when a property value is updated on the INDI server.

        Args:
            p (PyIndi.Property): The updated INDI property.
        """
        self.logger.info(
            f"update property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}"
        )

    def removeProperty(self, p):
        """
        Callback method emitted when a property is deleted for an INDI driver.

        Args:
            p (PyIndi.Property): The INDI property that was removed.
        """
        self.logger.info(
            f"remove property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}"
        )

    def newMessage(self, d, m):
        """
        Callback method emitted when a new message arrives from the INDI server.

        Args:
            d (PyIndi.Device): The device the message is from.
            m (PyIndi.Message): The received message.
        """
        self.logger.info(f"new Message {d.messageQueue(m)}")

    def serverConnected(self):
        """
        Callback method emitted when the client successfully connects to the INDI server.
        """
        self.logger.info(f"Server connected ({self.getHost()}:{self.getPort()})")

    def serverDisconnected(self, code):
        """
        Callback method emitted when the client disconnects from the INDI server.

        Args:
            code (int): The exit code of the disconnected server.
        """
        self.logger.info(
            f"Server disconnected (exit code = {code},{self.getHost()}:{self.getPort()})"
        )


# Configure basic logging
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

# Create an instance of the IndiClient class and initialize its host/port members
indiClient = IndiClient()
indiClient.setServer("localhost", 7624)

# Connect to the INDI server
print("Connecting and waiting 1 sec")
if not indiClient.connectServer():
    print(
        f"No indiserver running on {indiClient.getHost()}:{indiClient.getPort()} - Try to run"
    )
    print("  indiserver indi_simulator_telescope indi_simulator_ccd")
    sys.exit(1)

# Waiting for devices to be discovered by the client
time.sleep(1)

# Print list of devices. The list is obtained from the wrapper function getDevices as indiClient is an instance
# of PyIndi.BaseClient and the original C++ array is mapped to a Python List. Each device in this list is an
# instance of PyIndi.BaseDevice, so we use getDeviceName to print its actual name.
print("List of devices")
deviceList = indiClient.getDevices()
for device in deviceList:
    print(f"   > {device.getDeviceName()}")

# Print all properties and their associated values for each discovered device.
print("List of Device Properties")
for device in deviceList:
    print(f"-- {device.getDeviceName()}")
    # Get the list of properties for the current device
    genericPropertyList = device.getProperties()

    # Iterate through each property
    for genericProperty in genericPropertyList:
        print(f"   > {genericProperty.getName()} {genericProperty.getTypeAsString()}")

        # Check the property type and iterate through its elements (widgets)
        if genericProperty.getType() == PyIndi.INDI_TEXT:
            for widget in PyIndi.PropertyText(genericProperty):
                print(
                    f"       {widget.getName()}({widget.getLabel()}) = {widget.getText()}"
                )

        if genericProperty.getType() == PyIndi.INDI_NUMBER:
            for widget in PyIndi.PropertyNumber(genericProperty):
                print(
                    f"       {widget.getName()}({widget.getLabel()}) = {widget.getValue()}"
                )

        if genericProperty.getType() == PyIndi.INDI_SWITCH:
            for widget in PyIndi.PropertySwitch(genericProperty):
                print(
                    f"       {widget.getName()}({widget.getLabel()}) = {widget.getStateAsString()}"
                )

        if genericProperty.getType() == PyIndi.INDI_LIGHT:
            for widget in PyIndi.PropertyLight(genericProperty):
                print(
                    f"       {widget.getLabel()}({widget.getLabel()}) = {widget.getStateAsString()}"
                )

        if genericProperty.getType() == PyIndi.INDI_BLOB:
            for widget in PyIndi.PropertyBlob(genericProperty):
                print(
                    f"       {widget.getName()}({widget.getLabel()}) = <blob {widget.getSize()} bytes>"
                )

# Disconnect from the indiserver
print("Disconnecting")
indiClient.disconnectServer()
