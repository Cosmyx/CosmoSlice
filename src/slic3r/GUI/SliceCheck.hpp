#pragma once

#include <string>
#include <vector>
#include <wx/window.h>

namespace Slic3r { namespace GUI {

// ---------------------------------------------------------------------------
// Tag constants (fixed list — 5 tags)
// ---------------------------------------------------------------------------
constexpr const char* SLICECHECK_TAG_FILAMENT = "filament";
constexpr const char* SLICECHECK_TAG_PROCESS  = "process";
constexpr const char* SLICECHECK_TAG_MACHINE  = "machine";
constexpr const char* SLICECHECK_TAG_SAFETY   = "safety";
constexpr const char* SLICECHECK_TAG_TIPS     = "tips";

// AppConfig keys used to persist mute state
constexpr const char* SLICECHECK_CFG_MUTE_FILAMENT = "pre_slice_check_mute_filament";
constexpr const char* SLICECHECK_CFG_MUTE_PROCESS  = "pre_slice_check_mute_process";
constexpr const char* SLICECHECK_CFG_MUTE_MACHINE  = "pre_slice_check_mute_machine";
constexpr const char* SLICECHECK_CFG_MUTE_SAFETY   = "pre_slice_check_mute_safety";
constexpr const char* SLICECHECK_CFG_MUTE_TIPS     = "pre_slice_check_mute_tips";

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

enum class SliceCheckType { PRE, POST };

// A single SET action inside an ON block
struct SliceCheckAction {
    std::string key;         // OrcaSlicer config option key
    std::string value_expr;  // literal, formula string, or quoted string; empty if suppress_tag
    bool        suppress_tag = false; // SUPPRESS_TAG keyword
};

// A button and the actions to execute when it is clicked
struct SliceCheckButton {
    std::string                   label;
    std::vector<SliceCheckAction> actions;
};

// One parsed .check file
struct SliceCheck {
    std::string  file_path;
    std::string  title;          // base-language string; translated via ProfileTranslator at display time
    std::string  message;        // base-language string; translated via ProfileTranslator at display time
    std::string  icon;           // "warning" | "info" | "error"  (default: "warning")
    std::string  tag;            // must be one of SLICECHECK_TAG_* constants
    SliceCheckType type;         // PRE or POST

    std::string  condition_src;  // raw WHEN block text; empty = always triggers

    // Buttons shown in the dialog.  Default when empty: ["Apply & Slice", "Slice Anyway"] for PRE
    //                                                   ["OK", "Mute Checks"]             for POST
    std::vector<SliceCheckButton> buttons;
};

// ---------------------------------------------------------------------------
// SliceCheckManager  (singleton)
// ---------------------------------------------------------------------------

class SliceCheckManager
{
public:
    static SliceCheckManager& get_instance();

    // Scan all vendor profile directories under {resources_dir}/profiles/
    // for a checks/ subdirectory and load all *.check files found.
    // Call once at startup (same timing as ProfileTranslator::load_translations).
    void load_all();

    // --- Called from Plater.cpp (one-liners) ---

    // Evaluate PRE checks, show dialog if any triggered.
    // Blocks until the user dismisses the dialog; never prevents slicing.
    void run_pre_checks(wxWindow* parent);

    // Evaluate POST checks, show dialog if any triggered.
    // Call when slicing succeeds, before showing the send-to-printer dialog.
    void run_post_checks(wxWindow* parent);

    // --- Tag mute helpers (also used by SliceCheckDialog) ---

    static bool        is_tag_muted(const std::string& tag);
    static void        set_tag_muted(const std::string& tag, bool muted);
    static const char* cfg_key_for_tag(const std::string& tag); // returns nullptr if unknown tag

    // Apply a list of actions to the current preset bundle/config.
    // Public so SliceCheckDialog can call it after the user picks a button.
    static void apply_actions(const std::vector<SliceCheckAction>& actions,
                              const std::string& check_tag);

private:
    SliceCheckManager()  = default;
    ~SliceCheckManager() = default;
    SliceCheckManager(const SliceCheckManager&)            = delete;
    SliceCheckManager& operator=(const SliceCheckManager&) = delete;

    // Parsing helpers
    static SliceCheck   parse_file(const std::string& path);
    static std::string  strip_comments(const std::string& src);
    static std::vector<SliceCheckButton> parse_buttons_line(const std::string& line);
    static SliceCheckAction              parse_action_line(const std::string& line);

    // Condition evaluation
    bool evaluate_condition(const std::string& expr) const;

    // Formula evaluation (for SET value expressions)
    static double evaluate_formula(const std::string& expr);

    std::vector<SliceCheck> m_checks;
};

}} // namespace Slic3r::GUI
