/**
 * Main entry point for the QR Code Generator and Detector demonstration.
 * Encodes a fixed string, renders the matrix, decodes it back, and prints the result.
 */
public class Main {
    
    /**
     * Main method that demonstrates the QR code encoding, rendering, and decoding process.
     * 
     * @param args command-line arguments (not used)
     */
    public static void main(String[] args) {
        // Fixed demonstration string
        String msg = "hello-世界";
        
        // Create QR codec instance
        QRCodec codec = new QRCodec();
        
        // Encode the message
        QRMatrix matrix = codec.encode(msg);
        
        // Render the matrix
        String rendered = QRRenderer.render(matrix);
        
        // Decode the message back
        String decoded = codec.decode(matrix);
        
        // Print the concise result
        System.out.println("Original: " + msg);
        System.out.println("Decoded:  " + decoded);
        System.out.println("Match:    " + msg.equals(decoded));
        System.out.println("Rendered matrix:");
        System.out.println(rendered);
    }
}