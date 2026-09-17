#ifndef TRANSFER_H
#define TRANSFER_H

#include <cstddef>
#include <string>

/**
 * @brief Interface for transferring data from a URL.
 */
class ITransferAdapter {
public:
    virtual ~ITransferAdapter() = default;
    
    /**
     * @brief Gets the total number of bytes for a given URL.
     * @param url The URL to get the total bytes for.
     * @return The total number of bytes to transfer.
     */
    virtual std::size_t total_bytes(const std::string& url) const = 0;
};

/**
 * @brief A fake transfer adapter that returns a fixed total byte count.
 */
class FakeTransferAdapter final : public ITransferAdapter {
private:
    std::size_t fixed_total_;

public:
    /**
     * @brief Constructs a FakeTransferAdapter with a fixed total byte count.
     * @param total_bytes The fixed total byte count to return for all URLs.
     */
    explicit FakeTransferAdapter(std::size_t total_bytes = 12);
    
    /**
     * @brief Gets the fixed total number of bytes for any URL.
     * @param url The URL to get the total bytes for (ignored).
     * @return The fixed total byte count.
     */
    std::size_t total_bytes(const std::string& url) const override;
};

#endif // TRANSFER_H