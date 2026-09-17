/**
 * Explicit audit log service for recording audit events.
 * Provides append-only logging and defensive retrieval of events.
 */
import java.util.List;
import java.util.ArrayList;

public class AuditLogService {
    private final List<AuditEvent> events;

    /**
     * Creates a new AuditLogService with an empty log.
     */
    public AuditLogService() {
        this.events = new ArrayList<>();
    }

    /**
     * Logs an audit event.
     * 
     * @param event the audit event to log (must not be null)
     * @throws IllegalArgumentException if event is null
     */
    public void log(AuditEvent event) {
        if (event == null) {
            throw new IllegalArgumentException("Event cannot be null");
        }
        events.add(event);
    }

    /**
     * Gets all logged audit events.
     * Returns a defensive copy of the internal list.
     * 
     * @return a new list containing all audit events in order
     */
    public List<AuditEvent> getAllEvents() {
        return new ArrayList<>(events);
    }
}