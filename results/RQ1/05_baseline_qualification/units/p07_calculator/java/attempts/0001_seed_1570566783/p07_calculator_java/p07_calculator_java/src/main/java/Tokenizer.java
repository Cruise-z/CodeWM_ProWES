/**
 * Tokenizer for arithmetic expressions.
 * Converts a string input into a list of tokens.
 * Skips whitespace and recognizes numbers, operators, and parentheses.
 */
import java.util.ArrayList;
import java.util.List;

public class Tokenizer {
    /** The input string being tokenized */
    private final String input;
    
    /** Current position in the input string */
    private int position;
    
    /** Length of the input string */
    private final int length;

    /**
     * Constructs a new Tokenizer with the given input string.
     *
     * @param input the arithmetic expression to tokenize
     */
    public Tokenizer(String input) {
        this.input = input;
        this.position = 0;
        this.length = input.length();
    }

    /**
     * Tokenizes the input string into a list of tokens.
     *
     * @return a list of tokens representing the input expression
     * @throws TokenizationException if the input contains invalid characters or malformed numbers
     */
    public List<Token> tokenize() throws TokenizationException {
        List<Token> tokens = new ArrayList<>();
        
        while (position < length) {
            char ch = input.charAt(position);
            
            // Skip whitespace
            if (Character.isWhitespace(ch)) {
                position++;
                continue;
            }
            
            // Handle numbers (including decimals)
            if (Character.isDigit(ch) || ch == '.') {
                tokens.add(readNumber());
            } 
            // Handle operators and parentheses
            else if (ch == '+') {
                tokens.add(new Token(TokenType.PLUS, "+", null));
                position++;
            } else if (ch == '-') {
                tokens.add(new Token(TokenType.MINUS, "-", null));
                position++;
            } else if (ch == '*') {
                tokens.add(new Token(TokenType.STAR, "*", null));
                position++;
            } else if (ch == '/') {
                tokens.add(new Token(TokenType.SLASH, "/", null));
                position++;
            } else if (ch == '(') {
                tokens.add(new Token(TokenType.LPAREN, "(", null));
                position++;
            } else if (ch == ')') {
                tokens.add(new Token(TokenType.RPAREN, ")", null));
                position++;
            } 
            // Invalid character
            else {
                throw new TokenizationException("Invalid character '" + ch + "' at position " + position);
            }
        }
        
        // Add EOF token
        tokens.add(new Token(TokenType.EOF, "", null));
        return tokens;
    }

    /**
     * Reads a number token starting at the current position.
     *
     * @return a Token representing the number
     * @throws TokenizationException if the number is malformed
     */
    private Token readNumber() throws TokenizationException {
        int start = position;
        
        // Read digits and decimal point
        while (position < length && (Character.isDigit(input.charAt(position)) || input.charAt(position) == '.')) {
            position++;
        }
        
        // Extract the number string
        String numberStr = input.substring(start, position);
        
        // Validate and convert to Double
        try {
            Double numericValue = Double.parseDouble(numberStr);
            return new Token(TokenType.NUMBER, numberStr, numericValue);
        } catch (NumberFormatException e) {
            throw new TokenizationException("Malformed number '" + numberStr + "' at position " + start);
        }
    }
}