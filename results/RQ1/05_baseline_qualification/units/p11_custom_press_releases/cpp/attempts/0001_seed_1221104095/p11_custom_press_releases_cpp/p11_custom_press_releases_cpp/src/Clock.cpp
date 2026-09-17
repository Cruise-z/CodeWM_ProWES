#include "Clock.h"

FixedClock::FixedClock(const std::string& timestamp) : timestamp_(timestamp) {}

std::string FixedClock::now() const {
    return timestamp_;
}