#!/usr/bin/env bash
# UserPromptSubmit hook: when the correspondent's message looks like a
# correction of Claude's work, remind Claude to turn it into a House Style
# Log entry (AGENTS.md §12) via the claude-md-improver skill, with approval.
prompt="$(jq -r '.prompt // empty')"
[ -z "$prompt" ] && exit 0

# Correction cues; co(r+e+)+ct also catches typos such as "corect"/"coreect".
pattern="\b(wrong|incorrect|not (right|correct|what i)|that'?s not|should (be|have|read|say)|instead|rather than|don'?t|do not|never|stop|fix|mistake|error|typo|co(r+e+)+ct(ion|ions|ed)?|change (it|this|that) to|replace|use .* not|i (said|meant|asked))\b"

if printf '%s' "$prompt" | grep -qiE "$pattern"; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: "This message may correct your work. First apply the correction. Then use the claude-md-improver skill to propose a dated rule for the House Style Log in AGENTS.md section 12 (\"Corrections learnt from drafts\", or \"Confirmed\" if it is a standing rule), shown as a diff. Add it only after the correspondent confirms. If the message is not actually a correction, ignore this reminder."
    }
  }'
fi
exit 0
