/**
 * Orchestrates the encoding and decoding of QR codes.
 * Provides end-to-end functionality for converting text to QR matrices and vice versa.
 */
public class QRCodec {

    /**
     * Encodes the given text into a QR code matrix of the specified size.
     * 
     * @param text the text to encode
     * @param size the size of the QR code matrix (must be odd and >= 21)
     * @return a QRMatrix representing the encoded data
     * @throws IllegalArgumentException if size is invalid or if the text cannot fit
     */
    public QRMatrix encode(String text, int size) {
        // Validate the size
        MatrixValidator.ensureValidSize(size);
        
        // Get the reserved mask for the given size
        boolean[][] reserved = FinderPattern.reservedMask(size);
        
        // Get the capacity in bits
        int capacity = MatrixValidator.capacityBits(size);
        
        // Encode the payload
        byte[] frame = TextEncoder.encodePayload(text);
        int frameBitsLen = frame.length * 8;
        
        // Check if the frame fits within the capacity
        if (frameBitsLen > capacity) {
            throw new IllegalArgumentException("Text too long for the given matrix size");
        }
        
        // Convert frame to bits
        boolean[] bits = TextEncoder.bytesToBits(frame);
        
        // Create the matrix
        QRMatrix matrix = new QRMatrix(size);
        
        // Place the finder patterns
        FinderPattern.place(matrix);
        
        // Get the traversal order
        int[][] traversalOrder = ZigZag.traversal(size, reserved);
        
        // Fill the matrix with data bits
        for (int i = 0; i < bits.length; i++) {
            int[] coord = traversalOrder[i];
            matrix.set(coord[0], coord[1], bits[i]);
        }
        
        // Leave remaining cells as false
        return matrix;
    }

    /**
     * Encodes the given text into a QR code matrix with the smallest valid size
     * that can accommodate the text.
     * 
     * @param text the text to encode
     * @return a QRMatrix representing the encoded data
     */
    public QRMatrix encode(String text) {
        // Start with the minimum valid size
        int size = 21;
        
        // Keep increasing size until we have enough capacity
        while (true) {
            // Get the capacity for this size
            int capacity = MatrixValidator.capacityBits(size);
            
            // Encode the payload to get the required number of bits
            byte[] frame = TextEncoder.encodePayload(text);
            int frameBitsLen = frame.length * 8;
            
            // If the frame fits, encode with this size
            if (frameBitsLen <= capacity) {
                return encode(text, size);
            }
            
            // Otherwise, try the next size
            size += 2;
        }
    }

    /**
     * Decodes the given QR code matrix back into text.
     * 
     * @param matrix the QR code matrix to decode
     * @return the decoded text
     * @throws IllegalArgumentException if the matrix is invalid or corrupted
     */
    public String decode(QRMatrix matrix) {
        // Verify the finder patterns
        FinderPattern.verify(matrix);
        
        // Extract the payload bytes
        byte[] frame = QRDetector.extractPayloadBytes(matrix);
        
        // Decode the payload
        return TextEncoder.decodePayload(frame);
    }
}