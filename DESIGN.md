# CSEE 4119 Spring 2025, Assignment 2 Design File
## Your name: Nicholas Chimicles
## GitHub username: nac-codes

# Mini Reliable Transport Protocol Design

This document describes the design of the Mini Reliable Transport Protocol (MRT), including message types, protocol states, and how it handles various network challenges.

## Protocol Overview

The MRT protocol is built on top of UDP and provides reliable data transfer by implementing:
- Connection establishment and termination
- Reliable data transfer with acknowledgments
- Error detection through checksums
- Ordered delivery through sequence numbers
- Flow control using a sliding window mechanism

## Message Format

Each MRT segment contains the following fields:

| Field | Size (bytes) | Description |
|-------|--------------|-------------|
| Type | 1 | Segment type (SYN, ACK, DATA, FIN, etc.) |
| Seq | 4 | Sequence number |
| Ack | 4 | Acknowledgment number |
| Window | 2 | Advertised window size |
| Checksum | 8 | Error detection code |
| Payload Length | 4 | Length of payload data (up to 9000 bytes) |
| Payload | Variable | Application data (0 to segment_size bytes) |

## Segment Types

The MRT protocol defines the following segment types:

1. **SYN (Type=1)**: Used for connection establishment
2. **SYN-ACK (Type=2)**: Response to SYN during connection establishment
3. **DATA (Type=3)**: Carries application data
4. **ACK (Type=4)**: Acknowledges received segments
5. **FIN (Type=5)**: Used for connection termination
6. **FIN-ACK (Type=6)**: Response to FIN during connection termination

## Protocol States

### Client States:
- CLOSED: Initial state
- SYN_SENT: After sending SYN
- ESTABLISHED: After receiving SYN-ACK and sending ACK
- FIN_WAIT: After sending FIN
- TIME_WAIT: After receiving FIN-ACK

### Server States:
- LISTEN: Initial state, waiting for connections
- SYN_RCVD: After receiving SYN and sending SYN-ACK
- ESTABLISHED: After receiving ACK for SYN-ACK
- CLOSE_WAIT: After receiving FIN and sending ACK
- LAST_ACK: After sending FIN

## Feature Implementation

### 1. Handling Segment Losses

MRT uses a combination of timeouts and retransmissions to handle segment losses:

- **Timeout Mechanism**: For each sent segment, a timer is started. If no acknowledgment is received within the timeout period, the segment is retransmitted.
- **Retransmission Strategy**: The protocol implements a selective repeat mechanism where only unacknowledged segments are retransmitted.
- **Adaptive Timeout**: The timeout period is dynamically adjusted based on observed round-trip times.

### 2. Handling Data Corruption

Data corruption is handled through checksums:

- **Checksum Calculation**: A simple hash function is applied to the entire segment (excluding the checksum field) to generate a checksum.
- **Verification**: When a segment is received, the checksum is recalculated and compared with the received checksum. If they don't match, the segment is discarded.
- **Corrupted Segment Handling**: From the sender's perspective, a corrupted segment is equivalent to a lost segment, triggering a retransmission after timeout.

### 3. Handling Out-of-Order Delivery

To handle out-of-order delivery, MRT uses sequence numbers and a buffer at the receiver:

- **Sequence Numbers**: Each segment is assigned a sequence number that represents the position of its first byte in the data stream.
- **Receive Buffer**: Out-of-order segments are stored in the receive buffer until the missing segments arrive.
- **In-Order Delivery**: Data is delivered to the application in the correct order, regardless of the order in which segments are received.

### 4. Dealing with High-Latency Delivery

For efficient transmission over high-latency links, MRT implements:

- **Sliding Window**: Multiple segments can be in flight simultaneously without waiting for acknowledgments.
- **Window Size**: The window size determines how many unacknowledged segments can be outstanding at any time.
- **Pipelining**: The protocol pipelines segment transmissions to utilize available bandwidth efficiently.

### 5. Flow Control and Data Segmentation

Flow control is implemented to prevent overwhelming the receiver:

- **Advertised Window**: The receiver advertises the available buffer space in the Window field of ACK segments.
- **Sender Window Management**: The sender adjusts its transmission rate based on the advertised window.
- **Segmentation**: Large data chunks are split into segments of configurable size (up to 9000 bytes), allowing efficient transfer of data of any size.

## Optimizations

- **Fast Retransmit**: If multiple duplicate ACKs are received for the same sequence number, the sender assumes that segment is lost and retransmits it without waiting for the timeout.
- **Batched ACKs**: The receiver may acknowledge multiple segments with a single ACK to reduce overhead.
- **Congestion Control**: While not fully implementing TCP's congestion control, MRT does include basic mechanisms to avoid overwhelming the network.

## Limitations

- The protocol is designed for a single client-server connection.
- Very high bit error rates can lead to performance degradation as most segments become corrupted.
- Segment size is limited to 9000 bytes due to UDP datagram size limitations.
- The protocol continues retransmission indefinitely rather than giving up after a certain number of attempts.
