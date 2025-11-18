import pytest
import json
import struct
import threading
from datetime import datetime
from queue import Queue

# --- IMPORT APP COMPONENTS ---
# Assumes the multi-threaded Flask app is saved in server.py
try:
    # 1. Import the module itself to use with monkeypatch
    import server
    # 2. Import components needed directly, but access global state via the module prefix
    from server import app, data_buffer, EXPECTED_SIZE_BYTES
except ImportError:
    # If the app structure cannot be imported (e.g., during setup), 
    # we raise a clear error.
    raise ImportError("Could not import app components. Ensure your Flask server code is saved as 'server.py' in the same directory.")


# --- PYTEST FIXTURES ---

@pytest.fixture
def client():
    """Fixture for the Flask test client."""
    # Ensure the matrix state is clean for each test before the test starts
    # We set the global state directly on the imported 'server' module.
    server.latest_sensor_matrix = None 
    
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_latest_matrix_data():
    """Fixture that generates valid, processed data."""
    
    # Generate a simple, recognizable 128x128 array (16384 values)
    data = [50.0 + (i % 10) / 10.0 for i in range(16384)]
    
    return data

# --- TEST SUITE ---

def test_01_sensor_data_route_binary_format(client):
    """
    Test the /sensor_data (synthetic data) endpoint.
    It should return a binary response with the correct size and content type.
    """
    print("\nTesting /sensor_data (synthetic binary output)")
    
    response = client.get('/sensor_data')
    
    # 1. Check HTTP Status Code
    assert response.status_code == 200
    
    # 2. Check Content Type
    assert response.content_type == 'application/octet-stream'
    
    # 3. Check Binary Size
    # Expected size is 128 * 128 * 2 bytes = 32768 bytes
    assert len(response.data) == EXPECTED_SIZE_BYTES
    
    # 4. Check Decoding (Ensure the data is valid Int16 binary)
    try:
        # '<' = Little-Endian, 'h' = signed short (16-bit integer)
        format_string = f'<{16384}h'
        # Unpack the response data
        unpacked_data = struct.unpack(format_string, response.data)
        
        # Values should be integers scaled by 10 (0-1000)
        assert len(unpacked_data) == 16384
        # Check that values are within the expected scaled range (0 to 1000)
        assert all(0 <= v <= 1000 for v in unpacked_data), "Decoded values are outside the expected scaled range (0-1000)"
        
    except struct.error as e:
        pytest.fail(f"Failed to unpack binary response: {e}")


def test_02_latest_matrix_route_no_data(client):
    """
    Test the /latest_matrix endpoint when no UDP data has been received yet (None state).
    It should return a 204 No Content status code.
    """
    print("\nTesting /latest_matrix (no data received yet)")
    
    # Ensure global state is None before the test runs
    server.latest_sensor_matrix = None
    
    response = client.get('/latest_matrix')
    
    # Standard practice for 'nothing to send' is 204 No Content
    assert response.status_code == 204
    

def test_03_latest_matrix_route_live_data(client, mock_latest_matrix_data, monkeypatch):
    """
    Test the /latest_matrix endpoint when live UDP data is available.
    It should return valid JSON with the expected matrix structure.
    """
    print("\nTesting /latest_matrix (live data available)")
    
    # CRITICAL FIX: Use monkeypatch to set the global variable in the 'server' module's
    # namespace. This guarantees the Flask route function sees the mock data.
    monkeypatch.setattr(server, 'latest_sensor_matrix', mock_latest_matrix_data)
    
    response = client.get('/latest_matrix')
    
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    
    try:
        data = json.loads(response.data.decode('utf-8'))
    except json.JSONDecodeError:
        pytest.fail("Response data is not valid JSON.")
        
    # Check structure and content
    assert 'matrix' in data
    assert 'timestamp' in data
    assert 'message' in data
    
    # Check if the matrix size and content matches the fixture data
    assert isinstance(data['matrix'], list)
    assert len(data['matrix']) == 16384
    
    # Verify the actual content (first few values should match the fixture)
    assert data['matrix'][:5] == mock_latest_matrix_data[:5]
