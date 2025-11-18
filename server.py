from flask import Flask, jsonify, make_response
import socket
import struct
import threading
import random
from queue import Queue, Empty
from datetime import datetime
import time # Needed for time.sleep in generator loop (optional but useful)

# --- Configuration & Constants ---
# Network settings for the UDP listener
UDP_IP = "0.0.0.0" 
UDP_PORT = 5005     
# Matrix dimensions
MATRIX_N = 128
EXPECTED_ARRAY_SIZE = MATRIX_N * MATRIX_N # 16384 values
EXPECTED_SIZE_BYTES = EXPECTED_ARRAY_SIZE * 2 # 32768 bytes

# --- Shared Resources ---
# Thread-safe queue to buffer incoming raw UDP packets
data_buffer = Queue() 
# Global storage for the latest processed matrix
latest_sensor_matrix = None
# Flag to signal threads to stop
stop_listener = threading.Event() 

# --- Flask App Setup ---
app = Flask(__name__)

# --- 1. UDP Listener Thread ---

def udp_listener_thread():
    """
    Listens for raw binary packets from the microcontroller and buffers them quickly.
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] UDP Listener starting on {UDP_IP}:{UDP_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((UDP_IP, UDP_PORT))
        sock.settimeout(0.5) # Timeout allows periodic check of stop flag
    except OSError as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Failed to bind UDP socket: {e}")
        return

    while not stop_listener.is_set():
        try:
            binary_data, addr = sock.recvfrom(EXPECTED_SIZE_BYTES + 100) 
            
            if len(binary_data) == EXPECTED_SIZE_BYTES:
                data_buffer.put(binary_data)
            else:
                pass # Discard invalid size packets

        except socket.timeout:
            continue
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] UDP Listener exception: {e}")
            break
            
    sock.close()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] UDP Listener stopped.")

# --- 2. Data Processor Thread ---

def process_buffer_thread():
    """
    Pulls raw binary data from the Queue, decodes it, and updates the global matrix.
    """
    global latest_sensor_matrix
    sample_count = 0
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Data Processor thread started.")
    
    # '<' = Little-Endian, 'h' = signed short (16-bit integer)
    format_string = f'<{EXPECTED_ARRAY_SIZE}h'
    
    while not stop_listener.is_set():
        try:
            binary_data = data_buffer.get(timeout=0.1) 
            
            # Deserialize the binary data
            sensor_array_scaled = struct.unpack(format_string, binary_data)
            
            # Convert back to float (0-100 range)
            sensor_array = [v / 10.0 for v in sensor_array_scaled]
            
            latest_sensor_matrix = sensor_array 
            sample_count += 1
            
            # print(f"[{datetime.now().strftime('%H:%M:%S')}] Processed sample #{sample_count}. Queue size: {data_buffer.qsize()}")
            data_buffer.task_done()
            
        except Empty:
            continue
        except struct.error as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processor Error unpacking data: {e}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processor Exception: {e}")


# --- 3. Flask API Endpoints ---

@app.route('/sensor_data', methods=['GET'])
def send_sensor_data():
    """
    ORIGINAL ROUTE: Generates synthetic 128x128 matrix, serializes it 
    as a binary buffer, and sends it to the client.
    """
    # 1. Generate Synthetic Data (0-100, scaled to 0-1000 for Int16)
    sensor_array_scaled = []
    for _ in range(EXPECTED_ARRAY_SIZE):
        value = random.random() * 1000 
        sensor_array_scaled.append(int(value))

    # 2. Serialize the array into a binary buffer (32768 bytes)
    try:
        format_string = f'<{EXPECTED_ARRAY_SIZE}h'
        binary_data = struct.pack(format_string, *sensor_array_scaled)
    except struct.error as e:
        return jsonify({"message": f"Error packing binary data: {e}"}), 500

    # 3. Create and send the response
    response = make_response(binary_data)
    response.headers['Content-Type'] = 'application/octet-stream'
    # Allow the D3 client to fetch data from this port
    response.headers['Access-Control-Allow-Origin'] = '*' 
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent {len(binary_data)} bytes of synthetic binary data.")
    return response


@app.route('/latest_matrix', methods=['GET'])
def get_latest_matrix():
    """
    NEW ROUTE: Serves the latest processed data from the live UDP buffer.
    """
    # Check if we have received any live data
    if latest_sensor_matrix is None:
        return jsonify({"message": "No live UDP sensor data received yet"}), 204
        
    # Serve the latest processed data via JSON
    response = make_response(jsonify({
        "timestamp": datetime.now().isoformat(),
        "matrix": latest_sensor_matrix,
        "message": "Serving latest live UDP data."
    }))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


# --- Main Runtime ---

if __name__ == '__main__':
    # 1. Start the UDP Listener thread
    listener = threading.Thread(target=udp_listener_thread)
    listener.daemon = True 
    listener.start()
    
    # 2. Start the Data Processor thread
    processor = threading.Thread(target=process_buffer_thread)
    processor.daemon = True
    processor.start()

    # 3. Start the Flask server
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Flask Server started on http://127.0.0.1:5000")
        app.run(debug=False, port=5000)
    except Exception as e:
        print(f"Flask runtime error: {e}")
    finally:
        # Graceful shutdown
        stop_listener.set()
        listener.join(1) 
        processor.join(1)
        print("Application shutting down.")
