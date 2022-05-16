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

USE_SERIAL = True
USE_TCP = True
TCP_LISTEN_PORT = 8091
DEVICE_PORT = "/tmp/indi-synscan"
INDI_SERVER_HOST = "localhost"
INDI_SERVER_PORT = 7624
TELESCOPE_DEVICE = "EQMod Mount"
TELESCOPE_SIMULATION = True
TELESCOPE_SIMPROP = "SIMULATION"


class IndiClient(PyIndi.BaseClient):
    global logger

    def __init__(self):
        super(IndiClient, self).__init__()
        self.isconnected = False

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
        # logger.info("New value for number "+ nvp.name)
        pass

    def newText(self, tvp):
        pass

    def newLight(self, lvp):
        pass

    def newMessage(self, d, m):
        logger.info("Message for " + d.getDeviceName() + ":" + d.messageQueue(m))

    def serverConnected(self):
        self.isconnected = True
        logger.info(
            "Server connected (" + self.getHost() + ":" + str(self.getPort()) + ")"
        )

    def serverDisconnected(self, code):
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


numberFailures = set()
switchFailures = set()
textFailures = set()

def getNumberWithRetry(prop, ntry=5, delay=0.2):
    while ntry > 0:
        p = device.getNumber(prop)
        if type(p) == PyIndi.PropertyViewNumber:
            numberFailures.discard(prop)
            return p
        if prop in numberFailures:
            return None
        logger.info("Unable to get number property "+prop+", retrying")
        ntry -= 1
        time.sleep(delay)
    logger.info("Unable to get number property "+prop+", marking as failed")
    numberFailures.add(prop)
    return None

def getSwitchWithRetry(prop, ntry=5, delay=0.2):
    while ntry > 0:
        p = device.getSwitch(prop)
        if type(p) == PyIndi.PropertyViewSwitch:
            switchFailures.discard(prop)
            return p
        if prop in switchFailures:
            return None
        logger.info("Unable to get switch property "+prop+", retrying")
        ntry -= 1
        time.sleep(delay)
    logger.info("Unable to get switch property "+prop+", marking as failed")
    switchFailures.add(prop)
    return None

def getTextWithRetry(prop, ntry=5, delay=0.2):
    while ntry > 0:
        p = device.getText(prop)
        if type(p) == PyIndi.PropertyViewText:
            textFailures.discard(prop)
            return p
        if prop in textFailures:
            return None
        logger.info("Unable to get text property "+prop+", retrying")
        ntry -= 1
        time.sleep(delay)
    logger.info("Unable to get text property "+prop+", marking as failed")
    textFailures.add(prop)
    return None

def process_command(buf, indiclient, logger):
    global device
    # Default error
    reply_error = b"#"
    i = 0
    reply = b""
    while i < len(buf):
        cmd = buf[i]
        i += 1
        # Jump
        if cmd == ord(b"\x00"):
            pass
        elif cmd == ord("#"):
            reply += b'#'
        # Echo
        elif cmd == ord("K"):
            if not (indiclient.isconnected):
                reply += reply_error
            else:
                reply += buf[i : i + 1] + b"#"
            i += 1
        elif not (device) or not (indiclient.isconnected) or not (device.isConnected()):
            logger.info("Lost device " + TELESCOPE_DEVICE + ": cannot process command")
            return reply + reply_error
        # Alignment complete ?
        elif cmd == ord("J"):
            reply += b"\x01" + b"#"
        # Get Ra/Dec
        elif cmd in [ord('e'), ord('E')]:
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            radeg = (p[0].value * 360.0) / 24.0
            decdeg = p[1].value
            if decdeg < 0.0:
                decdeg = 360.0 + decdeg
            rahex = hex(int((radeg * 2**24) / 360.0))[2:].zfill(6).upper() + "00"
            dechex = hex(int((decdeg * 2**24) / 360.0))[2:].zfill(6).upper() + "00"
            if sys.version_info >= (3,):
                rahex = bytes(rahex, "ascii")
                dechex = bytes(dechex, "ascii")
            if cmd == ord("e"):
                reply += rahex + b"," + dechex + b"#"
            else:
                reply += rahex[0:4] + b"," + dechex[0:4] + b"#"
        # Get time
        elif cmd == ord("h"):
            p = getTextWithRetry("TIME_UTC")
            if p is None:
                reply += reply_error
                continue
            utc8601 = p[0].text
            if p[1].text:
                offset = int(p[1].text)
            else:
                offset = 0
            # could use dateutil.parser.parse
            utc = datetime.datetime.strptime(utc8601, "%Y-%m-%dT%H:%M:%S")
            utc = utc + datetime.timedelta(0, 0, 0, 0, 0, offset)
            if offset < 0:
                offset = 256 - offset
            reply += (
                struct.pack(
                    "BBBBBBBB",
                    utc.hour,
                    utc.minute,
                    utc.second,
                    utc.month,
                    utc.day,
                    utc.year - 2000,
                    offset,
                    0x00,
                )
                + b"#"
            )
        # Get Model
        elif cmd == ord("m"):
            p = getTextWithRetry("MOUNTINFORMATION")
            if p is None:
                m = b'!'
            else:
                skywatcher_models = {
                    "EQ6": b"\x00",
                    "HEQ5": b"\x01",
                    "EQ5": b"\x02",
                    "EQ3": b"\x03",
                    "EQ8": b"\x04",
                    "AZ-EQ6": b"\x05",
                    "AZ-EQ5": b"\x06",
                }
                if p[0].text in skywatcher_models:
                    m = skywatcher_models[p[0].text]
                else:
                    m = b"\x00"
            reply += m + b"#"
        # Get Location
        elif cmd == ord("w"):
            p = getNumberWithRetry("GEOGRAPHIC_COORD")
            if p is None:
                reply += reply_error
                continue
            latdeg = p[0].value
            longdeg = p[1].value
            elev = p[2].value
            latd = b"\x00"
            if latdeg < 0.0:
                latd = b"\x01"
                latdeg = -(latdeg)
            latfrac, lata = math.modf(latdeg)
            latfrac, latb = math.modf(latfrac * 60)
            latfrac, latc = math.modf(latfrac * 60)
            longh = b"\x00"
            if longdeg > 180.0:
                longdeg -= 360.0
            if longdeg < 0.0:
                longh = b"\x01"
                longdeg = -(longdeg)
            longfrac, longe = math.modf(longdeg)
            longfrac, longf = math.modf(longfrac * 60)
            longfrac, longg = math.modf(longfrac * 60)
            reply += (
                struct.pack("BBB", int(lata), int(latb), int(latc))
                + latd
                + struct.pack("BBB", int(longe), int(longf), int(longg))
                + longh
                + b"#"
            )
        # Get Version
        elif cmd == ord("V"):
            # reply += b"21#"
            # reply += b"\x04\x0E#"
            # reply += b"\x03\x03#"
            # nex skywatcher ?
            # reply += b"042508#"
            reply += b"032507"
            # celestron / old skywatcher ?
            # reply += b"\x04\x25\x07"
            # reply += b"\x04\x25\x07#" normally with a # but this corrupts the indi-synscan driver
        # Set time
        elif cmd == ord("H"):
            [h, m, s, mth, d, y, offset, dst] = buf[i : i + 8]
            i += 8
            y += 2000
            if offset < 0:
                offset = 256 - offset
            lt = datetime.datetime(y, mth, d, h, m, s, 0, None)
            utc = lt - datetime.timedelta(0, 0, 0, 0, 0, offset)
            logger.info("Setting time to " + utc.isoformat() + " " + str(offset))
            p = getTextWithRetry("TIME_UTC")
            if p is None:
                reply += reply_error
                continue
            p[0].text = utc.isoformat()
            p[1].text = str(offset)
            indiclient.sendNewText(p)
            reply += b"#"
        # Set Location
        elif cmd == ord("W"):
            data = buf[i : i + 8]
            i += 8
            lat = data[0] + (data[1] / 60) + (data[2] / 3600)
            if data[3] == 1:
                lat = -lat
            long = data[4] + (data[5] / 60) + (data[6] / 3600)
            if data[7] == 1:
                long = 360.0 - long
            p = getNumberWithRetry("GEOGRAPHIC_COORD")
            if p is None:
                reply += reply_error
                continue
            p[0].value = lat
            p[1].value = long
            indiclient.sendNewNumber(p)
            reply += b"#"
        # Goto/Sync
        elif cmd in [ord('r'), ord('R'), ord('s'), ord('S')]:
            ingoto = cmd in [ord('r'), ord('R')]
            if cmd in [ord('r'), ord('s')]:
                rahour = (int(buf[i : i + 8], 16) * 24.0) / (2**32)
                decdeg = (int(buf[i + 9 : i + 17], 16) * 360.0) / (2**32)
                i += 17
            else:
                rahour = (int(buf[i : i + 4], 16) * 24.0) / (2**16)
                decdeg = (int(buf[i + 5 : i + 9], 16) * 360.0) / (2**16)
                i += 9
            if decdeg >= 270.0:  # I don't check for 90.0 < values < 270.0
                decdeg = decdeg - 360.0
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            p[0].value = rahour
            p[1].value = decdeg
            pcs = getSwitchWithRetry("ON_COORD_SET")
            if pcs is None:
                reply += reply_error
                continue
            if ingoto:
                pcs[0].setState(PyIndi.ISS_ON)
                pcs[1].setState(PyIndi.ISS_OFF)
                pcs[2].setState(PyIndi.ISS_OFF)
                logger.info("Goto " + str(rahour) + ", " + str(decdeg))
            else:
                pcs[0].setState(PyIndi.ISS_OFF)
                pcs[1].setState(PyIndi.ISS_OFF)
                pcs[2].setState(PyIndi.ISS_ON)
                logger.info("Sync " + str(rahour) + ", " + str(decdeg))
            indiclient.sendNewSwitch(pcs)
            indiclient.sendNewNumber(p)
            reply += b"#"
        # in goto ?
        elif cmd == ord("L"):
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            if p.getState() == PyIndi.IPS_BUSY:
                reply += b'1#'
            else:
                reply += b'0#'
        # abort goto
        elif cmd == ord("M"):
            p = getNumberWithRetry("EQUATORIAL_EOD_COORD")
            if p is None:
                reply += reply_error
                continue
            if p.getState() == PyIndi.IPS_BUSY:
                p = getSwitchWithRetry("TELESCOPE_ABORT_MOTION")
                if p is None:
                    reply += reply_error
                    continue
                p[0].setState(PyIndi.ISS_ON)
                indiclient.sendNewSwitch(p)
            reply += b'#'
        # MoveWE/MoveNS
        elif cmd == ord("P"):
            data = buf[i : i + 7]
            i += 7
            if data[0] != 2: # variable rate not supported
                reply += reply_error
                continue
            if data[1] == 16:
                pmotionname = "TELESCOPE_MOTION_WE"
            else:  # should be 17
                pmotionname = "TELESCOPE_MOTION_NS"
            pmotion = getSwitchWithRetry(pmotionname)
            if pmotion is None:
                reply += reply_error
                continue
            rate = data[3]
            if rate == 0:  # stop
                pmotion[0].setState(PyIndi.ISS_OFF)
                pmotion[1].setState(PyIndi.ISS_OFF)
                indiclient.sendNewSwitch(pmotion)
            else:
                prate = getSwitchWithRetry("TELESCOPE_SLEW_RATE")
                if prate is None or len(prate) < 1:   # no slew rate
                    reply += reply_error
                    continue
                prateswitches = {
                    "SLEW_GUIDE": None,
                    "SLEW_CENTERING": None,
                    "SLEW_FIND": None,
                    "SLEW_MAX": None,
                }
                for p in prate:
                    p.setState(PyIndi.ISS_OFF)
                    if p.getName() in prateswitches:
                        prateswitches[p.getName()] = p
                prateset = prate[len(prate) - 1]
                if rate == 1 and prateswitches["SLEW_GUIDE"]:
                    prateset = prateswitches["SLEW_GUIDE"]
                if 2 <= rate <= 4 and prateswitches["SLEW_CENTERING"]:
                    prateset = prateswitches["SLEW_CENTERING"]
                if 5 <= rate <= 7 and prateswitches["SLEW_FIND"]:
                    prateset = prateswitches["SLEW_FIND"]
                if 8 <= rate <= 9 and prateswitches["SLEW_MAX"]:
                    prateset = prateswitches["SLEW_MAX"]
                prateset.setState(PyIndi.ISS_ON)
                indiclient.sendNewSwitch(prate)
                movedir = data[2]
                if movedir == 36:  # positive move i.e. West/North
                    pmotion[0].setState(PyIndi.ISS_ON)
                    pmotion[1].setState(PyIndi.ISS_OFF)
                else:  # should be 37 negative move i.e. East/South
                    pmotion[0].setState(PyIndi.ISS_OFF)
                    pmotion[1].setState(PyIndi.ISS_ON)
                indiclient.sendNewSwitch(pmotion)
            reply += b"#"
        # Pierside
        elif cmd == ord("p"):
            p = getSwitchWithRetry("TELESCOPE_PIER_SIDE")
            if p is None:
                reply += reply_error
                continue
            if p[0].getState() == PyIndi.ISS_ON:  # PIER_EAST
                reply += b"E#"
            else:
                reply += b"W#"
        # Get Tracking
        elif cmd == ord("t"):
            p = getSwitchWithRetry("TELESCOPE_TRACK_RATE")
            if p is None:
                reply += reply_error
                continue
            mode=b"0"
            if any(p[n].getState() == PyIndi.ISS_ON for n in range(4)):
                mode = b"2"
            reply += mode + b"#"
        # Set Tracking
        elif cmd == ord("T"):
            mode = buf[i]
            i += 1
            p = getSwitchWithRetry("TELESCOPE_TRACK_RATE")
            if p is None:
                reply += reply_error
                continue
            if mode in [ord('2'), ord('3')]:  # EQ/PEC tracking (no Alt/Az)
                if p[0].getState() == PyIndi.ISS_OFF:
                    p[0].setState(ON)
                    p[1].setState(OFF)
                    p[2].setState(OFF)
                    p[3].setState(OFF)
                    indiclient.sendNewSwitch(p)
            else:
                if any(p[n].getState() == PyIndi.ISS_ON for n in range(4)):
                    p[0].setState(OFF)
                    p[1].setState(OFF)
                    p[2].setState(OFF)
                    p[3].setState(OFF)
                    indiclient.sendNewSwitch(p)
            reply += b'#'
        else:  # unknown
            reply += reply_error
            i += 1
    return reply


logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)
logger = logging.getLogger("pyindi-synscan")


# initialize INDI device
indiclient = IndiClient()
indiclient.setServer(INDI_SERVER_HOST, INDI_SERVER_PORT)
indiclient.watchDevice(TELESCOPE_DEVICE)
device = None

# Connect server and device before launching serial port listening
# timeout is 2 secs in tty_read from the synscan driver
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
if not (device):
    device = indiclient.getDevice(TELESCOPE_DEVICE)
    while not (device):
        logger.info("Trying to get device " + TELESCOPE_DEVICE)
        time.sleep(0.5)
        device = indiclient.getDevice(TELESCOPE_DEVICE)
logger.info("Got device " + TELESCOPE_DEVICE)

if not (device.isConnected()):
    if TELESCOPE_SIMULATION:
        logger.info("setting " + TELESCOPE_SIMPROP + " On")
        device_sim = device.getSwitch(TELESCOPE_SIMPROP)
        while not (device_sim):
            logger.info("Trying to get poperty " + TELESCOPE_SIMPROP)
            time.sleep(0.5)
            device_sim = device.getSwitch(TELESCOPE_SIMPROP)

        device_sim[0].setState(PyIndi.ISS_ON)  # the "ENABLE" switch
        device_sim[1].setState(PyIndi.ISS_OFF)  # the "DISABLE" switch
        indiclient.sendNewSwitch(device_sim)

if not (device.isConnected()):
    device_connect = device.getSwitch("CONNECTION")
    while not (device_connect):
        logger.info("Trying to connect device " + TELESCOPE_DEVICE)
        time.sleep(0.5)
        device_connect = device.getSwitch("CONNECTION")
if not (device.isConnected()):
    device_connect[0].setState(PyIndi.ISS_ON)  # the "CONNECT" switch
    device_connect[1].setState(PyIndi.ISS_OFF)  # the "DISCONNECT" switch
    indiclient.sendNewSwitch(device_connect)
while not (device.isConnected()):
    time.sleep(0.2)
logger.info("Device " + TELESCOPE_DEVICE + " connected")

if USE_SERIAL:
    logger.info("Creating virtual serial port " + DEVICE_PORT)
    # create the virtual serial port
    master, slave = pty.openpty()
    # and link it to /tmp/indi-synscan
    os.symlink(os.ttyname(slave), DEVICE_PORT)

if USE_TCP:
    # Create a TCP/IP socket
    server_name = "0.0.0.0"
    server_port = TCP_LISTEN_PORT
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (server_name, server_port)
    logger.info(
        "Starting up on {0} port {1}\n".format(server_address[0], server_address[1])
    )
    sock.bind(server_address)
    sock.listen(1)

rlist = [master, sock]
wlist = []
xlist = [master, sock]

try:
    while True:
        rready, wready, eready = select.select(
            rlist, wlist, xlist, 1
        )  # timeout 1 sec to catch ctrl-C
        for f in rready:
            if f == master:
                # serial
                chars = os.read(master, 1024)
                if sys.version_info < (3,):
                    chars = bytearray(chars)
                # while chars!=b'':
                logger.info("read: " + repr(chars))
                reply = process_command(chars, indiclient, logger)
                # logger.info("write: "+ repr(reply))
                for c in reply.split(b"#")[:-1]:
                    logger.info("write: " + repr(c + b"#"))
                    os.write(master, c + b"#")
                    # chars=os.read(master, 1024)
                    # if sys.version_info < (3,):
                    #    chars=bytearray(chars)
            if f == sock:
                # SkySafari v4.0.1 continously opens and closed the connection,
                # while Stellarium via socat opens it and keeps it open using:
                # $ ./socat GOPEN:/dev/ptyp0,ignoreeof TCP:raspberrypi8:4030
                # (probably socat which is maintaining the link)
                # sys.stdout.write("waiting for a connection\n")
                connection, client_address = sock.accept()
                chars = ""
                try:
                    logger.info(
                        "Client connected: {0}, {1}".format(
                            client_address[0], client_address[1]
                        )
                    )
                    while True:
                        chars = connection.recv(1024)
                        if len(chars) == 0:
                            break
                        if sys.version_info < (3,):
                            chars = bytearray(chars)
                        logger.info("read: " + repr(chars))
                        reply = process_command(chars, indiclient, logger)
                        if reply != b"":
                            connection.sendall(reply)
                            logger.info("write: " + repr(reply))
                        else:
                            logger.info("nothing to respond")
                finally:
                    connection.close()

except KeyboardInterrupt:
    logger.info("pyindi-synscan stopped (Ctrl-C)")

if USE_SERIAL:
    os.remove(DEVICE_PORT)
