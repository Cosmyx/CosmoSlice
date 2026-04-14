#pragma once

#include "GUI_Utils.hpp"
#include "Widgets/Button.hpp"
#include "Widgets/TextInput.hpp"

#include <wx/stattext.h>
#include <string>

namespace Slic3r { namespace GUI {

// Dialog shown when a cosmoslice://add-printer URL is received.
// Displays the printer details from the URL pre-filled and editable,
// letting the user review before confirming.
class CosmoAddPrinterDialog : public DPIDialog
{
public:
    CosmoAddPrinterDialog(wxWindow*          parent,
                          const std::string& name,
                          const std::string& url,
                          const std::string& api_key,
                          const std::string& webui);

    ~CosmoAddPrinterDialog() = default;

private:
    TextInput* m_txt_name    { nullptr };
    TextInput* m_txt_url     { nullptr };
    TextInput* m_txt_api_key { nullptr };
    TextInput* m_txt_webui   { nullptr };
    Button*    m_btn_add     { nullptr };
    Button*    m_btn_cancel  { nullptr };

    void on_add(wxCommandEvent& event);
    void on_dpi_changed(const wxRect& suggested_rect) override {}
};

}} // namespace Slic3r::GUI
