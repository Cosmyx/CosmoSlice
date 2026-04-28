#pragma once

#include "GUI_Utils.hpp"
#include "SliceCheck.hpp"
#include <wx/dialog.h>
#include <wx/sizer.h>
#include <vector>
#include <string>

namespace Slic3r { namespace GUI {

// ---------------------------------------------------------------------------
// SliceCheckDialog
//
// A non-blocking advisory dialog shown before slicing (PRE) or before
// sending to the printer (POST).  All buttons ultimately allow slicing to
// proceed — none can block the user.
// ---------------------------------------------------------------------------
class SliceCheckDialog : public DPIDialog
{
public:
    SliceCheckDialog(wxWindow* parent, const std::vector<SliceCheck>& checks);

protected:
    void on_dpi_changed(const wxRect& suggested_rect) override;

private:
    void build_ui(const std::vector<SliceCheck>& checks);

    wxBoxSizer* m_main_sizer { nullptr };
};

// ---------------------------------------------------------------------------
// create_slice_check_prefs_sizer
//
// Returns a wxBoxSizer* containing the "Pre-Slice Checks" section (title +
// five mute checkboxes) ready to be inserted into the Preferences dialog.
// parent: the scrolled page wxWindow.
// ---------------------------------------------------------------------------
wxBoxSizer* create_slice_check_prefs_sizer(wxWindow* parent);

}} // namespace Slic3r::GUI
