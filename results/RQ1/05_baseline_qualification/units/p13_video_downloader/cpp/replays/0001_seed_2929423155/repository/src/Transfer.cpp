#include "Transfer.h"
#include <stdexcept>

FakeTransferAdapter::FakeTransferAdapter(std::size_t total_bytes) : fixed_total_(total_bytes) {
    if (fixed_total_ == 0) {
        throw std::invalid_argument("Total bytes must be positive");
    }
}

std::size_t FakeTransferAdapter::total_bytes(const std::string& url) const {
    return fixed_total_;
}