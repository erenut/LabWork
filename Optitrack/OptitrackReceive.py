# Written by Utku Eren
# 03/12/2017
# The script that receive Optitrack data via Multicast Feature


import socket as socket
import struct as struct


class OptitrackReceive:
    """The class file that receives data from Optitrack via NatNet in Multicast
    and decodes the message"""

    #
    def __init__(self, client_addr, server_addr, multicast_addr, comm_Port, data_Port):
        """Initialize the Socket and parameters"""

        self.SOCKET_BUFSIZE = 0x100000

        # Bind client address at data port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.sock.bind((client_addr, data_Port))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.SOCKET_BUFSIZE)

        # Add the client IP address to the multicast group
        self.mreq = struct.pack("=4s4s",
                                socket.inet_aton(multicast_addr),
                                socket.inet_aton(client_addr))
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, self.mreq)

        # Set to non-blocking
        self.sock.setblocking(0)

        # Start gettting the streamed data
        self._receive_data()

    #
    def _receive_data(self):
        """Receive the Data"""
        while True:
            try:
                msg, address = self.sock.recvfrom(self.SOCKET_BUFSIZE)
            except:
                pass
            else:
                # print(msg.encode('hex'))
                # print(int(msg[8:12][::-1].encode('hex'),32))
                self.decode_message(msg)

    #
    def decode_message(self, msg):
        """Decode the Message"""

        # Get the message ID
        msg_ID = int(msg[0:2][::-1].encode('hex'), 16)    # MESSAGE ID

        # Check if receiving the right message
        if msg_ID == 7:
            pck_size = int(msg[2:4][::-1].encode('hex'), 16)     # PACKAGE SIZE
            frame_num = int(msg[4:8][::-1].encode('hex'), 32)     # FRAME NUMBER
            dataset_num = int(msg[8:12][::-1].encode('hex'), 32)  # NUMBER of DATASETS
            ptr = 12

            #
            # DECODE the data of each DATASET
            for i in range(0, dataset_num):
                cnt = 0
                while msg[ptr + cnt] != '\x00':
                    cnt += 1
                ptr = ptr + cnt + 1

                # TODO: ADD OBJECT NAMES AND COORDINATES WHICH ARE NOT ADDRESSED IN THIS VERSION

            #
            # DECODE other MARKERS
            otherMARKERS_num = int(msg[ptr:(ptr + 4)][::-1].encode('hex'),
                                   32)  # NUMBER of OTHER MARKERS
            ptr += 4
            for i in range(0, otherMARKERS_num):
                x, y, z = struct.unpack(">fff", msg[ptr:(ptr + 12)])
                ptr += 12
                # print(x, y, z)
                # TODO: ADD OBJECT NAMES AND COORDINATES WHICH ARE NOT ADDRESSED IN THIS VERSION

            #
            # DECODE RIGID BODIES
            rigidBODY_num = int(msg[ptr:(ptr + 4)][::-1].encode('hex'), 32)
            ptr += 4
            for i in range(0, rigidBODY_num):

                rbody_ID = int(msg[ptr:(ptr + 4)][::-1].encode('hex'), 32)
                ptr += 4

                # decode the state vector
                x, y, z, q1, q2, q3, q0 = struct.unpack("fffffff", msg[ptr:(ptr + 28)])
                ptr += 28

                # decode rigid markers
                rigidmarker_num = int(msg[ptr:(ptr + 4)][::-1].encode('hex'), 32)
                ptr += 4
                ptr += rigidmarker_num * (3 * 4)  # 3*sizeof(float)
                ptr += rigidmarker_num * 2     # sizeof(int)
                ptr += (rigidmarker_num + 1) * 4  # sizeof(float)

                # decode parameters
                param = int(msg[ptr:(ptr + 2)][::-1].encode('hex'), 16)
                ptr += 2

                # TODO: ADD OBJECT NAMES AND COORDINATES WHICH ARE NOT ADDRESSED IN THIS VERSION

                if param:
                    # Successfully tracked
                    print "ID: %d  |    X: %f  |  Y: %f  |  Z: %f    |  Status: T" % (rbody_ID, x, z, -y)
                else:
                    # Not successful
                    print "ID: %d  |  Status: F" % rbody_ID

            return True
        # The message is not right return false
        else:
            return False


if __name__ == '__main__':

    # DEFINE ADDRESSES
    client_address = '192.168.1.2'
    server_address = '192.168.1.7'  # Motive Tracker set to Multicast
    multicast_address = '239.255.42.99'
    command_port = 1510
    data_port = 1509

    # Initiate the stream
    receiveObj = OptitrackReceive(client_address, server_address,
                                  multicast_address, command_port, data_port)
