import java.util.List;

/**
 * Repository interface for User entities.
 * Defines the CRUD operations for managing users.
 */
public interface UserRepository {
    
    /**
     * Finds a user by their ID.
     * 
     * @param id the ID of the user to find
     * @return the user with the specified ID, or null if not found
     */
    User findById(String id);
    
    /**
     * Retrieves all users.
     * Returns a defensive copy of the internal list to prevent external modification.
     * 
     * @return a list containing all users, preserving insertion/upsert order
     */
    List<User> findAll();
    
    /**
     * Saves a user, performing validation.
     * If a user with the same ID already exists, it will be replaced (upsert).
     * 
     * @param user the user to save
     * @return the saved user
     * @throws IllegalArgumentException if the user is invalid
     */
    User save(User user);
    
    /**
     * Deletes a user by their ID.
     * 
     * @param id the ID of the user to delete
     * @return true if a user was deleted, false if no user with the ID existed
     */
    boolean deleteById(String id);
}