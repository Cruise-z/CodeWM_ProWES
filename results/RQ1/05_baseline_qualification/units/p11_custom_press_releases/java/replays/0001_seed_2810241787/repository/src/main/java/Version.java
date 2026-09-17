/**
 * A value object representing a version of a press release.
 * Contains a version number and the rendered text at that time.
 */
public final class Version {
    private final int number;
    private final String renderedText;

    /**
     * Constructs a new Version with the given number and rendered text.
     *
     * @param number the version number
     * @param renderedText the rendered text of the press release at this version
     */
    public Version(int number, String renderedText) {
        this.number = number;
        this.renderedText = renderedText;
    }

    /**
     * Returns the version number.
     *
     * @return the version number
     */
    public int getNumber() {
        return number;
    }

    /**
     * Returns the rendered text of the press release at this version.
     *
     * @return the rendered text
     */
    public String getRenderedText() {
        return renderedText;
    }

    /**
     * Checks if this Version is equal to another object.
     * Two Versions are equal if they have the same number and renderedText.
     *
     * @param obj the object to compare with
     * @return true if the objects are equal, false otherwise
     */
    @Override
    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }
        Version version = (Version) obj;
        return number == version.number && 
               (renderedText == null ? version.renderedText == null : renderedText.equals(version.renderedText));
    }

    /**
     * Returns the hash code value for this Version.
     * The hash code is computed based on the number and renderedText.
     *
     * @return the hash code value
     */
    @Override
    public int hashCode() {
        int result = number;
        result = 31 * result + (renderedText != null ? renderedText.hashCode() : 0);
        return result;
    }

    /**
     * Returns a string representation of this Version.
     * The format is "Version{number=<number>, renderedText='<renderedText>'}".
     *
     * @return a string representation of this Version
     */
    @Override
    public String toString() {
        return "Version{" +
                "number=" + number +
                ", renderedText='" + renderedText + '\'' +
                '}';
    }
}