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

namespace Slic3r { namespace GUI {

static constexpr int FIELD_WIDTH  = 340;
static constexpr int FIELD_HEIGHT = 40;

// ---------------------------------------------------------------------------

CosmoAddPrinterDialog::CosmoAddPrinterDialog(wxWindow*          parent,
                                             const std::string& name,
                                             const std::string& url,
                                             const std::string& api_key,
                                             const std::string& webui)
    : DPIDialog(parent, wxID_ANY, _L("Add Printer via CosmoSlice Link"),
                wxDefaultPosition, wxDefaultSize,
                wxCLOSE_BOX | wxCAPTION | wxSYSTEM_MENU)
{
    SetBackgroundColour(*wxWHITE);
    SetSizeHints(wxDefaultSize, wxDefaultSize);

    auto* main_sizer = new wxBoxSizer(wxVERTICAL);
    main_sizer->AddSpacer(FromDIP(20));

    // ---- Header message ---------------------------------------------------
    auto* lbl_header = new wxStaticText(this, wxID_ANY,
        _L("A link is requesting to add a printer. Please review the details below:"));
    lbl_header->SetFont(Label::Body_13);
    lbl_header->SetForegroundColour(wxColour(50, 58, 61));
    lbl_header->Wrap(FromDIP(FIELD_WIDTH + 20));
    main_sizer->Add(lbl_header, 0, wxLEFT | wxRIGHT, FromDIP(30));
    main_sizer->AddSpacer(FromDIP(16));

    // ---- Helper to build a labelled field row -----------------------------
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

    make_field(_L("Printer Name:"), name,    m_txt_name);
    make_field(_L("Printer Host:"), url,     m_txt_url);
    make_field(_L("API Key:"),      api_key, m_txt_api_key);
    make_field(_L("Device UI:"),    webui,   m_txt_webui);

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

    StateColor add_bg(
        std::pair<wxColour, int>(wxColour(0, 137, 123), StateColor::Pressed),
        std::pair<wxColour, int>(wxColour(38, 166, 154), StateColor::Hovered),
        std::pair<wxColour, int>(wxColour(0, 150, 136), StateColor::Normal)
    );
    StateColor add_bd(std::pair<wxColour, int>(wxColour(0, 150, 136), StateColor::Normal));
    StateColor add_text(std::pair<wxColour, int>(wxColour(255, 255, 255), StateColor::Normal));

    m_btn_add = new Button(this, _L("Add Printer"));
    m_btn_add->SetFont(Label::Body_12);
    m_btn_add->SetMinSize(wxSize(FromDIP(100), FromDIP(28)));
    m_btn_add->SetCornerRadius(FromDIP(14));
    m_btn_add->SetBackgroundColor(add_bg);
    m_btn_add->SetBorderColor(add_bd);
    m_btn_add->SetTextColor(add_text);
    m_btn_add->Bind(wxEVT_BUTTON, &CosmoAddPrinterDialog::on_add, this);
    btn_sizer->Add(m_btn_add, 0, wxRIGHT, FromDIP(0));

    main_sizer->Add(btn_sizer, 0, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(30));
    main_sizer->AddSpacer(FromDIP(20));

    SetSizer(main_sizer);
    main_sizer->SetSizeHints(this);
    CenterOnParent();
}

// ---------------------------------------------------------------------------

void CosmoAddPrinterDialog::on_add(wxCommandEvent& /*event*/)
{
    const std::string printer_name  = m_txt_name->GetTextCtrl()->GetValue().ToUTF8().data();
    const std::string printer_url   = m_txt_url->GetTextCtrl()->GetValue().ToUTF8().data();
    const std::string printer_api   = m_txt_api_key->GetTextCtrl()->GetValue().ToUTF8().data();
    const std::string printer_webui = m_txt_webui->GetTextCtrl()->GetValue().ToUTF8().data();

    if (printer_name.empty() || printer_url.empty()) {
        BOOST_LOG_TRIVIAL(warning) << "CosmoAddPrinterDialog: name or URL is empty";
        wxGetApp().notification_manager()->push_notification(
            NotificationType::CustomNotification,
            NotificationManager::NotificationLevel::WarningNotificationLevel,
            _u8L("Printer name and URL are required.")
        );
        return;
    }

    // Build the printer using the default config from the currently edited preset.
    PresetBundle* bundle  = wxGetApp().preset_bundle;
    const Preset& current = bundle->printers.get_edited_preset();

    PhysicalPrinter new_printer(printer_name, current.config);
    new_printer.config.set_key_value("host_type", new ConfigOptionEnum<PrintHostType>(htOctoPrint));
    new_printer.config.opt_string("print_host")       = printer_url;
    new_printer.config.opt_string("printhost_apikey") = printer_api;
    new_printer.config.opt_string("print_host_webui") = printer_webui;
    new_printer.add_preset(current.name);

    bundle->physical_printers.save_printer(new_printer);
    Tab* printer_tab = wxGetApp().get_tab(Preset::TYPE_PRINTER);
    if (printer_tab)
        printer_tab->update_tab_ui();

    BOOST_LOG_TRIVIAL(info) << "CosmoLinkHandler: added printer '" << printer_name
                            << "' at " << printer_url;

    wxGetApp().notification_manager()->push_notification(
        NotificationType::CustomNotification,
        NotificationManager::NotificationLevel::RegularNotificationLevel,
        (boost::format(_u8L("Printer \"%1%\" has been added successfully.")) % printer_name).str()
    );

    EndModal(wxID_OK);
}

}} // namespace Slic3r::GUI
