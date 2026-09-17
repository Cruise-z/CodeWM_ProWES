#ifndef URL_H
#define URL_H

#include <string>
#include "DownloadTypes.h"

/**
 * @brief Checks if a given string is a valid URL.
 *
 * A valid URL must:
 * - Not contain whitespace anywhere
 * - Contain the literal substring "://" 
 * - Have a scheme of "http" or "https"
 * - Have a non-empty host portion
 *
 * @param url The URL string to validate.
 * @return True if the URL is valid, false otherwise.
 */
bool is_valid_url(const std::string& url);

/**
 * @brief Parses a format string into a Format enum value.
 *
 * Accepts case-insensitive values: "mp4", "webm", "audio".
 *
 * @param text The format string to parse.
 * @param out Reference to store the parsed Format value.
 * @return True if parsing was successful, false otherwise.
 */
bool parse_format(const std::string& text, Format& out);

/**
 * @brief Gets the file extension for a given format.
 *
 * Maps Format enum values to their corresponding file extensions:
 * - Format::MP4 -> ".mp4"
 * - Format::WEBM -> ".webm"
 * - Format::AUDIO -> ".mp3"
 *
 * @param format The format to get the extension for.
 * @return The file extension string.
 */
std::string extension_for(Format format);

#endif // URL_H