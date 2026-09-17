#ifndef SAFE_NAMER_H
#define SAFE_NAMER_H

#include <string>
#include <unordered_set>
#include <vector>

/**
 * @brief Interface for checking if a filename already exists.
 */
class IExistingFiles {
public:
    virtual ~IExistingFiles() = default;
    
    /**
     * @brief Checks if a filename exists.
     * @param name The filename to check.
     * @return True if the file exists, false otherwise.
     */
    virtual bool exists(const std::string& name) const = 0;
};

/**
 * @brief Implementation of IExistingFiles using an in-memory set.
 */
class InMemoryExistingFiles final : public IExistingFiles {
private:
    std::unordered_set<std::string> names_;

public:
    /**
     * @brief Constructs an empty InMemoryExistingFiles.
     */
    explicit InMemoryExistingFiles() = default;
    
    /**
     * @brief Constructs an InMemoryExistingFiles with initial filenames.
     * @param initial Vector of initial filenames.
     */
    explicit InMemoryExistingFiles(const std::vector<std::string>& initial);
    
    /**
     * @brief Checks if a filename exists.
     * @param name The filename to check.
     * @return True if the file exists, false otherwise.
     */
    bool exists(const std::string& name) const override;
    
    /**
     * @brief Adds a filename to the set.
     * @param name The filename to add.
     */
    void add(const std::string& name);
};

/**
 * @brief Sanitizes a base filename by keeping only alphanumeric, dash, and underscore characters.
 * @param base The base filename to sanitize.
 * @return The sanitized base filename.
 */
std::string sanitize_base(const std::string& base);

/**
 * @brief Generates a unique filename by appending a number if necessary.
 * @param base The base filename.
 * @param extension The file extension.
 * @param files The existing files checker.
 * @param reserved The set of reserved filenames.
 * @return A unique filename.
 */
std::string unique_name(const std::string& base,
                        const std::string& extension,
                        const IExistingFiles& files,
                        const std::unordered_set<std::string>& reserved);

#endif // SAFE_NAMER_H