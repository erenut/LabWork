#!/usr/bin/env python
# this example shows how to control many copter using one (or many) crazyradio dongles
# it is a slight modification from the ramp.py example

import time, sys
import socket, pickle, select
from threading import Thread
from userPositionInput import SetpointManipulator

#FIXME: Has to be launched from within the example folder
sys.path.append("../lib")
import cflib
from cflib.crazyflie import Crazyflie
from cfclient.utils.logconfigreader import LogConfig
from cflib.crtp.crtpstack import CRTPPacket, CRTPPort

import struct
import logging
logging.basicConfig(level=logging.ERROR)
# logger = logging.getLogger(__name__)


# GET the DATA from KEYBOARD
class Send_Commands:

    def __init__(self):
        self.yaw = [0] * 4
        self.posX = [0] * 4
        self.posY = [0] * 4
        self.posZ = [0] * 4
        self.quad = 0
        self.kill = 0

        # UDP Inputs
        self.UDP_IP = "127.0.0.1"
        self.UDP_Port = [5000, 5001, 5002, 5003]
        self.UDP_Sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  # udp

    def changeStuff(self, yaw = 0, pX = 0, pY = 0, pZ = 0, QuadNumber = 0, Kill = 0):
        # Select the Quad
        self.quad = (self.quad + QuadNumber) % 4
        # Change the Quad's inputs
        self.yaw[self.quad] = (self.yaw[self.quad] + yaw) % 360
        self.posX[self.quad] = self.posX[self.quad] + pX
        self.posY[self.quad] = self.posY[self.quad] + pY
        self.posZ[self.quad] = self.posZ[self.quad] + pZ
        if self.posZ[self.quad] < 0:  self.posZ[self.quad] = 0
        print "QUAD %d SetPoint /   yaw %d   /   posX %d   /   posY %d   /   posZ %d" % (self.quad, self.yaw[self.quad], self.posX[self.quad], self.posY[self.quad], self.posZ[self.quad])
        self.kill = Kill

        # send the changes to related quad!
        self.send_via_UDP()

    def send_via_UDP(self):
       #try:
            self.UDP_Sock.sendto(pickle.dumps([self.yaw[self.quad], self.posX[self.quad], self.posY[self.quad], self.posZ[self.quad], self.kill]), (self.UDP_IP, self.UDP_Port[self.quad]))
        #inally:
        #   self.udp_sock.close()


# MAIN THREAD
class Main:
    def __init__(self, IDN, uri):

        # Initial values for thrust
        self.yaw = 0
        self.posX = 0
        self.posY = 0
        self.posZ = 0

        self.idn = IDN
        self.killQuad = 0

        # UDP parameters
        self.UDP_IP = "127.0.0.1"
        self.UDP_Port = 5000 + self.idn
        self.UDP_Sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # udp
        self.UDP_Sock.bind((self.UDP_IP, self.UDP_Port))

        # Initialize the Crazyflie
        self.crazyflie = Crazyflie()
        self.uri = uri
        cflib.crtp.init_drivers()


        # You may need to update this value if your Crazyradio uses a different frequency.
        self.crazyflie.open_link(uri)

        # The definition of the logconfig can be made before connecting
        # self.log_stab = LogConfig(name="ext_pos", period_in_ms=10)
        # self.log_stab.add_variable("ext_pos.X", "float")
        # self.log_stab.add_variable("ext_pos.Y", "float")
        # self.log_stab.add_variable("ext_pos.Z", "float")

        self.log_stab = LogConfig(name="stabilizer", period_in_ms=10)
        # self.log_stab.add_variable("stabilizer.roll", "float")
        # self.log_stab.add_variable("stabilizer.pitch", "float")
        # self.log_stab.add_variable("stabilizer.yaw", "float")
        self.log_stab.add_variable("stabilizer.curX", "float")
        self.log_stab.add_variable("stabilizer.curY", "float")
        self.log_stab.add_variable("stabilizer.curZ", "float")
        self.log_stab.add_variable("stabilizer.thrust", "float")

        # self.log_stab = LogConfig(name="controller", period_in_ms=10)
        # self.log_stab.add_variable("controller.actuatorThrust", "float")
        # self.log_stab.add_variable("controller.roll", "float")
        # self.log_stab.add_variable("controller.pitch", "float")
        # self.log_stab.add_variable("controller.yaw", "float")

        # self.log_stab = LogConfig(name="ctrltarget", period_in_ms=10)
        # self.log_stab.add_variable("ctrltarget.tarX", "float")
        # self.log_stab.add_variable("ctrltarget.tarY", "float")
        # self.log_stab.add_variable("ctrltarget.tarZ", "float")
        # self.log_stab.add_variable("ctrltarget.roll", "float")
        # self.log_stab.add_variable("ctrltarget.yaw", "float")


        #-------------
        #FIXME: This part only exists because of a bug in the libraries (threading)
        self.crazyflie.commander.send_setpoint(0, 0, 0, 0)
        time.sleep(0.1)
        self.crazyflie.close_link()
        self.crazyflie.open_link(uri)
        #-------------

        # Set up the callback when connected
        self.crazyflie.connected.add_callback(self.connectSetupFinished)

    def _stab_log_error(self, logconf, msg):
        print("Error when logging %s: %s" % (logconf.name, msg))

    def _stab_log_data(self, timestamp, data, logconf):
        print("[%d][%s]: %s" % (timestamp, logconf.name, data))

    def connectSetupFinished(self, linkURI):
        # Start a separate thread to do the motor test.
        # Do not hijack the calling thread!
        Thread(target=self.pulse_command).start()

    def pulse_command(self):
        # Indicate that connection is Established
        print "Connected to %s" % self.uri

        try:
            self.crazyflie.log.add_config(self.log_stab)
            self.log_stab.data_received_cb.add_callback(self._stab_log_data)
            self.log_stab.error_cb.add_callback(self._stab_log_error)
            self.log_stab.start()

            # Inner Infinite Loop
            while self.killQuad == 0:

                # Listen for UDP data
                data = select.select([self.UDP_Sock], [], [], 0)

                # Send current state of CF to CF
                pk = CRTPPacket()
                pk.port = CRTPPort.STABILIZER
                pk.data = struct.pack('<fff', 0, 0, 0)
                self.crazyflie.send_packet(pk)
                #self.crazyflie.input.send_currentstate(0, 0, self.thrust, 0, 0, 0)

                # Send data to crazyflie
                # This the data placeholders defined in the onboard firmware
                self.crazyflie.commander.send_setpoint(self.posY, -self.posX, self.yaw, int(self.posZ*1000))
                time.sleep(0.01)

                # Check if new data arrived!
                if data[0] != []:
                    [self.yaw, self.posX, self.posY, self.posZ, self.killQuad] = pickle.loads(data[0][0].recv(1024))  # buffer size is 1024 bytes

        finally:
            print "Closing the connection with %s" % self.uri
            self.crazyflie.commander.send_setpoint(0, 0, 0, 0)
            time.sleep(0.1)
            self.crazyflie.close_link()
            self.UDP_Sock.close()


# Starting connection to both two copter. If a link using the same dongle
# is created, the communication will be shared with existing link
# Current implementation (as of Crazyradio 0.52) will divide the available
# bandwidth by 3 if used in that way so go easy on the log messages ;-)
# Future Crazyradio firmware will make that a bit more efficient


if __name__ == '__main__':

    # Set of Crazyflie addresses to be Connected
    IDN_address = []
    IDN_address.append("radio://0/30/1M/E7E7E7E7E7")
 #   IDN_address.append("radio://0/10/1M/E7E7E7E7E1")
 #   IDN_address.append("radio://0/10/1M/E7E7E7E7E2")
 #   IDN_address.append("radio://0/10/1M/E7E7E7E7E3")
 #   IDN_address.append("radio://0/10/1M/E7E7E7E7E4")

    # Run all Crazyflies
    cnt = 0
    for addr in IDN_address:
        Main(cnt, addr)
        cnt = cnt + 1
        time.sleep(0.5)

    All_or_Nothing = Send_Commands()
    KeyDetector = SetpointManipulator(All_or_Nothing.changeStuff)
