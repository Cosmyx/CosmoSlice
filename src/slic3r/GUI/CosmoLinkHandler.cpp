#include "CosmoLinkHandler.hpp"
#include "CosmoAddPrinterDialog.hpp"
#include "GUI_App.hpp"
#include "MainFrame.hpp"

#include <boost/log/trivial.hpp>
#include <wx/uri.h>
#include <wx/msgdlg.h>

#ifdef _WIN32
#include <windows.h>
#endif

namespace Slic3r { namespace GUI {

bool CosmoLinkHandler::handle(const std::string& url)
{
    BOOST_LOG_TRIVIAL(warning) << "[CosmoLink] handle() called with URL: " << url;

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

    BOOST_LOG_TRIVIAL(warning) << "[CosmoLink] command='" << command << "' query='" << query << "'";

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
    BOOST_LOG_TRIVIAL(warning) << "[CosmoLink] handle_add_printer() called";

    auto get = [&](const std::string& key) -> std::string {
        const auto it = params.find(key);
        return (it != params.end()) ? it->second : std::string{};
    };

    const std::string name  = get("name");
    const std::string host  = get("host");
    const std::string api   = get("api");
    const std::string webui = get("webui");

    BOOST_LOG_TRIVIAL(warning) << "[CosmoLink] name='" << name << "' host='" << host << "'";

    MainFrame* mf = wxGetApp().mainframe;
    if (mf) {
#ifdef _WIN32
        ::SetForegroundWindow(mf->GetHandle());
#endif
        mf->Raise();
    }

    BOOST_LOG_TRIVIAL(warning) << "[CosmoLink] About to create dialog (parent=" << (mf ? "valid" : "null") << ")";

    try {
        CosmoAddPrinterDialog dlg(mf, name, host, api, webui);
        BOOST_LOG_TRIVIAL(warning) << "[CosmoLink] Dialog created, calling ShowModal()";
        dlg.ShowModal();
        BOOST_LOG_TRIVIAL(warning) << "[CosmoLink] ShowModal() returned";
    } catch (const std::exception& ex) {
        BOOST_LOG_TRIVIAL(error) << "[CosmoLink] Exception in dialog: " << ex.what();
        wxMessageBox(wxString::FromUTF8(std::string("CosmoLink dialog error: ") + ex.what()),
                     "CosmoSlice Error", wxOK | wxICON_ERROR);
    } catch (...) {
        BOOST_LOG_TRIVIAL(error) << "[CosmoLink] Unknown exception in dialog";
        wxMessageBox("CosmoLink: unknown exception creating dialog", "CosmoSlice Error", wxOK | wxICON_ERROR);
    }

    return true;
}

}} // namespace Slic3r::GUI
