import java.util.List;

public interface TaskRepository {
    void add(Task task);
    Task findById(int id);
    void save(Task task);
    boolean deleteById(int id);
    List<Task> findAll();
}