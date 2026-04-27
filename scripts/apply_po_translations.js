#!/usr/bin/env node
/**
 * Apply translations from JSON files to PO files.
 *
 * Reads translation JSON files produced by the translation agents and
 * patches the corresponding PO files by filling in empty msgstr entries
 * for msgids that appear in the translation maps.
 *
 * Usage: node scripts/apply_po_translations.js
 */

const fs = require('fs');
const path = require('path');

const I18N_DIR = path.join(__dirname, '..', 'localization', 'i18n');

// Translation JSON files and the languages they contain.
// Grouped files (produced by the germanic/other_eu/east_asian agents) have
// multiple lang keys; per-language files have a single key.
const TRANSLATION_FILES = [
  // Germanic (grouped file)
  { file: 'translations_germanic.json',  langs: ['de', 'nl', 'sv'] },
  // Other EU — individual files (the grouped file had JSON issues)
  { file: 'translations_hu.json',   langs: ['hu'] },
  { file: 'translations_lt.json',   langs: ['lt'] },
  { file: 'translations_tr.json',   langs: ['tr'] },
  // East Asian — individual files (the grouped file had JSON issues)
  { file: 'translations_ja.json',    langs: ['ja'] },
  { file: 'translations_ko.json',    langs: ['ko'] },
  { file: 'translations_zh_CN.json', langs: ['zh_CN'] },
  { file: 'translations_zh_TW.json', langs: ['zh_TW'] },
  // Romance — individual per-language files
  { file: 'translations_es.json',    langs: ['es'] },
  { file: 'translations_fr.json',    langs: ['fr'] },
  { file: 'translations_it.json',    langs: ['it'] },
  { file: 'translations_pt_BR.json', langs: ['pt_BR'] },
  { file: 'translations_ca.json',    langs: ['ca'] },
  // Slavic — individual per-language files
  { file: 'translations_cs.json',    langs: ['cs'] },
  { file: 'translations_pl.json',    langs: ['pl'] },
  { file: 'translations_ru.json',    langs: ['ru'] },
  { file: 'translations_uk.json',    langs: ['uk'] },
];

// Load all translation maps: { lang -> { msgid -> msgstr } }
const allTranslations = {};

for (const { file, langs } of TRANSLATION_FILES) {
  const filePath = path.join(I18N_DIR, file);
  if (!fs.existsSync(filePath)) {
    console.warn(`WARNING: Missing translation file: ${file}`);
    continue;
  }

  let data;
  try {
    data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (e) {
    console.error(`ERROR: Failed to parse ${file}: ${e.message}`);
    continue;
  }

  for (const lang of langs) {
    if (!data[lang]) {
      console.warn(`WARNING: Language '${lang}' missing from ${file}`);
      continue;
    }
    allTranslations[lang] = data[lang];
    console.log(`Loaded ${Object.keys(data[lang]).length} translations for ${lang}`);
  }
}

/**
 * Escape a msgstr value for PO file format.
 * The translation JSON stores strings with \n as literal \n (escaped newline),
 * and \" as literal \" (escaped quote). These are already in PO-ready form.
 */
function escapeMsgstr(str) {
  // The strings from the JSON already use PO-style escaping for \n and \"
  // We just need to make sure the string is safe for a double-quoted PO value
  return str;
}

/**
 * Decode a PO string value into a plain key for map lookup.
 * PO stores escaped sequences like \" and \n literally within double-quoted strings.
 * We need the raw key exactly as it appears in the translation map.
 */
function decodePOString(raw) {
  // raw is everything between the outer double-quotes on a single line,
  // or concatenated from multiline segments. Keep as-is since the
  // translation map keys were extracted the same way.
  return raw;
}

/**
 * Apply translations to a single PO file.
 * Handles single-line msgids, msgids with \" inside, and multiline msgids.
 * Only fills in entries where msgstr is currently empty.
 */
function applyTranslationsToPo(poContent, translations) {
  let applied = 0;
  let skipped = 0;
  let notFound = 0;

  // Detect line ending style
  const lineEnding = poContent.includes('\r\n') ? '\r\n' : '\n';

  // ── Pass 1: Single-line msgid (including those with \" inside) ──
  // Pattern: msgid "..." where ... can contain escaped sequences
  let result = poContent.replace(
    /^(msgid "((?:[^"\\]|\\.)*)")\r?\n(msgstr "")$/gm,
    (match, msgidLine, msgid) => {
      if (msgid === '') return match; // skip multiline starters

      if (translations[msgid] !== undefined && translations[msgid] !== '') {
        applied++;
        return `${msgidLine}${lineEnding}msgstr "${escapeMsgstr(translations[msgid])}"`;
      } else if (translations[msgid] === '') {
        skipped++;
        return match;
      } else {
        notFound++;
        return match;
      }
    }
  );

  // ── Pass 2: Multiline msgid (msgid ""\n"part1\n"\n"part2" etc.) ──
  // Match the whole block: msgid "" followed by "..." lines, then empty msgstr
  result = result.replace(
    /^(msgid ""\r?\n(?:"[^"]*"\r?\n)+)(msgstr "")$/gm,
    (match, msgidBlock, emptyMsgstr) => {
      // Reconstruct the msgid key by concatenating the content of all "..." lines
      const parts = [];
      const lineRe = /"([^"]*)"/g;
      // Skip the first empty "" — start extracting from the continuation lines
      const continuationLines = msgidBlock.replace(/^msgid ""\r?\n/, '');
      let m2;
      while ((m2 = lineRe.exec(continuationLines)) !== null) {
        parts.push(m2[1]);
      }
      const msgid = parts.join('');

      if (translations[msgid] !== undefined && translations[msgid] !== '') {
        applied++;
        return `${msgidBlock}msgstr "${escapeMsgstr(translations[msgid])}"`;
      } else if (translations[msgid] === '') {
        skipped++;
        return match;
      } else {
        notFound++;
        return match;
      }
    }
  );

  // ── Pass 3: Plural form entries (msgid + msgid_plural + msgstr[0]/[1]) ──
  // Pattern: single-line msgid, msgid_plural, then empty msgstr[0] and msgstr[1]
  result = result.replace(
    /^(msgid "((?:[^"\\]|\\.)*)")\r?\n(msgid_plural "((?:[^"\\]|\\.)*)")\r?\n(msgstr\[0\] "")\r?\n(msgstr\[1\] "")$/gm,
    (match, msgidLine, singular, msgidPluralLine, plural) => {
      const singularTrans = translations[singular];
      const pluralTrans = translations[plural];

      if (!singularTrans && !pluralTrans) {
        notFound++;
        return match;
      }

      applied++;
      const s0 = singularTrans || singularTrans;
      const s1 = pluralTrans || singularTrans; // fallback plural to singular if no plural translation
      const le = lineEnding;
      return `${msgidLine}${le}${msgidPluralLine}${le}msgstr[0] "${escapeMsgstr(s0)}"${le}msgstr[1] "${escapeMsgstr(s1)}"`;
    }
  );

  return { content: result, applied, skipped, notFound };
}

// Process each language
const stats = {};
let totalApplied = 0;

for (const [lang, translations] of Object.entries(allTranslations)) {
  const poFile = path.join(I18N_DIR, lang, `OrcaSlicer_${lang}.po`);

  if (!fs.existsSync(poFile)) {
    console.warn(`WARNING: PO file not found for ${lang}: ${poFile}`);
    continue;
  }

  const content = fs.readFileSync(poFile, 'utf8');
  const { content: newContent, applied, skipped, notFound } = applyTranslationsToPo(content, translations);

  if (applied > 0) {
    fs.writeFileSync(poFile, newContent, 'utf8');
    console.log(`${lang}: applied ${applied} translations (${notFound} msgids not in translation set)`);
    totalApplied += applied;
  } else {
    console.log(`${lang}: no translations applied (${notFound} not in set, ${skipped} blank)`);
  }

  stats[lang] = { applied, skipped, notFound };
}

console.log('\n=== Summary ===');
console.log(`Total translations applied: ${totalApplied}`);
for (const [lang, s] of Object.entries(stats)) {
  if (s.applied > 0) {
    console.log(`  ${lang}: +${s.applied}`);
  }
}

// Also handle English: msgstr = msgid (English is source language, leave empty)
console.log('\nNote: English (en) PO file left unchanged — English uses empty msgstr as it is the source language.');
