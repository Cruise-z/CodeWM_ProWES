import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class TaskSorter {
    public static List<Task> sort(List<Task> tasks) {
        if (tasks == null) {
            return new ArrayList<>();
        }
        
        List<Task> result = new ArrayList<>(tasks);
        
        result.sort(new Comparator<Task>() {
            @Override
            public int compare(Task t1, Task t2) {
                // Higher priority rank first
                int priorityCompare = Integer.compare(t2.getPriority().rank(), t1.getPriority().rank());
                if (priorityCompare != 0) {
                    return priorityCompare;
                }
                
                // Non-null due dates before null due dates
                if (t1.getDueDate() == null && t2.getDueDate() != null) {
                    return 1;
                }
                if (t1.getDueDate() != null && t2.getDueDate() == null) {
                    return -1;
                }
                
                // Real dates ascending
                if (t1.getDueDate() != null && t2.getDueDate() != null) {
                    int dateCompare = t1.getDueDate().compareTo(t2.getDueDate());
                    if (dateCompare != 0) {
                        return dateCompare;
                    }
                }
                
                // Case-insensitive title
                int titleCompare = String.CASE_INSENSITIVE_ORDER.compare(t1.getTitle(), t2.getTitle());
                if (titleCompare != 0) {
                    return titleCompare;
                }
                
                // Id ascending
                return Integer.compare(t1.getId(), t2.getId());
            }
        });
        
        return result;
    }
}