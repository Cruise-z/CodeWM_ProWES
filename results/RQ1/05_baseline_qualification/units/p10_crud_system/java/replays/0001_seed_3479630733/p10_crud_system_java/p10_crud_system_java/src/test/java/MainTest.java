import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.ArrayList;

public class MainTest {

    @Test
    public void testRuntimeAndValueObjects() {
        // Test that Main.main runs without exception
        Main.main(new String[0]);
        
        // Test User value object behavior
        User user = new User("1", "Alice Smith", "alice@example.com");
        assertEquals("1", user.getId());
        assertEquals("Alice Smith", user.getName());
        assertEquals("alice@example.com", user.getEmail());
        assertEquals(user, new User("1", "Alice Smith", "alice@example.com"));
        assertNotEquals(user, new User("2", "Alice Smith", "alice@example.com"));
        
        // Test AuditEvent value object behavior with fixed timestamp
        long timestamp = 1640995200000L;
        AuditEvent event = new AuditEvent(timestamp, "CREATE_USER", "1");
        assertEquals(timestamp, event.getTimestamp());
        assertEquals("CREATE_USER", event.getAction());
        assertEquals("1", event.getUserId());
        assertEquals(event, new AuditEvent(timestamp, "CREATE_USER", "1"));
        assertNotEquals(event, new AuditEvent(timestamp, "UPDATE_USER", "1"));
    }

    @Test
    public void testValidationAndSearch() {
        // Test UserValidator behavior
        UserValidator validator = new UserValidator();
        assertFalse(validator.isValid(new User("", null, "")));
        
        // Test SearchService behavior with Alice Smith and Bob Jones fixture
        List<User> users = new ArrayList<>();
        users.add(new User("1", "Alice Smith", "alice@example.com"));
        users.add(new User("2", "Bob Jones", "bob@example.com"));
        
        SearchService searchService = new SearchService();
        List<User> results = searchService.search(users, "smith");
        
        assertEquals(1, results.size());
        assertEquals("1", results.get(0).getId());
        assertEquals("Alice Smith", results.get(0).getName());
    }

    @Test
    public void testCrudAndExplicitAudit() {
        // Setup
        InMemoryUserRepository repository = new InMemoryUserRepository();
        AuditLogService auditLogService = new AuditLogService();
        
        // Test CRUD operations
        User user1 = new User("1", "Alice Smith", "alice@example.com");
        repository.save(user1); // upsert
        
        User retrievedUser = repository.findById("1");
        assertNotNull(retrievedUser);
        assertEquals("1", retrievedUser.getId());
        assertEquals("Alice Smith", retrievedUser.getName());
        
        boolean deleted = repository.deleteById("1");
        assertTrue(deleted);
        
        User afterDelete = repository.findById("1");
        assertNull(afterDelete);
        
        // Test explicit audit logging
        long timestamp = 1640995200000L;
        auditLogService.log(new AuditEvent(timestamp, "CREATE_USER", "1"));
        auditLogService.log(new AuditEvent(timestamp, "DELETE_USER", "1"));
        
        List<AuditEvent> events = auditLogService.getAllEvents();
        assertEquals(2, events.size());
        assertEquals("CREATE_USER", events.get(0).getAction());
        assertEquals("DELETE_USER", events.get(1).getAction());
        
        // Verify repository didn't log implicitly
        List<AuditEvent> repoEvents = auditLogService.getAllEvents(); // Should still be 2
        assertEquals(2, repoEvents.size());
    }
}