"""
This is a minimal example demonstrating the basic steps to connect to an INDI server
using the PyIndi library.

It defines a simple client class and connects to a server running on localhost:7624.
A real application would typically include more logic to interact with INDI devices
and handle events after connecting.
"""

import PyIndi


class IndiClient(PyIndi.BaseClient):
    """
    A minimal INDI client class inheriting from PyIndi.BaseClient.

    This class does not override any callback methods, serving only as a basic
    client instance for connection.
    """

    def __init__(self):
        """
        Initializes a new minimal IndiClient instance.
        """
        super(IndiClient, self).__init__()


# Create an instance of the minimal IndiClient class
indiclient = IndiClient()
# Set the INDI server host and port
indiclient.setServer("localhost", 7624)

# Connect to the INDI server
indiclient.connectServer()

# Enter an infinite loop to keep the client running.
# In a real application, you would typically have event handling or other logic here
# to interact with INDI devices and process data.
while 1:
    pass
