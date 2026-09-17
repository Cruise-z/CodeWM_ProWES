#include "SearchIndex.h"
#include <algorithm>
#include <cctype>
#include <iterator>
#include <functional>

void SearchIndex::add(const ReleaseRecord& rec) {
    records_.push_back(rec);
}

void SearchIndex::clear() {
    records_.clear();
}

std::vector<ReleaseRecord> SearchIndex::search(const std::string& textQuery, 
                                              const std::set<std::string>& requiredTags) const {
    std::vector<ReleaseRecord> results;
    
    // Convert query to lowercase for case-insensitive comparison
    std::string lowerQuery = textQuery;
    std::transform(lowerQuery.begin(), lowerQuery.end(), lowerQuery.begin(), 
                   [](unsigned char c) { return std::tolower(c); });
    
    for (const auto& record : records_) {
        // Check if all required tags are present
        bool hasAllTags = true;
        for (const auto& requiredTag : requiredTags) {
            if (record.tags.find(requiredTag) == record.tags.end()) {
                hasAllTags = false;
                break;
            }
        }
        
        if (!hasAllTags) {
            continue;
        }
        
        // Check text query in headline and body (case-insensitive)
        std::string lowerHeadline = record.headline;
        std::transform(lowerHeadline.begin(), lowerHeadline.end(), lowerHeadline.begin(), 
                       [](unsigned char c) { return std::tolower(c); });
        
        std::string lowerBody = record.body;
        std::transform(lowerBody.begin(), lowerBody.end(), lowerBody.begin(), 
                       [](unsigned char c) { return std::tolower(c); });
        
        if (lowerHeadline.find(lowerQuery) != std::string::npos || 
            lowerBody.find(lowerQuery) != std::string::npos) {
            results.push_back(record);
        }
    }
    
    return results;
}