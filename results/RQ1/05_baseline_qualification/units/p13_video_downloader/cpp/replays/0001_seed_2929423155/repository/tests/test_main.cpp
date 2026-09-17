#include <cassert>
#include <vector>
#include "DownloadQueue.h"
#include "Url.h"

int main() {
    // Block 1: URL/format rules
    assert(is_valid_url("https://example.com"));
    assert(!is_valid_url("https://"));
    assert(!is_valid_url("http:///path"));
    Format f;
    assert(parse_format("WEBM", f) && f == Format::WEBM);

    // Block 2: Safe naming uniqueness
    InMemoryExistingFiles files;
    files.add("clip.mp4");
    FakeTransferAdapter adapter;
    DownloadQueue q(adapter, files);
    auto r = q.enqueue("https://example.com/clip", "mp4", "clip");
    assert(r.ok);
    assert(r.filename == "clip_2.mp4");

    // Block 3: Deterministic progress
    InMemoryExistingFiles files2;
    FakeTransferAdapter adapter2;
    DownloadQueue q2(adapter2, files2, 4);
    auto r2 = q2.enqueue("https://example.com/a", "audio", "song");
    const DownloadItem* it = q2.get(r2.id);
    assert(it && it->progress.bytes == 0 && it->progress.total == 12 && it->state == DownloadState::QUEUED);
    q2.tick();
    it = q2.get(r2.id);
    assert(it->progress.bytes == 4 && it->state == DownloadState::DOWNLOADING);
    q2.tick();
    it = q2.get(r2.id);
    assert(it->progress.bytes == 8);
    q2.tick();
    it = q2.get(r2.id);
    assert(it->progress.bytes == 12 && it->state == DownloadState::COMPLETED);

    // Block 4: Cancellation freezes progress
    InMemoryExistingFiles files3;
    FakeTransferAdapter adapter3;
    DownloadQueue q3(adapter3, files3, 4);
    auto r3 = q3.enqueue("https://example.com/b", "webm", "vid");
    q3.tick();
    const DownloadItem* it3 = q3.get(r3.id);
    assert(it3->progress.bytes == 4 && it3->state == DownloadState::DOWNLOADING);
    assert(q3.cancel(r3.id));
    it3 = q3.get(r3.id);
    assert(it3->state == DownloadState::CANCELED);
    q3.tick();
    it3 = q3.get(r3.id);
    assert(it3->progress.bytes == 4 && it3->state == DownloadState::CANCELED);

    return 0;
}