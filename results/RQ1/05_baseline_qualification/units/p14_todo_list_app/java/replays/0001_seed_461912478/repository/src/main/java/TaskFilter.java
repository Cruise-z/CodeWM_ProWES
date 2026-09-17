import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;

public class TaskFilter {
    
    public static List<Task> filter(List<Task> tasks, Boolean completed, Priority priority, Set<String> requiredTags) {
        if (tasks == null) {
            return new ArrayList<>();
        }
        
        List<Task> result = new ArrayList<>();
        
        // Normalize required tags once
        LinkedHashSet<String> normalizedRequiredTags = normalizeRequiredTags(requiredTags);
        
        for (Task task : tasks) {
            // Check completed constraint
            if (completed != null && task.isCompleted() != completed) {
                continue;
            }
            
            // Check priority constraint
            if (priority != null && task.getPriority() != priority) {
                continue;
            }
            
            // Check required tags constraint
            if (normalizedRequiredTags != null && !normalizedRequiredTags.isEmpty()) {
                Set<String> taskTags = task.getTags();
                boolean hasAllTags = true;
                
                for (String requiredTag : normalizedRequiredTags) {
                    if (!taskTags.contains(requiredTag)) {
                        hasAllTags = false;
                        break;
                    }
                }
                
                if (!hasAllTags) {
                    continue;
                }
            }
            
            result.add(task);
        }
        
        return result;
    }
    
    private static LinkedHashSet<String> normalizeRequiredTags(Set<String> inputTags) {
        if (inputTags == null || inputTags.isEmpty()) {
            return new LinkedHashSet<>();
        }
        
        TreeSet<String> sorted = new TreeSet<>();
        for (String tag : inputTags) {
            if (tag != null) {
                String normalized = tag.trim().toLowerCase(Locale.ROOT);
                if (!normalized.isEmpty()) {
                    sorted.add(normalized);
                }
            }
        }
        
        // Convert TreeSet back to LinkedHashSet to maintain insertion order
        LinkedHashSet<String> result = new LinkedHashSet<>();
        for (String s : sorted) {
            result.add(s);
        }
        
        return result;
    }
}