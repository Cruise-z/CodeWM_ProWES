#include "Url.h"
#include <algorithm>
#include <cctype>

namespace {

bool is_valid_scheme(const std::string& scheme) {
    return scheme == "http" || scheme == "https";
}

} // namespace

bool is_valid_url(const std::string& url) {
    // Reject URLs containing whitespace anywhere
    if (url.find(' ') != std::string::npos) {
        return false;
    }
    
    // Find the position of "://"
    std::size_t sep_pos = url.find("://");
    if (sep_pos == std::string::npos) {
        return false;
    }
    
    // Extract scheme
    std::string scheme = url.substr(0, sep_pos);
    if (!is_valid_scheme(scheme)) {
        return false;
    }
    
    // Set host begin position after "://"
    std::size_t host_begin = sep_pos + 3;
    
    // Find next '/' after host_begin or use end of string if not found
    std::size_t host_end = url.find('/', host_begin);
    if (host_end == std::string::npos) {
        host_end = url.size();
    }
    
    // Host must not be empty
    if (host_end <= host_begin) {
        return false;
    }
    
    // Additional check: host cannot be empty even if path is present
    // e.g., "https://example.com/" is valid, "https://example.com" is valid
    // But "https://example.com/path" is also valid
    // And "https://example.com///path" is valid too
    
    // If we have a host (which means host_end > host_begin), then it's valid
    return true;
}

bool parse_format(const std::string& text, Format& out) {
    // Convert to lowercase for case-insensitive comparison
    std::string lower_text = text;
    std::transform(lower_text.begin(), lower_text.end(), lower_text.begin(), 
                   [](unsigned char c) { return std::tolower(c); });
    
    if (lower_text == "mp4") {
        out = Format::MP4;
    } else if (lower_text == "webm") {
        out = Format::WEBM;
    } else if (lower_text == "audio") {
        out = Format::AUDIO;
    } else {
        return false;
    }
    
    return true;
}

std::string extension_for(Format format) {
    switch (format) {
        case Format::MP4:
            return ".mp4";
        case Format::WEBM:
            return ".webm";
        case Format::AUDIO:
            return ".mp3";
        default:
            return "";
    }
}