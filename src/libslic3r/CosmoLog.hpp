#pragma once

#include <boost/log/sources/severity_channel_logger.hpp>
#include <boost/log/sources/record_ostream.hpp>
#include <boost/log/trivial.hpp>

namespace Slic3r {

// Global channel-severity logger for all Cosmyx-specific additions.
// Messages logged through this are routed exclusively to the cosmo log file
// (cosmo_*.log) and are excluded from the main OrcaSlicer debug log.
extern boost::log::sources::severity_channel_logger_mt<
    boost::log::trivial::severity_level, std::string
> g_cosmo_logger;

} // namespace Slic3r

// Log a Cosmyx-specific message at the given severity level.
// Usage: COSMO_LOG(info) << "[Module] message";
#define COSMO_LOG(sev) \
    BOOST_LOG_CHANNEL_SEV(Slic3r::g_cosmo_logger, std::string("cosmo"), \
                          boost::log::trivial::sev)
