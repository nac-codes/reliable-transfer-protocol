# Mini Reliable Transport Protocol

This project implements a Mini Reliable Transport Protocol (MRT) built on top of UDP. The protocol provides reliable data transfer with protection against segment losses, data corruption, and out-of-order delivery.

## Project Structure

- `client.py`: Implementation of the client-side MRT protocol
- `server.py`: Implementation of the server-side MRT protocol
- `app_client.py`: Example application using client APIs to send a file
- `app_server.py`: Example application using server APIs to receive a file
- `network.py`: Network simulator for testing under lossy conditions

## Dependencies

- Python 3.6+

## Compilation and Usage

No compilation is needed as the project is written in Python. 

### Running the Network Simulator

```
python network.py <networkPort> <clientAddr> <clientPort> <serverAddr> <serverPort> <lossFile>
```

Parameters:
- `networkPort`: Port that the network is listening on (e.g., 51000)
- `clientAddr`: Address of the client (e.g., 127.0.0.1)
- `clientPort`: Port that the client is listening on (e.g., 50000)
- `serverAddr`: Address of the server (e.g., 127.0.0.1)
- `serverPort`: Port that the server is listening on (e.g., 60000)
- `lossFile`: File containing time, segment loss rate, and bit error rate

### Running the Server

```
python app_server.py <server_port> <buffer_size> <output_file>
```

Parameters:
- `server_port`: Port for the server to listen on
- `buffer_size`: Size of the receive buffer
- `output_file`: File to write received data to

### Running the Client

```
python app_client.py <client_port> <server_addr> <server_port> <segment_size> <input_file>
```

Parameters:
- `client_port`: Port for the client to listen on
- `server_addr`: Address of the server
- `server_port`: Port of the server
- `segment_size`: Size of each data segment (0-9000 bytes)
- `input_file`: File to send to the server

## MRT Protocol Description

The MRT protocol provides the following features:

1. **Reliable Delivery**: Ensures data is delivered accurately even in the presence of segment losses and bit errors.
2. **Corruption Detection**: Uses checksums to detect and handle corrupted segments.
3. **In-Order Delivery**: Guarantees that data is delivered in the correct order.
4. **Flow Control**: Prevents overwhelming the receiver with too much data.
5. **Efficient Transmission**: Implements a sliding window mechanism for efficient transfer.

## Limitations and Constraints

- Segment size must be between 0 and 9000 bytes. Larger sizes may cause "message too long" errors.
- Very high bit error rates (>0.001) can cause the protocol to struggle with completing transfers.
- The protocol can handle packet loss rates up to 10%.

## Log File Format

Log files are generated for each client and server instance in the format `log_<port>.txt`. Each log entry includes:

```
<time> <src_port> <dst_port> <seq> <ack> <type> <payload_length>
```

Additional fields include:
- `checksum`: The checksum value calculated for the segment
- `window`: The current window size
- `retransmit`: Boolean indicating if this is a retransmission