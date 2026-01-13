"""
This script implements a Python server that connects the Stellarium planetarium program
to an INDI server. It acts as a bridge, allowing Stellarium's Telescope Control plugin
to control a telescope connected to an INDI server.

It implements the Stellarium Telescope Control plugin protocol for communication
with Stellarium clients and uses the PyIndi library to interact with the INDI server.
"""

import signal, os, sys, logging, time, calendar, math, traceback
import socket, select

import PyIndi

# --- Global Variables ---

# INDI server host and port
indihost = "localhost"
indiport = 7624
# The name of the telescope device on the INDI server to control
inditelescope = "Telescope Simulator"
# Instance of the custom IndiClient
indiclient = None
# Flag to automatically connect to the telescope device when the INDI server is connected
autoconnect = True
# Flag indicating if the connection to the INDI server is established
indiServerConnected = False
# Flag indicating if the connection to the specified telescope device is established
isIndiTelescopeConnected = False
# Current JNow Right Ascension (RA) of the telescope
indiTelescopeRAJNOW = 0.0
# Current JNow Declination (DEC) of the telescope
indiTelescopeDECJNOW = 0.0
# Current UTC time reported by the telescope
indiTelescopeTIMEUTC = ""
# Queue for storing goto commands received from Stellarium clients
gotoQueue = []

# Stellarium server port
stelport = 10001
# Socket for listening for incoming Stellarium client connections
stelSocket = None
# Dictionary to hold connected Stellarium clients (socket object as key, StelClient instance as value)
stelClients = {}

# Flag to indicate if the script should terminate
killed = False


# --- Helper Functions for Byte Conversion ---


def to_be(n, size):
    """
    Converts an integer to a byte array of a specified size in big-endian format.

    Args:
        n (int): The integer to convert.
        size (int): The desired size of the byte array.

    Returns:
        bytearray: The integer represented as a byte array in big-endian.
    """
    b = bytearray(size)
    i = size - 1
    while i >= 0:
        b[i] = n % 256
        n = n >> 8
        i -= 1
    return b


def from_be(b):
    """
    Converts a byte array in big-endian format to an integer.

    Args:
        b (bytearray): The byte array to convert.

    Returns:
        int: The integer represented by the byte array.
    """
    n = 0
    for i in range(len(b)):
        n = (n << 8) + b[i]
    return n


def to_le(n, size):
    """
    Converts an integer to a byte array of a specified size in little-endian format.

    Args:
        n (int): The integer to convert.
        size (int): The desired size of the byte array.

    Returns:
        bytearray: The integer represented as a byte array in little-endian.
    """
    b = bytearray(size)
    i = 0
    while i < size:
        b[i] = n % 256
        n = n >> 8
        i += 1
    return b


def from_le(b):
    """
    Converts a byte array in little-endian format to an integer.

    Args:
        b (bytearray): The byte array to convert.

    Returns:
        int: The integer represented by the byte array.
    """
    n = 0
    for i in range(len(b) - 1, -1, -1):
        n = (n << 8) + b[i]
    return n


# Simple class to keep stellarium socket connections
class StelClient:
    """
    Represents a connected Stellarium client.

    Manages the socket connection, read/write buffers, and message queue
    for communication with a single Stellarium instance.
    """

    def __init__(self, sock, clientaddress):
        """
        Initializes a new StelClient instance.

        Args:
            sock (socket.socket): The socket object for the client connection.
            clientaddress (tuple): The address of the client (host, port).
        """
        self.socket = sock
        self.clientaddress = clientaddress
        self.writebuf = bytearray(120)
        self.readbuf = bytearray(120)
        self.recv = 0
        self.msgq = []
        self.tosend = 0

    def hasToWrite(self):
        """
        Checks if there is data to be sent to the client.

        Returns:
            bool: True if there is data to write, False otherwise.
        """
        return self.tosend > 0

    def performRead(self):
        """
        Performs a read operation on the client socket.

        Reads incoming data into the read buffer and processes complete messages.
        Handles client disconnection if no data is received.
        """
        # logging.info('Socket '+str(self.socket.fileno()) + ' has to read')
        buf = bytearray(120 - self.recv)
        nrecv = self.socket.recv_into(buf, 120 - self.recv)
        # logging.info('Socket '+str(self.socket.fileno()) + 'read: '+str(buf))
        if nrecv <= 0:
            logging.info("Client " + str(self.socket.fileno()) + " is away")
            self.disconnect()
            stelClients.pop(self.socket)
            return
        self.readbuf[self.recv : self.recv + nrecv] = buf
        self.recv += nrecv
        last = self.datareceived()
        if last > 0:
            self.readbuf = self.readbuf[last:]
            self.recv -= last

    def datareceived(self):
        """
        Processes the data received in the read buffer.

        Parses Stellarium protocol messages and handles goto commands.

        Returns:
            int: The number of bytes processed from the read buffer.
        """
        global gotoQueue
        p = 0
        while p < self.recv - 2:
            psize = from_le(self.readbuf[p : p + 2])
            if psize > len(self.readbuf) - p:
                break
            ptype = from_le(self.readbuf[p + 2 : p + 4])
            if ptype == 0:
                micros = from_le(self.readbuf[p + 4 : p + 12])
                if abs((micros / 1000000.0) - int(time.time())) > 60.0:
                    logging.warning(
                        "Client "
                        + str(self.socket.fileno())
                        + " clock differs for more than one minute: "
                        + str(int(micros / 1000000.0))
                        + "/"
                        + str(int(time.time()))
                    )
                targetraint = from_le(self.readbuf[p + 12 : p + 16])
                targetdecint = from_le(self.readbuf[p + 16 : p + 20])
                if targetdecint > (4294967296 / 2):
                    targetdecint = -(4294967296 - targetdecint)
                targetra = (targetraint * 24.0) / 4294967296.0
                targetdec = (targetdecint * 360.0) / 4294967296.0
                logging.info(
                    "Queuing goto (ra, dec)=("
                    + str(targetra)
                    + ", "
                    + str(targetdec)
                    + ")"
                )
                gotoQueue.append((targetra, targetdec))
                p += psize
            else:
                p += psize
        return p

    def performWrite(self):
        """
        Performs a write operation on the client socket.

        Sends data from the write buffer to the client. Handles client disconnection
        if the write fails.
        """
        global stelClients
        # logging.info('Socket '+str(self.socket.fileno()) + ' will write')
        sent = self.socket.send(self.writebuf[0 : self.tosend])
        if sent <= 0:
            logging.info("Client " + str(self.socket.fileno()) + " is away")
            self.disconnect()
            stelClients.pop(self.socket)
            return
        self.writebuf = self.writebuf[sent:]
        self.tosend -= sent
        if self.tosend == 0:
            if len(self.msgq) > 0:
                self.writebuf[0 : len(self.msgq[0])] = self.msgq[0]
                self.tosend = len(msgq[0])
                self.msgq = self.msgq[1:]

    def sendMsg(self, msg):
        """
        Queues a message to be sent to the client.

        Args:
            msg (bytearray): The message to send.
        """
        if self.tosend == 0:
            self.writebuf[0 : len(msg)] = msg
            self.tosend = len(msg)
        else:
            self.msgq.append(msg)

    def sendEqCoords(self, utc, rajnow, decjnow, status):
        """
        Sends equatorial coordinates to the Stellarium client.

        Formats the RA, DEC, UTC time, and status into a Stellarium protocol message
        and queues it for sending.

        Args:
            utc (str): The UTC time string.
            rajnow (float): The JNow Right Ascension in hours.
            decjnow (float): The JNow Declination in degrees.
            status (int): The telescope status code.
        """
        msg = bytearray(24)
        msg[0:2] = to_le(24, 2)
        msg[2:4] = to_le(0, 2)
        if utc != "":
            try:
                tstamp = calendar.timegm(time.strptime(utc, "%Y-%m-%dT%H:%M:%S"))
            except:
                tstamp = 0
        else:
            # Simulator does not send its UTC time, and timestamp are emptied somewhere
            tstamp = int(time.time())
        msg[4:12] = to_le(tstamp, 8)
        msg[12:16] = to_le(int(math.floor(rajnow * (4294967296.0 / 24.0))), 4)
        msg[16:20] = to_le(int(math.floor(decjnow * (4294967296.0 / (360.0)))), 4)
        msg[20:24] = to_le(status, 4)
        self.sendMsg(msg)

    def disconnect(self):
        """
        Disconnects the client socket.
        """
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except:
            traceback.print_exc()


# The IndiClient class which manages connections to the indi server
# and events from the telescope device.
# Keeps track (through python global variables) of the connection/deconnection
# and RA/DEC values of the telescope device.
# Beware that swig generally makes a copy of the C++ Object when calling a python method,
# so we must also make python-side copy of what we need.
class IndiClient(PyIndi.BaseClient):
    """
    Custom INDI client class that inherits from PyIndi.BaseClient.

    Manages the connection to the INDI server and handles events related to the
    specified telescope device. Updates global variables with the telescope's
    connection status, RA, and DEC.
    """

    def __init__(self, telescope):
        """
        Initializes a new IndiClient instance.

        Args:
            telescope (str): The name of the telescope device to watch.
        """
        super(IndiClient, self).__init__()
        self.logger = logging.getLogger("PyIndi.BaseClient")
        self.telescope = telescope
        self.tdevice = None

    # These new* and server* virtual methods live in a C++ thread.
    # Beware of their interaction with other python threads: swig locks
    # the python GIL before calling them from C++  and releases it at the end.
    # So it is safe to modify global python variables here.
    def newDevice(self, d):
        """
        Callback method called by the INDI client when a new device is created.

        Args:
            d (PyIndi.Device): The newly created INDI device.
        """
        # self.logger.info("new device " + d.getDeviceName())
        if d.getDeviceName() != self.telescope:
            self.logger.info("Receiving " + d.getDeviceName() + " Device...")
        self.tdevice = d

    def newProperty(self, p):
        """
        Callback method called by the INDI client when a new property is created for a device.

        Args:
            p (PyIndi.Property): The newly created INDI property.
        """
        global autoconnect, isIndiTelescopeConnected, indiTelescopeRAJNOW, indiTelescopeDECJNOW
        # self.logger.info("new property "+ p.getName() + " for device "+ p.getDeviceName())
        if p.getDeviceName() == self.telescope:
            if p.isNameMatch("CONNECTION"):
                if not (self.tdevice.isConnected()) and autoconnect:
                    self.logger.info("Autoconnecting device " + p.getDeviceName())
                    self.connectDevice(self.telescope)
                if self.tdevice.isConnected():
                    self.logger.info("Found connected device " + p.getDeviceName())
                    isIndiTelescopeConnected = True
            if p.isNameMatch("EQUATORIAL_EOD_COORD"):
                nvp = PyIndi.PropertyNumber(p)
                indiTelescopeRAJNOW = nvp[0].getValue()
                indiTelescopeDECJNOW = nvp[1].getValue()
                self.logger.info(
                    "Got JNow Eq. coords for "
                    + p.getDeviceName()
                    + ": (ra, dec)=("
                    + str(indiTelescopeRAJNOW)
                    + ", "
                    + str(indiTelescopeDECJNOW)
                    + ")"
                )

    def updateProperty(self, p):
        """
        Callback method called by the INDI client when a property's value is updated.

        Args:
            p (PyIndi.Property): The updated INDI property.
        """
        if p.getDeviceName() != self.telescope:
            return

        global isIndiTelescopeConnected
        if p.isNameMatch("CONNECTION"):
            svp = PyIndi.PropertySwitch(p)
            if svp[0].getState() == PyIndi.ISS_ON:
                isIndiTelescopeConnected = True
            if svp[1].getState() == PyIndi.ISS_ON:
                isIndiTelescopeConnected = False

        global indiTelescopeRAJNOW, indiTelescopeDECJNOW
        if p.isNameMatch("EQUATORIAL_EOD_COORD"):
            nvp = PyIndi.PropertyNumber(p)
            indiTelescopeRAJNOW = nvp[0].getValue()
            indiTelescopeDECJNOW = nvp[1].getValue()
            # self.logger.info ("RA/DEC Timestamp "+str(nvp.getTimestamp()))

        global indiTelescopeTIMEUTC
        if p.isNameMatch("TIME_UTC"):
            tvp = PyIndi.PropertyText(p)
            indiTelescopeTIMEUTC = tvp[0].getText()
            self.logger.info("UTC Time " + str(tvp[0].getText()))

    def serverConnected(self):
        """
        Callback method called by the INDI client when the connection to the INDI server is established.
        """
        global indiServerConnected
        indiServerConnected = True
        self.logger.info(
            "Server connected (" + self.getHost() + ":" + str(self.getPort()) + ")"
        )

    def serverDisconnected(self, code):
        """
        Callback method called by the INDI client when the connection to the INDI server is lost.

        Args:
            code (int): The exit code of the disconnected server.
        """
        global indiServerConnected
        self.logger.info(
            "Server disconnected (exit code = "
            + str(code)
            + ","
            + str(self.getHost())
            + ":"
            + str(self.getPort())
            + ")"
        )
        indiServerConnected = False

    # You may extend the BaseClient class with your own python methods.
    # These ones will live in the main python thread.
    def waitServer(self):
        """
        Waits for the INDI server to be available and connects to it.
        Retries connection every 5 seconds if the server is not found.
        """
        while not self.connectServer():
            self.logger.info(
                "No indiserver running on " + self.getHost() + ":" + str(self.getPort())
            )
            time.sleep(5)


def terminate(signum, frame):
    """
    Signal handler to set the killed flag for graceful termination.

    Args:
        signum (int): The signal number.
        frame (frame): The current stack frame.
    """
    killed = True


# how to get back this signal which is translated in a python exception ?
# signal.signal(signal.SIGKILL, terminate)
# Register signal handlers for graceful termination
signal.signal(signal.SIGHUP, terminate)
signal.signal(signal.SIGQUIT, terminate)

# Configure logging
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

# Create an instance of the IndiClient class and initialize its host/port members
indiclient = IndiClient(inditelescope)
indiclient.setServer(indihost, indiport)

# --- Stellarium Server Setup ---
# Whereas connection to the indiserver will be handled by the C++ thread and the
# above callbacks, connection from the stellarium client programs will be managed
# in the main python thread: we use the usual select method with non-blocking sockets,
# listening on the stellarium port (10001) and using buffered reads/writes on the
# connected stellarium client sockets.
stelSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Bind the socket to the specified port
stelSocket.bind(("", stelport))
# Listen for incoming connections (up to 5 queued)
stelSocket.listen(5)
# Set the socket to non-blocking mode
stelSocket.setblocking(0)
# Allow the socket to reuse the address
stelSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
status = 0  # Initial status for Stellarium clients

# --- Main Loop ---
try:
    while not killed:
        # try to reconnect indi server if server restarted
        if not (indiServerConnected):
            # Connect to the indi server restricting new* messages to our telescope device
            indiclient.watchDevice(inditelescope)
            indiclient.waitServer()
            logging.info(
                "Connected to indiserver@"
                + indiclient.getHost()
                + ":"
                + str(indiclient.getPort())
                + ', watching "'
                + inditelescope
                + '" device'
            )
        if isIndiTelescopeConnected:
            # logging.info('RA='+str(indiTelescopeRAJNOW)+', DEC='+str(indiTelescopeDECJNOW))
            # Send updated coordinates to all connected Stellarium clients
            for s in stelClients:
                stelClients[s].sendEqCoords(
                    indiTelescopeTIMEUTC,
                    indiTelescopeRAJNOW,
                    indiTelescopeDECJNOW,
                    status,
                )
            # Process goto commands from the queue
            if len(gotoQueue) > 0:
                logging.info("Sending goto (ra, dec)=" + str(gotoQueue[0]))
                # Get the telescope device
                d = indiclient.getDevice(inditelescope)
                # Get and set the ON_COORD_SET switch property to initiate goto
                oncoordset = d.getSwitch("ON_COORD_SET")
                oncoordset.reset()
                oncoordset[0].setState(PyIndi.ISS_ON)
                indiclient.sendNewProperty(oncoordset)

                # Get and set the target equatorial coordinates
                eqeodcoords = d.getNumber("EQUATORIAL_EOD_COORD")
                eqeodcoords[0].setValue(gotoQueue[0][0])
                eqeodcoords[1].setValue(gotoQueue[0][1])
                # Remove the processed command from the queue
                gotoQueue = gotoQueue[1:]
                # Send the updated coordinates property to the INDI server
                indiclient.sendNewProperty(eqeodcoords)
        # logging.info('Perform step')
        # perform one step
        # Use select to monitor sockets for read/write events
        readers = [stelSocket] + [s for s in stelClients]
        writers = [s for s in stelClients if stelClients[s].hasToWrite()]
        ready_to_read, ready_to_write, in_error = select.select(
            readers, writers, [], 0.5
        )
        # Handle sockets ready for reading
        for r in ready_to_read:
            if r == stelSocket:
                # Accept new Stellarium client connections
                news, newa = stelSocket.accept()
                news.setblocking(0)
                stelClients[news] = StelClient(news, newa)
                logging.info(
                    "New Stellarium client "
                    + str(news.fileno())
                    + " on port "
                    + str(newa)
                )
            else:
                # Read data from existing Stellarium clients
                stelClients[r].performRead()
        # Handle sockets ready for writing
        for r in ready_to_write:
            if r in stelClients.keys():
                stelClients[r].performWrite()
        # Handle sockets with errors
        for r in in_error:
            logging.info("Lost Stellarium client " + str(r.fileno()))
            if r in stelClients.keys():
                stelClients[r].disconnect()
                stelClients.pop(r)
        # Sleep briefly to avoid high CPU usage
        time.sleep(0.5)
except KeyboardInterrupt:
    logging.info("Bye")
else:
    traceback.print_exc()

# --- Cleanup ---
# Shutdown and close the Stellarium listening socket
stelSocket.shutdown(socket.SHUT_RDWR)
stelSocket.close()
# Disconnect all connected Stellarium clients
for sc in stelClients:
    stelClients[sc].disconnect()
stelSocket.close()
# Disconnect from the INDI server
indiclient.disconnectServer()

sys.exit(0)
