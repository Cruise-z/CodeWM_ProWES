#ifndef VALIDATOR_H
#define VALIDATOR_H

#include <string>
#include <vector>

/// @brief Result of validation operation
struct ValidationResult {
    /// @brief Whether the validation passed
    bool ok;
    
    /// @brief List of error messages if validation failed
    std::vector<std::string> errors;
};

/// @brief Validator for press release fields
class Validator {
public:
    /// @brief Validates press release fields according to business rules
    /// @param headline The press release headline
    /// @param body The press release body
    /// @param email The contact email address
    /// @param phone The contact phone number
    /// @return ValidationResult indicating success/failure and error messages
    ValidationResult validateFields(const std::string& headline,
                                   const std::string& body,
                                   const std::string& email,
                                   const std::string& phone) const;
};

#endif // VALIDATOR_H