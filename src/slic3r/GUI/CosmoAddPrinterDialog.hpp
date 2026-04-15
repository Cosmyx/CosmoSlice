#pragma once

#include <wx/dialog.h>
#include <wx/choice.h>
#include <wx/textctrl.h>
#include <wx/button.h>
#include <wx/stattext.h>
#include <string>

namespace Slic3r { namespace GUI {

// Dialog shown when a cosmoslice://add-printer URL is received.
// Uses only standard wxWidgets primitives so it is safe to show from
// post_init() / CallAfter() without risk of custom-widget crashes.
class CosmoAddPrinterDialog : public wxDialog
{
public:
    CosmoAddPrinterDialog(wxWindow*          parent,
                          const std::string& name,
                          const std::string& url,
                          const std::string& api_key,
                          const std::string& webui);

    ~CosmoAddPrinterDialog() = default;

private:
    wxChoice*   m_choice_preset { nullptr };
    wxTextCtrl* m_txt_name      { nullptr };
    wxTextCtrl* m_txt_url       { nullptr };
    wxTextCtrl* m_txt_api_key   { nullptr };
    wxTextCtrl* m_txt_webui     { nullptr };
    wxButton*   m_btn_apply     { nullptr };
    wxButton*   m_btn_cancel    { nullptr };

    void on_apply(wxCommandEvent& event);
};

}} // namespace Slic3r::GUI
