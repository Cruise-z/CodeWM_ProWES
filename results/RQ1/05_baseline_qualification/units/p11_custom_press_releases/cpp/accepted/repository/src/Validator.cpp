#include "Validator.h"
#include <regex>
#include <algorithm>
#include <cctype>

ValidationResult Validator::validateFields(const std::string& headline,
                                          const std::string& body,
                                          const std::string& email,
                                          const std::string& phone) const {
    ValidationResult result;
    result.ok = true;
    result.errors.clear();
    
    // Validate headline
    if (headline.empty()) {
        result.ok = false;
        result.errors.push_back("Headline cannot be empty");
    }
    
    // Validate body
    if (body.empty()) {
        result.ok = false;
        result.errors.push_back("Body cannot be empty");
    }
    
    // Validate email format (basic check)
    if (email.empty()) {
        result.ok = false;
        result.errors.push_back("Email cannot be empty");
    } else {
        // Basic email validation using regex
        const std::regex emailRegex(R"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})");
        if (!std::regex_match(email, emailRegex)) {
            result.ok = false;
            result.errors.push_back("Invalid email format");
        }
    }
    
    // Validate phone number (basic digit count check)
    if (phone.empty()) {
        result.ok = false;
        result.errors.push_back("Phone cannot be empty");
    } else {
        // Count digits only
        size_t digitCount = std::count_if(phone.begin(), phone.end(), ::isdigit);
        if (digitCount < 7) {  // Minimum reasonable phone digits
            result.ok = false;
            result.errors.push_back("Phone number too short");
        }
    }
    
    return result;
}