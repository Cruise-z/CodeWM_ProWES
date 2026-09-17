import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class TodoService {
    private TaskRepository repository;
    private int nextId;

    public TodoService(TaskRepository repository) {
        this.repository = repository;
        this.nextId = 1;
    }

    public Task createTask(String title, String description, Priority priority, LocalDate dueDate, Set<String> tags) {
        Task task = new Task(nextId, title, description, priority, dueDate, tags);
        repository.add(task);
        nextId += 1;
        return task;
    }

    public Task editTask(int id, String title, String description, Priority priority, LocalDate dueDate, Set<String> tags) {
        Task task = repository.findById(id);
        if (task == null) {
            throw new IllegalArgumentException("Task with id " + id + " does not exist");
        }
        task.edit(title, description, priority, dueDate, tags);
        repository.save(task);
        return task;
    }

    public boolean deleteTask(int id) {
        return repository.deleteById(id);
    }

    public Task setCompleted(int id, boolean completed) {
        Task task = repository.findById(id);
        if (task == null) {
            throw new IllegalArgumentException("Task with id " + id + " does not exist");
        }
        task.setCompleted(completed);
        repository.save(task);
        return task;
    }

    public List<Task> listTasks(Boolean completed, Priority priority, Set<String> requiredTags) {
        return TaskSorter.sort(TaskFilter.filter(repository.findAll(), completed, priority, requiredTags));
    }

    public Map<String, Integer> summary(LocalDate today) {
        if (today == null) {
            throw new IllegalArgumentException("Today cannot be null");
        }
        
        List<Task> allTasks = repository.findAll();
        int total = allTasks.size();
        int completedCount = 0;
        int pendingCount = 0;
        int overdueCount = 0;
        
        for (Task task : allTasks) {
            if (task.isCompleted()) {
                completedCount++;
            } else {
                pendingCount++;
                if (task.getDueDate() != null && task.getDueDate().isBefore(today)) {
                    overdueCount++;
                }
            }
        }
        
        Map<String, Integer> result = new LinkedHashMap<>();
        result.put("total", total);
        result.put("completed", completedCount);
        result.put("pending", pendingCount);
        result.put("overdue", overdueCount);
        
        return result;
    }
}