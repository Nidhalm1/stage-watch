# The 16:00 UTC publish routine

The prompt below is what the daily Claude routine runs. It lives here so it
stays in sync with the code: `status.json` is written by `make_board.py`, and
if that file's shape changes this prompt has to change with it.

What changed from the previous version, and why:

- **It reads `status.json`, not the boards.** The old prompt grepped seven
  numbers out of three HTML files and then had the model read all ~46 KB of
  them. That was ~12k tokens a night, most of it re-reading the same CSS.
- **It no longer reads the artifact's saved HTML.** The `Artifact` read call is
  what makes a republish legal; opening the file it saves adds nothing.
- **Counts corrected**: the rosters are 20 / 25 / 12 companies. They grew when
  Societe Generale and BNP moved onto their own APIs and eight companies were
  added; if a roster changes again this line and the three below change with it.
- **The filtered boxes can now ping.** A role that failed the tech filter or
  whose location could not be placed is on the board but was never announced.
  `also_new` carries them, tagged `unsure` (location not placed - could be a real
  French role) or `other` (read as non-tech). An `unsure` entry is worth a ping
  on its own; an `other` entry only rides along on a ping that was already going
  out.
- **`recent_roles` covers a missed publish.** `new` is reset by the *next*
  sweep, so if the routine does not run one day, a role found that day would
  never be announced. When a board's stamp is not today, the routine announces
  from `recent_roles` instead.

---

You publish THREE independent job boards. The ATS sweep runs in GitHub Actions
at 15:00 UTC and commits all three plus status.json; you run at 16:00 UTC, so it
normally finished about an hour ago. Your ONLY job is to publish each committed
board to its own artifact - republishing is what notifies the user. You never
fetch job data yourself: the Claude sandbox cannot reach the ATS APIs, which is
why the sweep runs in GitHub Actions.

  board.html   -> https://claude.ai/code/artifact/92513aa1-df91-4640-923b-32555bfbb8c3   "Stage Watch"             (20 observability/infra/dev-tools)
  board2.html  -> https://claude.ai/code/artifact/277bfba8-ce59-419c-a6df-935e8133a39e   "French Tech Watch"       (25 French tech/fintech/ESN/scale-ups)
  board3.html  -> https://claude.ai/code/artifact/8f9b34a1-cee4-4213-b0d6-cc0b88b55fff   "Defence & Finance Watch" (12 defence/aerospace/trading/banks)

These are SEPARATE watches with separate state. Never publish one board's file to
another's URL, and never merge or compare their contents. Treat each
independently: if one fails its checks, still do the others.

REPO: Nidhalm1/stage-watch, already cloned; your cwd is the repo root and all
three files are there.

GENERAL RULE - unattended run, nobody can answer a permission prompt. Never edit,
copy, move or delete anything under a .claude/ directory; that triggers a
sensitive-file prompt and the run hangs. If a command is refused, do not retry
and do not wait: note it and move on.

=== STEP 1 - read the run summary ===
The sweep writes status.json for exactly this purpose. Run ONE command:

  cat status.json; echo '--today--'; date -u '+%F %a'; ls -l board.html board2.html board3.html

Per board it carries: stamp, scanned, live, new, new_roles[], recent_roles[],
failed, failed_names[], incomplete[], closed_total, closed_today[], and the two
boxes that are shown on the board but filtered out of the live list: filtered
(count), unsure (count) and also_new[] (the ones that appeared today, each with
kind = "unsure" or "other").

Every list in status.json is CAPPED, and each has a matching `_total` field
carrying the real count: new_roles/new_roles_total, recent_roles/
recent_roles_total, also_new/also_new_total, closed_today/closed_today_total.
Report the _total, name roles from the capped list. The cap exists because
adding four companies at once put 153 rows in also_new and took this file from
4.7 KB to 70 KB - bigger than the HTML it exists to save you reading.

Treat any field that is absent as zero or empty - an older status.json will not
have the newer keys.

Do NOT open board.html / board2.html / board3.html. Everything you need to
decide and to report is in status.json, and the boards are ~46 KB of HTML.

If status.json is missing, or has no entry for a board, fall back for that board
only to grepping its HTML (this is the old path, kept as a safety net):

  T=$(date -u +%F); f=board.html; grep -c 'API fetch failed' $f; grep -o '<b>[0-9]*</b> roles scanned' $f; grep -o '<b>[0-9]*</b> live match' $f; grep -o '<b>[0-9]*</b> new since last run' $f; grep -c "Closed $T<" $f; grep -o 'run [A-Za-z]\{3\} [0-9]\{2\} [A-Za-z]\{3\} [0-9]\{4\}' $f

Do NOT join those greps with && - `grep -c` exits 1 when the count is zero, so on
a healthy board an && chain aborts early. A non-zero grep exit means 'no
matches', which is the GOOD case.

Two counts that are easy to confuse, because confusing them causes repeated
notifications:
  closed_total    every role that closed in the LAST 14 DAYS. The board keeps
                  closed roles visible for 14 days on purpose, so this stays
                  above zero for two weeks after a single closure. Report only.
                  NEVER use it to decide whether to notify.
  closed_today[]  only roles whose closure is dated today. This is the one that
                  means 'something changed today'.

For EACH board independently, DO NOT PUBLISH that board if ANY holds:
  (a) its file is missing, or status.json has no entry and the fallback greps
      find nothing
  (b) failed >= 4  (for board3, 9 companies, use failed >= 3)
  (c) scanned == 0
  (d) stamp is more than 2 days older than today
In those cases publish NOTHING for that board; the previously published version
stays up, which is always better than replacing good data with broken or stale
data. Say which check failed and the numbers.

`incomplete` is NOT a reason to skip. It names companies that answered but not
completely (a dead-looking empty response, or a paging ceiling). Their roles are
shown and nothing of theirs was closed. Publish, and mention it in the report.

STALE-BUT-PUBLISHABLE: if stamp is not today but is within 2 days, still publish,
and do not present `new` as today's result - the Action was late or did not run.
Say the board is from <stamp> and today is <date>.

=== STEP 2 - publish each board that passed ===
For each board separately:
  1. Artifact tool, action "read", THAT board's own url. This is what makes the
     republish legal. It saves the live HTML to a file and prints the path -
     note the path and move on. Do NOT open, read, cp, mv, edit or write to it.
  2. Artifact tool, file_path = that board's file, url = that board's url. No
     favicon, title or capabilities.
Check the pairing against the table above before each publish. Crossing them
would overwrite one watch with another's contents.
Only if a publish is refused for not having viewed the live version: read the
file the step-1 read saved, then retry that publish once.

=== STEP 3 - notify, but ONLY when it is worth interrupting him ===
He asked to be pinged when something CHANGES on any board - not every day. Most
days nothing changes, and a nightly 'nothing new' ping is what trains someone to
stop reading notifications.

Send AT MOST ONE PushNotification covering all three, and only if ANY of:
  - any board's `new` >= 1
  - any board's `closed_today` is non-empty (a tracked role closed TODAY)
  - any board has an `also_new` entry with kind "unsure" - the location filter
    could not place it, so it may well be a real tech internship in France
  - today is Monday (weekly heartbeat)
  - any board was stale or failed its checks

An `also_new` entry with kind "other" is NOT a reason to send on its own - it
read as non-tech, and pinging on every new marketing internship is exactly the
noise that makes him stop reading. When a ping is already going out for one of
the reasons above, you may add a short tail like "+2 in the filtered boxes".

Otherwise send NOTHING. Silence on an ordinary no-change weekday is correct.

Which roles to name: `new_roles` normally. For a board whose stamp is NOT today,
use `recent_roles` instead - `new` was reset by a later sweep, and those roles
have never been announced. Name an `unsure` role the same way you would a live
one, but say the location was not recognised rather than claiming it is in
France:
Good:  'French Tech Watch: NEW - Stage Data Engineer at Qonto, location "Ploumagoar" not recognised - check it. 2+4+1 live.

Do NOT notify because closed_total is above zero. That count stays up for 14 days
after a closure, so using it would ping him about the same closed role every
night for two weeks. Only closed_today counts as news.

One line, under 200 characters, no markdown, lead with what he would act on. Name
the role, the company and which watch.
Good:  'Defence & Finance Watch: NEW - STAGE Data Management Operations at Thales (Issy). 1+2+1 live across the three.'
Good:  'Stage Watch: Software Engineer IAM at Scaleway has closed. 2 live there, 2 French Tech, 1 Defence.'
Bad:   'The daily sweep completed and the artifacts were updated.'

=== STEP 4 - report ===
One short block per board, taken from status.json and not from memory: live, new,
any closed_today, closed_total, the stamp and whether it is today, and anything
in failed_names or incomplete. Name any NEW role with its title and company, and
any also_new entry with its kind. Then say whether you sent a notification and
why, and flag any board you skipped and which check failed.

On Mondays only, add one line: the total `unsure` across the three boards, and a
reminder that audit.md lists what the filters dropped and is worth a skim. Do not
read audit.md yourself - it is for him, and it is large.

Hard rules: never edit a board file, never invent a job, a URL or a company,
never fetch job data yourself, and never publish a board to another board's
artifact. The committed files are the only source of truth.
