#!/usr/bin/env node
// Find which new msgids aren't matched by the simple single-line regex
const fs = require('fs');
const path = require('path');

const I18N_DIR = path.join(__dirname, '..', 'localization', 'i18n');
const msgids = JSON.parse(fs.readFileSync(path.join(I18N_DIR, 'new_msgids.json'), 'utf8'));
const po = fs.readFileSync(path.join(I18N_DIR, 'de', 'OrcaSlicer_de.po'), 'utf8');

const simpleRegex = /^(msgid "([^"]*)")\r?\n(msgstr "")$/gm;

// Collect all simple-matched msgids
const simpleMatched = new Set();
let m;
while ((m = simpleRegex.exec(po)) !== null) {
  simpleMatched.add(m[2]);
}

console.log('Simple-matched (in file):', simpleMatched.size);

const missing = msgids.filter(id => !simpleMatched.has(id));
console.log('\nStrings not matched by simple regex:', missing.length);
missing.forEach(s => console.log(' -', JSON.stringify(s)));
