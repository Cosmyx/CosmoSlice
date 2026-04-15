#pragma once

#include "GUI_Utils.hpp"
#include "Widgets/Button.hpp"
#include "Widgets/TextInput.hpp"
#include "Widgets/ComboBox.hpp"

#include <wx/stattext.h>
#include <string>

namespace Slic3r { namespace GUI {

// Dialog shown when a cosmoslice://add-printer URL is received.
// Lets the user pick which printer profile to attach wireless settings to,
// then pre-fills and applies the host/api/webui values from the URL.
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
    ComboBox*  m_combo_preset { nullptr };
    TextInput* m_txt_name     { nullptr };
    TextInput* m_txt_url      { nullptr };
    TextInput* m_txt_api_key  { nullptr };
    TextInput* m_txt_webui    { nullptr };
    Button*    m_btn_apply    { nullptr };
    Button*    m_btn_cancel   { nullptr };

    void on_apply(wxCommandEvent& event);
    void on_dpi_changed(const wxRect& suggested_rect) override {}
};

}} // namespace Slic3r::GUI
