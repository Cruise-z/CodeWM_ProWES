import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;

public class Row {
    private final List<String> header;
    private final List<Cell> cells;

    public Row(List<String> header, List<Cell> cells) {
        this.header = new ArrayList<>(header);
        this.cells = new ArrayList<>(cells);
    }

    public List<String> header() {
        return new ArrayList<>(this.header);
    }

    public List<Cell> cells() {
        return new ArrayList<>(this.cells);
    }

    public Cell get(String column) {
        int index = this.header.indexOf(column);
        if (index >= 0 && index < this.cells.size()) {
            return this.cells.get(index);
        }
        return Cell.of("");
    }

    public LinkedHashMap<String, String> asStringMap() {
        LinkedHashMap<String, String> result = new LinkedHashMap<>();
        for (int i = 0; i < this.header.size(); i++) {
            String key = this.header.get(i);
            String value = (i < this.cells.size()) ? this.cells.get(i).raw() : "";
            result.put(key, value);
        }
        return result;
    }
}