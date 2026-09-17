import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.LinkedHashMap;

/**
 * In-memory implementation of the UserRepository interface.
 * Uses LinkedHashMap to maintain insertion/upsert order.
 * Performs validation on save operations.
 */
public class InMemoryUserRepository implements UserRepository {
    private final Map<String, User> store;
    private final UserValidator validator;

    /**
     * Creates a new InMemoryUserRepository with an empty store.
     */
    public InMemoryUserRepository() {
        this.store = new LinkedHashMap<>();
        this.validator = new UserValidator();
    }

    /**
     * Finds a user by their ID.
     * 
     * @param id the ID of the user to find
     * @return the user with the specified ID, or null if not found
     */
    @Override
    public User findById(String id) {
        return store.get(id);
    }

    /**
     * Retrieves all users.
     * Returns a defensive copy of the internal list to prevent external modification.
     * 
     * @return a list containing all users, preserving insertion/upsert order
     */
    @Override
    public List<User> findAll() {
        return new ArrayList<>(store.values());
    }

    /**
     * Saves a user, performing validation.
     * If a user with the same ID already exists, it will be replaced (upsert).
     * 
     * @param user the user to save
     * @return the saved user
     * @throws IllegalArgumentException if the user is invalid
     */
    @Override
    public User save(User user) {
        if (!validator.isValid(user)) {
            throw new IllegalArgumentException("Invalid user data");
        }
        return store.put(user.getId(), user);
    }

    /**
     * Deletes a user by their ID.
     * 
     * @param id the ID of the user to delete
     * @return true if a user was deleted, false if no user with the ID existed
     */
    @Override
    public boolean deleteById(String id) {
        return store.remove(id) != null;
    }
}