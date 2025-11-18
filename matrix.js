

// --- Configuration ---
        const N = 128; // Matrix dimension
        const CELL_SIZE = 512 / N; 
        const INTERVAL_MS = 1000; // 1 second update rate
        const DATA_API_URL = 'http://127.0.0.1:5000/latest_matrix';
        const SAMPLE_DATA_SOURCE_URL = 'http://127.0.0.1:5000/sensor_data';


        // --- D3 Setup ---
        const svg = d3.select("#matrix");
        const dataStatusDiv = d3.select("#data-status");
        
        // Color scale (0-100 map to color)
        const colorScale = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, 100]); 
        // const colorScale = d3.scaleSequential(d3.interpolateYlOrRd).domain([0, 100]); // Data normalized from 0 to 100
    
        // Initial data placeholder
        const initialData = Array(N * N).fill(0).map((d, i) => ({
            x: i % N,
            y: Math.floor(i / N),
            value: 0
        }));


        // --- Data Transformation Logic (Core Logic) ---

        /**
         * Decodes the JSON response containing the matrix array.
         * @param {Array<number>} flatValues - The 16384 element array of floats (0-100).
         * @returns {Array<Object>} D3-compatible data objects: [{x, y, value}, ...]
         */
        function transformFlatData(flatValues) {
            const data = [];
            for (let i = 0; i < flatValues.length; i++) {
                data.push({
                    x: i % N,
                    y: Math.floor(i / N),
                    value: flatValues[i]
                });
            }
            return data;
        }
        
        // --- D3 Rendering ---

        function updateMatrix(data) {
            const cells = svg.selectAll(".cell")
                .data(data, d => `${d.x}-${d.y}`);

            cells.enter()
                .append("rect")
                .attr("class", "cell")
                .attr("x", d => d.x * CELL_SIZE)
                .attr("y", d => d.y * CELL_SIZE)
                .attr("width", CELL_SIZE)
                .attr("height", CELL_SIZE)
                .merge(cells)
                .transition()
                .duration(INTERVAL_MS * 1)
                .attr("fill", d => colorScale(d.value));
        }

        // --- Data Fetching Loop ---

        function runFetchLoop() {
            d3.interval(() => {
                dataStatusDiv.html(`Fetching... (${new Date().toLocaleTimeString()})`);
                
                fetch(DATA_API_URL)
                    .then(response => {
                        if (response.status === 204) {
                            dataStatusDiv.text("Waiting for live UDP data...");
                            return Promise.reject("No data received yet (204)");
                        }
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json(); 
                    })
                    .then(data => {
                        const matrixData = transformFlatData(data.matrix);
                        updateMatrix(matrixData);
                        dataStatusDiv.html(`
                            <p>Status: <span class="text-green-600 font-bold">LIVE</span></p>
                            <p>Timestamp: ${new Date(data.timestamp).toLocaleTimeString()}</p>
                            <p>Source: ${data.message.includes("UDP") ? 'UDP Stream' : 'Synthetic Fallback'}</p>
                        `);
                    })
                    .catch(error => {
                        if (error !== "No data received yet (204)") {
                            dataStatusDiv.html(`<p class="text-red-600 font-bold">Error: ${error.message || error}</p>`);
                        }
                    });
            }, INTERVAL_MS);
        }
        
        runFetchLoop();
