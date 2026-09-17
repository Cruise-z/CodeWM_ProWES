/**
 * Provides utilities for encoding and decoding text payloads in QR code format.
 * Handles framing, checksum computation, and bit-level conversions with exact padding rules.
 */
public class TextEncoder {

    /**
     * Encodes a text string into a QR code payload frame.
     * The frame consists of: [length-high, length-low, payload, checksum]
     * where length is the unsigned big-endian representation of the payload length,
     * and checksum is computed over the prefix (length + payload) only.
     *
     * @param text the text to encode
     * @return the encoded payload frame as bytes
     */
    public static byte[] encodePayload(String text) {
        byte[] utf8Bytes = text.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        int length = utf8Bytes.length;
        
        // Create frame: [length-high, length-low, payload, checksum]
        byte[] frame = new byte[2 + length + 1];
        
        // Set length bytes (big-endian)
        frame[0] = (byte) ((length >> 8) & 0xFF);
        frame[1] = (byte) (length & 0xFF);
        
        // Copy payload bytes
        System.arraycopy(utf8Bytes, 0, frame, 2, length);
        
        // Compute and set checksum over prefix only (length + payload)
        byte[] prefix = java.util.Arrays.copyOf(frame, frame.length - 1);
        int checksum = Checksum.sumMod256(prefix);
        frame[frame.length - 1] = (byte) checksum;
        
        return frame;
    }

    /**
     * Decodes a QR code payload frame back into a text string.
     * Validates the frame length and checksum before decoding.
     *
     * @param frame the payload frame to decode
     * @return the decoded text string
     * @throws IllegalArgumentException if frame length is invalid or checksum doesn't match
     */
    public static String decodePayload(byte[] frame) {
        if (frame == null || frame.length < 3) {
            throw new IllegalArgumentException("Frame must have at least 3 bytes");
        }
        
        // Extract length from first two bytes
        int length = ((frame[0] & 0xFF) << 8) | (frame[1] & 0xFF);
        
        // Validate frame length: must be exactly 2 + length + 1
        int expectedLength = 2 + length + 1;
        if (frame.length != expectedLength) {
            throw new IllegalArgumentException(
                "Frame length mismatch: expected " + expectedLength + ", got " + frame.length);
        }
        
        // Validate checksum over prefix (length + payload)
        byte[] prefix = java.util.Arrays.copyOf(frame, frame.length - 1);
        int expectedChecksum = Checksum.sumMod256(prefix);
        int actualChecksum = frame[frame.length - 1] & 0xFF;
        
        if (expectedChecksum != actualChecksum) {
            throw new IllegalArgumentException(
                "Checksum mismatch: expected " + expectedChecksum + ", got " + actualChecksum);
        }
        
        // Return UTF-8 decoded string
        return new String(frame, 2, length, java.nio.charset.StandardCharsets.UTF_8);
    }

    /**
     * Converts an array of bytes into an array of bits.
     * Each byte contributes exactly 8 bits in MSB-first order.
     *
     * @param bytes the input byte array
     * @return a boolean array of bits
     */
    public static boolean[] bytesToBits(byte[] bytes) {
        if (bytes == null) {
            return new boolean[0];
        }
        
        boolean[] bits = new boolean[bytes.length * 8];
        for (int i = 0; i < bytes.length; i++) {
            for (int bit = 0; bit < 8; bit++) {
                bits[i * 8 + bit] = (bytes[i] & (1 << (7 - bit))) != 0;
            }
        }
        
        return bits;
    }

    /**
     * Converts an array of bits into an array of bytes.
     * Accepts any bit length, including non-multiples of 8.
     * Final partial byte is padded with trailing zeros.
     *
     * @param bits the input bit array
     * @return a byte array containing the converted bits
     */
    public static byte[] bitsToBytes(boolean[] bits) {
        if (bits == null) {
            return new byte[0];
        }
        
        // Calculate how many bytes we'll need (ceiling division)
        int byteCount = (bits.length + 7) / 8;
        byte[] result = new byte[byteCount];
        
        // Convert each bit to the corresponding byte
        for (int i = 0; i < bits.length; i++) {
            if (bits[i]) {
                result[i / 8] |= (byte) (1 << (7 - (i % 8)));
            }
        }
        
        return result;
    }
}