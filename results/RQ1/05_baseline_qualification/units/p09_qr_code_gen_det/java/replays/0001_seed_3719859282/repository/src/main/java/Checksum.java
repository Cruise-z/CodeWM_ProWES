/**
 * Provides utility methods for computing checksums.
 */
public class Checksum {
    
    /**
     * Computes the sum of bytes in the given array, treating each byte as unsigned,
     * and returns the result modulo 256.
     *
     * @param data the byte array to sum
     * @return the sum of all bytes modulo 256
     */
    public static int sumMod256(byte[] data) {
        int sum = 0;
        for (byte b : data) {
            sum += (b & 0xFF);
        }
        return sum % 256;
    }
}