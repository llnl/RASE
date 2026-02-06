# RASE Documentation Style Guide

This minimal guide defines audience, voice, grammar, and language guidelines for the RASE user manual written in reStructuredText (Sphinx).

## Audience

- Primary: Users familiar with the RASE domain interested in learning to use RASE for their work.
- Secondary: Expert users interested in using RASE advanced features.

## Voice and Tone

- Use second person and imperative mood: “Click Run”, “Select the file…”.
- Prefer active voice over passive: “RASE saves the file” not “The file is saved by RASE”.
- Be concise, task‑focused, and neutral. Avoid marketing language.
- Be helpful and empathetic; anticipate user questions and next steps.
- Use present tense for behavior, future tense only when strictly necessary.

## Grammar and Mechanics

- Language: US English.
- Consistency: Use the Oxford comma; avoid contractions (use “do not” instead of “don’t”).
- Numbers: Use numerals for 10 and above; words for zero–nine, unless paired with units, measurements, steps, or UI elements (e.g., “3 files”).
- Units: Use SI units and a non‑breaking space between number and unit where possible (e.g., “10 MB”, “5 s”). Do not pluralize symbols (write “10 MB”, not “10 MBs”).
- Capitalization: Sentence case for headings. Capitalize proper nouns and official UI labels exactly as they appear in the product.
- Punctuation: Keep sentences short (ideally under 25–30 words). Avoid exclamation marks.
- Lists: Use numbered lists for ordered procedures; bulleted lists for unordered items. Each step begins with an action verb.
- Code and literals: Use monospace for commands, file paths, config keys, and inline code.

## Language Guidelines

- Clarity: Prefer specific, concrete words over vague terms. Replace “simply”, “just”, “obviously”, and similar with explicit instructions.
- Jargon: Define specialized terms on first use; provide cross‑references if the term is explained elsewhere.
- Error messages: Quote the exact on‑screen text and provide likely causes and actionable fixes.
- UI references: Match on‑screen capitalization. Reference elements consistently.
- Screenshots: Use them to support text, not replace it. Ensure the text stands alone.

## reStructuredText Conventions (Sphinx)

- Roles for clarity:
  - `:guilabel:` for buttons and labels, e.g., ``:guilabel:`Run```.
  - `:menuselection:` for menu paths, e.g., ``:menuselection:`File → Open…```.
  - `:kbd:` for keys/shortcuts, e.g., ``:kbd:`Ctrl` + :kbd:`S```.
  - `:command:` for CLI commands, e.g., ``:command:`rase --version```.
  - `:file:` for paths and filenames, e.g., ``:file:`~/.rase/config.yaml```.
- Admonitions: Use `.. note::`, `.. tip::`, `.. warning::`, and `.. caution::` for important callouts. Keep them brief and actionable.
- Line breaks: Prefer one sentence per line in source for easier reviews and diffs.
- Cross‑refs: Use Sphinx references (e.g., ``:ref:`concept-id```), not raw URLs, where possible.

## Examples

- Procedure step: “Click :guilabel:`Run`, then select the input :file:`config.yaml`.”
- Menu path: “Go to :menuselection:`File → Preferences` and enable :guilabel:`Auto‑save`.”
- Error help: “If you see ‘Failed to load profile’, check that :file:`~/.rase/` exists and that you have read permissions.”

## Out of Scope

This guide covers writing style only. Image production, UI design, and build/CI details are handled separately.

