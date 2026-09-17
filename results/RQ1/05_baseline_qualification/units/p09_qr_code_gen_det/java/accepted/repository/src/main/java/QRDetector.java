/**
 * Provides utilities for detecting and extracting data from QR code matrices.
 */
public class QRDetector {

    /**
     * Reads all unreserved bits from the QR matrix in traversal order.
     * The returned array may not be byte-aligned.
     *
     * @param matrix the QR matrix to read from
     * @return a boolean array of all unreserved bits in traversal order
     */
    public static boolean[] readDataBits(QRMatrix matrix) {
        int size = matrix.getSize();
        boolean[][] reserved = FinderPattern.reservedMask(size);
        int[][] traversalOrder = ZigZag.traversal(size, reserved);
        
        boolean[] bits = new boolean[traversalOrder.length];
        for (int i = 0; i < traversalOrder.length; i++) {
            int[] coord = traversalOrder[i];
            bits[i] = matrix.get(coord[0], coord[1]);
        }
        
        return bits;
    }

    /**
     * Extracts the payload bytes from a QR matrix.
     * Reads all unreserved bits, converts them to bytes, extracts the length,
     * validates the frame, and returns the payload bytes.
     *
     * @param matrix the QR matrix to extract payload from
     * @return the extracted payload bytes
     * @throws IllegalArgumentException if the matrix is invalid or payload is malformed
     */
    public static byte[] extractPayloadBytes(QRMatrix matrix) {
        // Read all unreserved bits
        boolean[] bits = readDataBits(matrix);
        
        // Convert bits to bytes
        byte[] bytes = TextEncoder.bitsToBytes(bits);
        
        // Check if we have at least 2 bytes for length
        if (bytes.length < 2) {
            throw new IllegalArgumentException("Insufficient bytes to read length");
        }
        
        // Extract length from first two bytes (unsigned big-endian)
        int length = ((bytes[0] & 0xFF) << 8) | (bytes[1] & 0xFF);
        
        // Compute expected frame length
        int frameLength = 2 + length + 1;
        
        // Check if we have enough bytes
        if (bytes.length < frameLength) {
            throw new IllegalArgumentException(
                "Insufficient bytes for payload: expected at least " + frameLength + ", got " + bytes.length);
        }
        
        // Truncate to exact frame length
        byte[] frame = java.util.Arrays.copyOf(bytes, frameLength);
        
        // Validate the frame
        TextEncoder.decodePayload(frame);
        
        // Return the frame (payload + checksum)
        return frame;
    }
}