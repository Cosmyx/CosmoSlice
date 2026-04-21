#pragma once

#include <boost/log/sources/severity_channel_logger.hpp>
#include <boost/log/sources/record_ostream.hpp>
#include <boost/log/trivial.hpp>

namespace Slic3r {

// Returns the Cosmyx channel logger, created on first use (after main() starts).
// Using a function-local static avoids the static-initialization-order crash that
// occurs when a severity_channel_logger_mt is constructed as a global variable.
inline boost::log::sources::severity_channel_logger_mt<
    boost::log::trivial::severity_level, std::string
>& get_cosmo_logger()
{
    static boost::log::sources::severity_channel_logger_mt<
        boost::log::trivial::severity_level, std::string
    > s_logger;
    return s_logger;
}

} // namespace Slic3r

// Log a Cosmyx-specific message at the given severity level.
// Usage: COSMO_LOG(info) << "[Module] message";
#define COSMO_LOG(sev) \
    BOOST_LOG_CHANNEL_SEV(Slic3r::get_cosmo_logger(), std::string("cosmo"), \
                          boost::log::trivial::sev)
