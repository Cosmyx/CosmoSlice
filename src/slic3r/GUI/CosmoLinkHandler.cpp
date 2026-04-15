#include "CosmoLinkHandler.hpp"
#include "CosmoAddPrinterDialog.hpp"
#include "GUI_App.hpp"
#include "MainFrame.hpp"

#include <boost/log/trivial.hpp>
#include <wx/uri.h>

#ifdef _WIN32
#include <windows.h>
#endif

namespace Slic3r { namespace GUI {

bool CosmoLinkHandler::handle(const std::string& url)
{
    static const std::string prefix = "cosmoslice://";
    if (url.size() <= prefix.size()) {
        BOOST_LOG_TRIVIAL(warning) << "CosmoLinkHandler: URL too short: " << url;
        return false;
    }

    const std::string rest = url.substr(prefix.size());

    // Split on '?' → command + query string
    std::string command, query;
    const auto qpos = rest.find('?');
    if (qpos == std::string::npos) {
        command = rest;
    } else {
        command = rest.substr(0, qpos);
        query   = rest.substr(qpos + 1);
    }

    const auto params = parse_query(query);

    if (command == "add-printer")
        return handle_add_printer(params);

    BOOST_LOG_TRIVIAL(warning) << "CosmoLinkHandler: unknown command '" << command << "'";
    return false;
}

// ---------------------------------------------------------------------------

std::map<std::string, std::string> CosmoLinkHandler::parse_query(const std::string& query)
{
    std::map<std::string, std::string> result;
    if (query.empty())
        return result;

    size_t start = 0;
    while (start < query.size()) {
        const size_t amp = query.find('&', start);
        const size_t end = (amp == std::string::npos) ? query.size() : amp;

        const std::string token = query.substr(start, end - start);
        const size_t      eq    = token.find('=');
        if (eq != std::string::npos) {
            const std::string key = token.substr(0, eq);
            const std::string val = token.substr(eq + 1);
            // URL-decode the value (handles %XX and + as space)
            result[key] = wxURI::Unescape(wxString::FromUTF8(val)).ToUTF8().data();
        }

        start = end + 1;
    }
    return result;
}

// ---------------------------------------------------------------------------

bool CosmoLinkHandler::handle_add_printer(const std::map<std::string, std::string>& params)
{
    auto get = [&](const std::string& key) -> std::string {
        const auto it = params.find(key);
        return (it != params.end()) ? it->second : std::string{};
    };

    // Copy params by value so the lambda can safely capture them.
    const std::string name  = get("name");
    const std::string host  = get("host");
    const std::string api   = get("api");
    const std::string webui = get("webui");

    // Defer the dialog via CallAfter so it runs once the event loop is fully
    // spinning. ShowModal() called synchronously from post_init() (which runs
    // inside the first wxEVT_IDLE before the main frame has fully settled)
    // silently fails on Windows.
    wxGetApp().CallAfter([name, host, api, webui]() {
        MainFrame* mf = wxGetApp().mainframe;
        if (mf) {
#ifdef _WIN32
            ::SetForegroundWindow(mf->GetHandle());
#endif
            mf->Raise();
        }
        CosmoAddPrinterDialog dlg(mf, name, host, api, webui);
        dlg.ShowModal();
    });
    return true;
}

}} // namespace Slic3r::GUI
