#ifndef SEARCH_INDEX_H
#define SEARCH_INDEX_H

#include <string>
#include <vector>
#include <set>

/// @brief Record of a press release for indexing purposes
struct ReleaseRecord {
    /// @brief Unique identifier of the press release
    std::string id;
    
    /// @brief Headline of the press release
    std::string headline;
    
    /// @brief Body content of the press release
    std::string body;
    
    /// @brief Set of tags associated with the press release
    std::set<std::string> tags;
};

/// @brief Index for searching press releases by text and tags
class SearchIndex {
private:
    /// @brief Vector of indexed release records
    std::vector<ReleaseRecord> records_;

public:
    /// @brief Adds a release record to the index
    /// @param rec Release record to add
    void add(const ReleaseRecord& rec);

    /// @brief Clears all records from the index
    void clear();

    /// @brief Searches for press releases matching criteria
    /// @param textQuery Text to search for (case-insensitive contains)
    /// @param requiredTags Set of tags that must be present
    /// @return Vector of matching release records
    std::vector<ReleaseRecord> search(const std::string& textQuery, 
                                     const std::set<std::string>& requiredTags) const;
};

#endif // SEARCH_INDEX_H