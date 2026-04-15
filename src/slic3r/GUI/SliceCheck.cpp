#include "SliceCheck.hpp"
#include "SliceCheckDialog.hpp"
#include "GUI_App.hpp"
#include "Tab.hpp"
#include "GUI.hpp"
#include "libslic3r/AppConfig.hpp"
#include "libslic3r/PresetBundle.hpp"
#include "libslic3r/ProfileTranslator.hpp"
#include "libslic3r/Utils.hpp"

#include <boost/filesystem.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/log/trivial.hpp>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace Slic3r { namespace GUI {

namespace fs = boost::filesystem;

// ---------------------------------------------------------------------------
// Singleton
// ---------------------------------------------------------------------------

SliceCheckManager& SliceCheckManager::get_instance()
{
    static SliceCheckManager instance;
    return instance;
}

// ---------------------------------------------------------------------------
// Tag / mute helpers
// ---------------------------------------------------------------------------

const char* SliceCheckManager::cfg_key_for_tag(const std::string& tag)
{
    if (tag == SLICECHECK_TAG_FILAMENT) return SLICECHECK_CFG_MUTE_FILAMENT;
    if (tag == SLICECHECK_TAG_PROCESS)  return SLICECHECK_CFG_MUTE_PROCESS;
    if (tag == SLICECHECK_TAG_MACHINE)  return SLICECHECK_CFG_MUTE_MACHINE;
    if (tag == SLICECHECK_TAG_SAFETY)   return SLICECHECK_CFG_MUTE_SAFETY;
    if (tag == SLICECHECK_TAG_TIPS)     return SLICECHECK_CFG_MUTE_TIPS;
    return nullptr;
}

bool SliceCheckManager::is_tag_muted(const std::string& tag)
{
    const char* key = cfg_key_for_tag(tag);
    if (!key) return false;
    AppConfig* cfg = wxGetApp().app_config;
    if (!cfg) return false;
    return cfg->get_bool(key);
}

void SliceCheckManager::set_tag_muted(const std::string& tag, bool muted)
{
    const char* key = cfg_key_for_tag(tag);
    if (!key) return;
    AppConfig* cfg = wxGetApp().app_config;
    if (!cfg) return;
    cfg->set_bool(key, muted);
    cfg->save();
}

// ---------------------------------------------------------------------------
// Vendor loading
// ---------------------------------------------------------------------------

void SliceCheckManager::load_all()
{
    m_checks.clear();

    fs::path profiles_dir = fs::path(Slic3r::resources_dir()) / "profiles";
    if (!fs::exists(profiles_dir) || !fs::is_directory(profiles_dir)) return;

    size_t total = 0;
    for (const auto& vendor_entry : fs::directory_iterator(profiles_dir)) {
        if (!fs::is_directory(vendor_entry.path())) continue;

        fs::path checks_dir = vendor_entry.path() / "checks";
        if (!fs::exists(checks_dir) || !fs::is_directory(checks_dir)) continue;

        std::string vendor_name = vendor_entry.path().filename().string();

        // Collect .check files sorted alphabetically
        std::vector<fs::path> files;
        for (const auto& entry : fs::directory_iterator(checks_dir)) {
            if (entry.path().extension() == ".check")
                files.push_back(entry.path());
        }
        std::sort(files.begin(), files.end());

        for (const auto& f : files) {
            try {
                SliceCheck check = parse_file(f.string());
                m_checks.push_back(std::move(check));
                ++total;
                BOOST_LOG_TRIVIAL(debug) << "SliceCheck: loaded " << vendor_name
                                         << "/" << f.filename().string();
            } catch (const std::exception& ex) {
                BOOST_LOG_TRIVIAL(warning) << "SliceCheck: skipping "
                                           << vendor_name << "/" << f.filename().string()
                                           << " — " << ex.what();
            }
        }
    }
    BOOST_LOG_TRIVIAL(info) << "SliceCheck: loaded " << total << " check file(s) from all vendors";
}

// ---------------------------------------------------------------------------
// run_pre_checks / run_post_checks
// ---------------------------------------------------------------------------

void SliceCheckManager::run_pre_checks(wxWindow* parent)
{
    std::vector<SliceCheck> triggered;
    for (const auto& c : m_checks) {
        if (c.type != SliceCheckType::PRE)     continue;
        if (is_tag_muted(c.tag))               continue;
        if (c.condition_src.empty() || evaluate_condition(c.condition_src))
            triggered.push_back(c);
    }
    if (triggered.empty()) return;

    SliceCheckDialog dlg(parent, triggered);
    dlg.ShowModal();
}

void SliceCheckManager::run_post_checks(wxWindow* parent)
{
    std::vector<SliceCheck> triggered;
    for (const auto& c : m_checks) {
        if (c.type != SliceCheckType::POST)    continue;
        if (is_tag_muted(c.tag))               continue;
        if (c.condition_src.empty() || evaluate_condition(c.condition_src))
            triggered.push_back(c);
    }
    if (triggered.empty()) return;

    SliceCheckDialog dlg(parent, triggered);
    dlg.ShowModal();
}

// ---------------------------------------------------------------------------
// apply_actions
// ---------------------------------------------------------------------------

void SliceCheckManager::apply_actions(const std::vector<SliceCheckAction>& actions,
                                       const std::string& check_tag)
{
    for (const auto& action : actions) {
        if (action.suppress_tag) {
            set_tag_muted(check_tag, true);
            continue;
        }
        if (action.key.empty() || action.value_expr.empty()) continue;

        // Evaluate the formula to get the numeric result
        double result = 0.0;
        bool   is_string_value = (!action.value_expr.empty() && action.value_expr.front() == '"');

        std::string str_value;
        if (is_string_value) {
            // Strip surrounding quotes
            str_value = action.value_expr.substr(1, action.value_expr.size() - 2);
        } else {
            try { result = evaluate_formula(action.value_expr); }
            catch (const std::exception& ex) {
                BOOST_LOG_TRIVIAL(warning) << "SliceCheck: formula error for key "
                                           << action.key << ": " << ex.what();
                continue;
            }
        }

        // Find which preset contains this key and apply
        auto try_apply = [&](Preset::Type ptype) -> bool {
            Tab* tab = wxGetApp().get_tab(ptype);
            if (!tab || !tab->get_config()) return false;
            DynamicPrintConfig* cfg = tab->get_config();
            if (!cfg->has(action.key)) return false;

            const ConfigOptionDef* opt = cfg->def()->get(action.key);
            if (!opt) return false;

            boost::any val;
            if (is_string_value) {
                val = str_value;
            } else {
                // Cast to the right type
                switch (opt->type) {
                    case coInt:    val = (int)std::lround(result); break;
                    case coInts:   val = (int)std::lround(result); break;
                    case coFloat:  val = result;                   break;
                    case coFloats: val = result;                   break;
                    case coPercent:  val = result;                 break;
                    case coPercents: val = result;                 break;
                    case coFloatOrPercent: val = std::to_string(result); break;
                    default:
                        val = std::to_string(result);
                        break;
                }
            }

            change_opt_value(*cfg, action.key, val);
            tab->on_value_change(action.key, val);
            return true;
        };

        if (!try_apply(Preset::TYPE_FILAMENT) &&
            !try_apply(Preset::TYPE_PRINT) &&
            !try_apply(Preset::TYPE_PRINTER)) {
            BOOST_LOG_TRIVIAL(warning) << "SliceCheck: key not found in any preset: " << action.key;
        }
    }
}

// ===========================================================================
// Parsing
// ===========================================================================

// ---------------------------------------------------------------------------
// strip_comments: remove /* ... */ block comments and # inline comments
// ---------------------------------------------------------------------------

std::string SliceCheckManager::strip_comments(const std::string& src)
{
    std::string out;
    out.reserve(src.size());
    size_t i = 0;
    while (i < src.size()) {
        // Block comment
        if (i + 1 < src.size() && src[i] == '/' && src[i+1] == '*') {
            i += 2;
            while (i < src.size()) {
                if (i + 1 < src.size() && src[i] == '*' && src[i+1] == '/') {
                    i += 2;
                    break;
                }
                // Preserve newlines so line numbers stay meaningful
                if (src[i] == '\n') out += '\n';
                ++i;
            }
            continue;
        }
        // Inline comment
        if (src[i] == '#') {
            while (i < src.size() && src[i] != '\n')
                ++i;
            continue;
        }
        // Inside a quoted string — pass through verbatim
        if (src[i] == '"') {
            out += src[i++];
            while (i < src.size() && src[i] != '"') {
                if (src[i] == '\\' && i + 1 < src.size()) out += src[i++];
                out += src[i++];
            }
            if (i < src.size()) out += src[i++]; // closing "
            continue;
        }
        out += src[i++];
    }
    return out;
}

// ---------------------------------------------------------------------------
// parse_buttons_line: parse BUTTONS: ["a", "b", "c"]
// ---------------------------------------------------------------------------

std::vector<SliceCheckButton> SliceCheckManager::parse_buttons_line(const std::string& line)
{
    std::vector<SliceCheckButton> result;
    // Find the '[' ... ']' portion
    size_t start = line.find('[');
    size_t end   = line.rfind(']');
    if (start == std::string::npos || end == std::string::npos || end <= start)
        return result;

    std::string inner = line.substr(start + 1, end - start - 1);
    // Split by ',' respecting quoted strings
    std::vector<std::string> labels;
    std::string token;
    bool in_quote = false;
    for (char c : inner) {
        if (c == '"') { in_quote = !in_quote; }
        else if (c == ',' && !in_quote) {
            boost::trim(token);
            // strip surrounding quotes
            if (token.size() >= 2 && token.front() == '"' && token.back() == '"')
                token = token.substr(1, token.size() - 2);
            if (!token.empty()) labels.push_back(token);
            token.clear();
            continue;
        }
        if (!in_quote || c != '"') token += c; // accumulate non-quote chars inside
        else token += c;
    }
    boost::trim(token);
    if (token.size() >= 2 && token.front() == '"' && token.back() == '"')
        token = token.substr(1, token.size() - 2);
    if (!token.empty()) labels.push_back(token);

    for (auto& lbl : labels) {
        SliceCheckButton btn;
        btn.label = lbl;
        result.push_back(std::move(btn));
    }
    return result;
}

// ---------------------------------------------------------------------------
// parse_action_line: parse "SET key expr" or "SUPPRESS_TAG"
// ---------------------------------------------------------------------------

SliceCheckAction SliceCheckManager::parse_action_line(const std::string& line)
{
    SliceCheckAction action;
    std::string trimmed = boost::trim_copy(line);

    if (trimmed == "SUPPRESS_TAG") {
        action.suppress_tag = true;
        return action;
    }

    if (boost::istarts_with(trimmed, "SET ")) {
        std::string rest = boost::trim_copy(trimmed.substr(4));
        // rest = "key expr..."
        // key is everything up to the first space
        size_t space = rest.find(' ');
        if (space == std::string::npos) return action; // malformed
        action.key        = boost::trim_copy(rest.substr(0, space));
        action.value_expr = boost::trim_copy(rest.substr(space + 1));
    }
    return action;
}

// ---------------------------------------------------------------------------
// parse_file: parse a single .check file
// ---------------------------------------------------------------------------

SliceCheck SliceCheckManager::parse_file(const std::string& path)
{
    std::ifstream file(path);
    if (!file.is_open())
        throw std::runtime_error("cannot open file");

    std::string raw((std::istreambuf_iterator<char>(file)),
                     std::istreambuf_iterator<char>());
    std::string src = strip_comments(raw);

    SliceCheck check;
    check.file_path = path;
    check.icon      = "warning"; // default

    enum class Section { NONE, WHEN, BUTTONS, ON } section = Section::NONE;
    std::string current_on_label;
    std::string when_lines;

    auto find_button = [&](const std::string& label) -> SliceCheckButton* {
        for (auto& btn : check.buttons)
            if (btn.label == label) return &btn;
        return nullptr;
    };

    std::istringstream ss(src);
    std::string line;
    while (std::getline(ss, line)) {
        std::string trimmed = boost::trim_copy(line);
        if (trimmed.empty()) continue;

        // ---- Metadata fields (key: "value") ----
        // Only parsed when outside a section or when the line is a valid metadata key
        // (i.e. starts with a known keyword followed by ':')
        auto try_meta = [&](const std::string& key, std::string& field) -> bool {
            std::string prefix = key + ":";
            if (!boost::istarts_with(trimmed, prefix)) return false;
            std::string val = boost::trim_copy(trimmed.substr(prefix.size()));
            // strip surrounding quotes
            if (val.size() >= 2 && val.front() == '"' && val.back() == '"')
                val = val.substr(1, val.size() - 2);
            field = val;
            return true;
        };

        // ---- Section headers ----
        if (boost::istarts_with(trimmed, "WHEN:")) {
            section = Section::WHEN;
            continue;
        }
        if (boost::istarts_with(trimmed, "BUTTONS:")) {
            section = Section::BUTTONS;
            check.buttons = parse_buttons_line(trimmed);
            continue;
        }
        {
            // ON "label":
            if (boost::istarts_with(trimmed, "ON ") && trimmed.back() == ':') {
                section = Section::ON;
                // Extract label between first " and last "
                size_t q1 = trimmed.find('"');
                size_t q2 = trimmed.rfind('"');
                if (q1 != std::string::npos && q2 != q1) {
                    current_on_label = trimmed.substr(q1 + 1, q2 - q1 - 1);
                    // Ensure the button exists
                    if (!find_button(current_on_label)) {
                        SliceCheckButton btn;
                        btn.label = current_on_label;
                        check.buttons.push_back(std::move(btn));
                    }
                }
                continue;
            }
        }

        // ---- Metadata (only in NONE section context) ----
        if (section == Section::NONE || section == Section::BUTTONS) {
            if (try_meta("TITLE",   check.title))   { section = Section::NONE; continue; }
            if (try_meta("MESSAGE", check.message))  { section = Section::NONE; continue; }
            if (try_meta("ICON",    check.icon))     { section = Section::NONE; continue; }
            if (try_meta("TAG",     check.tag))      { section = Section::NONE; continue; }
            if (try_meta("TYPE",    [&]() -> std::string& {
                static std::string tmp;
                return tmp;
            }())) { /* handled below */ }
            // Handle TYPE: specially
            if (boost::istarts_with(trimmed, "TYPE:")) {
                std::string val = boost::trim_copy(trimmed.substr(5));
                boost::trim_if(val, [](char c){ return c == '"'; });
                boost::to_upper(val);
                check.type = (val == "POST") ? SliceCheckType::POST : SliceCheckType::PRE;
                section = Section::NONE;
                continue;
            }
        }

        // ---- Section body ----
        switch (section) {
            case Section::WHEN:
                when_lines += line + "\n";
                break;
            case Section::ON: {
                if (!current_on_label.empty()) {
                    SliceCheckButton* btn = find_button(current_on_label);
                    if (btn) {
                        SliceCheckAction action = parse_action_line(trimmed);
                        if (action.suppress_tag || !action.key.empty())
                            btn->actions.push_back(std::move(action));
                    }
                }
                break;
            }
            default:
                break;
        }
    }

    check.condition_src = boost::trim_copy(when_lines);

    // Validation
    if (check.title.empty())
        throw std::runtime_error("missing TITLE");
    if (check.message.empty())
        throw std::runtime_error("missing MESSAGE");
    if (check.tag.empty())
        throw std::runtime_error("missing TAG");
    if (cfg_key_for_tag(check.tag) == nullptr)
        throw std::runtime_error("unknown TAG: " + check.tag + " (must be filament/process/machine/safety/tips)");

    return check;
}

// ===========================================================================
// Condition evaluation
// ===========================================================================

namespace {

// Simple tokenizer for condition expressions
struct CondToken {
    enum Type {
        IDENT, NUMBER, STRING,
        LBRACKET, RBRACKET, LPAREN, RPAREN, COMMA,
        EQ, NEQ, LT, GT, LE, GE,
        AND_, OR_, NOT_,
        IN_, CONTAINS_, MATCHES_,
        ANY_, ALL_,
        END_
    } type;
    std::string str;
    double      num = 0.0;

    static std::string type_name(Type t) {
        switch (t) {
            case IDENT: return "IDENT"; case NUMBER: return "NUMBER";
            case STRING: return "STRING"; case END_: return "END";
            default: return "TOKEN";
        }
    }
};

struct CondLexer {
    const std::string& src;
    size_t pos = 0;
    std::vector<CondToken> tokens;
    size_t idx = 0;

    explicit CondLexer(const std::string& s) : src(s) { tokenize(); }

    void tokenize() {
        while (pos < src.size()) {
            char c = src[pos];
            if (std::isspace(c)) { ++pos; continue; }
            if (c == '[') { tokens.push_back({CondToken::LBRACKET}); ++pos; continue; }
            if (c == ']') { tokens.push_back({CondToken::RBRACKET}); ++pos; continue; }
            if (c == '(') { tokens.push_back({CondToken::LPAREN}); ++pos; continue; }
            if (c == ')') { tokens.push_back({CondToken::RPAREN}); ++pos; continue; }
            if (c == ',') { tokens.push_back({CondToken::COMMA}); ++pos; continue; }
            if (c == '=' && pos+1 < src.size() && src[pos+1] == '=') { tokens.push_back({CondToken::EQ}); pos+=2; continue; }
            if (c == '!' && pos+1 < src.size() && src[pos+1] == '=') { tokens.push_back({CondToken::NEQ}); pos+=2; continue; }
            if (c == '<' && pos+1 < src.size() && src[pos+1] == '=') { tokens.push_back({CondToken::LE}); pos+=2; continue; }
            if (c == '>' && pos+1 < src.size() && src[pos+1] == '=') { tokens.push_back({CondToken::GE}); pos+=2; continue; }
            if (c == '<') { tokens.push_back({CondToken::LT}); ++pos; continue; }
            if (c == '>') { tokens.push_back({CondToken::GT}); ++pos; continue; }
            if (c == '"') {
                ++pos;
                std::string s;
                while (pos < src.size() && src[pos] != '"') {
                    if (src[pos] == '\\' && pos+1 < src.size()) ++pos;
                    s += src[pos++];
                }
                if (pos < src.size()) ++pos;
                tokens.push_back({CondToken::STRING, s});
                continue;
            }
            if (std::isdigit(c) || (c == '-' && pos+1 < src.size() && std::isdigit(src[pos+1]))) {
                size_t start = pos;
                if (c == '-') ++pos;
                while (pos < src.size() && (std::isdigit(src[pos]) || src[pos] == '.')) ++pos;
                std::string ns = src.substr(start, pos - start);
                CondToken t; t.type = CondToken::NUMBER; t.str = ns; t.num = std::stod(ns);
                tokens.push_back(t);
                continue;
            }
            if (std::isalpha(c) || c == '_') {
                size_t start = pos;
                while (pos < src.size() && (std::isalnum(src[pos]) || src[pos] == '_')) ++pos;
                std::string word = src.substr(start, pos - start);
                std::string upper = word;
                boost::to_upper(upper);
                CondToken t;
                if (upper == "AND")      t.type = CondToken::AND_;
                else if (upper == "OR")  t.type = CondToken::OR_;
                else if (upper == "NOT") t.type = CondToken::NOT_;
                else if (upper == "IN")  t.type = CondToken::IN_;
                else if (upper == "CONTAINS") t.type = CondToken::CONTAINS_;
                else if (upper == "MATCHES")  t.type = CondToken::MATCHES_;
                else if (upper == "ANY")      t.type = CondToken::ANY_;
                else if (upper == "ALL")      t.type = CondToken::ALL_;
                else                          t.type = CondToken::IDENT;
                t.str = word;
                tokens.push_back(t);
                continue;
            }
            ++pos; // skip unknown
        }
        tokens.push_back({CondToken::END_});
    }

    CondToken& peek() { return tokens[idx]; }
    CondToken  consume() { return tokens[idx++]; }
    bool at_end() { return tokens[idx].type == CondToken::END_; }
};

// Simple glob match: * matches any substring, ? matches any single character
bool glob_match(const std::string& pattern, const std::string& text)
{
    size_t p = 0, t = 0;
    size_t star_p = std::string::npos, star_t = 0;
    while (t < text.size()) {
        if (p < pattern.size() && (pattern[p] == '?' || pattern[p] == text[t])) {
            ++p; ++t;
        } else if (p < pattern.size() && pattern[p] == '*') {
            star_p = p++; star_t = t;
        } else if (star_p != std::string::npos) {
            p = star_p + 1; t = ++star_t;
        } else {
            return false;
        }
    }
    while (p < pattern.size() && pattern[p] == '*') ++p;
    return p == pattern.size();
}

struct CondParser {
    CondLexer& lex;
    const DynamicPrintConfig& cfg;
    int num_extruders;

    explicit CondParser(CondLexer& l, const DynamicPrintConfig& c, int n)
        : lex(l), cfg(c), num_extruders(n) {}

    // Get string values for a key with optional [N], [ANY], [ALL] subscript
    // Returns a vector of strings to test against
    struct KeyAccess {
        std::string key;
        enum class Mode { SINGLE, INDEX, ANY, ALL } mode = Mode::SINGLE;
        int index = 0;
    };

    KeyAccess parse_key_access() {
        KeyAccess ka;
        ka.key = lex.consume().str; // IDENT
        if (lex.peek().type == CondToken::LBRACKET) {
            lex.consume(); // [
            auto& next = lex.peek();
            if (next.type == CondToken::NUMBER) {
                ka.mode = KeyAccess::Mode::INDEX;
                ka.index = (int)next.num;
                lex.consume();
            } else if (next.type == CondToken::ANY_) {
                ka.mode = KeyAccess::Mode::ANY;
                lex.consume();
            } else if (next.type == CondToken::ALL_) {
                ka.mode = KeyAccess::Mode::ALL;
                lex.consume();
            }
            if (lex.peek().type == CondToken::RBRACKET) lex.consume();
        }
        return ka;
    }

    std::vector<std::string> get_string_values(const KeyAccess& ka) {
        std::vector<std::string> result;
        const ConfigOption* opt = cfg.optptr(ka.key);
        if (!opt) return result;

        auto get_at = [&](int i) -> std::string {
            if (auto* sv = dynamic_cast<const ConfigOptionStrings*>(opt))
                return i < (int)sv->values.size() ? sv->values[i] : "";
            if (auto* sv = dynamic_cast<const ConfigOptionFloats*>(opt))
                return i < (int)sv->values.size() ? std::to_string(sv->values[i]) : "";
            if (auto* sv = dynamic_cast<const ConfigOptionInts*>(opt))
                return i < (int)sv->values.size() ? std::to_string(sv->values[i]) : "";
            return "";
        };

        int n = std::max(1, num_extruders);
        switch (ka.mode) {
            case KeyAccess::Mode::SINGLE: {
                // For scalar types, convert to string
                if (auto* sv = dynamic_cast<const ConfigOptionString*>(opt))
                    result.push_back(sv->value);
                else if (auto* sv = dynamic_cast<const ConfigOptionFloat*>(opt))
                    result.push_back(std::to_string(sv->value));
                else if (auto* sv = dynamic_cast<const ConfigOptionInt*>(opt))
                    result.push_back(std::to_string(sv->value));
                else if (auto* sv = dynamic_cast<const ConfigOptionBool*>(opt))
                    result.push_back(sv->value ? "true" : "false");
                else
                    result.push_back(get_at(0));
                break;
            }
            case KeyAccess::Mode::INDEX:
                result.push_back(get_at(ka.index));
                break;
            case KeyAccess::Mode::ANY:
            case KeyAccess::Mode::ALL:
                for (int i = 0; i < n; ++i)
                    result.push_back(get_at(i));
                break;
        }
        return result;
    }

    double get_numeric_value(const std::string& key) {
        const ConfigOption* opt = cfg.optptr(key);
        if (!opt) return 0.0;
        if (auto* v = dynamic_cast<const ConfigOptionFloat*>(opt))  return v->value;
        if (auto* v = dynamic_cast<const ConfigOptionInt*>(opt))    return (double)v->value;
        if (auto* v = dynamic_cast<const ConfigOptionPercent*>(opt)) return v->value;
        if (auto* v = dynamic_cast<const ConfigOptionFloats*>(opt))
            return v->values.empty() ? 0.0 : v->values[0];
        if (auto* v = dynamic_cast<const ConfigOptionInts*>(opt))
            return v->values.empty() ? 0.0 : (double)v->values[0];
        return 0.0;
    }

    // Parse a string list ["a", "b", ...]
    std::vector<std::string> parse_string_list() {
        std::vector<std::string> list;
        if (lex.peek().type != CondToken::LBRACKET) return list;
        lex.consume(); // [
        while (lex.peek().type != CondToken::RBRACKET && !lex.at_end()) {
            if (lex.peek().type == CondToken::STRING)
                list.push_back(lex.consume().str);
            else
                lex.consume(); // skip unexpected
            if (lex.peek().type == CondToken::COMMA) lex.consume();
        }
        if (lex.peek().type == CondToken::RBRACKET) lex.consume();
        return list;
    }

    // atom = NOT atom | ( expr ) | comparison
    bool parse_atom() {
        if (lex.peek().type == CondToken::NOT_) {
            lex.consume();
            return !parse_atom();
        }
        if (lex.peek().type == CondToken::LPAREN) {
            lex.consume();
            bool result = parse_expr();
            if (lex.peek().type == CondToken::RPAREN) lex.consume();
            return result;
        }
        return parse_comparison();
    }

    bool parse_comparison() {
        if (lex.peek().type != CondToken::IDENT) return false;
        KeyAccess ka = parse_key_access();

        auto& op = lex.peek();

        // IN or NOT IN  → string set comparison
        bool negated = false;
        if (op.type == CondToken::NOT_) {
            lex.consume();
            if (lex.peek().type == CondToken::IN_) {
                lex.consume();
                negated = true;
            } else return false;
        }
        if (op.type == CondToken::IN_ || negated) {
            if (!negated) lex.consume(); // consume IN
            auto list = parse_string_list();
            auto values = get_string_values(ka);
            bool any_match = false, all_match = true;
            for (auto& v : values) {
                bool found = std::find(list.begin(), list.end(), v) != list.end();
                if (found) any_match = true;
                if (!found) all_match = false;
            }
            bool result;
            if (ka.mode == KeyAccess::Mode::ALL) result = all_match;
            else                                  result = any_match;
            return negated ? !result : result;
        }

        // CONTAINS
        if (op.type == CondToken::CONTAINS_) {
            lex.consume();
            std::string substr = (lex.peek().type == CondToken::STRING) ? lex.consume().str : "";
            auto values = get_string_values(ka);
            for (auto& v : values)
                if (v.find(substr) != std::string::npos) return true;
            return false;
        }

        // MATCHES (glob)
        if (op.type == CondToken::MATCHES_) {
            lex.consume();
            std::string pattern = (lex.peek().type == CondToken::STRING) ? lex.consume().str : "";
            auto values = get_string_values(ka);
            for (auto& v : values)
                if (glob_match(pattern, v)) return true;
            return false;
        }

        // Numeric comparisons: ==, !=, <, >, <=, >=
        if (op.type == CondToken::EQ  || op.type == CondToken::NEQ ||
            op.type == CondToken::LT  || op.type == CondToken::GT  ||
            op.type == CondToken::LE  || op.type == CondToken::GE) {
            auto op_type = op.type;
            lex.consume();

            // RHS can be a string or number
            if (lex.peek().type == CondToken::STRING) {
                std::string rhs = lex.consume().str;
                auto values = get_string_values(ka);
                bool any_eq = false;
                for (auto& v : values) {
                    if (op_type == CondToken::EQ  && v == rhs) { any_eq = true; break; }
                    if (op_type == CondToken::NEQ && v != rhs) { any_eq = true; break; }
                }
                return any_eq;
            } else if (lex.peek().type == CondToken::NUMBER) {
                double rhs = lex.consume().num;
                double lhs = get_numeric_value(ka.key);
                switch (op_type) {
                    case CondToken::EQ:  return lhs == rhs;
                    case CondToken::NEQ: return lhs != rhs;
                    case CondToken::LT:  return lhs < rhs;
                    case CondToken::GT:  return lhs > rhs;
                    case CondToken::LE:  return lhs <= rhs;
                    case CondToken::GE:  return lhs >= rhs;
                    default: return false;
                }
            }
        }
        return false;
    }

    // term = atom (AND atom)*
    bool parse_term() {
        bool result = parse_atom();
        while (lex.peek().type == CondToken::AND_) {
            lex.consume();
            bool rhs = parse_atom();
            result = result && rhs;
        }
        return result;
    }

    // expr = term (OR term)*
    bool parse_expr() {
        bool result = parse_term();
        while (lex.peek().type == CondToken::OR_) {
            lex.consume();
            bool rhs = parse_term();
            result = result || rhs;
        }
        return result;
    }
};

} // anonymous namespace

bool SliceCheckManager::evaluate_condition(const std::string& expr) const
{
    const DynamicPrintConfig& cfg = wxGetApp().preset_bundle->full_config();
    int num_extruders = (int)wxGetApp().preset_bundle->filament_presets.size();

    try {
        CondLexer lexer(expr);
        CondParser parser(lexer, cfg, num_extruders);
        return parser.parse_expr();
    } catch (const std::exception& ex) {
        BOOST_LOG_TRIVIAL(warning) << "SliceCheck: condition eval error: " << ex.what()
                                   << " expr: " << expr;
        return false; // don't trigger on error
    }
}

// ===========================================================================
// Formula evaluation (for SET value expressions)
// ===========================================================================

namespace {

struct FormulaToken {
    enum Type { NUMBER, IDENT, PLUS, MINUS, STAR, SLASH, LPAREN, RPAREN, COMMA, END_ } type;
    std::string str;
    double num = 0.0;
};

struct FormulaLexer {
    const std::string& src;
    size_t pos = 0;
    std::vector<FormulaToken> tokens;
    size_t idx = 0;

    explicit FormulaLexer(const std::string& s) : src(s) { tokenize(); }

    void tokenize() {
        while (pos < src.size()) {
            char c = src[pos];
            if (std::isspace(c)) { ++pos; continue; }
            if (c == '+') { tokens.push_back({FormulaToken::PLUS}); ++pos; continue; }
            if (c == '*') { tokens.push_back({FormulaToken::STAR}); ++pos; continue; }
            if (c == '/') { tokens.push_back({FormulaToken::SLASH}); ++pos; continue; }
            if (c == '(') { tokens.push_back({FormulaToken::LPAREN}); ++pos; continue; }
            if (c == ')') { tokens.push_back({FormulaToken::RPAREN}); ++pos; continue; }
            if (c == ',') { tokens.push_back({FormulaToken::COMMA}); ++pos; continue; }
            if (c == '-') {
                // Unary minus or binary minus — peek ahead
                tokens.push_back({FormulaToken::MINUS}); ++pos; continue;
            }
            if (std::isdigit(c) || (c == '.' && pos+1 < src.size() && std::isdigit(src[pos+1]))) {
                size_t start = pos;
                while (pos < src.size() && (std::isdigit(src[pos]) || src[pos] == '.')) ++pos;
                std::string ns = src.substr(start, pos - start);
                FormulaToken t; t.type = FormulaToken::NUMBER; t.str = ns; t.num = std::stod(ns);
                tokens.push_back(t);
                continue;
            }
            if (std::isalpha(c) || c == '_') {
                size_t start = pos;
                while (pos < src.size() && (std::isalnum(src[pos]) || src[pos] == '_')) ++pos;
                std::string word = src.substr(start, pos - start);
                FormulaToken t; t.type = FormulaToken::IDENT; t.str = word;
                tokens.push_back(t);
                continue;
            }
            ++pos;
        }
        tokens.push_back({FormulaToken::END_});
    }

    FormulaToken& peek() { return tokens[idx]; }
    FormulaToken consume() { return tokens[idx++]; }
};

struct FormulaParser {
    FormulaLexer& lex;
    const DynamicPrintConfig& cfg;

    FormulaParser(FormulaLexer& l, const DynamicPrintConfig& c) : lex(l), cfg(c) {}

    double get_config_value(const std::string& key) {
        const ConfigOption* opt = cfg.optptr(key);
        if (!opt) return 0.0;
        if (auto* v = dynamic_cast<const ConfigOptionFloat*>(opt))  return v->value;
        if (auto* v = dynamic_cast<const ConfigOptionInt*>(opt))    return (double)v->value;
        if (auto* v = dynamic_cast<const ConfigOptionPercent*>(opt)) return v->value;
        if (auto* v = dynamic_cast<const ConfigOptionFloats*>(opt))
            return v->values.empty() ? 0.0 : v->values[0];
        if (auto* v = dynamic_cast<const ConfigOptionInts*>(opt))
            return v->values.empty() ? 0.0 : (double)v->values[0];
        return 0.0;
    }

    double parse_factor() {
        auto& t = lex.peek();
        if (t.type == FormulaToken::MINUS) {
            lex.consume();
            return -parse_factor();
        }
        if (t.type == FormulaToken::NUMBER) {
            return lex.consume().num;
        }
        if (t.type == FormulaToken::LPAREN) {
            lex.consume();
            double val = parse_expr();
            if (lex.peek().type == FormulaToken::RPAREN) lex.consume();
            return val;
        }
        if (t.type == FormulaToken::IDENT) {
            std::string name = lex.consume().str;
            std::string upper = name; boost::to_upper(upper);
            // Functions: MAX(a, b) and MIN(a, b)
            if ((upper == "MAX" || upper == "MIN") && lex.peek().type == FormulaToken::LPAREN) {
                lex.consume(); // (
                double a = parse_expr();
                if (lex.peek().type == FormulaToken::COMMA) lex.consume();
                double b = parse_expr();
                if (lex.peek().type == FormulaToken::RPAREN) lex.consume();
                return (upper == "MAX") ? std::max(a, b) : std::min(a, b);
            }
            // Config key reference
            return get_config_value(name);
        }
        return 0.0;
    }

    double parse_term() {
        double result = parse_factor();
        while (lex.peek().type == FormulaToken::STAR || lex.peek().type == FormulaToken::SLASH) {
            auto op = lex.consume().type;
            double rhs = parse_factor();
            if (op == FormulaToken::STAR) result *= rhs;
            else if (rhs != 0.0)         result /= rhs;
        }
        return result;
    }

    double parse_expr() {
        double result = parse_term();
        while (lex.peek().type == FormulaToken::PLUS || lex.peek().type == FormulaToken::MINUS) {
            auto op = lex.consume().type;
            double rhs = parse_term();
            if (op == FormulaToken::PLUS) result += rhs;
            else                          result -= rhs;
        }
        return result;
    }
};

} // anonymous namespace

double SliceCheckManager::evaluate_formula(const std::string& expr)
{
    const DynamicPrintConfig& cfg = wxGetApp().preset_bundle->full_config();
    FormulaLexer  lexer(expr);
    FormulaParser parser(lexer, cfg);
    return parser.parse_expr();
}

}} // namespace Slic3r::GUI
