import java.time.LocalDate;
import java.util.Map;
import java.util.Set;

public class Main {
    public static Map<String, Integer> runDemo() {
        TaskRepository repository = new InMemoryTaskRepository();
        TodoService service = new TodoService(repository);

        // Create "Write paper" task at HIGH priority due 2023-10-14 with work/urgent tags and mark it complete
        Task writePaper = service.createTask(
            "Write paper",
            "Draft the final report",
            Priority.HIGH,
            LocalDate.of(2023, 10, 14),
            Set.of("work", "urgent")
        );
        service.setCompleted(writePaper.getId(), true);

        // Create "Buy milk" task at MEDIUM priority due 2023-10-16 with home tag and leave it incomplete
        Task buyMilk = service.createTask(
            "Buy milk",
            "Get milk from the store",
            Priority.MEDIUM,
            LocalDate.of(2023, 10, 16),
            Set.of("home")
        );

        // Return summary at 2023-10-15
        return service.summary(LocalDate.of(2023, 10, 15));
    }

    public static void main(String[] args) {
        runDemo();
    }
}