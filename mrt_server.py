# 
# Columbia University - CSEE 4119 Computer Networks
# Assignment 2 - Mini Reliable Transport Protocol
#
# mrt_server.py - defining server APIs of the mini reliable transport protocol
#

import socket
import struct
import hashlib
import time
import threading
import random
import binascii  # Added for debug hex printing

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
BUFFER_THRESHOLD = 0.8  # When buffer is 80% full, slow down
UDP_MAX_SIZE = 9000  # Soft limit of 9000 bytes to avoid "message too long" errors

# Enable or disable detailed debugging
DEBUG = False

def debug_print(*args, **kwargs):
    """Print debug messages only if DEBUG is True"""
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)

class Connection:
    """Represents a connection with a client"""
    def __init__(self, server, addr, port, seq_num, ack_num):
        self.server = server
        self.addr = addr
        self.port = port
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.connected = True
        self.received_data = b''
        self.receive_buffer = {}  # To store out-of-order segments
        self.next_expected_seq = ack_num
        self.lock = threading.Lock()
        
        # Debug counters
        self.total_bytes_received = 0
        self.segments_received = 0
        self.out_of_order_segments = 0
        self.duplicate_segments = 0
        
        debug_print(f"Connection initialized with addr={addr}, port={port}, seq={seq_num}, ack={ack_num}")
        debug_print(f"Initial next_expected_seq={self.next_expected_seq}")

class Server:
    def __init__(self):
        """Initialize the server."""
        self.socket = None
        self.listen_port = None
        self.receive_buffer_size = None
        self.connections = {}  # Dictionary to store client connections
        self.listening = False
        self.log_file = None
        self.lock = threading.Lock()
        
    def init(self, listen_port, receive_buffer_size):
        """
        Initialize the server and create the server UDP channel.

        arguments:
        listen_port -- the port that the server is listening on
        receive_buffer_size -- the buffer size for receiving segments
        """
        self.listen_port = listen_port
        self.receive_buffer_size = min(receive_buffer_size, UDP_MAX_SIZE)  # Ensure buffer size doesn't exceed UDP limits
        
        print(f"Initializing server on port {listen_port} with buffer size {self.receive_buffer_size}")
        
        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', listen_port))
        
        # Initialize log file
        self.log_file = open(f"log_{listen_port}.txt", "w")
        
        # Start the receiver thread to handle all incoming segments
        self.listening = True
        self.receiver_thread = threading.Thread(target=self._receive_segments)
        self.receiver_thread.daemon = True
        self.receiver_thread.start()

    def _compute_checksum(self, data):
        """Compute a simple checksum for data verification."""
        return hashlib.md5(data).hexdigest()[:8]  # Use first 8 chars of MD5
    
    def _create_segment(self, seg_type, seq_num, ack_num, payload=b''):
        """
        Create a segment with the specified parameters.
        
        Format: |type(1B)|seq(4B)|ack(4B)|checksum(8B)|payload_len(4B)|payload|
        """
        # Header: type(1) + seq(4) + ack(4) + checksum(8) + payload_len(4) = 21 bytes
        payload_len = len(payload)
        
        # Create the segment without checksum
        segment = struct.pack(f'!BII4s{payload_len}s', 
                             seg_type, 
                             seq_num, 
                             ack_num, 
                             str(payload_len).zfill(4).encode('ascii'), 
                             payload)
        
        # Compute checksum
        checksum = self._compute_checksum(segment)
        
        # Insert checksum into segment
        segment = segment[:9] + checksum.encode('ascii') + segment[9:]
        
        return segment
    
    def _parse_segment(self, segment):
        """Parse a received segment and verify its integrity."""
        try:
            # Ensure the segment is long enough for basic header
            if len(segment) < 21:
                print(f"Segment too short: {len(segment)} bytes")
                return None, None, None, None, None

            # Extract components from segment
            seg_type = segment[0]
            seq_num = struct.unpack('!I', segment[1:5])[0]
            ack_num = struct.unpack('!I', segment[5:9])[0]
            
            # Use try-except to handle potential decode errors for checksum
            try:
                received_checksum = segment[9:17].decode('ascii')
            except UnicodeDecodeError:
                # Handle binary data that can't be decoded as UTF-8
                print(f"Checksum decode error: treating segment as corrupted")
                # Optionally print the hex representation for debugging
                if DEBUG:
                    debug_print(f"Corrupted checksum bytes: {binascii.hexlify(segment[9:17])}")
                return None, None, None, None, None
            
            # Verify checksum
            checksum_data = segment[:9] + segment[17:]
            computed_checksum = self._compute_checksum(checksum_data)
            
            if computed_checksum != received_checksum:
                print(f"Checksum mismatch: received {received_checksum}, computed {computed_checksum}")
                return None, None, None, None, None  # Corrupted segment
            
            # Use try-except for payload length decoding as well
            try:
                payload_len_str = segment[17:21].decode('ascii')
                payload_len = int(payload_len_str)
            except (UnicodeDecodeError, ValueError):
                print(f"Invalid payload length: cannot decode or convert to integer")
                if DEBUG:
                    debug_print(f"Corrupted payload length bytes: {binascii.hexlify(segment[17:21])}")
                return None, None, None, None, None
                
            # Ensure the segment includes the full payload
            if len(segment) < 21 + payload_len:
                print(f"Incomplete segment: expected {21 + payload_len} bytes, got {len(segment)}")
                return None, None, None, None, None
                
            payload = segment[21:21+payload_len]
            
            # Debug payload data (first few bytes)
            if DEBUG and payload_len > 0:
                preview = payload[:min(16, payload_len)]
                debug_print(f"Payload preview: {binascii.hexlify(preview).decode()} (first {len(preview)} of {payload_len} bytes)")
            
            return seg_type, seq_num, ack_num, payload_len, payload
            
        except Exception as e:
            print(f"Error parsing segment: {e}")
            import traceback
            traceback.print_exc()
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
    
    def _get_client_key(self, addr, port):
        """Generate a unique key for a client connection."""
        return f"{addr}:{port}"
    
    def _receive_segments(self):
        """Thread to receive segments from all clients."""
        self.socket.settimeout(0.1)  # Short timeout for non-blocking
        
        while self.listening:
            try:
                segment, addr = self.socket.recvfrom(65535)  # Use large buffer for receiving
                
                try:
                    # Parse and verify the segment
                    seg_type, seq_num, ack_num, payload_len, payload = self._parse_segment(segment)
                    
                    if seg_type is None:  # Corrupted segment
                        print(f"Received corrupted segment from {addr}")
                        continue
                    
                    client_key = self._get_client_key(addr[0], addr[1])
                    
                    # Log the received segment
                    self._log_segment(addr[1], self.listen_port, seq_num, ack_num, seg_type, payload_len, "RECV")
                    print(f"RECV: type={seg_type}, seq={seq_num}, ack={ack_num}, from={addr}")
                    
                    # Handle different types of segments
                    if seg_type == SYN:
                        # New connection request
                        self._handle_syn(addr, seq_num)
                    
                    elif client_key in self.connections:
                        conn = self.connections[client_key]
                        
                        if seg_type == ACK:
                            # Acknowledgment for data sent
                            self._handle_ack(conn, ack_num)
                        
                        elif seg_type == DATA:
                            # Data segment
                            self._handle_data(conn, seq_num, ack_num, payload)
                        
                        elif seg_type == FIN:
                            # Connection termination request
                            self._handle_fin(conn, seq_num)
                
                except UnicodeDecodeError as ude:
                    print(f"UnicodeDecodeError while processing segment from {addr}: {ude}")
                    if DEBUG:
                        debug_print(f"Problematic segment: {binascii.hexlify(segment)}")
                except Exception as inner_e:
                    print(f"Error processing segment from {addr}: {inner_e}")
                    if DEBUG:
                        import traceback
                        traceback.print_exc()
                
            except socket.timeout:
                pass
            except Exception as e:
                print(f"Error receiving segment: {e}")
                if DEBUG:
                    import traceback
                    traceback.print_exc()
    
    def _handle_syn(self, addr, seq_num):
        """Handle SYN segment from client."""
        # Generate a random sequence number for this connection
        server_seq_num = random.randint(0, 1000)
        
        # Create a new connection
        client_key = self._get_client_key(addr[0], addr[1])
        
        # Set acknowledgment number to client's sequence number + 1
        ack_num = seq_num + 1
        
        # Create new connection object if it doesn't exist
        if client_key not in self.connections:
            conn = Connection(self, addr[0], addr[1], server_seq_num, ack_num)
            with self.lock:
                self.connections[client_key] = conn
            
            # Send SYN-ACK segment
            syn_ack_segment = self._create_segment(SYN_ACK, server_seq_num, ack_num)
            self.socket.sendto(syn_ack_segment, addr)
            self._log_segment(self.listen_port, addr[1], server_seq_num, ack_num, SYN_ACK, 0)
            print(f"Sent SYN-ACK to {addr}, seq={server_seq_num}, ack={ack_num}")
        else:
            # Connection already exists, resend SYN-ACK
            conn = self.connections[client_key]
            syn_ack_segment = self._create_segment(SYN_ACK, conn.seq_num, conn.ack_num)
            self.socket.sendto(syn_ack_segment, addr)
            self._log_segment(self.listen_port, addr[1], conn.seq_num, conn.ack_num, SYN_ACK, 0)
            print(f"Resent SYN-ACK to {addr}, seq={conn.seq_num}, ack={conn.ack_num}")
    
    def _handle_ack(self, conn, ack_num):
        """Handle ACK segment from client."""
        # Just update the connection state
        print(f"Received ACK {ack_num} from {conn.addr}:{conn.port}")
    
    def _handle_data(self, conn, seq_num, ack_num, payload):
        """Handle DATA segment from client."""
        debug_print(f"DATA segment: seq={seq_num}, ack={ack_num}, payload_size={len(payload)}")
        debug_print(f"Connection state: next_expected_seq={conn.next_expected_seq}")
        debug_print(f"Current received_data size: {len(conn.received_data)} bytes")
        debug_print(f"Buffered segments: {sorted(conn.receive_buffer.keys())}")
        
        with conn.lock:
            # Check if this is the next expected segment
            if seq_num == conn.next_expected_seq:
                debug_print(f"Adding segment seq={seq_num} directly to received_data ({len(payload)} bytes)")
                # Add payload to received data
                before_len = len(conn.received_data)
                conn.received_data += payload
                after_len = len(conn.received_data)
                
                debug_print(f"received_data size change: {before_len} -> {after_len}")
                
                conn.next_expected_seq += 1
                conn.segments_received += 1
                conn.total_bytes_received += len(payload)
                
                # Check if we have any buffered segments that can now be added
                next_seq = conn.next_expected_seq
                debug_print(f"Checking buffer for next_seq={next_seq}")
                
                segments_processed = 0
                bytes_processed = 0
                
                while next_seq in conn.receive_buffer:
                    buffered_payload = conn.receive_buffer[next_seq]
                    debug_print(f"Found buffered segment seq={next_seq} with {len(buffered_payload)} bytes")
                    
                    before_len = len(conn.received_data)
                    conn.received_data += buffered_payload
                    after_len = len(conn.received_data)
                    
                    debug_print(f"received_data size change from buffer: {before_len} -> {after_len}")
                    
                    bytes_processed += len(buffered_payload)
                    segments_processed += 1
                    
                    del conn.receive_buffer[next_seq]
                    next_seq += 1
                
                conn.next_expected_seq = next_seq
                
                if segments_processed > 0:
                    debug_print(f"Processed {segments_processed} buffered segments ({bytes_processed} bytes)")
                
                # Send ACK for the latest segment we've processed
                ack_segment = self._create_segment(ACK, conn.seq_num, conn.next_expected_seq)
                self.socket.sendto(ack_segment, (conn.addr, conn.port))
                self._log_segment(self.listen_port, conn.port, conn.seq_num, conn.next_expected_seq, ACK, 0)
                print(f"Sent ACK {conn.next_expected_seq} to {conn.addr}:{conn.port}")
                
                debug_print(f"After processing: received_data size={len(conn.received_data)}, next_expected_seq={conn.next_expected_seq}")
                debug_print(f"Remaining buffered segments: {sorted(conn.receive_buffer.keys())}")
                
            elif seq_num > conn.next_expected_seq:
                # Out of order segment, buffer it
                debug_print(f"Out-of-order segment seq={seq_num}, expecting {conn.next_expected_seq}")
                conn.receive_buffer[seq_num] = payload
                conn.out_of_order_segments += 1
                
                # Debug buffer contents
                debug_print(f"Buffer now contains segments: {sorted(conn.receive_buffer.keys())}")
                debug_print(f"Total buffered data: {sum(len(data) for data in conn.receive_buffer.values())} bytes")
                
                # Send ACK for the last in-order segment we've received
                ack_segment = self._create_segment(ACK, conn.seq_num, conn.next_expected_seq)
                self.socket.sendto(ack_segment, (conn.addr, conn.port))
                self._log_segment(self.listen_port, conn.port, conn.seq_num, conn.next_expected_seq, ACK, 0)
                print(f"Sent duplicate ACK {conn.next_expected_seq} to {conn.addr}:{conn.port}")
                
            else:
                # Duplicate segment, ignore but send ACK
                debug_print(f"Duplicate segment seq={seq_num}, already received (next_expected_seq={conn.next_expected_seq})")
                conn.duplicate_segments += 1
                
                ack_segment = self._create_segment(ACK, conn.seq_num, conn.next_expected_seq)
                self.socket.sendto(ack_segment, (conn.addr, conn.port))
                self._log_segment(self.listen_port, conn.port, conn.seq_num, conn.next_expected_seq, ACK, 0)
                print(f"Sent ACK {conn.next_expected_seq} for duplicate segment")
    
    def _handle_fin(self, conn, seq_num):
        """Handle FIN segment from client."""
        # Send FIN-ACK segment
        fin_ack_segment = self._create_segment(FIN_ACK, conn.seq_num, seq_num + 1)
        self.socket.sendto(fin_ack_segment, (conn.addr, conn.port))
        self._log_segment(self.listen_port, conn.port, conn.seq_num, seq_num + 1, FIN_ACK, 0)
        print(f"Sent FIN-ACK to {conn.addr}:{conn.port}")
        
        # Mark connection as closed - don't remove it yet as we might need to resend FIN-ACK
        conn.connected = False
        
        # Print debug stats
        if DEBUG:
            debug_print("=== Connection Statistics at Close ===")
            debug_print(f"Total bytes received: {conn.total_bytes_received}")
            debug_print(f"Total segments received: {conn.segments_received}")
            debug_print(f"Out-of-order segments: {conn.out_of_order_segments}")
            debug_print(f"Duplicate segments: {conn.duplicate_segments}")
            debug_print(f"Final received_data size: {len(conn.received_data)} bytes")
            debug_print(f"Remaining buffered segments: {sorted(conn.receive_buffer.keys())}")
            debug_print(f"Remaining buffered data size: {sum(len(data) for data in conn.receive_buffer.values())} bytes")
            debug_print("=====================================")
    
    def accept(self):
        """
        Accept a connection from a client.
        Blocking until a connection is established.
        
        return:
        A connection object that can be used to receive data from this client.
        """
        print("Waiting for client connection...")
        
        # Wait for a connection to be established
        while not self.connections or not any(conn.connected for conn in self.connections.values()):
            time.sleep(0.1)
        
        # Find the first connected client and return it
        for client_key, conn in self.connections.items():
            if conn.connected:
                print(f"Accepted connection from {conn.addr}:{conn.port}")
                return conn
        
        return None
    
    def receive(self, conn, length):
        """
        Receive data from the client.
        Blocking until the specified amount of data is received.
        
        arguments:
        conn -- the connection to receive data from
        length -- the amount of data to receive in bytes
        
        return:
        The received data as bytes.
        """
        if not conn or not conn.connected:
            raise Exception("Connection is not established")
        
        print(f"Waiting to receive {length} bytes from {conn.addr}:{conn.port}")
        debug_print(f"receive() called for {length} bytes")
        debug_print(f"Current received_data size: {len(conn.received_data)} bytes")
        debug_print(f"Current buffered segments: {sorted(conn.receive_buffer.keys())}")
        
        # Wait until we have enough data
        wait_start_time = time.time()
        wait_iteration = 0
        
        while len(conn.received_data) < length and conn.connected:
            wait_iteration += 1
            if wait_iteration % 10 == 0:  # Log every 10 iterations (approximately every second)
                elapsed = time.time() - wait_start_time
                debug_print(f"Still waiting after {elapsed:.2f}s... have {len(conn.received_data)}/{length} bytes")
                debug_print(f"Buffered segments: {sorted(conn.receive_buffer.keys())}")
                if conn.receive_buffer:
                    debug_print(f"Total buffered data: {sum(len(data) for data in conn.receive_buffer.values())} bytes")
                    smallest_seq = min(conn.receive_buffer.keys()) if conn.receive_buffer else None
                    gap = smallest_seq - conn.next_expected_seq if smallest_seq is not None else None
                    debug_print(f"Next expected seq: {conn.next_expected_seq}, smallest buffered: {smallest_seq}, gap: {gap}")
            
            time.sleep(0.1)
        
        # Check if the connection was closed before receiving enough data
        if not conn.connected and len(conn.received_data) < length:
            debug_print(f"Connection closed before receiving enough data. Available: {len(conn.received_data)}/{length} bytes")
            print(f"Connection closed before receiving enough data. Received {len(conn.received_data)}/{length} bytes")
            
            # Debug dump of first part of data
            if len(conn.received_data) > 0:
                preview_len = min(50, len(conn.received_data))
                debug_print(f"Data preview: {binascii.hexlify(conn.received_data[:preview_len]).decode()} ({preview_len} bytes)")
            
            return conn.received_data
        
        # Return the requested amount of data
        with conn.lock:
            debug_print(f"Receiving {length} bytes from received_data buffer (buffer size: {len(conn.received_data)} bytes)")
            data = conn.received_data[:length]
            conn.received_data = conn.received_data[length:]
            debug_print(f"After receiving: received_data size={len(conn.received_data)} bytes")
            
            # Debug dump of retrieved data
            if len(data) > 0:
                preview_len = min(50, len(data))
                debug_print(f"Data preview: {binascii.hexlify(data[:preview_len]).decode()} ({preview_len} bytes)")
        
        print(f"Received {len(data)} bytes from {conn.addr}:{conn.port}")
        return data
    
    def close(self):
        """
        Close all connections and clean up.
        """
        print("Closing server and all connections")
        
        # Debug dump of connection statistics
        if DEBUG:
            for client_key, conn in self.connections.items():
                debug_print(f"Connection {client_key} stats:")
                debug_print(f"  Total bytes received: {conn.total_bytes_received}")
                debug_print(f"  Total segments received: {conn.segments_received}")
                debug_print(f"  Out-of-order segments: {conn.out_of_order_segments}")
                debug_print(f"  Duplicate segments: {conn.duplicate_segments}")
                debug_print(f"  Final received_data size: {len(conn.received_data)} bytes")
                debug_print(f"  Remaining buffered segments: {sorted(conn.receive_buffer.keys())}")
        
        # Stop the receiver thread
        self.listening = False
        
        # Close all connections
        for client_key, conn in list(self.connections.items()):
            if conn.connected:
                # Send FIN-ACK segment
                fin_ack_segment = self._create_segment(FIN_ACK, conn.seq_num, conn.ack_num)
                self.socket.sendto(fin_ack_segment, (conn.addr, conn.port))
                self._log_segment(self.listen_port, conn.port, conn.seq_num, conn.ack_num, FIN_ACK, 0)
                print(f"Sent FIN-ACK to {conn.addr}:{conn.port}")
                conn.connected = False
        
        # Close the log file and socket
        if self.log_file:
            self.log_file.close()
        
        if self.socket:
            self.socket.close()
