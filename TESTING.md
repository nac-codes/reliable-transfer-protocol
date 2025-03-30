# Mini Reliable Transport Protocol Testing

This document describes the tests performed on the Mini Reliable Transport Protocol (MRT) implementation and the results observed.

## Test Environment

- Operating System: MacOS 24.3.0
- Python Version: 3.9+
- Network: Local (127.0.0.1)
- Test File: large_data.txt (large text file used for transfer tests)

## Test Scenarios

### 1. Basic Functionality Testing

**Test:** Transfer a small file (1KB) with no network impairments
**Network Configuration:** Loss rate = 0.0, Bit error rate = 0.0
**Result:** Successful transfer with 100% data integrity

**Test:** Transfer a medium file (1MB) with no network impairments
**Network Configuration:** Loss rate = 0.0, Bit error rate = 0.0
**Result:** Successful transfer with 100% data integrity

### 2. Segment Size Testing

**Test:** Transfer with different segment sizes
**Segment Sizes Tested:** 100, 999, 5000, 9000 bytes
**Network Configuration:** Loss rate = 0.01, Bit error rate = 0.0001
**Results:**
- All segment sizes transferred successfully
- Larger segments (5000, 9000) showed higher throughput but were more susceptible to bit errors
- Segment sizes above 9000 bytes resulted in "message too long" errors

### 3. Loss Rate Testing

**Test:** Transfer large_data.txt with different packet loss rates
**Segment Size:** 999 bytes
**Network Configurations:**
1. Loss rate = 0.01, Bit error rate = 0.0
2. Loss rate = 0.05, Bit error rate = 0.0
3. Loss rate = 0.10, Bit error rate = 0.0

**Results:**
- 1% loss: Successful transfer with minimal retransmissions
- 5% loss: Successful transfer with moderate retransmissions
- 10% loss: Successful transfer with significant retransmissions but still completed

### 4. Bit Error Rate Testing

**Test:** Transfer large_data.txt with different bit error rates
**Segment Size:** 999 bytes
**Network Configurations:**
1. Loss rate = 0.0, Bit error rate = 0.0001
2. Loss rate = 0.0, Bit error rate = 0.001
3. Loss rate = 0.0, Bit error rate = 0.01

**Results:**
- 0.0001 bit error rate: Successful transfer with occasional corrupted segments
- 0.001 bit error rate: Successful transfer but with high latency due to frequent retransmissions
- 0.01 bit error rate: Transfer failed to make progress due to nearly all segments being corrupted

### 5. Combined Impairment Testing

**Test:** Transfer large_data.txt with combined loss and bit errors
**Network Configurations:**
1. Loss rate = 0.05, Bit error rate = 0.0001 (moderate impairment)
2. Loss rate = 0.10, Bit error rate = 0.0001 (severe impairment)

**Results:**
- Moderate impairment: Successful transfer with increased retransmissions
- Severe impairment: Successful transfer but with significant delay

### 6. Dynamic Network Condition Testing

**Test:** Transfer large_data.txt with changing network conditions over time
**Network Configuration:**
```
0 0.0 0.0
5 0.01 0.0001
10 0.02 0.0001
15 0.1 0.0001
```

**Results:**
- Transfer proceeded quickly during the initial 5 seconds
- As impairments increased, the protocol adapted with more retransmissions
- Even with 10% loss rate after 15 seconds, the transfer completed successfully

### 7. Segment Size vs. Bit Error Rate Analysis

**Observation:** The relationship between segment size and tolerable bit error rate was analyzed:
- For 5000-byte segments: Bit error rates up to 0.00001 worked well
- For 999-byte segments: Bit error rates up to 0.0001 worked well, and 0.001 was tolerable but slow
- For small segments (<500 bytes): Higher bit error rates could be tolerated

**Conclusion:** Smaller segments are more resilient to bit errors but reduce overall throughput.

## Sample Log Analysis

Below is an analysis of the logs showing the protocol in action:

### Connection Establishment

The logs show the three-way handshake for connection establishment:
```
SYN segment sent from client to server
SYN-ACK segment received from server
ACK segment sent from client to server
```

### Data Transfer with Corruption

The logs show how corrupted segments are handled:
```
Checksum mismatch: received ec7f27d0, computed ff428116
Received corrupted segment from ('127.0.0.1', 51000)
```

### Retransmission on Timeout

The logs show timeout-triggered retransmissions:
```
Timeout, retransmitting from segment 229
Sent segment 229, seq=375, size=978
```

### Flow Control in Action

The logs show flow control with sliding window:
```
Marking segment 227 (seq=373) as acknowledged
Marking segment 228 (seq=374) as acknowledged
Received ACK for seq 374, current base seq: 375
```

## Conclusion

The MRT protocol successfully implements reliable data transfer over UDP with the following characteristics:

1. **Reliability:** Successfully transfers data even with up to 10% packet loss
2. **Error Handling:** Detects and recovers from bit errors using checksums
3. **Performance:** Balances throughput and reliability based on segment size
4. **Limitations:**
   - Segment size must be below 9000 bytes
   - Very high bit error rates (>0.001) can prevent successful transfers
   - For segments of 5000 bytes, optimal bit error rate is 0.00001 or lower
   - For segments of 999 bytes, optimal bit error rate is 0.0001 or lower