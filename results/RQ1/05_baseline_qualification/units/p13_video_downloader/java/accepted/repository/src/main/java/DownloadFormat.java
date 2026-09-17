/**
 * Enumeration of supported download formats and their canonical extensions.
 */
public enum DownloadFormat {
    MP4("mp4"),
    WEBM("webm");

    private final String extension;

    /**
     * Constructs a download format with the specified extension.
     *
     * @param extension the canonical file extension for this format
     */
    DownloadFormat(String extension) {
        this.extension = extension;
    }

    /**
     * Returns the canonical file extension for this format.
     *
     * @return the file extension
     */
    public String extension() {
        return extension;
    }

    /**
     * Resolves a DownloadFormat from its file extension.
     *
     * @param ext the file extension to resolve
     * @return the corresponding DownloadFormat
     * @throws IllegalArgumentException if the extension is not recognized
     */
    public static DownloadFormat fromExtension(String ext) {
        for (DownloadFormat format : values()) {
            if (format.extension().equals(ext)) {
                return format;
            }
        }
        throw new IllegalArgumentException("Unknown format extension: " + ext);
    }

    /**
     * Returns the canonical file extension for this format.
     *
     * @return the canonical file extension
     */
    public String defaultExtension() {
        return extension();
    }
}