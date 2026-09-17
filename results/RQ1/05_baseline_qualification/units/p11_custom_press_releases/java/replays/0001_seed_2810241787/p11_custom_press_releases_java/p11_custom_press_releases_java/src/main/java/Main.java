/**
 * Main class for demonstrating the press release system functionality.
 * This is a thin non-interactive demo that constructs a template and press release,
 * exercises the validation, lifecycle transitions, and rendering, then prints results.
 */
public class Main {
    /**
     * Entry point for the application.
     * Demonstrates the press release lifecycle and rendering functionality.
     * 
     * @param args command line arguments (not used)
     */
    public static void main(String[] args) {
        // Create a basic template with placeholders
        Template template = new Template("basic", "{{headline}}|{{body}}|{{contact}}");
        
        // Create a press release with sample data
        PressRelease release = new PressRelease(
            "r1", 
            "Hello", 
            "Body", 
            "a@b.com", 
            template, 
            java.util.Collections.emptyMap()
        );
        
        // Validate the press release
        boolean isValid = release.validate();
        System.out.println("Press release is valid: " + isValid);
        
        // Submit for review
        release.submitForReview();
        System.out.println("State after submit for review: " + release.getState());
        
        // Publish the press release
        release.publish();
        System.out.println("State after publish: " + release.getState());
        
        // Render as plain text
        String rendered = release.renderPlainText();
        System.out.println("Rendered text: " + rendered);
        
        // Get version history
        java.util.List<Version> versions = release.getVersionHistory();
        System.out.println("Version history size: " + versions.size());
        if (!versions.isEmpty()) {
            Version version = versions.get(0);
            System.out.println("First version number: " + version.getNumber());
            System.out.println("First version text: " + version.getRenderedText());
        }
    }
}