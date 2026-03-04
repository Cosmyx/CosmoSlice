#!/usr/bin/env node
/**
 * Recover translations for newly added empty msgstr entries in PO files.
 *
 * Strategy:
 * 1. Parse PO file to find empty msgstr entries
 * 2. Build a map of obsolete (#~) translations from the same file
 * 3. Fill in msgstr where a matching obsolete translation exists
 * 4. Report which strings still need translation
 */

const fs = require('fs');
const path = require('path');

const I18N_DIR = path.join(__dirname, '..', 'localization', 'i18n');

/**
 * Parse a PO file into sections:
 * - entries: array of {msgid, msgid_plural, msgstr, msgstr_plural, raw, start, end}
 * - obsolete: map of msgid -> msgstr (from #~ entries)
 */
function parsePo(content) {
  const lines = content.split('\n');
  const entries = [];
  const obsolete = new Map();

  let i = 0;

  // Parse obsolete entries first (from #~ blocks)
  const obsoleteBlocks = [];
  let inObsolete = false;
  let obsBlock = [];

  for (let li = 0; li < lines.length; li++) {
    const line = lines[li];
    if (line.startsWith('#~ ') || line.startsWith('#~\n') || line === '#~') {
      inObsolete = true;
      obsBlock.push(line);
    } else if (inObsolete && line.trim() === '') {
      if (obsBlock.length > 0) {
        obsoleteBlocks.push(obsBlock.join('\n'));
        obsBlock = [];
      }
      inObsolete = false;
    } else if (inObsolete) {
      obsBlock.push(line);
    }
  }
  if (obsBlock.length > 0) obsoleteBlocks.push(obsBlock.join('\n'));

  // Extract msgid -> msgstr from obsolete blocks
  for (const block of obsoleteBlocks) {
    const msgidMatch = block.match(/#~ msgid "((?:[^"\\]|\\.)*)"/);
    const msgstrMatch = block.match(/#~ msgstr "((?:[^"\\]|\\.)*)"/);
    if (msgidMatch && msgstrMatch && msgstrMatch[1]) {
      obsolete.set(msgidMatch[1], msgstrMatch[1]);
    }
    // Handle multiline obsolete msgid
    const multiMsgid = block.match(/#~ msgid ""\n((?:#~ ".*"\n?)*)/);
    const multiMsgstr = block.match(/#~ msgstr ""\n((?:#~ ".*"\n?)*)/);
    if (multiMsgid && multiMsgstr) {
      const id = multiMsgid[1].replace(/#~ "/g, '').replace(/"\n?/g, '\n').trim();
      const str = multiMsgstr[1].replace(/#~ "/g, '').replace(/"\n?/g, '\n').trim();
      if (str) obsolete.set(id, str);
    }
  }

  return { obsolete };
}

/**
 * Find all empty msgstr entries in a PO file and recover from obsolete if possible.
 * Returns the modified content and a list of still-missing strings.
 */
function recoverTranslations(content, lang) {
  const { obsolete } = parsePo(content);

  let recovered = 0;
  let stillMissing = [];

  // Find all msgid + empty msgstr pairs and try to fill them
  // We process the content as text to preserve formatting
  const result = content.replace(
    /^(msgid "([^"]*)")\n(msgstr "")$/gm,
    (match, msgidLine, msgid, emptyMsgstr) => {
      if (msgid === '') return match; // skip header
      if (obsolete.has(msgid)) {
        recovered++;
        return `${msgidLine}\nmsgstr "${obsolete.get(msgid)}"`;
      }
      stillMissing.push(msgid);
      return match;
    }
  );

  return { content: result, recovered, stillMissing };
}

// Get newly added msgids from the diff (stored separately)
function getNewMsgids() {
  // Read from the diff we extracted
  const diffFile = path.join('/tmp', 'new_msgids_clean.json');
  if (fs.existsSync(diffFile)) {
    return JSON.parse(fs.readFileSync(diffFile, 'utf8'));
  }
  return null;
}

// Main: process all language files
const langs = ['ca', 'cs', 'de', 'en', 'es', 'fr', 'hu', 'it', 'ja', 'ko', 'lt', 'nl', 'pl', 'pt_BR', 'ru', 'sv', 'tr', 'uk', 'zh_CN', 'zh_TW'];

const report = {};

for (const lang of langs) {
  const poFile = path.join(I18N_DIR, lang, `OrcaSlicer_${lang}.po`);
  if (!fs.existsSync(poFile)) {
    console.log(`Skipping ${lang}: file not found`);
    continue;
  }

  const content = fs.readFileSync(poFile, 'utf8');
  const { content: newContent, recovered, stillMissing } = recoverTranslations(content, lang);

  if (recovered > 0) {
    fs.writeFileSync(poFile, newContent, 'utf8');
    console.log(`${lang}: recovered ${recovered} translations from obsolete entries`);
  } else {
    console.log(`${lang}: no recoverable obsolete translations found`);
  }

  report[lang] = { recovered, stillMissingCount: stillMissing.length };
}

console.log('\n=== Summary ===');
for (const [lang, info] of Object.entries(report)) {
  console.log(`${lang}: ${info.recovered} recovered, ${info.stillMissingCount} still need translation`);
}
