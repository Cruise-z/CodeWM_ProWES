/**
 * Enum representing the different types of tokens that can be generated
 * during the tokenization of an arithmetic expression.
 */
public enum TokenType {
    /** Represents a numeric literal */
    NUMBER,
    
    /** Represents the addition operator */
    PLUS,
    
    /** Represents the subtraction operator */
    MINUS,
    
    /** Represents the multiplication operator */
    STAR,
    
    /** Represents the division operator */
    SLASH,
    
    /** Represents an opening parenthesis */
    LPAREN,
    
    /** Represents a closing parenthesis */
    RPAREN,
    
    /** Represents the end of file/input */
    EOF
}