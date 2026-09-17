/**
 * Stateless search service for filtering users by name tokens.
 * Performs exact case-insensitive whitespace-delimited name-token matching.
 * Preserves input order and never mutates inputs.
 */
import java.util.List;
import java.util.ArrayList;

public class SearchService {

    /**
     * Searches for users whose names contain the specified query as a whitespace-delimited token.
     * 
     * @param users the list of users to search through (can be null)
     * @param query the query string to search for (can be null or blank)
     * @return a new list containing matching users, or an empty list if users is null
     *         or query is null/blank; otherwise returns a defensive copy of users
     *         where each user's name contains the query as a token
     */
    public List<User> search(List<User> users, String query) {
        // Handle null users list
        if (users == null) {
            return new ArrayList<>();
        }
        
        // Handle null or blank query
        if (query == null || query.trim().isEmpty()) {
            // Return a defensive copy of the original list
            return new ArrayList<>(users);
        }
        
        // Process the query
        String processedQuery = query.trim().toLowerCase();
        
        // Result list
        List<User> results = new ArrayList<>();
        
        // Iterate through users
        for (User user : users) {
            // Skip null users
            if (user == null) {
                continue;
            }
            
            // Get the user's name
            String userName = user.getName();
            
            // Skip users with null or blank names
            if (userName == null || userName.trim().isEmpty()) {
                continue;
            }
            
            // Split the user's name into tokens (whitespace delimited)
            String[] nameTokens = userName.trim().toLowerCase().split("\\s+");
            
            // Check if any token matches the query
            for (String token : nameTokens) {
                if (token.equals(processedQuery)) {
                    results.add(user);
                    break; // No need to check remaining tokens for this user
                }
            }
        }
        
        return results;
    }
}