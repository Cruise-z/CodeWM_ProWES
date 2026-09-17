/**
 * Stateless utility for searching press releases by tag.
 * Provides a method to find releases that contain a specific tag.
 */
public final class TaggingSystem {
    
    /**
     * Searches for press releases that have a specific tag.
     * The search is case-sensitive and matches exact trimmed tags.
     * Preserves the input order of releases.
     * 
     * @param releases the list of press releases to search through
     * @param tag the tag to search for (trimmed for comparison)
     * @return a new list containing only the releases that have the specified tag, in input order
     */
    public static java.util.List<PressRelease> searchByTag(java.util.List<PressRelease> releases, String tag) {
        // Handle null inputs defensively
        if (releases == null || tag == null) {
            return new java.util.ArrayList<>();
        }
        
        // Trim the search tag once for efficiency
        String trimmedTag = tag.trim();
        
        // Create a new list to avoid modifying the input
        java.util.List<PressRelease> result = new java.util.ArrayList<>();
        
        // Iterate through all releases and check if they contain the tag
        for (PressRelease release : releases) {
            if (release != null && release.getTags().contains(trimmedTag)) {
                result.add(release);
            }
        }
        
        return result;
    }
}