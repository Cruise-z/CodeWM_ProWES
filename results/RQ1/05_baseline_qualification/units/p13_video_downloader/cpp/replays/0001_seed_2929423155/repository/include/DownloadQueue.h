#ifndef DOWNLOAD_QUEUE_H
#define DOWNLOAD_QUEUE_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <unordered_set>
#include <vector>

#include "DownloadTypes.h"
#include "SafeNamer.h"
#include "Transfer.h"

/**
 * @brief Manages a queue of downloads with lifecycle control.
 */
class DownloadQueue {
private:
    ITransferAdapter& adapter_;
    const IExistingFiles& files_;
    std::vector<DownloadItem> items_;
    std::unordered_set<std::string> reserved_names_;
    std::uint64_t next_id_ = 1;
    std::size_t chunk_size_;

public:
    /**
     * @brief Constructs a DownloadQueue with the given adapter, files checker, and chunk size.
     * @param adapter The transfer adapter to use for getting total bytes.
     * @param files The existing files checker.
     * @param chunk_size The chunk size to use for downloading (default is 4).
     */
    explicit DownloadQueue(ITransferAdapter& adapter,
                          const IExistingFiles& files,
                          std::size_t chunk_size = 4);

    /**
     * @brief Enqueues a new download request.
     * @param url The URL to download.
     * @param format_text The format string (e.g., "mp4", "webm", "audio").
     * @param desired_base The desired base filename.
     * @return The result of the enqueue operation.
     */
    EnqueueResult enqueue(const std::string& url,
                         const std::string& format_text,
                         const std::string& desired_base);

    /**
     * @brief Cancels a download by ID.
     * @param id The ID of the download to cancel.
     * @return True if the download was canceled, false if not found or already completed/canceled/failed.
     */
    bool cancel(std::uint64_t id);

    /**
     * @brief Gets a download item by ID.
     * @param id The ID of the download to retrieve.
     * @return Pointer to the download item or nullptr if not found.
     */
    const DownloadItem* get(std::uint64_t id) const;

    /**
     * @brief Lists all download items.
     * @return A vector containing copies of all download items.
     */
    std::vector<DownloadItem> list() const;

    /**
     * @brief Processes one tick of the download queue.
     * This function advances the progress of the first queued or downloading item.
     */
    void tick();
};

#endif // DOWNLOAD_QUEUE_H