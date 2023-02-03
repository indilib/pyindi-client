import PyIndi


class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()


indiclient = IndiClient()
indiclient.setServer("localhost", 7624)

indiclient.connectServer()
while 1:
    pass
