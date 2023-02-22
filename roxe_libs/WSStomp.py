import websocket
import time
from threading import Thread
import ssl
import json

BYTE = {
    'LF': '\x0A',
    'NULL': '\x00'
}

VERSIONS = '1.0,1.1'


class Stomp:
    def __init__(self, host, sockjs=False, wss=True):
        """
        Initialize STOMP communication. This is the high level API that is exposed to clients.

        Args:
            host: Hostname
            sockjs: True if the STOMP server is sockjs
            wss: True if communication is over SSL

        attention:  only support sockjsjs is True
        """
        # websocket.enableTrace(True)
        ws_host = host if sockjs is False else host + "/websocket"
        protocol = "ws://" if wss is False else "wss://"

        self.url = protocol + ws_host
        self.dispatcher = WSClient(self.url, stomp=self)

        # maintain callback registry for subscriptions -> topic (str) vs callback (func)
        self.callback_registry = {}
        # set flag to false
        self.connected = False

    def connect(self):
        """
        Connect to the remote STOMP server
        """
        # attempt to connect
        self.dispatcher.connect_ws()

        # wait until connected
        while self.connected is False:
            time.sleep(.50)

        return self.connected

    def close(self):
        self.dispatcher.disconnect()

    def subscribe(self, destination, callback):
        """
        Subscribe to a destination and supply a callback that should be executed
        when a message is received on that destination
        """
        # create entry in registry against destination
        self.callback_registry[destination] = callback
        self.dispatcher.subscribe_topic(destination)

    def unsubscribe(self, destination):
        # remove destination callback
        self.callback_registry.pop(destination)
        self.dispatcher.unsubscribe_topic(destination)

    def send(self, destination, message):
        """
        Send a message to a destination
        """
        self.dispatcher.send_msg(destination, message)


class WSClient(websocket.WebSocket):

    def __init__(self, url, msg=[], subscribe=None, stomp=None):
        self.url = url.replace("http", 'ws')
        self.stomp = stomp
        if stomp:
            self.ws = websocket.WebSocketApp(self.stomp.url)
        else:
            self.ws = websocket.WebSocketApp(self.url)

        # register websocket callbacks
        self.ws.on_open = self._on_open
        self.ws.on_message = self._on_message
        self.ws.on_error = self._on_error
        self.ws.on_close = self._on_close
        self.msg = msg
        self.subscribe = subscribe  # send message for subscribe channel

        # run event loop on separate thread
        if self.url.startswith('wss'):
            sslopt = {'cert_reqs': ssl.CERT_NONE}
        else:
            sslopt = None
        self.t = Thread(target=self.ws.run_forever, args=(None, sslopt))

        self.t.setDaemon(True)
        self.t.start()

        self.opened = False

        while self.opened is False:
            time.sleep(.50)

    def _on_message(self, message):
        """
        Executed when WS received message
        """
        if isinstance(self.msg, list):
            self.msg.append(message)
        else:
            self.msg = message

        command, headers, body = self._parse_message(message)

        # if connected, let Stomp know
        if command == "CONNECTED":
            self.stomp.connected = True

        if command == "DISCONNECTED":
            self.stomp.connected = False

        # if message received, call appropriate callback
        if command == "MESSAGE":
            print(self.stomp.callback_registry)
            if self.stomp.callback_registry:
                self.stomp.callback_registry[headers['destination']](body)
            else:
                self.msg.append(body)

    def _on_error(self, error):
        """
        Executed when WS connection errors out
        """
        print(error)

    def _on_close(self):
        """
        Executed when WS connection is closed
        """
        print("### closed ###")
        print(self.subscribe)
        # self._on_open()

    def _on_open(self):
        """
        Executed when WS connection is opened
        """
        self.opened = True
        if self.subscribe:
            # 订阅channel 需要向服务器发送订阅消息
            print(self.subscribe)
            if isinstance(self.subscribe, dict):
                self.ws.send(json.dumps(self.subscribe))
            elif isinstance(self.subscribe, str):
                self.ws.send(self.subscribe)

    def _transmit(self, command, headers, msg=None):
        """
        Marshalls and transmits the frame
        """
        # Contruct the frame
        lines = []
        lines.append(command + BYTE['LF'])
        # add headers
        for key in headers:
            lines.append(key + ":" + headers[key] + BYTE['LF'])

        lines.append(BYTE['LF'])

        # add message, if any
        if msg is not None:
            lines.append(msg)

        # terminate with null octet
        lines.append(BYTE['NULL'])

        frame = ''.join(lines)
        # print(frame)
        # transmit over ws
        self.ws.send(frame)

    def _parse_message(self, frame):
        """
        Returns:
            command
            headers
            body

        Args:
            frame: raw frame string
        """
        lines = frame.split(BYTE['LF'])

        command = lines[0].strip()
        headers = {}

        # get all headers
        i = 1
        while lines[i] != '':
            # get key, value from raw header
            (key, value) = lines[i].split(':')
            headers[key] = value
            i += 1

        # set body to None if there is no body
        body = None if lines[i + 1] == BYTE['NULL'] else lines[i + 1]

        return command, headers, body

    def connect_ws(self):
        """
        Transmit a CONNECT frame
        """

        headers = dict()
        headers['host'] = self.stomp.url
        headers['accept-version'] = VERSIONS
        headers['heart-beat'] = '10000,10000'

        self._transmit('CONNECT', headers)

    def subscribe_topic(self, destination):
        """
        Transmit a SUBSCRIBE frame
        """
        headers = dict()

        # TODO id should be auto generated
        headers['id'] = 'sub-1'
        headers['ack'] = 'client'
        headers['destination'] = destination

        self._transmit('SUBSCRIBE', headers)

    def unsubscribe_topic(self, destination):
        """
        Transmit a SUBSCRIBE frame
        """
        headers = dict()

        # TODO id should be auto generated
        headers['id'] = 'sub-1'
        headers['ack'] = 'client'
        headers['destination'] = destination

        self._transmit('UNSUBSCRIBE', headers)

    def send_msg(self, destination, message):
        """
        Transmit a SEND frame
        """
        headers = dict()

        headers['destination'] = destination
        headers['content-length'] = str(len(message))

        self._transmit('SEND', headers, msg=message)

    def disconnect(self):

        headers = {}

        self._transmit('DISCONNECT', headers)
