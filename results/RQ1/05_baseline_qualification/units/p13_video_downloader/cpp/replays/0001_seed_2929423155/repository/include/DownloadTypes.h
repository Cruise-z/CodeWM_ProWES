#ifndef DOWNLOAD_TYPES_H
#define DOWNLOAD_TYPES_H

#include <cstddef>
#include <cstdint>
#include <string>

/**
 * @brief Enumerates the supported video/audio formats.
 */
enum class Format {
    MP4,
    WEBM,
    AUDIO
};

/**
 * @brief Enumerates the possible download states.
 */
enum class DownloadState {
    QUEUED,
    DOWNLOADING,
    COMPLETED,
    CANCELED,
    FAILED
};

/**
 * @brief Represents download progress information.
 */
struct Progress {
    std::size_t bytes;  ///< Number of bytes downloaded so far.
    std::size_t total;  ///< Total number of bytes to download.
};

/**
 * @brief Represents a single download item in the queue.
 */
struct DownloadItem {
    std::uint64_t id;         ///< Unique identifier for the download.
    std::string url;          ///< URL of the resource to download.
    Format format;            ///< Format of the resource.
    std::string filename;     ///< Output filename for the download.
    DownloadState state;      ///< Current state of the download.
    Progress progress;        ///< Download progress information.
    std::string error;        ///< Error message if the download failed.
};

/**
 * @brief Result structure returned by the enqueue operation.
 */
struct EnqueueResult {
    bool ok;              ///< Indicates whether the enqueue operation succeeded.
    std::uint64_t id;     ///< ID of the newly enqueued item, valid only if ok is true.
    std::string filename; ///< Filename assigned to the download, valid only if ok is true.
    std::string error;    ///< Error message if the enqueue operation failed.
};

#endif // DOWNLOAD_TYPES_H