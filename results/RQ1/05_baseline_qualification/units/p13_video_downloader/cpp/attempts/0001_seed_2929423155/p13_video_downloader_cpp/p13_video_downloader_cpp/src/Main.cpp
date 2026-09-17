#include "DownloadQueue.h"
#include "Transfer.h"
#include "SafeNamer.h"

int main() {
    // Construct empty existing-files boundary with the literal unambiguous declaration
    InMemoryExistingFiles files;
    
    // Construct FakeTransferAdapter and DownloadQueue
    FakeTransferAdapter adapter;
    DownloadQueue queue(adapter, files, 4);
    
    // Enqueue one fixed https URL
    auto result = queue.enqueue("https://example.com/clip", "mp4", "clip");
    
    // Tick a bounded number of times
    for (int i = 0; i < 4; ++i) {
        queue.tick();
    }
    
    return 0;
}