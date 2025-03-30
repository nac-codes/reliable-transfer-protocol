# CSEE 4119 Spring 2025, Assignment 2 Design File
## Your name: Nicholas Chimicles
## GitHub username: nac-codes

# Mini Reliable Transport Protocol (MRT) Design

## 1. Protocol Overview

The Mini Reliable Transport Protocol (MRT) is designed to provide reliable data transfer over an unreliable UDP connection. MRT implements the following reliability features:
- Connection establishment and termination
- Reliable data transfer with acknowledgments
- Error detection via checksums
- Handling of out-of-order delivery
- Flow control
- Segmentation for large data transfers

## 2. Segment Structure

Each MRT segment consists of a header and an optional payload. The header structure is as follows:

| Field          | Size (bytes) | Description                                      |
|----------------|--------------|--------------------------------------------------|
| Type           | 1            | Type of segment (SYN, ACK, DATA, etc.)           |
| Sequence #     | 4            | Sequence number of the segment                   |
| Acknowledgment #| 4            | Acknowledgment number (next expected sequence #) |
| Checksum       | 8            | MD5 hash (first 8 characters) for error detection|
| Payload Length | 3            | Length of the payload in bytes                   |
| Payload        | Variable     | The actual data (optional)                       |

Total header size: 20 bytes

### Segment Types:
- SYN (0): Connection establishment request
- SYN-ACK (1): Connection establishment acknowledgment
- ACK (2): Data acknowledgment
- DATA (3): Data segment
- FIN (4): Connection termination request
- FIN-ACK (5): Connection termination acknowledgment

## 3. Connection Establishment (Three-way Handshake)

MRT uses a three-way handshake similar to TCP:

1. **Client → Server**: SYN segment with initial sequence number
2. **Server → Client**: SYN-ACK segment with server's initial sequence number and acknowledgment of client's sequence number
3. **Client → Server**: ACK segment acknowledging server's sequence number

## 4. Data Transfer

### Reliable Transfer
Data transfer uses a sliding window protocol with cumulative acknowledgments:

1. **Sender**: Divides large data into segments and sends multiple segments up to the window size
2. **Receiver**: Acknowledges received segments with ACK segments
3. **Sender**: Advances the window when ACKs are received

### Loss Recovery
- **Timeout-based retransmission**: If an ACK is not received within a timeout period, the sender retransmits unacknowledged segments
- **Window-based flow control**: The sender limits the number of unacknowledged segments to prevent overwhelming the receiver

### Out-of-order Delivery
- The receiver maintains a buffer for out-of-order segments
- When segments arrive out of order, they are stored in the buffer
- When the missing segment(s) arrive, the receiver can reconstruct the original data stream

### Error Detection
- A checksum is computed for each segment using MD5 hashing
- The receiver verifies the checksum and discards corrupted segments
- The sender will retransmit corrupted segments when no ACK is received

## 5. Flow Control

Flow control is implemented using a fixed-size sliding window:
- The window size determines how many unacknowledged segments can be in flight
- The receiver can process segments up to its buffer size
- The sender will not send more data than the receiver can handle

## 6. Connection Termination

MRT uses a simplified connection termination process:

1. **Client → Server**: FIN segment to initiate connection closure
2. **Server → Client**: FIN-ACK segment to acknowledge the closure
3. The client closes the connection upon receiving the FIN-ACK

## 7. Handling Protocol Challenges

### Segment Loss
- Sender uses timeouts to detect lost segments
- Retransmission of unacknowledged segments after timeout

### Data Corruption
- Checksums detect corrupted segments
- Receiver discards corrupted segments
- Sender retransmits when no ACK is received

### Out-of-order Delivery
- Sequence numbers identify the correct order
- Receiver buffers out-of-order segments
- Data delivered to application in correct order

### High Link Latency
- Sliding window allows multiple segments in flight
- Sender doesn't have to wait for each ACK before sending next segment

## 8. Optimizations

- Random initial sequence numbers for security
- Threaded implementation for concurrent sending and receiving
- Efficient buffering for out-of-order segments
- Logging for debugging and analysis