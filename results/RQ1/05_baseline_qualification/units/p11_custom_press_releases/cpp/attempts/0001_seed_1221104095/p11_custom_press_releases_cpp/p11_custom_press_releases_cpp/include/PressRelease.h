#ifndef PRESS_RELEASE_H
#define PRESS_RELEASE_H

#include <string>
#include <set>
#include <map>
#include "Clock.h"
#include "VersionHistory.h"
#include "Validator.h"

/// @brief Enum representing the lifecycle state of a press release
enum class LifecycleState {
    Draft,        ///< Initial state before review
    InReview,     ///< Under review process
    Published     ///< Successfully published
};

/// @brief Contact information for a press release
struct Contact {
    /// @brief Name of the contact person
    std::string name;
    
    /// @brief Email address of the contact
    std::string email;
    
    /// @brief Phone number of the contact
    std::string phone;
};

/// @brief Press release entity with lifecycle management and version history
class PressRelease {
private:
    /// @brief Unique identifier for the press release
    std::string id_;
    
    /// @brief Headline of the press release
    std::string headline_;
    
    /// @brief Body content of the press release
    std::string body_;
    
    /// @brief Contact information for the press release
    Contact contact_;
    
    /// @brief Set of tags for audience targeting
    std::set<std::string> tags_;
    
    /// @brief Current lifecycle state
    LifecycleState state_;
    
    /// @brief History of version changes
    VersionHistory history_;

public:
    /// @brief Constructor initializes a new press release
    /// @param id Unique identifier for the press release
    explicit PressRelease(const std::string& id);

    /// @brief Gets the unique identifier of the press release
    /// @return The press release ID
    const std::string& id() const;

    /// @brief Gets the headline of the press release
    /// @return The headline
    const std::string& headline() const;

    /// @brief Gets the body content of the press release
    /// @return The body content
    const std::string& body() const;

    /// @brief Gets the contact information for the press release
    /// @return The contact information
    const Contact& contact() const;

    /// @brief Gets the current lifecycle state
    /// @return The current state
    LifecycleState state() const;

    /// @brief Gets the set of tags associated with the press release
    /// @return Const reference to the tags set
    const std::set<std::string>& tags() const;

    /// @brief Sets the headline of the press release
    /// @param value New headline value
    /// @param clock Clock instance to get timestamp from
    /// @param desc Description of the change for version history
    void setHeadline(const std::string& value, const Clock& clock, const std::string& desc);

    /// @brief Sets the body content of the press release
    /// @param value New body content
    /// @param clock Clock instance to get timestamp from
    /// @param desc Description of the change for version history
    void setBody(const std::string& value, const Clock& clock, const std::string& desc);

    /// @brief Sets the contact information for the press release
    /// @param contact New contact information
    /// @param clock Clock instance to get timestamp from
    /// @param desc Description of the change for version history
    void setContact(const Contact& contact, const Clock& clock, const std::string& desc);

    /// @brief Adds a tag to the press release
    /// @param tag Tag to add
    /// @param clock Clock instance to get timestamp from
    /// @param desc Description of the change for version history
    void addTag(const std::string& tag, const Clock& clock, const std::string& desc);

    /// @brief Removes a tag from the press release
    /// @param tag Tag to remove
    /// @param clock Clock instance to get timestamp from
    /// @param desc Description of the change for version history
    void removeTag(const std::string& tag, const Clock& clock, const std::string& desc);

    /// @brief Submits the press release for review
    /// @param validator Validator instance to use for validation
    /// @param clock Clock instance to get timestamp from
    /// @param desc Description of the change for version history
    /// @return True if submission was successful, false otherwise
    bool submitForReview(const Validator& validator, const Clock& clock, const std::string& desc);

    /// @brief Publishes the press release
    /// @param validator Validator instance to use for validation
    /// @param clock Clock instance to get timestamp from
    /// @param desc Description of the change for version history
    /// @return True if publishing was successful, false otherwise
    bool publish(const Validator& validator, const Clock& clock, const std::string& desc);

    /// @brief Converts the press release to a map of field names to values
    /// @return Map of field names to values, including nested keys like contact.email
    std::map<std::string, std::string> toFieldMap() const;

    /// @brief Gets the version history of this press release
    /// @return Const reference to the version history
    const VersionHistory& history() const;
};

#endif // PRESS_RELEASE_H