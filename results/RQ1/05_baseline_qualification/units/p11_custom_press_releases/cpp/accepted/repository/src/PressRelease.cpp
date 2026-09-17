#include "PressRelease.h"
#include <algorithm>
#include <sstream>

PressRelease::PressRelease(const std::string& id) 
    : id_(id), state_(LifecycleState::Draft) {}

const std::string& PressRelease::id() const {
    return id_;
}

const std::string& PressRelease::headline() const {
    return headline_;
}

const std::string& PressRelease::body() const {
    return body_;
}

const Contact& PressRelease::contact() const {
    return contact_;
}

LifecycleState PressRelease::state() const {
    return state_;
}

const std::set<std::string>& PressRelease::tags() const {
    return tags_;
}

void PressRelease::setHeadline(const std::string& value, 
                              const Clock& clock, 
                              const std::string& desc) {
    headline_ = value;
    history_.append(clock, desc);
}

void PressRelease::setBody(const std::string& value, 
                          const Clock& clock, 
                          const std::string& desc) {
    body_ = value;
    history_.append(clock, desc);
}

void PressRelease::setContact(const Contact& contact, 
                             const Clock& clock, 
                             const std::string& desc) {
    contact_ = contact;
    history_.append(clock, desc);
}

void PressRelease::addTag(const std::string& tag, 
                         const Clock& clock, 
                         const std::string& desc) {
    tags_.insert(tag);
    history_.append(clock, desc);
}

void PressRelease::removeTag(const std::string& tag, 
                            const Clock& clock, 
                            const std::string& desc) {
    tags_.erase(tag);
    history_.append(clock, desc);
}

bool PressRelease::submitForReview(const Validator& validator, 
                                  const Clock& clock, 
                                  const std::string& desc) {
    ValidationResult result = validator.validateFields(headline_, body_, contact_.email, contact_.phone);
    
    if (result.ok && state_ == LifecycleState::Draft) {
        state_ = LifecycleState::InReview;
        history_.append(clock, desc);
        return true;
    }
    
    return false;
}

bool PressRelease::publish(const Validator& validator, 
                          const Clock& clock, 
                          const std::string& desc) {
    ValidationResult result = validator.validateFields(headline_, body_, contact_.email, contact_.phone);
    
    if (result.ok && state_ == LifecycleState::InReview) {
        state_ = LifecycleState::Published;
        history_.append(clock, desc);
        return true;
    }
    
    return false;
}

std::map<std::string, std::string> PressRelease::toFieldMap() const {
    std::map<std::string, std::string> fields;
    
    fields["id"] = id_;
    fields["headline"] = headline_;
    fields["body"] = body_;
    fields["contact.name"] = contact_.name;
    fields["contact.email"] = contact_.email;
    fields["contact.phone"] = contact_.phone;
    
    // Add tags as a comma-separated string
    std::ostringstream tagsStream;
    bool first = true;
    for (const auto& tag : tags_) {
        if (!first) {
            tagsStream << ",";
        }
        tagsStream << tag;
        first = false;
    }
    fields["tags"] = tagsStream.str();
    
    return fields;
}

const VersionHistory& PressRelease::history() const {
    return history_;
}