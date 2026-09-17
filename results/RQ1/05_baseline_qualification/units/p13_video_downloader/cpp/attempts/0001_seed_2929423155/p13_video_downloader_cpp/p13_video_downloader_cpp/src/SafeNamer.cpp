#include "SafeNamer.h"
#include <algorithm>
#include <cctype>
#include <utility>

namespace {

std::string trim(const std::string& str) {
    auto start = str.find_first_not_of("_");
    if (start == std::string::npos) {
        return "";
    }
    auto end = str.find_last_not_of("_");
    return str.substr(start, end - start + 1);
}

} // namespace

InMemoryExistingFiles::InMemoryExistingFiles(const std::vector<std::string>& initial) {
    for (const auto& name : initial) {
        names_.insert(name);
    }
}

bool InMemoryExistingFiles::exists(const std::string& name) const {
    return names_.find(name) != names_.end();
}

void InMemoryExistingFiles::add(const std::string& name) {
    names_.insert(name);
}

std::string sanitize_base(const std::string& base) {
    std::string result;
    result.reserve(base.length());
    
    bool last_was_underscore = false;
    for (char c : base) {
        if (std::isalnum(c) || c == '-' || c == '_') {
            if (last_was_underscore && result.back() == '_') {
                // Skip consecutive underscores
                continue;
            }
            result += c;
            last_was_underscore = false;
        } else {
            if (!last_was_underscore) {
                result += '_';
                last_was_underscore = true;
            }
        }
    }
    
    // Trim leading and trailing underscores
    result = trim(result);
    
    // If result is empty, return "download"
    if (result.empty()) {
        return "download";
    }
    
    return result;
}

std::string unique_name(const std::string& base,
                        const std::string& extension,
                        const IExistingFiles& files,
                        const std::unordered_set<std::string>& reserved) {
    std::string candidate = base + extension;
    
    // Check if the candidate is already taken by either files or reserved
    if (files.exists(candidate) || reserved.find(candidate) != reserved.end()) {
        // Try suffixes until we find an available name
        int counter = 2;
        do {
            candidate = base + "_" + std::to_string(counter) + extension;
            counter++;
        } while ((files.exists(candidate) || reserved.find(candidate) != reserved.end()) && 
                 counter <= 1000); // Prevent infinite loop
    }
    
    return candidate;
}