import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class Task {
    private final int id;
    private String title;
    private String description;
    private Priority priority;
    private LocalDate dueDate;
    private LinkedHashSet<String> tags;
    private boolean completed;

    public Task(int id, String title, String description, Priority priority, LocalDate dueDate, Set<String> tags) {
        if (id <= 0) {
            throw new IllegalArgumentException("Task id must be positive");
        }
        if (title == null || title.trim().isEmpty()) {
            throw new IllegalArgumentException("Task title cannot be null or blank");
        }
        if (priority == null) {
            throw new IllegalArgumentException("Task priority cannot be null");
        }

        this.id = id;
        this.title = title.trim();
        this.description = (description == null) ? "" : description;
        this.priority = priority;
        this.dueDate = dueDate;
        this.tags = normalizeTags(tags);
        this.completed = false;
    }

    public int getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }

    public Priority getPriority() {
        return priority;
    }

    public LocalDate getDueDate() {
        return dueDate;
    }

    public Set<String> getTags() {
        return Collections.unmodifiableSet(new LinkedHashSet<>(tags));
    }

    public boolean isCompleted() {
        return completed;
    }

    public void edit(String title, String description, Priority priority, LocalDate dueDate, Set<String> tags) {
        if (title == null || title.trim().isEmpty()) {
            throw new IllegalArgumentException("Task title cannot be null or blank");
        }
        if (priority == null) {
            throw new IllegalArgumentException("Task priority cannot be null");
        }

        this.title = title.trim();
        this.description = (description == null) ? "" : description;
        this.priority = priority;
        this.dueDate = dueDate;
        this.tags = normalizeTags(tags);
    }

    public void setCompleted(boolean completed) {
        this.completed = completed;
    }

    private static LinkedHashSet<String> normalizeTags(Set<String> inputTags) {
        if (inputTags == null || inputTags.isEmpty()) {
            return new LinkedHashSet<>();
        }

        LinkedHashSet<String> result = new LinkedHashSet<>();
        for (String tag : inputTags) {
            if (tag != null) {
                String normalized = tag.trim().toLowerCase(Locale.ROOT);
                if (!normalized.isEmpty()) {
                    result.add(normalized);
                }
            }
        }

        // Convert to ArrayList to sort lexicographically, then back to LinkedHashSet
        List<String> sorted = new ArrayList<>(result);
        Collections.sort(sorted);
        
        LinkedHashSet<String> ordered = new LinkedHashSet<>();
        for (String s : sorted) {
            ordered.add(s);
        }
        
        return ordered;
    }
}