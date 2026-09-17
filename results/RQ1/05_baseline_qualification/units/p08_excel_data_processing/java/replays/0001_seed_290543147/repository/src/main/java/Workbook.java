import java.util.LinkedHashMap;
import java.util.Optional;
import java.util.Set;
import java.util.Collections;
import java.util.HashSet;

public class Workbook {
    private final LinkedHashMap<String, Sheet> sheets;

    public Workbook() {
        this.sheets = new LinkedHashMap<>();
    }

    public void addSheet(Sheet sheet) {
        this.sheets.put(sheet.name(), sheet);
    }

    public Optional<Sheet> getSheet(String name) {
        return Optional.ofNullable(this.sheets.get(name));
    }

    public Set<String> sheetNames() {
        return Collections.unmodifiableSet(new HashSet<>(this.sheets.keySet()));
    }
}