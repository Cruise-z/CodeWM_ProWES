/**
 * Stateless validation rules for headline, body, and contact fields.
 * Provides static methods to validate press release content.
 */
public final class Validator {
    
    /**
     * Validates that the headline is not null and not blank.
     * 
     * @param text the headline to validate
     * @return true if the headline is valid, false otherwise
     */
    public static boolean validateHeadline(String text) {
        return text != null && !text.trim().isEmpty();
    }
    
    /**
     * Validates that the body is not null and not blank.
     * 
     * @param text the body to validate
     * @return true if the body is valid, false otherwise
     */
    public static boolean validateBody(String text) {
        return text != null && !text.trim().isEmpty();
    }
    
    /**
     * Validates that the contact information is not null,
     * contains exactly one '@' character, and has non-empty
     * local and domain parts on both sides of the '@'.
     * 
     * @param text the contact information to validate
     * @return true if the contact is valid, false otherwise
     */
    public static boolean validateContact(String text) {
        if (text == null) {
            return false;
        }
        
        int atIndex = text.indexOf('@');
        // Must contain exactly one '@'
        if (atIndex == -1 || text.indexOf('@', atIndex + 1) != -1) {
            return false;
        }
        
        // Split the text at '@' and check both parts
        String localPart = text.substring(0, atIndex);
        String domainPart = text.substring(atIndex + 1);
        
        // Both parts must be non-empty after trimming
        return !localPart.trim().isEmpty() && !domainPart.trim().isEmpty();
    }
}