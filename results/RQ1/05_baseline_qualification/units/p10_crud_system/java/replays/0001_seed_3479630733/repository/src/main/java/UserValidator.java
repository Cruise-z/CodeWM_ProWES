/**
 * Stateless validation rule for User objects.
 * Checks that user fields are not null or blank.
 */
public class UserValidator {
    
    /**
     * Validates a User object.
     * Returns false for null user or null/blank id, name, or email.
     * Returns true otherwise.
     *
     * @param user the User to validate
     * @return true if valid, false otherwise
     */
    public boolean isValid(User user) {
        if (user == null) {
            return false;
        }
        
        String id = user.getId();
        String name = user.getName();
        String email = user.getEmail();
        
        return !isBlank(id) && !isBlank(name) && !isBlank(email);
    }
    
    /**
     * Checks if a string is null or blank (contains only whitespace).
     *
     * @param str the string to check
     * @return true if null or blank, false otherwise
     */
    private boolean isBlank(String str) {
        return str == null || str.trim().isEmpty();
    }
}