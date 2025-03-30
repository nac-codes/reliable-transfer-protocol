# 
# Columbia University - CSEE 4119 Computer Networks
# Assignment 2 - Mini Reliable Transport Protocol
#
# mrt_client.py - defining client APIs of the mini reliable transport protocol
#

import socket # for UDP connection
import struct
import hashlib
import time
import random
import threading

# MRT segment types
SYN = 0
SYN_ACK = 1
ACK = 2
DATA = 3
FIN = 4
FIN_ACK = 5

# Constants
MAX_RETRIES = 10
TIMEOUT = 0.5  # 500ms timeout

class Client:
    def init(self, src_port, dst_addr, dst_port, segment_size):
        """
        initialize the client and create the client UDP channel

        arguments:
        src_port -- the port the client is using to send segments
        dst_addr -- the address of the server/network simulator
        dst_port -- the port of the server/network simulator
        segment_size -- the maximum size of a segment (including the header)
        """
        self.src_port = src_port
        self.dst_addr = dst_addr
        self.dst_port = dst_port
        self.segment_size = segment_size
        self.seq_num = random.randint(0, 1000)  # Initial sequence number
        self.ack_num = 0
        self.connected = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', src_port))
        self.socket.settimeout(TIMEOUT)
        self.header_size = 20  # 1(type) + 4(seq) + 4(ack) + 8(checksum) + 3(payload_len)
        self.max_payload_size = segment_size - self.header_size
        self.log_file = open(f"client_log_{src_port}.txt", "w")
        self.lock = threading.Lock()

    def _compute_checksum(self, data):
        """Compute a simple checksum for data verification."""
        return hashlib.md5(data).hexdigest()[:8]  # Use first 8 chars of MD5
    
    def _create_segment(self, seg_type, seq_num, ack_num, payload=b''):
        """
        Create a segment with the specified parameters.
        
        Format: |type(1B)|seq(4B)|ack(4B)|checksum(8B)|payload_len(3B)|payload|
        """
        # Header: type(1) + seq(4) + ack(4) + checksum(8) + payload_len(3) = 20 bytes
        payload_len = len(payload)
        
        # Create the segment without checksum
        segment = struct.pack(f'!BII3s{payload_len}s', 
                             seg_type, 
                             seq_num, 
                             ack_num, 
                             str(payload_len).zfill(3).encode(), 
                             payload)
        
        # Compute checksum
        checksum = self._compute_checksum(segment)
        
        # Insert checksum into segment
        segment = segment[:9] + checksum.encode() + segment[9:]
        
        return segment
    
    def _parse_segment(self, segment):
        """Parse a received segment and verify its integrity."""
        try:
            # Ensure the segment is long enough for basic header
            if len(segment) < 20:
                print(f"Segment too short: {len(segment)} bytes")
                return None, None, None, None, None

            # Extract components from segment
            seg_type = segment[0]
            seq_num = struct.unpack('!I', segment[1:5])[0]
            ack_num = struct.unpack('!I', segment[5:9])[0]
            received_checksum = segment[9:17].decode()
            
            # Verify checksum
            checksum_data = segment[:9] + segment[17:]
            computed_checksum = self._compute_checksum(checksum_data)
            
            if computed_checksum != received_checksum:
                print(f"Checksum mismatch: received {received_checksum}, computed {computed_checksum}")
                return None, None, None, None, None  # Corrupted segment
            
            payload_len_str = segment[17:20].decode()
            try:
                payload_len = int(payload_len_str)
            except:
                print(f"Invalid payload length: {payload_len_str}")
                return None, None, None, None, None
                
            # Ensure the segment includes the full payload
            if len(segment) < 20 + payload_len:
                print(f"Incomplete segment: expected {20 + payload_len} bytes, got {len(segment)}")
                return None, None, None, None, None
                
            payload = segment[20:20+payload_len]
            
            return seg_type, seq_num, ack_num, payload_len, payload
            
        except Exception as e:
            print(f"Error parsing segment: {e}")
            return None, None, None, None, None
    
    def _log_segment(self, src_port, dst_port, seq_num, ack_num, seg_type, payload_len, direction="SEND"):
        """Log segment information."""
        type_str = {
            SYN: "SYN",
            SYN_ACK: "SYN-ACK",
            ACK: "ACK",
            DATA: "DATA",
            FIN: "FIN",
            FIN_ACK: "FIN-ACK"
        }.get(seg_type, "UNKNOWN")
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"{timestamp} {src_port} {dst_port} {seq_num} {ack_num} {type_str} {payload_len} {direction}\n"
        
        with self.lock:
            self.log_file.write(log_entry)
            self.log_file.flush()

    def connect(self):
        """
        connect to the server
        blocking until the connection is established

        it should support protection against segment loss/corruption/reordering 
        """
        if self.connected:
            print("Already connected")
            return
        
        print(f"Connecting to {self.dst_addr}:{self.dst_port}")
        
        # Send SYN segment
        retry_count = 0
        while retry_count < MAX_RETRIES:
            # Create and send SYN segment
            syn_segment = self._create_segment(SYN, self.seq_num, 0)
            self.socket.sendto(syn_segment, (self.dst_addr, self.dst_port))
            self._log_segment(self.src_port, self.dst_port, self.seq_num, 0, SYN, 0)
            print(f"Sent SYN, seq={self.seq_num}")
            
            # Wait for SYN-ACK
            try:
                response, addr = self.socket.recvfrom(self.segment_size)
                seg_type, srv_seq_num, srv_ack_num, payload_len, payload = self._parse_segment(response)
                
                if seg_type is None:  # Corrupted segment
                    print("Received corrupted segment")
                    retry_count += 1
                    continue
                
                self._log_segment(addr[1], self.src_port, srv_seq_num, srv_ack_num, seg_type, payload_len, "RECV")
                
                if seg_type == SYN_ACK and srv_ack_num == self.seq_num + 1:
                    # Valid SYN-ACK received
                    print(f"Received SYN-ACK, seq={srv_seq_num}, ack={srv_ack_num}")
                    
                    # Update sequence and acknowledgment numbers
                    self.ack_num = srv_seq_num + 1
                    self.seq_num = srv_ack_num
                    
                    # Send ACK to complete three-way handshake
                    ack_segment = self._create_segment(ACK, self.seq_num, self.ack_num)
                    self.socket.sendto(ack_segment, (self.dst_addr, self.dst_port))
                    self._log_segment(self.src_port, self.dst_port, self.seq_num, self.ack_num, ACK, 0)
                    print(f"Sent ACK, seq={self.seq_num}, ack={self.ack_num}")
                    
                    self.connected = True
                    print("Connection established")
                    return
                
            except socket.timeout:
                print(f"Timeout waiting for SYN-ACK, retrying ({retry_count + 1}/{MAX_RETRIES})")
                retry_count += 1
        
        raise Exception("Failed to connect after maximum retries")

    def send(self, data):
        """
        send a chunk of data of arbitrary size to the server
        blocking until all data is sent

        it should support protection against segment loss/corruption/reordering and flow control

        arguments:
        data -- the bytes to be sent to the server
        """
        if not self.connected:
            raise Exception("Not connected to server")
        
        print(f"Sending {len(data)} bytes of data")
        
        # Break data into segments
        segments = []
        data_pos = 0
        
        # Store original sequence number to use as base
        base_seq_num = self.seq_num
        
        while data_pos < len(data):
            # Calculate payload size for this segment
            # Limit to max size of 999 bytes to ensure payload length fits in 3 characters
            # This prevents the truncation issue where "1440" becomes "144"
            payload_size = min(self.max_payload_size, len(data) - data_pos, 999)
            payload = data[data_pos:data_pos + payload_size]
            
            # Create segment with current sequence number
            segment = self._create_segment(DATA, self.seq_num, self.ack_num, payload)
            segments.append((segment, self.seq_num, payload_size))
            
            # Update sequence number for next segment
            # Important: Server expects sequential numbers, not based on payload size
            self.seq_num += 1
            data_pos += payload_size
        
        # Track acknowledged segments
        acked_segments = [False] * len(segments)
        
        # Send segments with retransmission for reliability
        window_size = 1  # Start with window size of 1 for reliability
        base = 0  # Base of the window (index of the first unacked segment)
        next_to_send = 0  # Next segment to send (index)
        
        # Set up timer for retransmission
        timer = None
        
        # Continue until all segments are acknowledged
        while base < len(segments):
            # Send segments in window
            while next_to_send < base + window_size and next_to_send < len(segments):
                segment, seq_num, payload_size = segments[next_to_send]
                self.socket.sendto(segment, (self.dst_addr, self.dst_port))
                self._log_segment(self.src_port, self.dst_port, seq_num, self.ack_num, DATA, payload_size)
                print(f"Sent segment {next_to_send}, seq={seq_num}, size={payload_size}")
                
                # Start timer for the oldest unacknowledged segment if not already running
                if timer is None:
                    timer = time.time()
                
                next_to_send += 1
                
                # Small delay between segments to prevent network congestion
                time.sleep(0.01)
            
            # Wait for ACKs with a timeout
            try:
                response, addr = self.socket.recvfrom(self.segment_size)
                seg_type, srv_seq_num, srv_ack_num, payload_len, payload = self._parse_segment(response)
                
                if seg_type is None:  # Corrupted segment
                    print("Received corrupted ACK")
                    continue
                
                self._log_segment(addr[1], self.src_port, srv_seq_num, srv_ack_num, seg_type, payload_len, "RECV")
                
                if seg_type == ACK:
                    # Calculate which segment this ACK is for
                    # Server ACKs with next expected sequence number
                    acked_seq = srv_ack_num - 1  # The sequence number that was acknowledged
                    
                    print(f"Received ACK for seq {acked_seq}, current base seq: {segments[base][1]}")
                    
                    # Mark segments as acknowledged
                    for i in range(base, len(segments)):
                        if segments[i][1] <= acked_seq:
                            if not acked_segments[i]:
                                print(f"Marking segment {i} (seq={segments[i][1]}) as acknowledged")
                                acked_segments[i] = True
                        else:
                            break
                    
                    # Advance base to the first unacknowledged segment
                    while base < len(segments) and acked_segments[base]:
                        base += 1
                    
                    # If we have acknowledged all segments, we're done
                    if base == len(segments):
                        print("All segments acknowledged")
                        break
                    
                    # Reset timer if there are still unacknowledged segments
                    if base < len(segments):
                        timer = time.time()
                    else:
                        timer = None
                    
                    # Adjust window size (simple flow control)
                    window_size = min(window_size + 1, 5)  # Increase window, max 5
            
            except socket.timeout:
                # Check if we need to retransmit (timeout)
                if timer is not None and time.time() - timer > TIMEOUT:
                    print(f"Timeout, retransmitting from segment {base}")
                    
                    # Reduce window size for congestion control
                    window_size = max(1, window_size // 2)
                    
                    # Reset next_to_send to retransmit from base
                    next_to_send = base
                    timer = time.time()  # Reset timer
                    
                    # A bit of additional delay before retransmission
                    time.sleep(0.05)
        
        print(f"All {len(segments)} segments sent and acknowledged")

    def close(self):
        """
        request to close the connection with the server
        blocking until the connection is closed
        """
        if not self.connected:
            print("Not connected")
            return
        
        print(f"Closing connection with {self.dst_addr}:{self.dst_port}")
        
        # Send FIN segment
        retry_count = 0
        while retry_count < MAX_RETRIES:
            # Create and send FIN segment
            fin_segment = self._create_segment(FIN, self.seq_num, self.ack_num)
            self.socket.sendto(fin_segment, (self.dst_addr, self.dst_port))
            self._log_segment(self.src_port, self.dst_port, self.seq_num, self.ack_num, FIN, 0)
            print(f"Sent FIN, seq={self.seq_num}, ack={self.ack_num}")
            
            # Wait for FIN-ACK
            try:
                response, addr = self.socket.recvfrom(self.segment_size)
                seg_type, srv_seq_num, srv_ack_num, payload_len, payload = self._parse_segment(response)
                
                if seg_type is None:  # Corrupted segment
                    print("Received corrupted segment")
                    retry_count += 1
                    continue
                
                self._log_segment(addr[1], self.src_port, srv_seq_num, srv_ack_num, seg_type, payload_len, "RECV")
                
                if seg_type == FIN_ACK:
                    # Valid FIN-ACK received
                    print(f"Received FIN-ACK, seq={srv_seq_num}, ack={srv_ack_num}")
                    self.connected = False
                    
                    # Close the socket and log file
                    self.log_file.close()
                    self.socket.close()
                    
                    print("Connection closed")
                    return
                
            except socket.timeout:
                print(f"Timeout waiting for FIN-ACK, retrying ({retry_count + 1}/{MAX_RETRIES})")
                retry_count += 1
        
        # Even if we didn't get FIN-ACK, close resources
        self.connected = False
        self.log_file.close()
        self.socket.close()
        print("Connection forcibly closed after maximum retries")
