/**
 * Utility class for URL validation and safe output naming.
 */
public class ValidationUtils {

    /**
     * Validates if the given string is a well-formed URL.
     * This method checks for a valid scheme and basic structure,
     * but does not perform network requests.
     *
     * @param url the string to validate as a URL
     * @return true if the URL is valid, false otherwise
     */
    public static boolean isValidUrl(String url) {
        if (url == null || url.isEmpty()) {
            return false;
        }
        
        // Basic check for URL scheme
        if (!url.contains("://")) {
            return false;
        }
        
        try {
            new java.net.URL(url);
            return true;
        } catch (java.net.MalformedURLException e) {
            return false;
        }
    }

    /**
     * Sanitizes a string to make it safe for use as a filename.
     * Removes or replaces characters that are invalid or dangerous
     * in filenames on most operating systems.
     *
     * @param name the input string to sanitize
     * @return a filesystem-safe version of the input string
     */
    public static String sanitizeName(String name) {
        if (name == null || name.isEmpty()) {
            return "unnamed";
        }
        
        // Replace potentially dangerous characters with underscores
        String sanitized = name.replaceAll("[<>:\"/\\|?*]", "_");
        
        // Trim whitespace
        sanitized = sanitized.trim();
        
        // Normalize spaces
        sanitized = sanitized.replaceAll("\\s+", " ");
        
        // Handle edge case where result is empty after sanitization
        if (sanitized.isEmpty()) {
            return "unnamed";
        }
        
        return sanitized;
    }

    /**
     * Appends the canonical file extension for the given format to the base name.
     *
     * @param baseName the base name for the file
     * @param format the download format to use for extension
     * @return the full filename with extension
     */
    public static String withExtension(String baseName, DownloadFormat format) {
        if (baseName == null || baseName.isEmpty()) {
            throw new IllegalArgumentException("Base name cannot be null or empty");
        }
        if (format == null) {
            throw new IllegalArgumentException("Format cannot be null");
        }
        
        return baseName + "." + format.defaultExtension();
    }
}