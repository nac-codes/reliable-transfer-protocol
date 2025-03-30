# CSEE 4119 Spring 2025, Assignment 2
## Your name: Nicholas Chimicles
## GitHub username: nac-codes

# Mini Reliable Transport Protocol (MRT)

This project implements a reliable transport protocol on top of UDP. The MRT protocol provides protection against segment losses, data corruption, out-of-order delivery, and supports flow control.

## Project Structure

- **mrt_client.py**: Client-side implementation of the MRT protocol
- **mrt_server.py**: Server-side implementation of the MRT protocol
- **app_client.py**: Example client application using MRT
- **app_server.py**: Example server application using MRT
- **network.py**: Network simulator to introduce segment loss and corruption
- **data.txt**: Sample data file for testing
- **DESIGN.md**: Design documentation for the MRT protocol
- **TESTING.md**: Testing documentation and results

## Prerequisites

- Python 3.8 or higher
- UDP port availability for client, server, and network simulator

## How to Run

### 1. Start the Server

```
python app_server.py <server_port> <buffer_size>
```

Example:
```
python app_server.py 60000 4096
```

Parameters:
- `server_port`: The port the server listens on (e.g., 60000)
- `buffer_size`: Size of the receive buffer in bytes (e.g., 4096)

### 2. Start the Network Simulator

```
python network.py <network_port> <client_addr> <client_port> <server_addr> <server_port> <loss_file>
```

Example:
```
python network.py 51000 127.0.0.1 50000 127.0.0.1 60000 loss.txt
```

Parameters:
- `network_port`: Port for the network simulator (e.g., 51000)
- `client_addr`: Client's IP address (e.g., 127.0.0.1)
- `client_port`: Client's port (e.g., 50000)
- `server_addr`: Server's IP address (e.g., 127.0.0.1)
- `server_port`: Server's port (e.g., 60000)
- `loss_file`: File specifying segment loss and bit error rates

### 3. Start the Client

```
python app_client.py <client_port> <network_addr> <network_port> <segment_size>
```

Example:
```
python app_client.py 50000 127.0.0.1 51000 1460
```

Parameters:
- `client_port`: Port for the client (e.g., 50000)
- `network_addr`: Network simulator's IP address (e.g., 127.0.0.1)
- `network_port`: Network simulator's port (e.g., 51000)
- `segment_size`: Maximum size of a segment in bytes (e.g., 1460)

## Loss File Format

The loss file specifies the segment loss rate and bit error rate over time:

```
<time> <segment_loss_rate> <bit_error_rate>
```

Example (loss.txt):
```
0 0.0 0.0
5 0.1 0.001
10 0.2 0.002
```

This means:
- At the start (t=0s): 0% segment loss, 0% bit error
- After 5 seconds: 10% segment loss, 0.1% bit error
- After 10 seconds: 20% segment loss, 0.2% bit error

## Log Files

The MRT protocol logs all segment activity to files named `log_<port>.txt`, where `<port>` is the port of the client or server. Each log entry has the format:

```
<time> <src_port> <dst_port> <seq> <ack> <type> <payload_length> <direction>
```

Example:
```
2025-02-23 14:15:35.123 50000 51000 123 0 SYN 0 SEND
```

## Protocol Features

- **Reliability**: Detects and recovers from segment losses using retransmissions
- **Error Detection**: Uses MD5 checksums to detect corrupted segments
- **Ordering**: Handles out-of-order delivery with sequence numbers
- **Flow Control**: Prevents buffer overflow using sliding window mechanism
- **Connection Management**: Establishes and terminates connections reliably

## Assumptions

1. The MRT protocol is designed to work with a single client-server connection.
2. The server always has enough buffer space to receive the amount of data requested by the application.
3. The network simulator runs on the same machine as the client and server (localhost) in the examples, but it can be configured to run on different machines.
4. The protocol is optimized for the specific requirements of this assignment and may not handle all edge cases found in production-grade protocols.