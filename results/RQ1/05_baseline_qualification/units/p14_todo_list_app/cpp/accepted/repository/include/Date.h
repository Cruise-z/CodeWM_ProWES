#ifndef INCLUDE_DATE_H_
#define INCLUDE_DATE_H_

#include <string>

/**
 * @brief Provides date validation and comparison utilities.
 */
class DateRules {
 public:
  /**
   * @brief Checks if a date string is a valid ISO date (YYYY-MM-DD).
   * @param date The date string to validate.
   * @return True if the date is valid, false otherwise.
   */
  static bool is_valid_iso_date(const std::string& date);

  /**
   * @brief Compares two date strings lexicographically.
   *        Empty dates sort after valid dates.
   * @param date1 First date string.
   * @param date2 Second date string.
   * @return Negative if date1 < date2, zero if equal, positive if date1 > date2.
   */
  static int compare_dates(const std::string& date1, const std::string& date2);
};

#endif // INCLUDE_DATE_H_