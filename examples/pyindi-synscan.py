"""
This script acts as a bridge between the INDI protocol and the SynScan serial protocol.
It allows controlling a telescope that uses the SynScan protocol (like some Sky-Watcher
and Celestron mounts) through an INDI server.

It can expose the SynScan interface either as a virtual serial port or a TCP server.
"""
#!/usr/bin/python
# -*- coding: utf8 -*-

import logging
import os
import sys
import pty
import time
import datetime
import math
import struct
import socket
import select

import PyIndi

# --- Configuration Variables ---

# Enable or disable the virtual serial port interface
USE_SERIAL = True
# Enable or disable the TCP server interface
USE_TCP = True
# The TCP port to listen on if USE_TCP is True
TCP_LISTEN_PORT = 8091
# The path for the virtual serial port device file if USE_SERIAL is True
DEVICE_PORT = "/tmp/indi-synscan"
# The host of the INDI server
INDI_SERVER_HOST = "localhost"
# The port of the INDI server
INDI_SERVER_PORT = 7624
# The name of the telescope device on the INDI server to control
TELESCOPE_DEVICE = "EQMod Mount"
# Enable or disable simulation mode for the telescope device
TELESCOPE_SIMULATION = True
# The name of the simulation property for the telescope device
TELESCOPE_SIMPROP = "SIMULATION"


class IndiClient(PyIndi.BaseClient):
    """
    Custom INDI client class that inherits from PyIndi.BaseClient.

    Handles connection status and messages from the INDI server.
    """
    global logger

    def __init__(self):
        """
        Initializes a new IndiClient instance.
        """
        super(IndiClient, self).__init__()
        self.isconnected = False

    def newMessage(self, d, m):
        """
        Callback method called by the INDI client when a new message is received from a device.

        Args:
            d (PyIndi.Device): The device the message is from.
            m (PyIndi.Message): The received message.
        """
        logger.info("Message for " + d.getDeviceName() + ":" + d.messageQueue(m))

    def serverConnected(self):
        """
        Callback method called by the INDI client when the connection to the INDI server is established.
        """
        self.isconnected = True
        logger.info(
            "Server connected (" + self.getHost() + ":" + str(self.getPort()) + ")"
        )

    def serverDisconnected(self, code):
        """
        Callback method called by the INDI client when the connection to the INDI server is lost.

        Args:
            code (int): The exit code of the disconnected server.
        """
        self.isconnected = False
        logger.info(
            "Server disconnected (exit code = "
            + str(code)
            + ","
            + str(self.getHost())
            + ":"
            + str(self.getPort())
            + ")"
        )


# Sets to keep track of properties that failed to retrieve to avoid
# repeatedly trying to get them.
numberFailures = set()
switchFailures = set()
textFailures = set()


def getNumberWithRetry(prop, ntry=5, delay=0.2):
    """
    Attempts to retrieve a Number property from the device with retries.

    Args:
        prop (str): The name of the Number property.
        ntry (int): The number of retry attempts.
        delay (float): The delay between retries in seconds.

    Returns:
        PyIndi.PropertyNumber or None: The property if successfully retrieved, None otherwise.
    """
    while ntry > 0:
        p = device.getNumber(prop)
        if p.isValid():
            numberFailures.discard(prop)
            return p
        if prop in numberFailures:
            return None
        logger.info("Unable to get number property " + prop + ", retrying")
        ntry -= 1
        time.sleep(delay)
    logger.info("Unable to get number property " + prop + ", marking as failed")
    numberFailures.add(prop)
    return None


def getSwitchWithRetry(prop, ntry=5, delay=0.2):
    """
    Attempts to retrieve a Switch property from the device with retries.

    Args:
        prop (str): The name of the Switch property.
        ntry (int): The number of retry attempts.
        delay (float): The delay between retries in seconds.

    Returns:
        PyIndi.PropertySwitch or None: The property if successfully retrieved, None otherwise.
    """
    while ntry > 0:
        p = device.getSwitch(prop)
        if p.isValid():
            switchFailures.discard(prop)
            return p
        if prop in switchFailures:
            return None
        logger.info("Unable to get switch property " + prop + ", retrying")
        ntry -= 1
        time.sleep(delay)
    logger.info("Unable to get switch property " + prop + ", marking as failed")
    switchFailures.add(prop)
    return None


def getTextWithRetry(prop, ntry=5, delay=0.2):
    """
    Attempts to retrieve a Text property from the device with retries.

    Args:
        prop (str): The name of the Text property.
        ntry (int): The number of retry attempts.
        delay (float): The delay between retries in seconds.

    Returns:
        PyIndi.PropertyText or None: The property if successfully retrieved, None otherwise.
    """
    while ntry > 0:
        p = device.getText(prop)
        if p.isValid():
            textFailures.discard(prop)
            return p
        if prop in textFailures:
            return None
        logger.info("Unable to get text property " + prop + ", retrying")
        ntry -= 1
        time.sleep(delay)
    logger.info("Unable to get text property " + prop + ", marking as failed")
    textFailures.add(prop)
    return None


def process_command(buf, indiclient, logger):
    """
    Processes incoming SynScan commands and translates them to INDI commands.

    Args:
        buf (bytearray): The buffer containing the received SynScan command.
        indiclient (IndiClient): The INDI client instance.
        logger (logging.Logger): The logger instance.

    Returns:
        bytearray: The response to be sent back in SynScan protocol.
    """
    global device
    # Default error reply in SynScan protocol
    reply_error = b"#"
    i = 0
    reply = b""
    while i < len(buf):
        cmd = buf[i]
        i += 1
        # Jump command (no operation)
        if cmd == ord(b"\x00"):
            pass
        # End of command marker
        elif cmd == ord("#"):
            reply += b"#"
        # Echo command
        elif cmd == ord("K"):
            if not (indiclient.isconnected):
                reply += reply_error
            else:
                reply += buf[i : i + 1] + b"#"
            i += 1
        # Check if the INDI device is connected before processing other commands
        elif not (device) or not (indiclient.isconnected) or not (device.isConnected()):
            logger.info("Lost device " + TELESCOPE_DEVICE + ": cannot process command")
            return reply + reply_error
        # Alignment complete? (Always reports complete for simplicity)
        elif cmd == ord("J"):
            reply += b"\x01" + b"#"
        # Get Ra/Dec (JNow Equatorial Coordinates)
        elif cmd in [ord("e"), ord("E")]:
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            radeg = (p[0].getValue() * 360.0) / 24.0
            decdeg = p[1].getValue()
            if decdeg < 0.0:
                decdeg = 360.0 + decdeg
            # Convert degrees to SynScan's internal 24-bit or 32-bit integer format
            rahex = hex(int((radeg * 2**24) / 360.0))[2:].zfill(6).upper() + "00"
            dechex = hex(int((decdeg * 2**24) / 360.0))[2:].zfill(6).upper() + "00"
            if sys.version_info >= (3,):
                rahex = bytes(rahex, "ascii")
                dechex = bytes(dechex, "ascii")
            if cmd == ord("e"): # 32-bit coordinates
                reply += rahex + b"," + dechex + b"#"
            else: # 24-bit coordinates
                reply += rahex[0:4] + b"," + dechex[0:4] + b"#"
        # Get time (UTC)
        elif cmd == ord("h"):
            p = getTextWithRetry("TIME_UTC")
            if p is None:
                reply += reply_error
                continue
            utc8601 = p[0].getText()
            if p[1].getText():
                offset = int(p[1].getText())
            else:
                offset = 0
            # Parse the ISO 8601 time string
            utc = datetime.datetime.strptime(utc8601, "%Y-%m-%dT%H:%M:%S")
            # Adjust for the offset (though SynScan protocol might expect local time)
            utc = utc + datetime.timedelta(0, 0, 0, 0, 0, offset)
            if offset < 0:
                offset = 256 - offset # SynScan uses unsigned byte for offset
            # Pack time components into SynScan format
            reply += (
                struct.pack(
                    "BBBBBBBB",
                    utc.hour,
                    utc.minute,
                    utc.second,
                    utc.month,
                    utc.day,
                    utc.year - 2000, # SynScan uses year since 2000
                    offset,
                    0x00, # DST flag (not used here)
                )
                + b"#"
            )
        # Get Mount Model
        elif cmd == ord("m"):
            p = getTextWithRetry("MOUNTINFORMATION")
            if p is None:
                m = b"!" # Error indicator
            else:
                # Map INDI mount names to SynScan model bytes
                skywatcher_models = {
                    "EQ6": b"\x00",
                    "HEQ5": b"\x01",
                    "EQ5": b"\x02",
                    "EQ3": b"\x03",
                    "EQ8": b"\x04",
                    "AZ-EQ6": b"\x05",
                    "AZ-EQ5": b"\x06",
                }
                if p[0].getText() in skywatcher_models:
                    m = skywatcher_models[p[0].getText()]
                else:
                    m = b"\x00" # Default to EQ6 if model is unknown
            reply += m + b"#"
        # Get Location (Geographic Coordinates)
        elif cmd == ord("w"):
            p = getNumberWithRetry("GEOGRAPHIC_COORD")
            if p is None:
                reply += reply_error
                continue
            latdeg = p[0].getValue()
            longdeg = p[1].getValue()
            elev = p[2].getValue() # Elevation is not used in SynScan location reply
            latd = b"\x00" # Latitude direction (0 for North, 1 for South)
            if latdeg < 0.0:
                latd = b"\x01"
                latdeg = -(latdeg)
            # Convert latitude degrees to degrees, minutes, seconds
            latfrac, lata = math.modf(latdeg)
            latfrac, latb = math.modf(latfrac * 60)
            latfrac, latc = math.modf(latfrac * 60)
            longh = b"\x00" # Longitude direction (0 for East, 1 for West)
            if longdeg > 180.0:
                longdeg -= 360.0
            if longdeg < 0.0:
                longh = b"\x01"
                longdeg = -(longdeg)
            # Convert longitude degrees to degrees, minutes, seconds
            longfrac, longe = math.modf(longdeg)
            longfrac, longf = math.modf(longfrac * 60)
            longfrac, longg = math.modf(longfrac * 60)
            # Pack location components into SynScan format
            reply += (
                struct.pack("BBB", int(lata), int(latb), int(latc))
                + latd
                + struct.pack("BBB", int(longe), int(longf), int(longg))
                + longh
                + b"#"
            )
        # Get Version (Firmware Version)
        elif cmd == ord("V"):
            # This is a hardcoded response for compatibility.
            # A real implementation might try to get a firmware version property from INDI.
            # reply += b"21#" # Example version
            # reply += b"\x04\x0E#" # Example version bytes
            # reply += b"\x03\x03#" # Example version bytes
            # nex skywatcher ?
            # reply += b"042508#"
            reply += b"032507" # Common version string
            # celestron / old skywatcher ?
            # reply += b"\x04\x25\x07"
            # reply += b"\x04\x25\x07#" normally with a # but this corrupts the indi-synscan driver
        # Set time (UTC)
        elif cmd == ord("H"):
            # Unpack time components from the command buffer
            [h, m, s, mth, d, y, offset, dst] = buf[i : i + 8]
            i += 8
            y += 2000 # SynScan uses year since 2000
            if offset < 0:
                offset = 256 - offset # Convert unsigned byte back to signed
            # Create datetime object and adjust for offset
            lt = datetime.datetime(y, mth, d, h, m, s, 0, None)
            utc = lt - datetime.timedelta(0, 0, 0, 0, 0, offset)
            logger.info("Setting time to " + utc.isoformat() + " " + str(offset))
            # Get the TIME_UTC property and set its values
            p = getTextWithRetry("TIME_UTC")
            if p is None:
                reply += reply_error
                continue
            p[0].setText(utc.isoformat())
            p[1].setText(str(offset))
            # Send the updated property to the INDI server
            indiclient.sendNewProperty(p)
            reply += b"#"
        # Set Location (Geographic Coordinates)
        elif cmd == ord("W"):
            # Unpack location components from the command buffer
            data = buf[i : i + 8]
            i += 8
            # Convert degrees, minutes, seconds back to degrees
            lat = data[0] + (data[1] / 60) + (data[2] / 3600)
            if data[3] == 1:
                lat = -lat # Apply South direction
            long = data[4] + (data[5] / 60) + (data[6] / 3600)
            if data[7] == 1:
                long = 360.0 - long # Apply West direction (SynScan uses 0-360 for longitude)
            # Get the GEOGRAPHIC_COORD property and set its values
            p = getNumberWithRetry("GEOGRAPHIC_COORD")
            if p is None:
                reply += reply_error
                continue
            p[0].setValue(lat)
            p[1].setValue(long)
            # Send the updated property to the INDI server
            indiclient.sendNewProperty(p)
            reply += b"#"
        # Goto/Sync command
        elif cmd in [ord("r"), ord("R"), ord("s"), ord("S")]:
            ingoto = cmd in [ord("r"), ord("R")] # Check if it's a goto command
            if cmd in [ord("r"), ord("s")]: # 32-bit coordinates
                rahour = (int(buf[i : i + 8], 16) * 24.0) / (2**32)
                decdeg = (int(buf[i + 9 : i + 17], 16) * 360.0) / (2**32)
                i += 17
            else: # 24-bit coordinates
                rahour = (int(buf[i : i + 4], 16) * 24.0) / (2**16)
                decdeg = (int(buf[i + 5 : i + 9], 16) * 360.0) / (2**16)
                i += 9
            if decdeg >= 270.0:  # Adjust declination for values > 270 (SynScan uses 0-360)
                decdeg = decdeg - 360.0
            # Get the target coordinate property and set the new RA and DEC values
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            p[0].setValue(rahour)
            p[1].setValue(decdeg)
            # Get the ON_COORD_SET switch property to initiate Goto or Sync
            pcs = getSwitchWithRetry("ON_COORD_SET")
            if pcs is None:
                reply += reply_error
                continue
            if ingoto:
                # Set the "Goto" switch
                pcs.reset()
                pcs[0].setState(PyIndi.ISS_ON)
                logger.info("Goto " + str(rahour) + ", " + str(decdeg))
            else:
                # Set the "Sync" switch
                pcs.reset()
                pcs[2].setState(PyIndi.ISS_ON)
                logger.info("Sync " + str(rahour) + ", " + str(decdeg))
            # Send the updated switch and number properties to the INDI server
            indiclient.sendNewProperty(pcs)
            indiclient.sendNewProperty(p)
            reply += b"#"
        # In Goto? command
        elif cmd == ord("L"):
            # Check the state of the target coordinate property
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            if p.getState() == PyIndi.IPS_BUSY:
                reply += b"1#" # Return 1 if busy (in goto)
            else:
                reply += b"0#" # Return 0 if not busy
        # Abort Goto command
        elif cmd == ord("M"):
            # Check if the mount is currently busy
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            if p.getState() == PyIndi.IPS_BUSY:
                # Get the TELESCOPE_ABORT_MOTION switch property and set it to ON
                p = getSwitchWithRetry("TELESCOPE_ABORT_MOTION")
                if p is None:
                    reply += reply_error
                    continue
                p[0].setState(PyIndi.ISS_ON)
                # Send the updated property to the INDI server
                indiclient.sendNewProperty(p)
            reply += b"#"
        # Move West/East or North/South command
        elif cmd == ord("P"):
            # Unpack motion data from the command buffer
            data = buf[i : i + 7]
            i += 7
            if data[0] != 2:  # Check for supported rate mode (variable rate not supported)
                reply += reply_error
                continue
            if data[1] == 16: # Check if it's a West/East motion command
                pmotionname = "TELESCOPE_MOTION_WE"
            else:  # Should be 17 for North/South motion
                pmotionname = "TELESCOPE_MOTION_NS"
            # Get the corresponding motion switch property
            pmotion = getSwitchWithRetry(pmotionname)
            if pmotion is None:
                reply += reply_error
                continue
            rate = data[3] # Get the slew rate from the command
            if rate == 0:  # Stop motion
                pmotion.reset()
                indiclient.sendNewProperty(pmotion)
            else: # Start motion
                # Get the TELESCOPE_SLEW_RATE switch property to set the desired speed
                prate = getSwitchWithRetry("TELESCOPE_SLEW_RATE")
                if prate is None or len(prate) < 1:  # Check if slew rate property exists
                    reply += reply_error
                    continue
                # Map SynScan rate values to INDI slew rate switches
                prateswitches = {
                    "SLEW_GUIDE": None,
                    "SLEW_CENTERING": None,
                    "SLEW_FIND": None,
                    "SLEW_MAX": None,
                }
                # Reset all slew rate switches and find the corresponding switch objects
                for p in prate:
                    p.setState(PyIndi.ISS_OFF)
                    if p.getName() in prateswitches:
                        prateswitches[p.getName()] = p
                # Default to the last switch if no specific rate switch is found
                prateset = prate[len(prate) - 1]
                # Select the appropriate slew rate switch based on the SynScan rate
                if rate == 1 and prateswitches["SLEW_GUIDE"]:
                    prateset = prateswitches["SLEW_GUIDE"]
                if 2 <= rate <= 4 and prateswitches["SLEW_CENTERING"]:
                    prateset = prateswitches["SLEW_CENTERING"]
                if 5 <= rate <= 7 and prateswitches["SLEW_FIND"]:
                    prateset = prateswitches["SLEW_FIND"]
                if 8 <= rate <= 9 and prateswitches["SLEW_MAX"]:
                    prateset = prateswitches["SLEW_MAX"]
                # Set the selected slew rate switch to ON
                prateset.setState(PyIndi.ISS_ON)
                # Send the updated slew rate property to the INDI server
                indiclient.sendNewProperty(prate)
                movedir = data[2] # Get the move direction from the command
                if movedir == 36:  # Positive move (West for RA, North for DEC)
                    pmotion[0].setState(PyIndi.ISS_ON)
                    pmotion[1].setState(PyIndi.ISS_OFF)
                else:  # Should be 37 for negative move (East for RA, South for DEC)
                    pmotion[0].setState(PyIndi.ISS_OFF)
                    pmotion[1].setState(PyIndi.ISS_ON)
                # Send the updated motion property to the INDI server
                indiclient.sendNewProperty(pmotion)
            reply += b"#"
        # Pierside command
        elif cmd == ord("p"):
            # Get the TELESCOPE_PIER_SIDE switch property
            p = getSwitchWithRetry("TELESCOPE_PIER_SIDE")
            if p is None:
                reply += reply_error
                continue
            if p[0].getState() == PyIndi.ISS_ON:  # Check if the pier side is East
                reply += b"E#" # Return 'E' for East
            else:
                reply += b"W#" # Return 'W' for West
        # Get Tracking command
        elif cmd == ord("t"):
            # Get the TELESCOPE_TRACK_RATE switch property
            p = getSwitchWithRetry("TELESCOPE_TRACK_RATE")
            if p is None:
                reply += reply_error
                continue
            mode = b"0" # Default to unknown mode
            # Check if any tracking rate is enabled
            if any(p[n].getState() == PyIndi.ISS_ON for n in range(4)):
                mode = b"2" # Indicate tracking is on (SynScan mode 2 or 3)
            reply += mode + b"#"
        # Set Tracking command
        elif cmd == ord("T"):
            # Get the desired tracking mode from the command
            mode = buf[i]
            i += 1
            # Get the TELESCOPE_TRACK_RATE switch property
            p = getSwitchWithRetry("TELESCOPE_TRACK_RATE")
            if p is None:
                reply += reply_error
                continue
            if mode in [ord("2"), ord("3")]:  # Check for EQ or PEC tracking modes
                # If not already in EQ tracking, set the EQ tracking switch to ON
                if p[0].getState() == PyIndi.ISS_OFF:
                    p.reset()
                    p[0].setState(ON) # Assuming ON is defined elsewhere or using PyIndi.ISS_ON
                    indiclient.sendNewProperty(p)
            else: # Other modes (like Alt/Az or Off)
                # If any tracking is on, turn off all tracking rates
                if any(p[n].getState() == PyIndi.ISS_ON for n in range(4)):
                    p.reset()
                    indiclient.sendNewProperty(p)
            reply += b"#"
        else:  # Unknown command
            reply += reply_error # Return error for unknown commands
            i += 1
    return reply


# --- Main Execution ---

# Configure logging for the script
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)
logger = logging.getLogger("pyindi-synscan")

# Initialize the INDI client and set the server host/port
indiclient = IndiClient()
indiclient.setServer(INDI_SERVER_HOST, INDI_SERVER_PORT)
# Tell the INDI client to watch the specified telescope device
indiclient.watchDevice(TELESCOPE_DEVICE)
device = None # Variable to hold the telescope device object

# Connect to the INDI server and get the telescope device.
# This section waits until the server is connected and the device is available.
# The timeout is set to 2 seconds in the synscan driver's tty_read, so we
# need to ensure the device is ready before the driver tries to read from the port.
logger.info(
    "Connecting server " + indiclient.getHost() + ":" + str(indiclient.getPort())
)
serverconnected = indiclient.connectServer()
while not (serverconnected):
    logger.info(
        "No indiserver running on "
        + indiclient.getHost()
        + ":"
        + str(indiclient.getPort())
    )
    time.sleep(2)
    serverconnected = indiclient.connectServer()
# Get the telescope device object
if not (device):
    device = indiclient.getDevice(TELESCOPE_DEVICE)
    while not (device):
        logger.info("Trying to get device " + TELESCOPE_DEVICE)
        time.sleep(0.5)
        device = indiclient.getDevice(TELESCOPE_DEVICE)
logger.info("Got device " + TELESCOPE_DEVICE)

# If the device is not connected, attempt to connect it.
if not (device.isConnected()):
    # If simulation is enabled, set the simulation property to ON.
    if TELESCOPE_SIMULATION:
        logger.info("setting " + TELESCOPE_SIMPROP + " On")
        device_sim = device.getSwitch(TELESCOPE_SIMPROP)
        while not (device_sim):
            logger.info("Trying to get poperty " + TELESCOPE_SIMPROP)
            time.sleep(0.5)
            device_sim = device.getSwitch(TELESCOPE_SIMPROP)

        # Set the "ENABLE" switch for simulation to ON
        device_sim[0].setState(PyIndi.ISS_ON)
        # Set the "DISABLE" switch for simulation to OFF
        device_sim[1].setState(PyIndi.ISS_OFF)
        # Send the updated simulation property to the INDI server
        indiclient.sendNewProperty(device_sim)

    # Get the CONNECTION switch property
    if not (device.isConnected()):
        device_connect = device.getSwitch("CONNECTION")
        while not (device_connect):
            logger.info("Trying to connect device " + TELESCOPE_DEVICE)
            time.sleep(0.5)
            device_connect = device.getSwitch("CONNECTION")
    # If still not connected, set the "CONNECT" switch to ON
    if not (device.isConnected()):
        device_connect[0].setState(PyIndi.ISS_ON)  # the "CONNECT" switch
        device_connect[1].setState(PyIndi.ISS_OFF)  # the "DISCONNECT" switch
        indiclient.sendNewProperty(device_connect)
    # Wait until the device is reported as connected
    while not (device.isConnected()):
        time.sleep(0.2)
logger.info("Device " + TELESCOPE_DEVICE + " connected")

# --- Interface Setup (Serial or TCP) ---

# If serial interface is enabled, create a virtual serial port.
if USE_SERIAL:
    logger.info("Creating virtual serial port " + DEVICE_PORT)
    # Create a pseudo-terminal pair
    master, slave = pty.openpty()
    # Create a symbolic link to the slave end of the pseudo-terminal
    os.symlink(os.ttyname(slave), DEVICE_PORT)

# If TCP interface is enabled, create a TCP server socket.
if USE_TCP:
    # Create a TCP/IP socket
    server_name = "0.0.0.0" # Listen on all available interfaces
    server_port = TCP_LISTEN_PORT
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (server_name, server_port)
    logger.info(
        "Starting up on {0} port {1}\n".format(server_address[0], server_address[1])
    )
    # Bind the socket to the specified address and port
    sock.bind(server_address)
    # Listen for incoming connections (queue up to 1 connection)
    sock.listen(1)

# --- Communication Loop ---

# List of sockets to monitor for read events
rlist = [master, sock]

# List of sockets to monitor for write events (not used in this simple example)
wlist = []
# List of sockets to monitor for exceptional conditions (errors)
xlist = [master, sock]

try:
    # Main loop to handle incoming connections and data
    while True:
        # Use select to wait for activity on the sockets with a timeout
        rready, wready, eready = select.select(
            rlist, wlist, xlist, 1
        )  # timeout 1 sec to catch ctrl-C
        # Process sockets ready for reading
        for f in rready:
            if f == master:
                # Handle data from the virtual serial port
                chars = os.read(master, 1024)
                if sys.version_info < (3,):
                    chars = bytearray(chars)
                # while chars!=b'': # This loop seems incorrect and is commented out
                logger.info("read: " + repr(chars))
                # Process the received SynScan command
                reply = process_command(chars, indiclient, logger)
                # logger.info("write: "+ repr(reply)) # Log the raw reply
                # Split the reply by '#' and send each part followed by '#'
                for c in reply.split(b"#")[:-1]:
                    logger.info("write: " + repr(c + b"#"))
                    os.write(master, c + b"#")
                    # chars=os.read(master, 1024) # This read seems incorrect and is commented out
                    # if sys.version_info < (3,):
                    #    chars=bytearray(chars)
            if f == sock:
                # Handle new incoming TCP connections
                # SkySafari v4.0.1 continously opens and closed the connection,
                # while Stellarium via socat opens it and keeps it open using:
                # $ ./socat GOPEN:/dev/ptyp0,ignoreeof TCP:raspberrypi8:4030
                # (probably socat which is maintaining the link)
                # sys.stdout.write("waiting for a connection\n") # Debug print
                connection, client_address = sock.accept()
                chars = "" # Variable to hold received data
                try:
                    logger.info(
                        "Client connected: {0}, {1}".format(
                            client_address[0], client_address[1]
                        )
                    )
                    # Loop to receive data from the connected client
                    while True:
                        chars = connection.recv(1024)
                        if len(chars) == 0:
                            break # Break if no data is received (client disconnected)
                        if sys.version_info < (3,):
                            chars = bytearray(chars)
                        logger.info("read: " + repr(chars))
                        # Process the received SynScan command
                        reply = process_command(chars, indiclient, logger)
                        if reply != b"":
                            # Send the reply back to the client
                            connection.sendall(reply)
                            logger.info("write: " + repr(reply))
                        else:
                            logger.info("nothing to respond")
                finally:
                    # Ensure the connection is closed when done
                    connection.close()

except KeyboardInterrupt:
    logger.info("pyindi-synscan stopped (Ctrl-C)")

# --- Cleanup ---

# If serial interface was enabled, remove the virtual serial port device file.
if USE_SERIAL:
    os.remove(DEVICE_PORT)
