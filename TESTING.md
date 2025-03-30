# CSEE 4119 Spring 2025, Assignment 2 Testing Document

## Test Scenarios and Results

This document outlines the test scenarios used to verify the functionality of the Mini Reliable Transport Protocol (MRT). We will test all required features under various network conditions.

## 1. Basic Functionality Tests

### 1.1 Connection Establishment

**Test Procedure**:
1. Start server with `python app_server.py 60000 4096`
2. Start network simulator with `python network.py 51000 127.0.0.1 50000 127.0.0.1 60000 loss.txt`
3. Start client with `python app_client.py 50000 127.0.0.1 51000 1460`
4. Verify connection establishment through logs

**Expected Results**:
- Three-way handshake completes successfully
- Log shows SYN, SYN-ACK, and ACK segments

### 1.2 Data Transfer (No Loss)

**Test Procedure**:
1. Set up a loss file with 0% loss and 0% corruption rate
2. Run the client and server with the network simulator
3. Verify data transfer through logs

**Expected Results**:
- All data is transferred correctly
- Server reports successful data reception
- Log shows DATA and ACK segments

## 2. Reliability Tests

### 2.1 Segment Loss Handling

**Test Procedure**:
1. Create a loss file with gradually increasing segment loss rates:
   ```
   0 0.0 0.0
   5 0.1 0.0
   10 0.2 0.0
   15 0.3 0.0
   ```
2. Run the client and server with the network simulator
3. Verify data transfer through logs

**Expected Results**:
- Data transfer should complete despite packet losses
- Logs should show retransmissions
- Server should receive all data correctly

### 2.2 Data Corruption Handling

**Test Procedure**:
1. Create a loss file with bit error rates:
   ```
   0 0.0 0.0
   5 0.0 0.001
   10 0.0 0.005
   15 0.0 0.01
   ```
2. Run the client and server with the network simulator
3. Verify data transfer through logs

**Expected Results**:
- Corrupted segments should be detected and discarded
- Retransmissions should occur for corrupted segments
- Server should receive all data correctly

### 2.3 Out-of-order Delivery Handling

**Test Procedure**:
1. Check logs to verify out-of-order handling (the network simulator might deliver segments out of order due to retransmissions)
2. Verify data is delivered in the correct order to the application

**Expected Results**:
- Log should show out-of-order segments being received
- Server should buffer out-of-order segments
- Application should receive data in the correct order

## 3. Flow Control Tests

### 3.1 Window-based Flow Control

**Test Procedure**:
1. Run the client with a large data file that exceeds the buffer size
2. Set server receive buffer to various sizes (1KB, 4KB, 8KB)
3. Verify data transfer through logs

**Expected Results**:
- Client should not overwhelm the server
- Data transfer should complete successfully regardless of buffer size
- Log should show flow control in action with window management

## 4. Combined Tests

### 4.1 High Latency with Losses

**Test Procedure**:
1. Create a loss file with high loss and reasonable corruption:
   ```
   0 0.1 0.001
   ```
2. Run the client and server with the network simulator
3. Verify data transfer through logs

**Expected Results**:
- Data transfer should complete despite challenging conditions
- Logs should show adaptive behavior with retransmissions
- Server should receive all data correctly

### 4.2 Large Data Transfer

**Test Procedure**:
1. Create a large data file (>100KB)
2. Run the client and server with the network simulator
3. Verify data transfer through logs

**Expected Results**:
- All data should be segmented properly
- Data transfer should complete successfully
- Server should receive all data correctly

## 5. Example Test Output

```
# log_50000.txt (client) - Example excerpt showing connection establishment and data transfer with retransmissions

2025-02-23 14:15:35.123 50000 51000 123 0 SYN 0 SEND
2025-02-23 14:15:35.223 51000 50000 456 124 SYN-ACK 0 RECV
2025-02-23 14:15:35.324 50000 51000 124 457 ACK 0 SEND
2025-02-23 14:15:35.425 50000 51000 124 457 DATA 1000 SEND
2025-02-23 14:15:35.525 50000 51000 125 457 DATA 1000 SEND
2025-02-23 14:15:35.625 51000 50000 456 125 ACK 0 RECV
2025-02-23 14:15:35.825 50000 51000 125 457 DATA 1000 RESEND
2025-02-23 14:15:35.925 51000 50000 456 126 ACK 0 RECV
...
```

```
# log_60000.txt (server) - Example excerpt showing connection acceptance and data reception

2025-02-23 14:15:35.223 60000 50000 456 124 SYN-ACK 0 SEND
2025-02-23 14:15:35.323 50000 60000 124 457 ACK 0 RECV
2025-02-23 14:15:35.425 50000 60000 124 457 DATA 1000 RECV
2025-02-23 14:15:35.425 60000 50000 456 125 ACK 0 SEND
2025-02-23 14:15:35.525 50000 60000 125 457 DATA 1000 RECV
2025-02-23 14:15:35.525 60000 50000 456 126 ACK 0 SEND
...
```

## 6. Test Results Summary

The MRT protocol successfully demonstrated:
- Reliable data transfer despite segment losses
- Detection and handling of corrupted segments
- Proper ordering of data despite out-of-order delivery
- Flow control to prevent buffer overflow
- Efficient segmentation and reassembly of large data
- Adaptability to different network conditions

All these capabilities were verified through the log files and successful data transfer between client and server applications.