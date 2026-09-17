/**
 * Value object representing a requested download.
 * This class encapsulates all the information needed to initiate a download,
 * including the URL, desired format, and output naming.
 */
public class VideoDownloadRequest {
    private final String url;
    private final DownloadFormat format;
    private final String suggestedName;
    private final String outputName;

    /**
     * Private constructor to enforce use of the factory method.
     *
     * @param url the URL to download from
     * @param format the download format to use
     * @param suggestedName the suggested name for the output file
     * @param outputName the computed safe output name
     */
    private VideoDownloadRequest(String url, DownloadFormat format, String suggestedName, String outputName) {
        this.url = url;
        this.format = format;
        this.suggestedName = suggestedName;
        this.outputName = outputName;
    }

    /**
     * Creates a new VideoDownloadRequest with validated parameters.
     *
     * @param url the URL to download from
     * @param format the download format to use
     * @param suggestedName the suggested name for the output file
     * @return a new VideoDownloadRequest instance
     * @throws IllegalArgumentException if the URL is invalid or any parameter is null
     */
    public static VideoDownloadRequest of(String url, DownloadFormat format, String suggestedName) {
        if (url == null) {
            throw new IllegalArgumentException("URL cannot be null");
        }
        if (format == null) {
            throw new IllegalArgumentException("Format cannot be null");
        }
        if (suggestedName == null) {
            throw new IllegalArgumentException("Suggested name cannot be null");
        }
        
        if (!ValidationUtils.isValidUrl(url)) {
            throw new IllegalArgumentException("Invalid URL: " + url);
        }
        
        String sanitizedBaseName = ValidationUtils.sanitizeName(suggestedName);
        String outputName = ValidationUtils.withExtension(sanitizedBaseName, format);
        
        return new VideoDownloadRequest(url, format, suggestedName, outputName);
    }

    /**
     * Gets the URL to download from.
     *
     * @return the download URL
     */
    public String getUrl() {
        return url;
    }

    /**
     * Gets the download format.
     *
     * @return the download format
     */
    public DownloadFormat getFormat() {
        return format;
    }

    /**
     * Gets the suggested name provided during request creation.
     *
     * @return the suggested name
     */
    public String getSuggestedName() {
        return suggestedName;
    }

    /**
     * Gets the computed safe output name with extension.
     *
     * @return the output name
     */
    public String getOutputName() {
        return outputName;
    }
}