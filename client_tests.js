// Set up global references to the assertion library and the function under test
const expect = chai.expect;
const assert = chai.assert;

// Reference the globally exposed function and constants from testing_client.html
const N = window.N;
const transformFlatData = window.transformFlatData;
const EXPECTED_ARRAY_SIZE = N * N;

describe('Data Transformation Logic (transformFlatData)', () => {

    it('should correctly transform a flat array into 16384 D3 coordinate objects', () => {
        // Arrange: Create a mock input array of the expected size
        const mockInput = Array(EXPECTED_ARRAY_SIZE).fill(50);
        
        // Act
        const output = transformFlatData(mockInput);
        
        // Assert
        expect(output).to.be.an('array');
        expect(output).to.have.lengthOf(EXPECTED_ARRAY_SIZE, `The output array length must be ${EXPECTED_ARRAY_SIZE}`);
        expect(output[0]).to.have.keys(['x', 'y', 'value']);
    });

    it('should correctly map values and calculate grid coordinates', () => {
        // Arrange: Input array with specific values to check mapping and coordinates
        const specificValue = 77.7;
        const mockInput = [0, 100, specificValue]; // Check index 2
        for (let i = 3; i < EXPECTED_ARRAY_SIZE; i++) { mockInput.push(50); } // Pad the rest

        // The coordinate for index 2 should be x=2, y=0 (since 2 % 128 = 2 and floor(2/128) = 0)
        const output = transformFlatData(mockInput);

        // Assert: Value check
        expect(output[0].value).to.equal(0);
        expect(output[1].value).to.equal(100);
        expect(output[2].value).to.equal(specificValue);

        // Assert: Coordinate check (index 129 should be x=1, y=1)
        const index129 = N + 1; // 129
        expect(output[index129].x).to.equal(1, 'Expected x=1');
        expect(output[index129].y).to.equal(1, 'Expected y=1');
        
        // Assert: Coordinate check (index 128 should be x=0, y=1)
        const index128 = N; // 128
        expect(output[index128].x).to.equal(0, 'Expected x=0');
        expect(output[index128].y).to.equal(1, 'Expected y=1');
    });

    it('should handle floating point numbers correctly', () => {
        // Arrange
        const floatValue = 3.14159;
        const mockInput = Array(EXPECTED_ARRAY_SIZE).fill(floatValue);
        const output = transformFlatData(mockInput);
        
        // Assert using closeTo for floating point comparison safety
        expect(output[500].value).to.be.closeTo(floatValue, 0.00001, 'Value should match the float input');
    });
});
