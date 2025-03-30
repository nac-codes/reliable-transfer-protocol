# 
# Columbia University - CSEE 4119 Computer Networks
# Assignment 2 - Mini Reliable Transport 
#
# network.py - network simulator that serves as a server to the 
#   actual client and a client to the actual server. It varies
#   link loss characteristics (i.e., segment loss and bit error 
#   rate) based on an external file (e.g., loss.txt).

#!/usr/bin/env python3.10
import argparse
from socket import *
import threading
import time
import random

loss = {}

def createSocket(p):
    """
    creating network listening socket

    arguments:
    p -- the port of the network
    """
    s = socket(AF_INET,SOCK_DGRAM)
    s.bind(('',p))
    return s

def setUpLoss(lossFile):
    """
    reads loss file

    arguments:
    lossFile -- name of the loss file
    """
    for line in open(lossFile, 'r').readlines():
        loss[line.split()[0]] = [float(line.split()[1]), float(line.split()[2])]
    return True

def getCurrentLoss(st):
    """
    determines current loss rate and bit error of the link

    arguments:
    st -- the start time of the client connection
    """
    ct = time.time() - st

    lastPktLoss = 0
    lastBitError = 0

    for t in loss.keys():
        if ct > int(t):
            lastPktLoss = loss[t][0]
            lastBitError = loss[t][1]
    return lastPktLoss, lastBitError

def handleMessage(ns, ca, sa, st): 
    """
    handling the server's response (data)

    arguments:
    ns -- the network socket
    ca - the client address
    sa - the server address
    st - the connection start time
    """
    buff_size = 2000000000
    while True:
        c, a = ns.recvfrom(buff_size)
        print(f"Network received {len(c)} bytes from {a}")
        
        pktLoss, bitError = getCurrentLoss(st)
        print(f"Current loss rate: {pktLoss}, bit error rate: {bitError}")
        
        if random.random() <= pktLoss:
            print(f"Dropping packet from {a} due to packet loss")
            continue
        else:
            d = bytearray(c)
            
            # Check if any bit errors occurred
            bit_errors = 0
            for i in range(len(d)):
                for j in range(8):
                    if random.random() <= bitError:
                        d[i] = d[i] ^ (1 << j)
                        bit_errors += 1
            
            if bit_errors > 0:
                print(f"Applied {bit_errors} bit errors to packet")
                
            # Identify segment type if possible (first byte)
            if len(d) > 0:
                seg_type = d[0]
                type_str = {0: "SYN", 1: "SYN-ACK", 2: "ACK", 3: "DATA", 4: "FIN", 5: "FIN-ACK"}.get(seg_type, "UNKNOWN")
                print(f"Forwarding {type_str} segment")
                
            if a == sa:
                print(f"Forwarding packet from server {sa} to client {ca}")
                ns.sendto(d, ca)
            else:
                print(f"Forwarding packet from client {a} to server {sa}")
                ns.sendto(d, sa)
  
if __name__ == '__main__':
    # accepts commandline arguments
    parser = argparse.ArgumentParser(
                    prog='network.py',
                    description='network.py simulates the network. It forwards data between the server/client programs and varies the packet loss characteristics of the link between them.')
    parser.add_argument('networkPort', type=int, choices=range(49151,65535), metavar='networkPort: (49151 – 65535)')
    parser.add_argument('clientAddr', type=str)
    parser.add_argument('clientPort', type=int, choices=range(49151,65535), metavar='clientPort: (49151 – 65535)')
    parser.add_argument('serverAddr', type=str)
    parser.add_argument('serverPort', type=int, choices=range(49151,65535), metavar='serverPort: (49151 – 65535)')
    parser.add_argument('lossFile', type=str)

    args = parser.parse_args()

    # reads in loss file and connects required sockets
    setup = setUpLoss(args.lossFile)

    clientAddr = (args.clientAddr, args.clientPort)
    serverAddr = (args.serverAddr, args.serverPort)


    netSocket = createSocket(args.networkPort)

    startTime = time.time()
    # starts child thread that handles client requests
    t = threading.Thread(target=handleMessage, args=(netSocket, clientAddr, serverAddr, startTime, ))
    t.start()
    