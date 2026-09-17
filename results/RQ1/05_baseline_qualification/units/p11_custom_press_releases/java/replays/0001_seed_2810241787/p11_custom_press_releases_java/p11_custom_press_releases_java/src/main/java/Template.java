/**
 * An immutable template with deterministic {{key}} substitution.
 * The template contains a name and content where placeholders of the form {{key}}
 * are replaced with values from a provided map.
 */
public final class Template {
    private final String name;
    private final String content;

    /**
     * Constructs a new Template with the given name and content.
     *
     * @param name the name of the template
     * @param content the content of the template which may contain {{key}} placeholders
     */
    public Template(String name, String content) {
        this.name = name;
        this.content = content;
    }

    /**
     * Returns the name of the template.
     *
     * @return the name
     */
    public String getName() {
        return name;
    }

    /**
     * Returns the content of the template.
     *
     * @return the content
     */
    public String getContent() {
        return content;
    }

    /**
     * Applies custom fields to the template content by replacing {{key}} placeholders
     * with corresponding values from the provided map.
     * If a key is not present in the map, the placeholder remains unchanged.
     * If the fields map is null, it's treated as an empty map.
     *
     * @param fields the map of field names to values to substitute into the template
     * @return the content with placeholders replaced by values
     */
    public String applyCustomFields(java.util.Map<String, String> fields) {
        // Handle null fields map by treating it as empty
        if (fields == null) {
            fields = java.util.Collections.emptyMap();
        }

        String result = content;
        
        // Find all placeholders of the form {{key}} and replace them
        java.util.regex.Pattern pattern = java.util.regex.Pattern.compile("\\{\\{([^}]+)\\}\\}");
        java.util.regex.Matcher matcher = pattern.matcher(result);
        
        StringBuffer buffer = new StringBuffer();
        while (matcher.find()) {
            String key = matcher.group(1);
            String value = fields.get(key);
            // If the key is not found in the fields map, keep the placeholder unchanged
            // If the value is null, treat it as an empty string
            matcher.appendReplacement(buffer, value == null ? "" : java.util.regex.Matcher.quoteReplacement(value));
        }
        matcher.appendTail(buffer);
        
        return buffer.toString();
    }
}