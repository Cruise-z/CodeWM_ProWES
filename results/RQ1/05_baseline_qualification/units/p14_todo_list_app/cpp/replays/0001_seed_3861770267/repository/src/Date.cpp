#include "Date.h"
#include <cctype>
#include <string>

namespace {
// Helper function to check if a character is a digit
bool IsDigit(char c) {
  return std::isdigit(static_cast<unsigned char>(c));
}

// Helper function to check if a year is a leap year
bool IsLeapYear(int year) {
  return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
}

// Helper function to validate a day
bool IsValidDay(int year, int month, int day) {
  if (day <= 0) return false;
  
  // Days in each month (non-leap year)
  static const int days_in_month[12] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
  
  // Adjust February for leap years
  int max_day = days_in_month[month - 1];
  if (month == 2 && IsLeapYear(year)) {
    max_day = 29;
  }
  
  return day <= max_day;
}

// Helper function to parse an integer from a substring
bool ParseInt(const std::string& str, int start, int length, int& result) {
  if (start + length > static_cast<int>(str.length())) {
    return false;
  }
  
  for (int i = 0; i < length; ++i) {
    if (!IsDigit(str[start + i])) {
      return false;
    }
  }
  
  result = 0;
  for (int i = 0; i < length; ++i) {
    result = result * 10 + (str[start + i] - '0');
  }
  
  return true;
}
}  // namespace

bool DateRules::is_valid_iso_date(const std::string& date) {
  // Check if the date string has the correct length (YYYY-MM-DD)
  if (date.length() != 10) {
    return false;
  }
  
  // Check if the separators are correct
  if (date[4] != '-' || date[7] != '-') {
    return false;
  }
  
  // Parse year, month, and day
  int year, month, day;
  if (!ParseInt(date, 0, 4, year) ||
      !ParseInt(date, 5, 2, month) ||
      !ParseInt(date, 8, 2, day)) {
    return false;
  }
  
  // Check if month is valid
  if (month < 1 || month > 12) {
    return false;
  }
  
  // Check if day is valid
  return IsValidDay(year, month, day);
}

int DateRules::compare_dates(const std::string& date1, const std::string& date2) {
  // If both dates are empty, they are equal
  if (date1.empty() && date2.empty()) {
    return 0;
  }
  
  // If only date1 is empty, date1 < date2 (empty comes before valid)
  if (date1.empty()) {
    return -1;
  }
  
  // If only date2 is empty, date1 > date2 (empty comes before valid)
  if (date2.empty()) {
    return 1;
  }
  
  // Both dates are non-empty, compare lexicographically
  if (date1 < date2) {
    return -1;
  } else if (date1 > date2) {
    return 1;
  } else {
    return 0;
  }
}