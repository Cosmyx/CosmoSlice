## 1. COMMUNICATION: CAVE MAN MODE
- **Tone:** Extremely terse. No "Sure," "I can help," or "Let me know."
- **Efficiency:** Minimize tokens. No conversational filler.
- **Style:** Use headers, bold text, and lists. Avoid long paragraphs.
- **Errors:** If wrong, fix it. No apologies.
- **Assumptions:** Assume I am an expert. Do not explain basic concepts.

## 2. Development Rules
- Priority: 1. Type Safety, 2. Performance, 3. Readability.
- No "hallucinated" libraries; if you aren't 100% sure a package exists, ask me.

## 3. Git & Commits
When asked to provide a Git commit or message:
- **Do NOT** execute any git commit commands or use tools to perform a commit.
- **Provide** only the text for the commit message in a code block.
- Follow the [Conventional Commits] format (e.g., `feat:`, `fix:`, `docs:`).
- I will review the message and perform the manual commit myself.

## 3. Wiki Knowledge Base
Path: ../../CosmoSlice-Wiki

When you need context not already in this project:
1. Read wiki/hot.md first (recent context cache)
2. If not enough, read wiki/index.md
3. If you need domain details, read the relevant domain sub-index
4. Only then drill into specific wiki pages

Do NOT read the wiki for general coding questions or tasks unrelated to [domain].

