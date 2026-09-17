import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;

public class InMemoryTaskRepository implements TaskRepository {
    private LinkedHashMap<Integer, Task> store;

    public InMemoryTaskRepository() {
        this.store = new LinkedHashMap<>();
    }

    @Override
    public void add(Task task) {
        if (task == null) {
            throw new IllegalArgumentException("Task cannot be null");
        }
        if (store.containsKey(task.getId())) {
            throw new IllegalArgumentException("Task with id " + task.getId() + " already exists");
        }
        store.put(task.getId(), task);
    }

    @Override
    public Task findById(int id) {
        return store.get(id);
    }

    @Override
    public void save(Task task) {
        if (task == null) {
            throw new IllegalArgumentException("Task cannot be null");
        }
        if (!store.containsKey(task.getId())) {
            throw new IllegalArgumentException("Task with id " + task.getId() + " does not exist");
        }
        store.put(task.getId(), task);
    }

    @Override
    public boolean deleteById(int id) {
        return store.remove(id) != null;
    }

    @Override
    public List<Task> findAll() {
        return new ArrayList<>(store.values());
    }
}