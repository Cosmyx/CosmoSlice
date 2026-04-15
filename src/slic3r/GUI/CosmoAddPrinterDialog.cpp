#include "CosmoAddPrinterDialog.hpp"

#include "GUI_App.hpp"
#include "I18N.hpp"
#include "NotificationManager.hpp"
#include "Tab.hpp"
#include "Widgets/Label.hpp"

#include "libslic3r/Preset.hpp"
#include "libslic3r/PresetBundle.hpp"
#include "libslic3r/PrintConfig.hpp"

#include <wx/sizer.h>
#include <wx/stattext.h>

#include <boost/log/trivial.hpp>
#include <boost/format.hpp>

namespace Slic3r { namespace GUI {

static constexpr int FIELD_WIDTH  = 340;
static constexpr int FIELD_HEIGHT = 40;

// ---------------------------------------------------------------------------

CosmoAddPrinterDialog::CosmoAddPrinterDialog(wxWindow*          parent,
                                             const std::string& name,
                                             const std::string& url,
                                             const std::string& api_key,
                                             const std::string& webui)
    : DPIDialog(parent, wxID_ANY, _L("Add Wireless Printer via CosmoSlice Link"),
                wxDefaultPosition, wxDefaultSize,
                wxCLOSE_BOX | wxCAPTION | wxSYSTEM_MENU)
{
    SetBackgroundColour(*wxWHITE);
    SetSizeHints(wxDefaultSize, wxDefaultSize);

    auto* main_sizer = new wxBoxSizer(wxVERTICAL);
    main_sizer->AddSpacer(FromDIP(20));

    // ---- Header message ---------------------------------------------------
    auto* lbl_header = new wxStaticText(this, wxID_ANY,
        _L("A link wants to add wireless settings to a printer.\n"
           "Select the printer profile to apply them to:"));
    lbl_header->SetFont(Label::Body_13);
    lbl_header->SetForegroundColour(wxColour(50, 58, 61));
    lbl_header->Wrap(FromDIP(FIELD_WIDTH + 20));
    main_sizer->Add(lbl_header, 0, wxLEFT | wxRIGHT, FromDIP(30));
    main_sizer->AddSpacer(FromDIP(16));

    // ---- Helper to build a labelled text-field row ------------------------
    auto make_field = [&](const wxString& label_text,
                          const std::string& value,
                          TextInput*& out_field)
    {
        auto* lbl = new wxStaticText(this, wxID_ANY, label_text);
        lbl->SetFont(Label::Body_13);
        lbl->SetForegroundColour(wxColour(50, 58, 61));
        main_sizer->Add(lbl, 0, wxLEFT | wxRIGHT, FromDIP(30));
        main_sizer->AddSpacer(FromDIP(4));

        out_field = new TextInput(this, wxString::FromUTF8(value));
        out_field->SetFont(Label::Body_13);
        out_field->SetCornerRadius(FromDIP(5));
        out_field->SetSize(wxSize(FromDIP(FIELD_WIDTH), FromDIP(FIELD_HEIGHT)));
        out_field->SetMinSize(wxSize(FromDIP(FIELD_WIDTH), FromDIP(FIELD_HEIGHT)));
        out_field->SetBackgroundColour(*wxWHITE);
        out_field->GetTextCtrl()->SetForegroundColour(wxColour(50, 58, 61));
        main_sizer->Add(out_field, 0, wxLEFT | wxRIGHT, FromDIP(30));
        main_sizer->AddSpacer(FromDIP(12));
    };

    // ---- Printer profile selector -----------------------------------------
    {
        auto* lbl = new wxStaticText(this, wxID_ANY, _L("Printer Profile:"));
        lbl->SetFont(Label::Body_13);
        lbl->SetForegroundColour(wxColour(50, 58, 61));
        main_sizer->Add(lbl, 0, wxLEFT | wxRIGHT, FromDIP(30));
        main_sizer->AddSpacer(FromDIP(4));

        m_combo_preset = new ComboBox(this, wxID_ANY, wxEmptyString,
                                      wxDefaultPosition,
                                      wxSize(FromDIP(FIELD_WIDTH), FromDIP(FIELD_HEIGHT)));
        m_combo_preset->SetFont(Label::Body_13);

        PresetBundle* bundle = wxGetApp().preset_bundle;
        for (const Preset& p : bundle->printers.get_presets()) {
            if (!p.is_visible || p.is_default)
                continue;
            m_combo_preset->Append(wxString::FromUTF8(p.name));
        }

        // Pre-select the currently active printer preset
        const std::string& current_name = bundle->printers.get_edited_preset().name;
        int sel = m_combo_preset->FindString(wxString::FromUTF8(current_name));
        m_combo_preset->SetSelection(sel >= 0 ? sel : 0);

        main_sizer->Add(m_combo_preset, 0, wxLEFT | wxRIGHT, FromDIP(30));
        main_sizer->AddSpacer(FromDIP(12));
    }

    // ---- Editable fields --------------------------------------------------
    make_field(_L("Physical Printer Name:"), name,    m_txt_name);
    make_field(_L("Host:"),                  url,     m_txt_url);
    make_field(_L("Device UI:"),             webui,   m_txt_webui);
    make_field(_L("API Key:"),               api_key, m_txt_api_key);

    main_sizer->AddSpacer(FromDIP(8));

    // ---- Buttons ---------------------------------------------------------
    auto* btn_sizer = new wxBoxSizer(wxHORIZONTAL);
    btn_sizer->AddStretchSpacer();

    StateColor cancel_bg(
        std::pair<wxColour, int>(wxColour(206, 206, 206), StateColor::Pressed),
        std::pair<wxColour, int>(wxColour(238, 238, 238), StateColor::Hovered),
        std::pair<wxColour, int>(wxColour(255, 255, 255), StateColor::Normal)
    );
    StateColor cancel_bd(std::pair<wxColour, int>(wxColour(172, 172, 172), StateColor::Normal));
    StateColor cancel_text(std::pair<wxColour, int>(wxColour(50, 58, 61), StateColor::Normal));

    m_btn_cancel = new Button(this, _L("Cancel"));
    m_btn_cancel->SetFont(Label::Body_12);
    m_btn_cancel->SetMinSize(wxSize(FromDIP(88), FromDIP(28)));
    m_btn_cancel->SetCornerRadius(FromDIP(14));
    m_btn_cancel->SetBackgroundColor(cancel_bg);
    m_btn_cancel->SetBorderColor(cancel_bd);
    m_btn_cancel->SetTextColor(cancel_text);
    m_btn_cancel->Bind(wxEVT_BUTTON, [this](wxCommandEvent&) { EndModal(wxID_CANCEL); });
    btn_sizer->Add(m_btn_cancel, 0, wxRIGHT, FromDIP(8));

    StateColor apply_bg(
        std::pair<wxColour, int>(wxColour(0, 137, 123), StateColor::Pressed),
        std::pair<wxColour, int>(wxColour(38, 166, 154), StateColor::Hovered),
        std::pair<wxColour, int>(wxColour(0, 150, 136), StateColor::Normal)
    );
    StateColor apply_bd(std::pair<wxColour, int>(wxColour(0, 150, 136), StateColor::Normal));
    StateColor apply_text(std::pair<wxColour, int>(wxColour(255, 255, 255), StateColor::Normal));

    m_btn_apply = new Button(this, _L("Apply"));
    m_btn_apply->SetFont(Label::Body_12);
    m_btn_apply->SetMinSize(wxSize(FromDIP(88), FromDIP(28)));
    m_btn_apply->SetCornerRadius(FromDIP(14));
    m_btn_apply->SetBackgroundColor(apply_bg);
    m_btn_apply->SetBorderColor(apply_bd);
    m_btn_apply->SetTextColor(apply_text);
    m_btn_apply->Bind(wxEVT_BUTTON, &CosmoAddPrinterDialog::on_apply, this);
    btn_sizer->Add(m_btn_apply, 0, wxRIGHT, FromDIP(0));

    main_sizer->Add(btn_sizer, 0, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(30));
    main_sizer->AddSpacer(FromDIP(20));

    SetSizer(main_sizer);
    main_sizer->SetSizeHints(this);
    CenterOnParent();
}

// ---------------------------------------------------------------------------

void CosmoAddPrinterDialog::on_apply(wxCommandEvent& /*event*/)
{
    const std::string preset_name   = m_combo_preset->GetValue().ToUTF8().data();
    const std::string printer_name  = m_txt_name->GetTextCtrl()->GetValue().ToUTF8().data();
    const std::string printer_url   = m_txt_url->GetTextCtrl()->GetValue().ToUTF8().data();
    const std::string printer_api   = m_txt_api_key->GetTextCtrl()->GetValue().ToUTF8().data();
    const std::string printer_webui = m_txt_webui->GetTextCtrl()->GetValue().ToUTF8().data();

    if (preset_name.empty() || printer_name.empty() || printer_url.empty()) {
        wxGetApp().notification_manager()->push_notification(
            NotificationType::CustomNotification,
            NotificationManager::NotificationLevel::WarningNotificationLevel,
            _u8L("Please select a printer profile and fill in the name and host.")
        );
        return;
    }

    PresetBundle* bundle = wxGetApp().preset_bundle;
    const Preset* selected = bundle->printers.find_preset(preset_name);
    if (!selected) {
        BOOST_LOG_TRIVIAL(error) << "CosmoAddPrinterDialog: preset not found: " << preset_name;
        wxGetApp().notification_manager()->push_notification(
            NotificationType::CustomNotification,
            NotificationManager::NotificationLevel::WarningNotificationLevel,
            _u8L("Selected printer profile not found.")
        );
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
        (boost::format(_u8L("Printer \"%1%\" has been added successfully.")) % printer_name).str()
    );

    EndModal(wxID_OK);
}

}} // namespace Slic3r::GUI
