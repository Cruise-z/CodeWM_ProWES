/**
 * Represents a user with an ID, name, and email.
 * This is a typed stored domain object with value semantics.
 * The constructor stores arguments unchanged and never validates them.
 * Validation is performed by UserValidator.
 */
public final class User {
    private final String id;
    private final String name;
    private final String email;

    /**
     * Creates a new User with the specified ID, name, and email.
     * Values are stored unchanged (including null or blank values).
     *
     * @param id    the user's ID
     * @param name  the user's name
     * @param email the user's email
     */
    public User(String id, String name, String email) {
        this.id = id;
        this.name = name;
        this.email = email;
    }

    /**
     * Gets the user's ID.
     *
     * @return the user's ID
     */
    public String getId() {
        return id;
    }

    /**
     * Gets the user's name.
     *
     * @return the user's name
     */
    public String getName() {
        return name;
    }

    /**
     * Gets the user's email.
     *
     * @return the user's email
     */
    public String getEmail() {
        return email;
    }

    /**
     * Checks if this User is equal to another object.
     * Two Users are equal if they have the same ID, name, and email.
     *
     * @param obj the object to compare with
     * @return true if the objects are equal, false otherwise
     */
    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }

        User user = (User) obj;

        if (id != null ? !id.equals(user.id) : user.id != null) {
            return false;
        }
        if (name != null ? !name.equals(user.name) : user.name != null) {
            return false;
        }
        return email != null ? email.equals(user.email) : user.email == null;
    }

    /**
     * Returns a hash code value for the User.
     *
     * @return a hash code value for this User
     */
    @Override
    public int hashCode() {
        int result = id != null ? id.hashCode() : 0;
        result = 31 * result + (name != null ? name.hashCode() : 0);
        result = 31 * result + (email != null ? email.hashCode() : 0);
        return result;
    }

    /**
     * Returns a string representation of the User.
     *
     * @return a string representation of the User
     */
    @Override
    public String toString() {
        return "User{" +
                "id='" + id + '\'' +
                ", name='" + name + '\'' +
                ", email='" + email + '\'' +
                '}';
    }
}