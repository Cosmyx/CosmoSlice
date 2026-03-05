#pragma once

#include <string>
#include <map>

namespace Slic3r { namespace GUI {

// CosmoLinkHandler — central dispatcher for all cosmoslice:// deep-link commands.
//
// Entry point: CosmoLinkHandler::handle(url)
//
// URL format:  cosmoslice://<command>?<key>=<value>&<key>=<value>...
//
// Supported commands:
//   add-printer  ?url=<host_url>&name=<display_name>&api=<api_key>
//
// New commands can be added by implementing a private handle_<command>() method
// and registering it in handle().

class CosmoLinkHandler
{
public:
    // Main entry point. Returns true if the URL was recognised and handled.
    static bool handle(const std::string& url);

private:
    // Parse a URL query string ("key=val&key2=val2") into a key→value map.
    // Values are URL-decoded.
    static std::map<std::string, std::string> parse_query(const std::string& query);

    // cosmoslice://add-printer?url=...&name=...&api=...
    // Opens CosmoAddPrinterDialog pre-filled with the supplied parameters.
    static bool handle_add_printer(const std::map<std::string, std::string>& params);
};

}} // namespace Slic3r::GUI
