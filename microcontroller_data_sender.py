import socket
import struct
import random
import time
from datetime import datetime

# --- Configuration (Must match server settings) ---
TARGET_IP = "127.0.0.1"  # Target the local host where Flask/Listener is running
TARGET_PORT = 5005       # Target the UDP listener port
MATRIX_N = 128           # 128x128 matrix
EXPECTED_ARRAY_SIZE = MATRIX_N * MATRIX_N # 16384 elements
PACKET_DELAY_S = 0.1   # Send rate: 0.1 == 10 packets per second (10Hz)

# Format string: '<' = Little-Endian, 'h' = signed short (16-bit integer)
FORMAT_STRING = f'<{EXPECTED_ARRAY_SIZE}h'

def generate_and_send_udp():
    """
    Simulates a microcontroller continuously generating and sending sensor data.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sample_count = 0
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting UDP sender to {TARGET_IP}:{TARGET_PORT}")
    print(f"Sending {EXPECTED_ARRAY_SIZE} values (32KB packet) every {PACKET_DELAY_S}s...")

    try:
        while True:
            # 1. Generate Synthetic Data (0-100 float range)
            # We'll simulate a dynamic center point to make the visualization interesting
            center_x = random.randint(30, 90)
            center_y = random.randint(30, 90)
            
            sensor_array_scaled = []
            
            for i in range(EXPECTED_ARRAY_SIZE):
                x = i % MATRIX_N
                y = i // MATRIX_N
                
                # Calculate distance from the moving center
                distance = ((x - center_x)**2 + (y - center_y)**2)**0.5
                
                # Apply a smooth falloff (0-100)
                # Max value is 100, minimum is near 0
                normalized_value = max(0, 100 - distance * 1.3)
                
                # 2. Scale to Int16 (0-1000 range)
                scaled_value = int(normalized_value * 10)
                
                sensor_array_scaled.append(scaled_value)

            # 3. Pack the array into a single binary buffer
            try:
                binary_data = struct.pack(FORMAT_STRING, *sensor_array_scaled)
            except struct.error as e:
                print(f"Error packing binary data: {e}")
                time.sleep(1)
                continue
            
            # 4. Send the UDP packet
            sock.sendto(binary_data, (TARGET_IP, TARGET_PORT))
            
            sample_count += 1
            if sample_count % 10 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent sample #{sample_count}. Data size: {len(binary_data)} bytes.")

            time.sleep(PACKET_DELAY_S)

    except KeyboardInterrupt:
        print("\nSender script stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        sock.close()
        print("UDP socket closed.")

if __name__ == '__main__':
    generate_and_send_udp()

"""
How to Test:
1.  **Run the Server:** Start your Flask application (assuming it's named `server.py`):
    ```bash
    python server.py
    ```
2.  **Run the Sender:** Open a **new terminal window** and run the sender script:
    ```bash
    python udp_sender.py
"""
