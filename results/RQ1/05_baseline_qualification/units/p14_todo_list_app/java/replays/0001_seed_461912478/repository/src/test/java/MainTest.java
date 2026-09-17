import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class MainTest {

    @Test
    public void testRuntimeDemo() {
        // Test that Main.main runs without exception and returns expected result
        Map<String, Integer> result = Main.runDemo();
        
        // Verify the exact expected values from the demo
        assertEquals(2, result.get("total").intValue());
        assertEquals(1, result.get("completed").intValue());
        assertEquals(1, result.get("pending").intValue());
        assertEquals(0, result.get("overdue").intValue());
    }

    @Test
    public void testCRUDValidation() {
        // Create a fresh repository and service for isolated testing
        TaskRepository repository = new InMemoryTaskRepository();
        TodoService service = new TodoService(repository);
        
        // Test 1: Blank title should throw IllegalArgumentException
        assertThrows(IllegalArgumentException.class, () -> {
            service.createTask("", "description", Priority.LOW, null, null);
        });
        
        // Test 2: Create a valid task
        Task task = service.createTask("Alpha", "description", Priority.LOW, null, null);
        assertEquals(1, task.getId());
        
        // Test 3: Edit the task to Beta
        Task editedTask = service.editTask(1, "Beta", "new description", Priority.MEDIUM, null, null);
        assertEquals("Beta", editedTask.getTitle());
        assertEquals("new description", editedTask.getDescription());
        assertEquals(Priority.MEDIUM, editedTask.getPriority());
        
        // Test 4: Mark as completed
        Task completedTask = service.setCompleted(1, true);
        assertTrue(completedTask.isCompleted());
        
        // Test 5: Delete the task
        assertTrue(service.deleteTask(1));
        assertFalse(service.deleteTask(1)); // Should return false on second attempt
        
        // Verify repository is now empty
        List<Task> allTasks = repository.findAll();
        assertEquals(0, allTasks.size());
    }

    @Test
    public void testFilterSort() {
        // Create a fresh repository and service for isolated testing
        TaskRepository repository = new InMemoryTaskRepository();
        TodoService service = new TodoService(repository);
        
        // Create tasks as described in test case:
        // Low due 2023-10-16 tagged work
        Task lowTask = service.createTask("Low", "description", Priority.LOW, LocalDate.of(2023, 10, 16), Set.of("work"));
        // High due 2023-10-17 tagged work/urgent
        Task highTask = service.createTask("High", "description", Priority.HIGH, LocalDate.of(2023, 10, 17), Set.of("work", "urgent"));
        // Medium with null due date tagged home
        Task mediumTask = service.createTask("Medium", "description", Priority.MEDIUM, null, Set.of("home"));
        
        // Filter incomplete tasks requiring work
        List<Task> filtered = service.listTasks(false, null, Set.of("work"));
        
        // Should return High then Low due to higher priority first
        assertEquals(2, filtered.size());
        assertEquals("High", filtered.get(0).getTitle());
        assertEquals("Low", filtered.get(1).getTitle());
    }

    @Test
    public void testSummary() {
        // Create a fresh repository and service for isolated testing
        TaskRepository repository = new InMemoryTaskRepository();
        TodoService service = new TodoService(repository);
        
        // Create tasks as described in test case:
        // Incomplete HIGH task due 2023-10-14
        service.createTask("High", "description", Priority.HIGH, LocalDate.of(2023, 10, 14), null);
        // Incomplete LOW task due 2023-10-16
        service.createTask("Low", "description", Priority.LOW, LocalDate.of(2023, 10, 16), null);
        // Completed MEDIUM task due 2023-10-14
        Task mediumTask = service.createTask("Medium", "description", Priority.MEDIUM, LocalDate.of(2023, 10, 14), null);
        service.setCompleted(mediumTask.getId(), true);
        
        // Summary at 2023-10-15
        Map<String, Integer> summary = service.summary(LocalDate.of(2023, 10, 15));
        
        // Verify exact counts
        assertEquals(3, summary.get("total").intValue());
        assertEquals(1, summary.get("completed").intValue());
        assertEquals(2, summary.get("pending").intValue());
        assertEquals(1, summary.get("overdue").intValue());
    }
}