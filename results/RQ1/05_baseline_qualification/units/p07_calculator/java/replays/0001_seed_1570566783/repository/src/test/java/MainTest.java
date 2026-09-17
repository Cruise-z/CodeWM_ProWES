import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.util.List;

public class MainTest {

    @Test
    public void testCalculatorWiringPrecedenceWithUnaryMinus() {
        Calculator calc = new Calculator();
        CalculationResult result = calc.evaluate("-3 + 4*2/(1-5)");
        
        assertTrue(result.isSuccess(), "Expression should evaluate successfully");
        assertEquals(-5.0, result.getResult(), 0.0001, "Result should match expected precedence and unary minus behavior");
    }

    @Test
    public void testDivisionByZeroErrorPropagation() {
        Calculator calc = new Calculator();
        CalculationResult result = calc.evaluate("1/0");
        
        assertFalse(result.isSuccess(), "Division by zero should result in failure");
        assertNotNull(result.getErrorMessage(), "Error message should not be null");
        assertTrue(result.getErrorMessage().contains("Division by zero"), "Error message should indicate division by zero");
    }

    @Test
    public void testHistoryCapacity() {
        Calculator calc = new Calculator(2); // History capacity of 2
        
        // Perform three evaluations
        calc.evaluate("1+1");
        calc.evaluate("2+2"); 
        calc.evaluate("3+3"); // This should evict the first entry
        
        List<HistoryEntry> history = calc.history();
        assertEquals(2, history.size(), "History should contain exactly 2 entries");
        
        // Check that the first entry (index 0) was evicted
        assertEquals("2+2", history.get(0).getExpression(), "First entry should be second expression");
        assertEquals("3+3", history.get(1).getExpression(), "Second entry should be third expression");
    }
}