/**
 * Value object holding information about a token during lexical analysis.
 * Contains the token type, original text, and optional numeric value for NUMBER tokens.
 */
public class Token {
    /** The type of this token */
    public final TokenType type;
    
    /** The original text representation of this token */
    public final String text;
    
    /** The numeric value if this is a NUMBER token, otherwise null */
    public final Double numericValue;

    /**
     * Constructs a new Token with the specified type, text, and numeric value.
     *
     * @param type the type of the token
     * @param text the original text of the token
     * @param numericValue the numeric value if this is a NUMBER token, otherwise null
     */
    public Token(TokenType type, String text, Double numericValue) {
        this.type = type;
        this.text = text;
        this.numericValue = numericValue;
    }
}