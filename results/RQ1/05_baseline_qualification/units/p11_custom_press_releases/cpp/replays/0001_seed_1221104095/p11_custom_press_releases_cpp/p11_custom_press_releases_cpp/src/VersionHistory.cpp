#include "VersionHistory.h"
#include <sstream>
#include <iomanip>

void VersionHistory::append(const Clock& clock, const std::string& description) {
    VersionEntry entry;
    entry.timestamp = clock.now();
    entry.description = description;
    entries_.push_back(entry);
}

const std::vector<VersionEntry>& VersionHistory::entries() const {
    return entries_;
}

std::size_t VersionHistory::size() const {
    return entries_.size();
}

std::string VersionHistory::toString() const {
    std::ostringstream oss;
    for (const auto& entry : entries_) {
        oss << entry.timestamp << " - " << entry.description << "\n";
    }
    return oss.str();
}