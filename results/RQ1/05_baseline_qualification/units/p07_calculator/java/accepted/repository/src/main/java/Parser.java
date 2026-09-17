/**
 * Recursive-descent parser and evaluator for arithmetic expressions.
 * Honors operator precedence (*, / over +, -), left associativity,
 * parentheses, and unary minus. Evaluates tokens to a double.
 */
public class Parser {
    /** List of tokens to parse */
    private final java.util.List<Token> tokens;
    
    /** Current position in the token list */
    private int position;

    /**
     * Constructs a new Parser with the given list of tokens.
     *
     * @param tokens the list of tokens to parse
     */
    public Parser(java.util.List<Token> tokens) {
        this.tokens = tokens;
        this.position = 0;
    }

    /**
     * Parses and evaluates the expression represented by the tokens.
     *
     * @return the numeric result of the evaluation
     * @throws ParseException if there are syntax errors
     * @throws EvaluationException if there are arithmetic errors (e.g., division by zero)
     */
    public double evaluate() throws ParseException, EvaluationException {
        double result = parseExpression();
        
        // Ensure we've consumed all tokens
        if (currentToken().type != TokenType.EOF) {
            throw new ParseException("Unexpected token at end of expression");
        }
        
        return result;
    }

    /**
     * Parses an expression with addition and subtraction operators.
     * Handles left-associative operators with same precedence.
     *
     * @return the evaluated result of the expression
     * @throws ParseException if there are syntax errors
     * @throws EvaluationException if there are arithmetic errors
     */
    private double parseExpression() throws ParseException, EvaluationException {
        double result = parseTerm();
        
        while (currentToken().type == TokenType.PLUS || currentToken().type == TokenType.MINUS) {
            TokenType operator = currentToken().type;
            advance(); // consume operator
            
            double right = parseTerm();
            
            if (operator == TokenType.PLUS) {
                result += right;
            } else {
                result -= right;
            }
        }
        
        return result;
    }

    /**
     * Parses a term with multiplication and division operators.
     * Handles left-associative operators with same precedence.
     *
     * @return the evaluated result of the term
     * @throws ParseException if there are syntax errors
     * @throws EvaluationException if there are arithmetic errors
     */
    private double parseTerm() throws ParseException, EvaluationException {
        double result = parseFactor();
        
        while (currentToken().type == TokenType.STAR || currentToken().type == TokenType.SLASH) {
            TokenType operator = currentToken().type;
            advance(); // consume operator
            
            double right = parseFactor();
            
            if (operator == TokenType.STAR) {
                result *= right;
            } else {
                if (right == 0.0) {
                    throw new DivisionByZeroException();
                }
                result /= right;
            }
        }
        
        return result;
    }

    /**
     * Parses a factor which can be a number, parenthesized expression, or unary minus.
     *
     * @return the evaluated result of the factor
     * @throws ParseException if there are syntax errors
     * @throws EvaluationException if there are arithmetic errors
     */
    private double parseFactor() throws ParseException, EvaluationException {
        Token token = currentToken();
        
        switch (token.type) {
            case NUMBER:
                advance(); // consume number
                return token.numericValue;
                
            case MINUS:
                advance(); // consume minus
                return -parseFactor(); // unary minus
                
            case LPAREN:
                advance(); // consume (
                double result = parseExpression();
                
                // Expect closing parenthesis
                if (currentToken().type != TokenType.RPAREN) {
                    throw new ParseException("Expected ')' after expression");
                }
                
                advance(); // consume )
                return result;
                
            default:
                throw new ParseException("Unexpected token: " + token.text);
        }
    }

    /**
     * Returns the current token without advancing the position.
     *
     * @return the current token
     */
    private Token currentToken() {
        return tokens.get(position);
    }

    /**
     * Advances the position to the next token.
     */
    private void advance() {
        position++;
    }
}