#include "DownloadQueue.h"
#include "Url.h"
#include <algorithm>
#include <stdexcept>

DownloadQueue::DownloadQueue(ITransferAdapter& adapter,
                           const IExistingFiles& files,
                           std::size_t chunk_size)
    : adapter_(adapter), files_(files), chunk_size_(chunk_size) {}

EnqueueResult DownloadQueue::enqueue(const std::string& url,
                                   const std::string& format_text,
                                   const std::string& desired_base) {
    // Validate URL
    if (!is_valid_url(url)) {
        return {false, 0, std::string(), std::string("invalid url")};
    }

    // Parse format
    Format format;
    if (!parse_format(format_text, format)) {
        return {false, 0, std::string(), std::string("invalid format")};
    }

    // Generate safe filename
    std::string base = sanitize_base(desired_base);
    std::string ext = extension_for(format);
    std::string candidate = unique_name(base, ext, files_, reserved_names_);

    // Reserve the name
    reserved_names_.insert(candidate);

    // Get total bytes
    std::size_t total = adapter_.total_bytes(url);

    // Create and add the download item
    DownloadItem item;
    item.id = next_id_++;
    item.url = url;
    item.format = format;
    item.filename = candidate;
    item.state = DownloadState::QUEUED;
    item.progress.bytes = 0;
    item.progress.total = total;
    item.error = "";

    items_.push_back(item);

    return {true, item.id, item.filename, std::string()};
}

bool DownloadQueue::cancel(std::uint64_t id) {
    auto it = std::find_if(items_.begin(), items_.end(),
                          [id](const DownloadItem& item) {
                              return item.id == id;
                          });

    if (it == items_.end()) {
        return false;
    }

    // Check if item is in a terminal state
    if (it->state == DownloadState::COMPLETED ||
        it->state == DownloadState::CANCELED ||
        it->state == DownloadState::FAILED) {
        return false;
    }

    // Cancel the item
    it->state = DownloadState::CANCELED;
    return true;
}

const DownloadItem* DownloadQueue::get(std::uint64_t id) const {
    auto it = std::find_if(items_.begin(), items_.end(),
                          [id](const DownloadItem& item) {
                              return item.id == id;
                          });

    if (it == items_.end()) {
        return nullptr;
    }

    return &(*it);
}

std::vector<DownloadItem> DownloadQueue::list() const {
    return items_;
}

void DownloadQueue::tick() {
    // Find the first item that is either QUEUED or DOWNLOADING
    auto it = std::find_if(items_.begin(), items_.end(),
                          [](const DownloadItem& item) {
                              return item.state == DownloadState::QUEUED ||
                                     item.state == DownloadState::DOWNLOADING;
                          });

    if (it == items_.end()) {
        return;
    }

    // Process the item
    if (it->state == DownloadState::QUEUED) {
        it->state = DownloadState::DOWNLOADING;
    }

    // Calculate how much to advance
    std::size_t remaining = it->progress.total - it->progress.bytes;
    std::size_t add = std::min(chunk_size_, remaining);
    it->progress.bytes += add;

    // Check if download is complete
    if (it->progress.bytes == it->progress.total) {
        it->state = DownloadState::COMPLETED;
    }
}