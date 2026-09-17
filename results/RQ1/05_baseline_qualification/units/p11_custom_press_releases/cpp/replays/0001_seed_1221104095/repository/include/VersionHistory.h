#ifndef VERSION_HISTORY_H
#define VERSION_HISTORY_H

#include <string>
#include <vector>
#include "Clock.h"

/// @brief Represents a single version entry in the history
struct VersionEntry {
    /// @brief Timestamp of when this entry was created
    std::string timestamp;
    
    /// @brief Description of what changed in this version
    std::string description;
};

/// @brief Append-only history of version changes with human-readable toString
class VersionHistory {
private:
    /// @brief Vector of version entries
    std::vector<VersionEntry> entries_;

public:
    /// @brief Appends a new entry to the history
    /// @param clock Clock instance to get timestamp from
    /// @param description Description of the change
    void append(const Clock& clock, const std::string& description);

    /// @brief Gets all entries in the history
    /// @return Const reference to the vector of entries
    const std::vector<VersionEntry>& entries() const;

    /// @brief Gets the number of entries in the history
    /// @return Size of the entries vector
    std::size_t size() const;

    /// @brief Converts the entire history to a human-readable string
    /// @return Formatted string representation of the history
    std::string toString() const;
};

#endif // VERSION_HISTORY_H