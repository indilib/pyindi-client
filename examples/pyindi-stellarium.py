# A python server for the stellarium planetarium program
# it implements the stellarium Telescope Control plugin protocol.
import signal, os, sys, logging, time, calendar, math, traceback
import socket, select

import PyIndi

indihost = "localhost"
indiport = 7624
inditelescope = "Telescope Simulator"
indiclient = None
autoconnect = True
indiServerConnected = False
isIndiTelescopeConnected = False
indiTelescopeRAJNOW = 0.0
indiTelescopeDECJNOW = 0.0
indiTelescopeTIMEUTC = ""
gotoQueue = []

stelport = 10001
stelSocket = None
# current stellarium clients
stelClients = {}

killed = False


def to_be(n, size):
    b = bytearray(size)
    i = size - 1
    while i >= 0:
        b[i] = n % 256
        n = n >> 8
        i -= 1
    return b


def from_be(b):
    n = 0
    for i in range(len(b)):
        n = (n << 8) + b[i]
    return n


def to_le(n, size):
    b = bytearray(size)
    i = 0
    while i < size:
        b[i] = n % 256
        n = n >> 8
        i += 1
    return b


def from_le(b):
    n = 0
    for i in range(len(b) - 1, -1, -1):
        n = (n << 8) + b[i]
    return n


# Simple class to keep stellarium socket connections
class StelClient:
    def __init__(self, sock, clientaddress):
        self.socket = sock
        self.clientaddress = clientaddress
        self.writebuf = bytearray(120)
        self.readbuf = bytearray(120)
        self.recv = 0
        self.msgq = []
        self.tosend = 0

    def hasToWrite(self):
        return self.tosend > 0

    def performRead(self):
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
        if self.tosend == 0:
            self.writebuf[0 : len(msg)] = msg
            self.tosend = len(msg)
        else:
            self.msgq.append(msg)

    def sendEqCoords(self, utc, rajnow, decjnow, status):
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
    def __init__(self, telescope):
        super(IndiClient, self).__init__()
        self.logger = logging.getLogger("PyIndi.BaseClient")
        self.telescope = telescope
        self.tdevice = None

    # These new* and server* virtual methods live in a C++ thread.
    # Beware of their interaction with other python threads: swig locks
    # the python GIL before calling them from C++  and releases it at the end.
    # So it is safe to modify global python variables here.
    def newDevice(self, d):
        # self.logger.info("new device " + d.getDeviceName())
        if d.getDeviceName() != self.telescope:
            self.logger.info("Receiving " + d.getDeviceName() + " Device...")
        self.tdevice = d

    def newProperty(self, p):
        global autoconnect, isIndiTelescopeConnected, indiTelescopeRAJNOW, indiTelescopeDECJNOW
        # self.logger.info("new property "+ p.getName() + " for device "+ p.getDeviceName())
        if p.getDeviceName() == self.telescope:
            if p.getName() == "CONNECTION":
                if not (self.tdevice.isConnected()) and autoconnect:
                    self.logger.info("Autoconnecting device " + p.getDeviceName())
                    self.connectDevice(self.telescope)
                if self.tdevice.isConnected():
                    self.logger.info("Found connected device " + p.getDeviceName())
                    isIndiTelescopeConnected = True
            if p.getName() == "EQUATORIAL_EOD_COORD":
                nvp = p.getNumber()
                indiTelescopeRAJNOW = nvp[0].value
                indiTelescopeDECJNOW = nvp[1].value
                self.logger.info(
                    "Got JNow Eq. coords for "
                    + p.getDeviceName()
                    + ": (ra, dec)=("
                    + str(indiTelescopeRAJNOW)
                    + ", "
                    + str(indiTelescopeDECJNOW)
                    + ")"
                )

    def removeProperty(self, p):
        pass

    def newBLOB(self, bp):
        pass

    def newSwitch(self, svp):
        global isIndiTelescopeConnected
        # self.logger.info ("new Switch "+ svp.name.decode() + " for device "+ svp.device.decode())
        if svp.device == self.telescope:
            if svp.name == "CONNECTION":
                if svp[0].s == PyIndi.ISS_ON:
                    isIndiTelescopeConnected = True
                if svp[1].s == PyIndi.ISS_ON:
                    isIndiTelescopeConnected = False

    def newNumber(self, nvp):
        global indiTelescopeRAJNOW, indiTelescopeDECJNOW
        if nvp.device == self.telescope:
            if nvp.name == "EQUATORIAL_EOD_COORD":
                indiTelescopeRAJNOW = nvp[0].value
                indiTelescopeDECJNOW = nvp[1].value
                # self.logger.info ("RA/DEC Timestamp "+str(nvp.timestamp))

    def newText(self, tvp):
        global indiTelescopeTIMEUTC
        if tvp.device == self.telescope:
            if tvp.name == "TIME_UTC":
                indiTelescopeTIMEUTC = tvp[0].text
                self.logger.info("UTC Time " + str(tvp[0].text))

    def newLight(self, lvp):
        pass

    def newMessage(self, d, m):
        pass

    def serverConnected(self):
        global indiServerConnected
        indiServerConnected = True
        self.logger.info(
            "Server connected (" + self.getHost() + ":" + str(self.getPort()) + ")"
        )

    def serverDisconnected(self, code):
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
        while not self.connectServer():
            self.logger.info(
                "No indiserver running on " + self.getHost() + ":" + str(self.getPort())
            )
            time.sleep(5)


def terminate(signum, frame):
    killed = True


# how to get back this signal which is translated in a python exception ?
# signal.signal(signal.SIGKILL, terminate)
signal.signal(signal.SIGHUP, terminate)
signal.signal(signal.SIGQUIT, terminate)

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)

# Create an instance of the IndiClient class and initialize its host/port members
indiclient = IndiClient(inditelescope)
indiclient.setServer(indihost, indiport)

# Whereas connection to the indiserver will be handled by the C++ thread and the
# above callbacks, connection from the stellarium client programs will be managed
# in the main python thread: we use the usual select method with non-blocking sockets,
# listening on the stellarium port (10001) and using buffered reads/writes on the
# connected stellarium client sockets.
stelSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
stelSocket.bind(("", stelport))
stelSocket.listen(5)
stelSocket.setblocking(0)
stelSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
status = 0
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
            for s in stelClients:
                stelClients[s].sendEqCoords(
                    indiTelescopeTIMEUTC,
                    indiTelescopeRAJNOW,
                    indiTelescopeDECJNOW,
                    status,
                )
            if len(gotoQueue) > 0:
                logging.info("Sending goto (ra, dec)=" + str(gotoQueue[0]))
                d = indiclient.getDevice(inditelescope)
                oncoordset = d.getSwitch("ON_COORD_SET")
                oncoordset[0].s = PyIndi.ISS_ON
                oncoordset[1].s = PyIndi.ISS_OFF
                oncoordset[2].s = PyIndi.ISS_OFF
                indiclient.sendNewSwitch(oncoordset)
                eqeodcoords = d.getNumber("EQUATORIAL_EOD_COORD")
                eqeodcoords[0].value = gotoQueue[0][0]
                eqeodcoords[1].value = gotoQueue[0][1]
                gotoQueue = gotoQueue[1:]
                indiclient.sendNewNumber(eqeodcoords)
        # logging.info('Perform step')
        # perform one step
        readers = [stelSocket] + [s for s in stelClients]
        writers = [s for s in stelClients if stelClients[s].hasToWrite()]
        ready_to_read, ready_to_write, in_error = select.select(
            readers, writers, [], 0.5
        )
        for r in ready_to_read:
            if r == stelSocket:
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
                stelClients[r].performRead()
        for r in ready_to_write:
            if r in stelClients.keys():
                stelClients[r].performWrite()
        for r in in_error:
            logging.info("Lost Stellarium client " + str(r.fileno()))
            if r in stelClients.keys():
                stelClients[r].disconnect()
                stelClients.pop(r)
        time.sleep(0.5)
except KeyboardInterrupt:
    logging.info("Bye")
else:
    traceback.print_exc()

stelSocket.shutdown(socket.SHUT_RDWR)
stelSocket.close()
for sc in stelClients:
    stelClients[sc].disconnect()
stelSocket.close()
indiclient.disconnectServer()

sys.exit(0)
