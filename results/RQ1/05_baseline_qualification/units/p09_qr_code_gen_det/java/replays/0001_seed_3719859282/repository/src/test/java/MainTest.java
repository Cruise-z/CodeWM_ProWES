import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class MainTest {

    @Test
    public void testMainReturnsNormally() {
        // Test that Main.main executes without throwing exceptions
        Main.main(new String[0]);
    }

    @Test
    public void testNineBitPaddingFixture() {
        // Test the exact nine-bit padding fixture
        boolean[] input = {true, false, false, false, false, false, false, false, true};
        byte[] result = TextEncoder.bitsToBytes(input);
        
        // Should produce two bytes with values 128 and 128
        assertEquals(2, result.length);
        assertEquals(128, result[0] & 0xFF); // Unsigned comparison
        assertEquals(128, result[1] & 0xFF); // Unsigned comparison
    }

    @Test
    public void testRoundTripAndRendering() {
        // Test direct round trip: encodePayload -> decodePayload
        String originalText = "hello-世界";
        byte[] encoded = TextEncoder.encodePayload(originalText);
        String decoded = TextEncoder.decodePayload(encoded);
        assertEquals(originalText, decoded);

        // Test matrix codec round trip
        QRCodec codec = new QRCodec();
        QRMatrix matrix = codec.encode(originalText);
        String decodedFromMatrix = codec.decode(matrix);
        assertEquals(originalText, decodedFromMatrix);

        // Test rendering has one line per row
        String rendered = QRRenderer.render(matrix);
        long lineCount = rendered.chars().filter(ch -> ch == '\n').count();
        assertEquals(matrix.getSize() - 1, lineCount, "Should have exactly one less newline than rows");
    }

    @Test
    public void testFinderCorruptionThrowsException() {
        // Test that corrupting a finder cell causes decode to throw IllegalArgumentException
        QRCodec codec = new QRCodec();
        String originalText = "hello-世界";
        QRMatrix matrix = codec.encode(originalText);
        
        // Make a copy of the matrix to avoid modifying the original
        boolean[][] copyCells = matrix.copyCells();
        QRMatrix corruptedMatrix = new QRMatrix(matrix.getSize());
        for (int i = 0; i < matrix.getSize(); i++) {
            for (int j = 0; j < matrix.getSize(); j++) {
                corruptedMatrix.set(i, j, copyCells[i][j]);
            }
        }
        
        // Flip the top-left finder cell [0][0]
        corruptedMatrix.set(0, 0, !corruptedMatrix.get(0, 0));
        
        // Attempt to decode the corrupted matrix - should throw
        assertThrows(IllegalArgumentException.class, () -> codec.decode(corruptedMatrix));
    }
}