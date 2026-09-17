#include "Task.h"
#include <algorithm>
#include <cctype>
#include <functional>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {
// Helper function to check if a character is whitespace
bool IsWhitespace(char c) {
  return std::isspace(static_cast<unsigned char>(c));
}

// Helper function to trim whitespace from both ends of a string
std::string TrimImpl(const std::string& str) {
  auto start = str.find_first_not_of(" \t\n\r\f\v");
  if (start == std::string::npos) {
    return "";
  }
  auto end = str.find_last_not_of(" \t\n\r\f\v");
  return str.substr(start, end - start + 1);
}
}  // namespace

std::string Task::Trim(const std::string& str) {
  return TrimImpl(str);
}

std::string Task::NormalizeTag(const std::string& tag) {
  std::string trimmed = TrimImpl(tag);
  if (trimmed.empty()) {
    return "";
  }
  std::transform(trimmed.begin(), trimmed.end(), trimmed.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  return trimmed;
}

std::vector<std::string> Task::NormalizeTags(const std::vector<std::string>& tags) {
  std::vector<std::string> normalized;
  for (const auto& tag : tags) {
    std::string normalized_tag = NormalizeTag(tag);
    if (!normalized_tag.empty()) {
      normalized.push_back(normalized_tag);
    }
  }
  
  // Sort and remove duplicates
  std::sort(normalized.begin(), normalized.end());
  normalized.erase(std::unique(normalized.begin(), normalized.end()), normalized.end());
  
  return normalized;
}

bool Task::IsValidTitle(const std::string& title) {
  return !title.empty();
}