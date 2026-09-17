/**
 * Thin non-interactive demo entry point.
 * This class demonstrates the basic functionality of the system
 * without declaring or referencing any collection types.
 */
public class Main {
    
    /**
     * Main method serves as the runtime entry point.
     * Constructs required components and performs a demonstration search.
     * 
     * @param args command line arguments (unused)
     */
    public static void main(String[] args) {
        // Create repository and search service instances
        InMemoryUserRepository repository = new InMemoryUserRepository();
        SearchService searchService = new SearchService();
        
        // Perform the mandated standalone search call
        // This call is made without storing the result or declaring any collections
        searchService.search(repository.findAll(), "alice");
    }
}