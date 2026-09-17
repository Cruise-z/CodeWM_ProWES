/**
 * Represents an audit event with a timestamp, action, and user ID.
 * This is a typed stored domain object with validating constructor.
 */
public final class AuditEvent {
    private final long timestamp;
    private final String action;
    private final String userId;

    /**
     * Creates a new AuditEvent with the specified timestamp, action, and user ID.
     * Validates that action and userId are not null or blank.
     *
     * @param timestamp the event timestamp
     * @param action    the action performed
     * @param userId    the ID of the user who performed the action
     * @throws IllegalArgumentException if action or userId is null or blank
     */
    public AuditEvent(long timestamp, String action, String userId) {
        if (action == null || action.trim().isEmpty()) {
            throw new IllegalArgumentException("Action cannot be null or blank");
        }
        if (userId == null || userId.trim().isEmpty()) {
            throw new IllegalArgumentException("User ID cannot be null or blank");
        }
        this.timestamp = timestamp;
        this.action = action;
        this.userId = userId;
    }

    /**
     * Gets the event timestamp.
     *
     * @return the event timestamp
     */
    public long getTimestamp() {
        return timestamp;
    }

    /**
     * Gets the action performed.
     *
     * @return the action performed
     */
    public String getAction() {
        return action;
    }

    /**
     * Gets the ID of the user who performed the action.
     *
     * @return the user ID
     */
    public String getUserId() {
        return userId;
    }

    /**
     * Checks if this AuditEvent is equal to another object.
     * Two AuditEvents are equal if they have the same timestamp, action, and userId.
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

        AuditEvent that = (AuditEvent) obj;

        if (timestamp != that.timestamp) {
            return false;
        }
        if (action != null ? !action.equals(that.action) : that.action != null) {
            return false;
        }
        return userId != null ? userId.equals(that.userId) : that.userId == null;
    }

    /**
     * Returns a hash code value for the AuditEvent.
     *
     * @return a hash code value for this AuditEvent
     */
    @Override
    public int hashCode() {
        int result = (int) (timestamp ^ (timestamp >>> 32));
        result = 31 * result + (action != null ? action.hashCode() : 0);
        result = 31 * result + (userId != null ? userId.hashCode() : 0);
        return result;
    }

    /**
     * Returns a string representation of the AuditEvent.
     *
     * @return a string representation of the AuditEvent
     */
    @Override
    public String toString() {
        return "AuditEvent{" +
                "timestamp=" + timestamp +
                ", action='" + action + '\'' +
                ", userId='" + userId + '\'' +
                '}';
    }
}