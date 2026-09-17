#ifndef TEMPLATE_ENGINE_H
#define TEMPLATE_ENGINE_H

#include <string>
#include <map>
#include <vector>

/// @brief Result of template substitution operation
struct SubstitutionResult {
    /// @brief The output string after substitution
    std::string output;
    
    /// @brief List of keys that were not found in the fields map
    std::vector<std::string> missingKeys;
};

/// @brief Template engine for substituting placeholders in templates
class TemplateEngine {
public:
    /// @brief Renders a template by replacing placeholders with field values
    /// @param tmpl Template string containing placeholders in {{key}} format
    /// @param fields Map of field names to their values
    /// @return SubstitutionResult containing output and missing keys
    SubstitutionResult render(const std::string& tmpl, 
                             const std::map<std::string, std::string>& fields) const;
};

#endif // TEMPLATE_ENGINE_H