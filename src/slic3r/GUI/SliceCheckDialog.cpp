#include "SliceCheckDialog.hpp"
#include "SliceCheck.hpp"
#include "GUI_App.hpp"
#include "I18N.hpp"
#include "Widgets/Button.hpp"
#include "Widgets/CheckBox.hpp"
#include "libslic3r/AppConfig.hpp"
#include "libslic3r/ProfileTranslator.hpp"
#include "GUI_Utils.hpp"

#include <wx/panel.h>
#include <wx/stattext.h>
#include <wx/statline.h>
#include <wx/scrolwin.h>
#include <wx/sizer.h>
#include <wx/artprov.h>

namespace Slic3r { namespace GUI {

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static wxString translate_check_str(const std::string& s)
{
    const std::string& t = ProfileTranslator::instance().translate(s);
    return wxString::FromUTF8(t.c_str());
}

static wxString icon_label_for(const std::string& icon)
{
    if (icon == "error")   return wxString::FromUTF8("\xe2\x9c\x95"); // ✕
    if (icon == "info")    return wxString::FromUTF8("\xe2\x84\xb9"); // ℹ
    return                         wxString::FromUTF8("\xe2\x9a\xa0"); // ⚠ (warning, default)
}

static wxColour color_for_icon(const std::string& icon)
{
    if (icon == "error")   return wxColour(220, 50, 50);
    if (icon == "info")    return wxColour(50, 120, 220);
    return                         wxColour(220, 160, 0); // warning
}

// ---------------------------------------------------------------------------
// SliceCheckDialog::build_ui
// ---------------------------------------------------------------------------

SliceCheckDialog::SliceCheckDialog(wxWindow* parent, const std::vector<SliceCheck>& checks)
    : DPIDialog(parent, wxID_ANY, _L("Pre-Slice Checks"),
                wxDefaultPosition, wxSize(FromDIP(480), -1),
                wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)
{
    SetBackgroundColour(*wxWHITE);
    build_ui(checks);
    Fit();
    Centre();
}

void SliceCheckDialog::on_dpi_changed(const wxRect& /*suggested_rect*/)
{
    // Let wxWidgets handle the layout rescaling
    Layout();
    Fit();
}

void SliceCheckDialog::build_ui(const std::vector<SliceCheck>& checks)
{
    m_main_sizer = new wxBoxSizer(wxVERTICAL);

    // Scrolled area for the check rows
    auto* scroll = new wxScrolledWindow(this, wxID_ANY, wxDefaultPosition, wxSize(-1, FromDIP(360)),
                                        wxVSCROLL | wxBORDER_NONE);
    scroll->SetScrollRate(0, FromDIP(8));
    scroll->SetBackgroundColour(*wxWHITE);

    auto* scroll_sizer = new wxBoxSizer(wxVERTICAL);
    scroll_sizer->AddSpacer(FromDIP(8));

    for (size_t ci = 0; ci < checks.size(); ++ci) {
        const SliceCheck& check = checks[ci];

        // Separator between checks
        if (ci > 0) {
            auto* sep = new wxStaticLine(scroll, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxLI_HORIZONTAL);
            scroll_sizer->Add(sep, 0, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(16));
            scroll_sizer->AddSpacer(FromDIP(8));
        }

        // Row panel
        auto* row = new wxPanel(scroll, wxID_ANY);
        row->SetBackgroundColour(*wxWHITE);
        auto* row_sizer = new wxBoxSizer(wxHORIZONTAL);

        // Icon label
        auto* icon_lbl = new wxStaticText(row, wxID_ANY, icon_label_for(check.icon));
        icon_lbl->SetFont(icon_lbl->GetFont().Bold().Larger());
        icon_lbl->SetForegroundColour(color_for_icon(check.icon));
        row_sizer->Add(icon_lbl, 0, wxALIGN_TOP | wxLEFT | wxTOP, FromDIP(8));
        row_sizer->AddSpacer(FromDIP(8));

        // Content column
        auto* content_sizer = new wxBoxSizer(wxVERTICAL);

        // Title
        auto* title_lbl = new wxStaticText(row, wxID_ANY, translate_check_str(check.title));
        title_lbl->SetFont(title_lbl->GetFont().Bold());
        content_sizer->Add(title_lbl, 0, wxEXPAND);
        content_sizer->AddSpacer(FromDIP(4));

        // Message (wraps)
        auto* msg_lbl = new wxStaticText(row, wxID_ANY, translate_check_str(check.message),
                                          wxDefaultPosition, wxDefaultSize, wxST_NO_AUTORESIZE);
        msg_lbl->Wrap(FromDIP(370));
        content_sizer->Add(msg_lbl, 0, wxEXPAND);
        content_sizer->AddSpacer(FromDIP(8));

        // Buttons row
        auto* btn_sizer = new wxBoxSizer(wxHORIZONTAL);

        // Build button list: use check.buttons if defined, else defaults
        std::vector<SliceCheckButton> buttons = check.buttons;
        if (buttons.empty()) {
            if (check.type == SliceCheckType::PRE) {
                SliceCheckButton apply_btn, skip_btn;
                apply_btn.label = "Apply & Slice";
                skip_btn.label  = "Slice Anyway";
                buttons = { apply_btn, skip_btn };
            } else {
                SliceCheckButton ok_btn;
                ok_btn.label = "OK";
                buttons = { ok_btn };
            }
        }

        // Capture data for button callbacks
        struct BtnData {
            std::vector<SliceCheckAction> actions;
            std::string tag;
            wxDialog* dialog;
        };

        for (const auto& btn_def : buttons) {
            auto* btn = new Button(row, wxString::FromUTF8(btn_def.label.c_str()));
            btn->SetStyle(ButtonStyle::Regular, ButtonType::Window);
            btn->SetMinSize(wxSize(-1, FromDIP(28)));

            // Capture by value
            auto actions = btn_def.actions;
            auto tag     = check.tag;
            auto* dlg    = this;

            btn->Bind(wxEVT_LEFT_DOWN, [actions, tag, dlg](wxMouseEvent& /*e*/) {
                SliceCheckManager::apply_actions(actions, tag);
                dlg->EndModal(wxID_OK);
            });

            btn_sizer->Add(btn, 0, wxRIGHT, FromDIP(6));
        }

        content_sizer->Add(btn_sizer, 0, 0);
        content_sizer->AddSpacer(FromDIP(8));

        row_sizer->Add(content_sizer, 1, wxEXPAND | wxRIGHT | wxBOTTOM, FromDIP(8));
        row->SetSizer(row_sizer);
        scroll_sizer->Add(row, 0, wxEXPAND | wxLEFT | wxRIGHT, FromDIP(8));
    }

    scroll_sizer->AddSpacer(FromDIP(8));
    scroll->SetSizer(scroll_sizer);
    scroll->FitInside();

    m_main_sizer->Add(scroll, 1, wxEXPAND | wxALL, 0);

    SetSizer(m_main_sizer);
}

// ---------------------------------------------------------------------------
// create_slice_check_prefs_sizer
//
// Builds the "Pre-Slice Checks" section for the Preferences dialog.
// parent should be the scrolled page.
// ---------------------------------------------------------------------------

wxBoxSizer* create_slice_check_prefs_sizer(wxWindow* parent)
{
    AppConfig* app_config = wxGetApp().app_config;

    auto* outer = new wxBoxSizer(wxVERTICAL);

    // Section title (same style as other Preferences sections)
    {
        auto* title_sizer = new wxBoxSizer(wxHORIZONTAL);
        auto* title = new wxStaticText(parent, wxID_ANY, _L("Pre-Slice Checks"));
        title->SetForegroundColour(wxColour(0x38, 0x38, 0x38));
        title->SetFont(::Label::Head_13);
        title->Wrap(-1);
        auto* sep = new wxPanel(parent, wxID_ANY, wxDefaultPosition, wxSize(-1, 1));
        sep->SetBackgroundColour(wxColour(0xC0, 0xC0, 0xC0));
        title_sizer->Add(title, 0, wxALIGN_CENTER | wxALL, 3);
        title_sizer->Add(0, 0, 0, wxLEFT, 9);
        auto* sep_vsizer = new wxBoxSizer(wxVERTICAL);
        sep_vsizer->Add(sep, 0, wxEXPAND);
        title_sizer->Add(sep_vsizer, 1, wxALIGN_CENTER);
        outer->Add(title_sizer, 0, wxEXPAND | wxTOP, 6);
    }

    // One checkbox per tag
    struct TagRow { const char* cfg_key; wxString label; wxString tooltip; };
    static const TagRow rows[] = {
        { SLICECHECK_CFG_MUTE_FILAMENT, _L("Mute Filament checks"),
          _L("Disable all pre-slice checks related to filament/material settings.") },
        { SLICECHECK_CFG_MUTE_PROCESS,  _L("Mute Process checks"),
          _L("Disable all pre-slice checks related to print process settings.") },
        { SLICECHECK_CFG_MUTE_MACHINE,  _L("Mute Machine checks"),
          _L("Disable all pre-slice checks related to printer hardware settings.") },
        { SLICECHECK_CFG_MUTE_SAFETY,   _L("Mute Safety checks"),
          _L("Disable safety warnings. Not recommended.") },
        { SLICECHECK_CFG_MUTE_TIPS,     _L("Mute Tips"),
          _L("Disable informational tips and best-practice hints.") },
    };

    for (const auto& row : rows) {
        auto* cb_sizer = new wxBoxSizer(wxHORIZONTAL);
        cb_sizer->Add(0, 0, 0, wxLEFT, 23);

        auto* checkbox = new ::CheckBox(parent);
        checkbox->SetValue(app_config ? app_config->get_bool(row.cfg_key) : false);
        checkbox->SetToolTip(row.tooltip);
        cb_sizer->Add(checkbox, 0, wxALIGN_CENTER);
        cb_sizer->Add(0, 0, 0, wxLEFT, 8);

        auto* lbl = new wxStaticText(parent, wxID_ANY, row.label);
        lbl->SetForegroundColour(wxColour(0x33, 0x33, 0x33));
        lbl->SetFont(::Label::Body_13);
        lbl->SetToolTip(row.tooltip);
        lbl->Wrap(-1);
        cb_sizer->Add(lbl, 0, wxALIGN_CENTER | wxALL, 3);

        const char* cfg_key = row.cfg_key;
        checkbox->Bind(wxEVT_TOGGLEBUTTON, [app_config, cfg_key, checkbox](wxCommandEvent& /*e*/) {
            if (app_config) {
                app_config->set_bool(cfg_key, checkbox->GetValue());
                app_config->save();
            }
        });

        outer->Add(cb_sizer, 0, wxEXPAND | wxTOP, 3);
    }

    return outer;
}

}} // namespace Slic3r::GUI
