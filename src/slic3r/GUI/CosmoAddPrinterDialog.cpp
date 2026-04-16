#include "CosmoAddPrinterDialog.hpp"

#include "GUI_App.hpp"
#include "Tab.hpp"
#include "NotificationManager.hpp"

#include "libslic3r/Preset.hpp"
#include "libslic3r/PresetBundle.hpp"
#include "libslic3r/PrintConfig.hpp"

#include <wx/sizer.h>
#include <wx/stattext.h>

#include <boost/log/trivial.hpp>
#include <boost/format.hpp>

namespace Slic3r { namespace GUI {

// ---------------------------------------------------------------------------

CosmoAddPrinterDialog::CosmoAddPrinterDialog(wxWindow*          parent,
                                             const std::string& name,
                                             const std::string& url,
                                             const std::string& api_key,
                                             const std::string& webui)
    : wxDialog(parent, wxID_ANY, "Add Wireless Printer via CosmoSlice Link",
               wxDefaultPosition, wxDefaultSize,
               wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)
{
    BOOST_LOG_TRIVIAL(info) << "[CosmoLink] CosmoAddPrinterDialog constructor start (parent=" << (parent ? "valid" : "null") << ")";
    auto* main_sizer = new wxBoxSizer(wxVERTICAL);

    // ---- Header -------------------------------------------------------
    auto* lbl_header = new wxStaticText(this, wxID_ANY,
        "A link wants to add wireless settings to a printer.\n"
        "Select the printer profile to apply them to:");
    main_sizer->Add(lbl_header, 0, wxALL, 10);

    // ---- Printer profile selector -------------------------------------
    main_sizer->Add(new wxStaticText(this, wxID_ANY, "Printer Profile:"),
                    0, wxLEFT | wxRIGHT | wxTOP, 10);

    m_choice_preset = new wxChoice(this, wxID_ANY);
    {
        BOOST_LOG_TRIVIAL(info) << "[CosmoLink] Dialog: loading printer presets (preset_bundle=" << (wxGetApp().preset_bundle ? "valid" : "null") << ")";
        const PresetCollection& printers = wxGetApp().preset_bundle->printers;
        const std::string& current_name  = printers.get_edited_preset().name;
        BOOST_LOG_TRIVIAL(info) << "[CosmoLink] Dialog: current preset='" << current_name << "'";
        int sel = 0, idx = 0;
        for (const Preset& p : printers.get_presets()) {
            if (!p.is_visible || p.is_default)
                continue;
            BOOST_LOG_TRIVIAL(info) << "[CosmoLink] Dialog: adding preset '" << p.name << "'";
            m_choice_preset->Append(wxString::FromUTF8(p.name));
            if (p.name == current_name)
                sel = idx;
            ++idx;
        }
        BOOST_LOG_TRIVIAL(info) << "[CosmoLink] Dialog: " << idx << " preset(s) loaded, selection=" << sel;
        if (m_choice_preset->GetCount() > 0)
            m_choice_preset->SetSelection(sel);
    }
    main_sizer->Add(m_choice_preset, 0, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, 10);

    // ---- Text fields --------------------------------------------------
    auto make_field = [&](const wxString& label, const std::string& value,
                          wxTextCtrl*& out)
    {
        main_sizer->Add(new wxStaticText(this, wxID_ANY, label),
                        0, wxLEFT | wxRIGHT | wxTOP, 10);
        out = new wxTextCtrl(this, wxID_ANY, wxString::FromUTF8(value),
                             wxDefaultPosition, wxSize(360, -1));
        main_sizer->Add(out, 0, wxEXPAND | wxLEFT | wxRIGHT | wxBOTTOM, 10);
    };

    make_field("Physical Printer Name:", name,    m_txt_name);
    make_field("Host:",                  url,     m_txt_url);
    make_field("Device UI:",             webui,   m_txt_webui);
    make_field("API Key:",               api_key, m_txt_api_key);

    // ---- Buttons ------------------------------------------------------
    auto* btn_sizer = new wxBoxSizer(wxHORIZONTAL);
    btn_sizer->AddStretchSpacer();

    m_btn_cancel = new wxButton(this, wxID_CANCEL, "Cancel");
    m_btn_apply  = new wxButton(this, wxID_OK,     "Apply");
    m_btn_apply->Bind(wxEVT_BUTTON, &CosmoAddPrinterDialog::on_apply, this);

    btn_sizer->Add(m_btn_cancel, 0, wxRIGHT, 8);
    btn_sizer->Add(m_btn_apply,  0);
    main_sizer->Add(btn_sizer, 0, wxEXPAND | wxALL, 10);

    SetSizerAndFit(main_sizer);
    CentreOnParent();
    BOOST_LOG_TRIVIAL(info) << "[CosmoLink] CosmoAddPrinterDialog constructor complete";
}

// ---------------------------------------------------------------------------

void CosmoAddPrinterDialog::on_apply(wxCommandEvent& /*event*/)
{
    const std::string preset_name   = m_choice_preset->GetStringSelection().ToUTF8().data();
    const std::string printer_name  = m_txt_name->GetValue().ToUTF8().data();
    const std::string printer_url   = m_txt_url->GetValue().ToUTF8().data();
    const std::string printer_api   = m_txt_api_key->GetValue().ToUTF8().data();
    const std::string printer_webui = m_txt_webui->GetValue().ToUTF8().data();

    if (preset_name.empty() || printer_name.empty() || printer_url.empty()) {
        wxMessageBox("Please select a printer profile and fill in the name and host.",
                     "CosmoSlice", wxOK | wxICON_WARNING, this);
        return;
    }

    PresetBundle*  bundle   = wxGetApp().preset_bundle;
    const Preset*  selected = bundle->printers.find_preset(preset_name);
    if (!selected) {
        BOOST_LOG_TRIVIAL(error) << "CosmoAddPrinterDialog: preset not found: " << preset_name;
        wxMessageBox("Selected printer profile not found.",
                     "CosmoSlice", wxOK | wxICON_WARNING, this);
        return;
    }

    PhysicalPrinter new_printer(printer_name, selected->config);
    new_printer.config.set_key_value("host_type", new ConfigOptionEnum<PrintHostType>(htOctoPrint));
    new_printer.config.opt_string("print_host")       = printer_url;
    new_printer.config.opt_string("printhost_apikey") = printer_api;
    new_printer.config.opt_string("print_host_webui") = printer_webui;
    new_printer.add_preset(selected->name);

    bundle->physical_printers.save_printer(new_printer);

    Tab* printer_tab = wxGetApp().get_tab(Preset::TYPE_PRINTER);
    if (printer_tab)
        printer_tab->update_tab_ui();

    BOOST_LOG_TRIVIAL(info) << "CosmoLinkHandler: added printer '" << printer_name
                            << "' on profile '" << preset_name
                            << "' at " << printer_url;

    wxGetApp().notification_manager()->push_notification(
        NotificationType::CustomNotification,
        NotificationManager::NotificationLevel::RegularNotificationLevel,
        (boost::format("Printer \"%1%\" has been added successfully.") % printer_name).str()
    );

    EndModal(wxID_OK);
}

}} // namespace Slic3r::GUI
