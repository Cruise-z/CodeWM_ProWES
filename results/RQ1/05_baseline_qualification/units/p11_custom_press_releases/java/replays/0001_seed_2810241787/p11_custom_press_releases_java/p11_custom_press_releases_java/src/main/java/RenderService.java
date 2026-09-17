/**
 * Stateless rendering service for press releases.
 * Provides a static method to convert a press release to plain text.
 */
public final class RenderService {
    
    /**
     * Converts a press release to its plain text representation.
     * Delegates the actual rendering to the press release's renderPlainText method.
     *
     * @param release the press release to render
     * @return the plain text representation of the press release
     * @throws NullPointerException if the release is null
     */
    public static String toPlainText(PressRelease release) {
        if (release == null) {
            throw new NullPointerException("Press release cannot be null");
        }
        return release.renderPlainText();
    }
}