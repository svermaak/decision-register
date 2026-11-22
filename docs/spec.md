# Decision Register and Knowledge Base: Specification

Status: draft 4 for review. Nothing is built yet.

All names in the examples are made up (project `DEMO`, areas `API` and `DATA`). The public repo must hold no real project names, tenant IDs, URLs or keys. Those come from configuration at run time.

## 0. Summary

- **The register** is one database that holds every decision, fact, rule, open question, action, risk, assumption and term for a project. It is the single source of truth.
- **The knowledge base** is a search index over two things: the register's records, and outside sources such as policies, procedures, pages, files and meeting notes. It replaces the knowledge base used today.
- **One API** sits in front of both. The portal and the agents use it. The API enforces the rules, so nobody can skip them.
- **An MCP server** gives agents the same API as a small set of tools. Agents use it to look things up when they write a change paper or a solution design.
- **Confluence** gets a generated copy of the register, one way.
- Every change makes a new version. Nothing is overwritten or hard deleted.
- A copy of the data is useless without the key (section 5.4).

### Decisions made so far

| Topic | Decision |
|---|---|
| Main home | AWS, as a Docker container on a Linux EC2 server, deployed by pipeline. |
| Other homes | Your own machine with no admin rights and no Docker. Azure with the same container. |
| Cloudflare | Left for later. ChromaDB cannot run inside it. |
| Language | Python. |
| Search engine | ChromaDB, running inside the app, with its built-in model. No text leaves the server. |
| Encryption | A copied database must not be usable elsewhere. |
| Sources | Files, web pages, Confluence pages, meeting notes and transcripts, and text sent by agents. |
| Answers | The knowledge base returns matching text with its sources. The agent writes the answer. |
| Confluence reading | Only from spaces you pick. |
| Local sign-in | None. Entra ID sign-in is for the team version only. |
| Roles | Set in the portal, not in Entra. |
| Entra tenant | The Dev tenant. This is a Dev tool. |
| Web address | Fixed, and provided by the pipeline together with HTTPS. |
| IDs | The letter had no meaning. A simple scheme is proposed in 1.2. |
| Old data | None. The register starts empty. |

## 1. Data model

### 1.1 Tables

| Table | What it holds |
|---|---|
| `project` | One row per project: key (`DEMO`), name, active or closed. |
| `area` | One row per area in a project: key (`API`), name. |
| `id_counter` | The last number used for each ID prefix in a project. It only goes up. |
| `record` | One row per record. Holds the things that never change. |
| `record_version` | One row per version of a record. Holds everything that can change. Rows are only added. |
| `link` | One row per typed link between two records. |
| `review_flag` | One row each time a record is flagged for review. |
| `group` | A named list of people, for example "Security" or "Architecture board". |
| `group_member` | Which person is in which group. |
| `record_stakeholder` | The owners and approvers of a record. Each is a person or a group. |
| `sign_off` | One row per approval or rejection of one version of a record. Rows are only added. |
| `comment` | The discussion under a record. |
| `audit_log` | One row per write, or refused write. Rows are only added. |
| `user` | One row per person who has signed in: Entra object ID, display name. |
| `role_grant` | Which role a person has on which project. |
| `kb_source` | One row per outside source in the knowledge base (section 6). |
| `kb_source_version` | One row each time a source's content changed. |
| `kb_chunk` | The pieces of text that search returns. |
| `publish_run` | One row per Confluence publishing run. |
| `publish_page` | Which Confluence page belongs to which project or area, with a hash of the last content. |

### 1.2 `record` (never changes)

| Field | Notes |
|---|---|
| `id` | Internal key. Not shown to people. |
| `public_id` | The stable ID. Unique in the project. Never reused, even if the record is withdrawn. |
| `project_id` | The project. |
| `type` | Decision, Fact, Rule, Open question, Action, Risk, Assumption, Term. A record never changes type. |
| `created_by`, `created_at` | Who made it and when. |
| `created_via` | `portal`, or the name of the agent. |

Stable IDs are a short word for the type and a number, counted per project:

| Type | ID looks like |
|---|---|
| Decision | `DEC-14` |
| Fact | `FACT-3` |
| Rule | `RULE-2` |
| Open question | `Q-9` |
| Action | `ACT-5` |
| Risk | `RISK-4` |
| Assumption | `ASM-7` |
| Term | `TERM-12` |
| Knowledge base source | `SRC-31` |

The word tells a person or an agent what the record is before they open it.

### 1.3 `record_version` (a new row for every change)

| Field | Notes |
|---|---|
| `record_id`, `version_no` | Version 1, 2, 3 and so on. The highest number is the current version. |
| `area_id` | The area. A record can move area; the ID stays the same. |
| `title`, `body` | Body is Markdown text. |
| `why` | Required for decisions. Empty for other types. |
| `status` | See 1.5. |
| `source_type` | Person, Meeting, Document, Test. |
| `source_ref` | Who said it, which meeting and date, or which test. It can point at a knowledge base source, for example `SRC-31`. |
| `details` | Extra fields for the type. See 1.4. |
| `changed_by`, `changed_at` | Who made this version and when. |
| `changed_via` | `portal`, or the name of the agent. |
| `change_note` | A short reason for the change. Required from version 2 onward. |

### 1.4 Extra fields by type

| Type | Extra fields |
|---|---|
| Decision | `why` (required). `agreed_at`, set by the system when the last needed sign-off arrives. Who agreed is read from the sign-offs (1.9). |
| Fact | `value` (the checked value). `checked_by`, `checked_at`, `check_method`. All required. |
| Rule | None. |
| Open question | `needs` (an answer or a test). `needed_by` date, optional. |
| Action | `assignee` (who owes it), `due_date`. Both required. |
| Risk | `likelihood`, `impact` (Low, Medium, High). `response` (Reduce, Accept, Avoid, Transfer). `accepted_at`, set by the system. Who accepted is read from the sign-offs (1.9). |
| Assumption | `how_to_check` (what test or source would confirm it). |
| Term | `meaning` (the one agreed meaning). `not_to_be_confused_with`, optional. |

### 1.5 Status by type

| Type | Statuses |
|---|---|
| Decision | Proposed, Leaning, For discussion, Needs sign-off, Agreed, Replaced, Withdrawn |
| Rule | Proposed, Agreed, Replaced, Withdrawn |
| Term | Proposed, Agreed, Replaced, Withdrawn |
| Fact | Checked, Out of date, Replaced, Withdrawn |
| Open question | Open, Answered, Withdrawn |
| Action | Open, In progress, Done, Withdrawn |
| Risk | Open, Reduced, Accepted, Closed, Withdrawn |
| Assumption | Unchecked, Promoted, Proved wrong, Withdrawn |

An admin can add more statuses to a type in Settings when they are needed. The statuses that the rules in 1.8 use (Proposed, Agreed, Accepted, Answered, Promoted, Replaced, Withdrawn) are fixed and cannot be renamed or removed. A status that is in use cannot be removed.

### 1.6 Links

One row per link: `from_record`, `link_type`, `to_record`, `note`, `created_by`, `created_at`, `removed_by`, `removed_at`.

| Link type | Reads as | Shown on the other record as |
|---|---|---|
| `replaces` | DEC-17 replaces DEC-7 | DEC-7 is replaced by DEC-17 |
| `depends_on` | A depends on B | B is needed by A |
| `answers` | Decision D answers question Q | Q is answered by D |
| `raises` | Record A raises question or risk B | B is raised by A |
| `relates_to` | A relates to B | B relates to A |

- A link is stored once and shown on both records. This is how "both records link to each other" is kept true: it cannot be half done.
- Links are never deleted. Removing a link fills in `removed_by` and `removed_at`.
- A record cannot link to itself. `replaces` and `depends_on` cannot form a loop.
- `replaces` must join two records of the same type, with one exception: a Fact can replace an Assumption (rule 4 in 1.8).

### 1.7 Versioning and history

- Every change adds a `record_version` row. Old rows are never changed.
- Every change must say which version it started from. If someone else changed the record in between, the change is refused and the caller must read again. This stops two agents, or an agent and a person, from writing over each other.
- Any old version can be read, and any two versions can be compared.
- The register can be read "as of" a past date.
- There is no hard delete. A record ends as Replaced or Withdrawn.

### 1.8 Rules the system enforces

1. **Agents propose, people agree.** A decision created by an agent starts as Proposed. Only people can sign off, and only in the portal (1.9). The same applies to Agreed on rules and terms, and Accepted on risks.
2. **Replacing is one step.** A `replaces` link can be added while the new record is still Proposed. The old record changes to Replaced at the moment the new one becomes Agreed, in the same write. A record cannot be set to Replaced without a `replaces` link pointing at it.
3. **Review flags.** When a record is changed, replaced or withdrawn, every record that directly depends on it gets a review flag. The flag says which record and which version caused it. An editor clears the flag with a note ("still correct") or by changing the record. Changing it flags its own dependents in turn. An editor or an agent can mark a change as a "small edit" (a typo). A small edit raises no flags, but it still makes a new version and is logged as a small edit. A status change can never be a small edit.
4. **Assumptions are never facts.** A fact cannot be saved without `checked_by`, `checked_at` and `check_method`. Promoting an assumption creates a new Fact that `replaces` it, and sets the assumption to Promoted. Records that depended on the assumption are flagged, so they can be pointed at the fact.
5. **Answering a question.** Adding an `answers` link from an Agreed decision sets the open question to Answered.
6. **Sources are not truth.** Adding something to the knowledge base never creates a record. A record is only made by a person or an agent on purpose, and an agent's record starts as Proposed.
7. **Every write is logged** (section 5.3).

### 1.9 Owners, approvers and sign-offs

**Groups**

- A group is a named list of people. Admins manage groups in the portal. Groups are shared by all projects.
- A group can stand for people who do not use the system, for example "Board". It then has no members, and its sign-offs are recorded for it (see below).

**Stakeholders on a record** (`record_stakeholder`)

| Field | Notes |
|---|---|
| `record_id` | The record. |
| `user_id` or `group_id` | One person or one group. |
| `role` | Owner or Approver. |
| `added_by`, `added_at`, `removed_by`, `removed_at` | Rows are never deleted. Every change is in the audit log. |

- A record has one or more owners. Owners answer for the record and are told when it is flagged or commented on.
- A record has zero or more approvers. These are the stakeholders whose sign-off is needed.
- Editors can change the list. Once a record is at Needs sign-off, only a project approver can add or remove an approver, so the list cannot be cut down to get a quick yes.

**Sign-offs** (`sign_off`)

| Field | Notes |
|---|---|
| `record_id`, `version_no` | The exact version that was signed. |
| `for_user_id` or `for_group_id` | Which named approver this sign-off counts for. |
| `outcome` | Approved or Rejected. |
| `note` | Optional. Long Markdown text with no length limit, for conditions, concerns or reasons. |
| `signed_by`, `signed_at` | The person who made the entry, and when. |
| `on_behalf` | Yes when it was recorded for someone else. |
| `source` | Required when `on_behalf` is yes: the meeting and date, the email, or the document. |

How it works:

1. Sign-offs are collected while a record is at Needs sign-off.
2. A named person signs for themselves. Any one member of a named group signs for that group.
3. A project approver can record a sign-off on behalf of a named person or group, and must give the source. It is always shown as "recorded by", so it is clear the stakeholder did not click it.
4. When every named approver has an Approved sign-off on the current version, the record becomes Agreed (or Accepted, for a risk) by itself.
5. A Rejected sign-off moves the record back to For discussion. The note says why.
6. If a record names no approvers, any person with the project approver role can agree it. That is stored as a sign-off too, so there is one place to look.
7. A sign-off belongs to one version. If the record changes after it, the sign-off stays in the history but no longer counts. A small edit does not reset sign-offs.
8. Changing an Agreed record, other than by a small edit, moves it back to Needs sign-off. To change what was decided, replace the decision instead.
9. Sign-offs are made in the portal only. An agent can never sign off, for itself or for anyone else.

### 1.10 Comments

| Field | Notes |
|---|---|
| `record_id` | The record the comment is on. |
| `reply_to` | Another comment, for replies. |
| `body` | Markdown text. |
| `author`, `via`, `created_at` | Who wrote it, through the portal or which agent, and when. |
| `edited_at` | Set when the author changes it. The earlier text is kept in the audit log. |
| `resolved_by`, `resolved_at` | Set when the thread is marked resolved. |
| `removed_by`, `removed_at` | A removed comment is hidden, not deleted. |

- Anyone who can read a record can comment on it. This includes agents, and an agent's comment is labelled as such.
- A comment never changes the record. It makes no new version and raises no review flag.
- Comments are discussion, not truth. They are not published to Confluence and not put in the knowledge base.

## 2. API

One HTTP API returning JSON. The portal, the MCP server and any other client use the same endpoints with the same rules. All lists are paged.

### 2.1 Read and search the register

| Endpoint | Does |
|---|---|
| `GET /projects` | Lists projects the caller can see. |
| `GET /projects/{key}/areas` | Lists areas in a project. |
| `GET /records` | Searches records. Filters below. |
| `GET /records/{id}` | One record: current version, links both ways, open review flags. |
| `GET /records/{id}/links` | The record's links. Filter by type and direction. |
| `GET /me` | The caller's name and roles. |

Filters on `GET /records`, which can be combined:

- `project`, `area`, `type`, `status`
- `owner`, `approver` (a person or a group)
- `waiting_for` (records at Needs sign-off that still need this person, or one of their groups)
- `flagged=true` (has an open review flag)
- `linked_to={id}` with `link_type` and `direction` (for example: everything that depends on `DEC-14`)
- `changed_since`, `due_before` (actions)
- `as_of` (the register at a past date)
- `q` (exact words in title, body, why and value)

### 2.2 Create and change

| Endpoint | Does |
|---|---|
| `POST /records` | Creates a record. The system gives the ID and the starting status. |
| `PATCH /records/{id}` | Changes fields. Needs `base_version` and `change_note`. Makes a new version. |
| `POST /records/{id}/status` | Changes status. Checks the caller's role and the rules in 1.8. Agreed and Accepted cannot be set here; they come from sign-offs (1.9). |
| `POST /records/{id}/replace` | Names the record that replaces this one. Adds the link; see rule 2. |
| `POST /records/{id}/promote` | Assumption only. Creates the Fact; see rule 4. |
| `POST /records/{id}/withdraw` | Sets Withdrawn, with a reason. |

There is no delete endpoint.

### 2.3 Links

| Endpoint | Does |
|---|---|
| `POST /links` | Adds a typed link between two records. |
| `DELETE /links/{id}` | Marks the link as removed. The row stays. |

### 2.4 Stakeholders, sign-offs and comments

| Endpoint | Does |
|---|---|
| `GET /groups`, `POST /groups`, `PATCH /groups/{id}` | Lists and manages groups and their members. Changes are for admins only. |
| `GET /records/{id}/stakeholders` | Owners and approvers, with sign-off progress on the current version. |
| `POST /records/{id}/stakeholders` | Adds a person or group as Owner or Approver. |
| `DELETE /records/{id}/stakeholders/{sid}` | Marks the stakeholder as removed. The row stays. |
| `GET /records/{id}/sign-offs` | All sign-offs, for every version. |
| `POST /records/{id}/sign-offs` | Approves or rejects the current version. Portal only. Needs `source` when made on behalf of someone. |
| `GET /records/{id}/comments` | The comment thread. |
| `POST /records/{id}/comments` | Adds a comment or a reply. |
| `PATCH /comments/{id}` | Edits own comment, or marks the thread resolved. |
| `DELETE /comments/{id}` | Hides the comment. The row stays. |

### 2.5 History, review and audit

| Endpoint | Does |
|---|---|
| `GET /records/{id}/history` | All versions: number, who, when, change note. |
| `GET /records/{id}/versions/{n}` | One old version in full. |
| `GET /records/{id}/diff?from=&to=` | What changed between two versions. |
| `GET /review-flags` | Open flags. Filter by project, area, owner. |
| `POST /review-flags/{id}/clear` | Clears a flag, with a note. |
| `GET /audit` | The audit log. Filter by record, user, date. Approvers and admins only. |

### 2.6 Knowledge base

| Endpoint | Does |
|---|---|
| `POST /kb/search` | Finds text by meaning. Returns passages with their source or record ID. Filters: project, kind, record type, status. |
| `POST /kb/sources` | Adds a source: pasted text, a link, or a file upload. |
| `GET /kb/sources` | Lists sources. Filter by project, kind, status. |
| `GET /kb/sources/{id}` | One source: details, versions, and the full text. |
| `POST /kb/sources/{id}/refresh` | Reads the source again now. |
| `POST /kb/sources/{id}/withdraw` | Takes the source out of search. The row stays. |
| `POST /kb/rebuild` | Rebuilds the whole search index from stored text. Admins only. |

### 2.7 Publishing

| Endpoint | Does |
|---|---|
| `POST /publish` | Starts a Confluence rebuild for a project or one area. |
| `GET /publish/runs` | Past runs and their results. |

### 2.8 Errors

Refused writes return a clear reason an agent can act on. For example: "Only a person can sign off, and only in the portal" or "The record changed since version 3; read it again".

## 3. Portal

| Screen | What it does |
|---|---|
| Project home | Counts by type and status. Lists: needs sign-off, flagged for review, actions due soon, changed lately. |
| Register | The main list. Filter by type, area, status, owner, approver and flag. Text search. Each filter set has a link that can be shared. |
| Record | The current version, with all fields, links in both directions and open flags. A stakeholder panel shows the owners, the approvers, and progress such as "2 of 3 approved", with who signed, when, and their note. Buttons shown by role: edit, change status, link, replace, promote, withdraw, approve, reject. |
| Sign-off box (on Record) | Approve or reject, with a large note field. A project approver can tick "on behalf of" and must then give the source. |
| Comments (tab on Record) | The discussion thread, with replies and a "resolved" tick. A large text box. Agent comments are labelled. |
| History (tab on Record) | Every version with who, when and why. Compare any two versions side by side. |
| New and Edit | A form for the type, with only that type's fields. A change note is required on edit. |
| Review queue | Records flagged for review, with the change that caused each flag. Clear with a note, or open to edit. |
| Sign-off queue | Everything waiting for you or one of your groups. Project approvers also see records with no named approvers. Approve or reject with a note. |
| Glossary | All terms, A to Z. |
| Search | One search box over the knowledge base. Results show the passage, where it came from, and a label: register record (with its status) or outside source. |
| Sources | The list of knowledge base sources. Add text, a link or a file. See when each was last read and whether it failed. Refresh or withdraw. |
| Audit log | Approvers and admins only. Search by record, person and date. |
| Publishing | Last run, result, link to the Confluence pages, and a "Rebuild now" button. |
| Settings | Admins only. Projects, areas, people and roles, groups and their members, extra statuses, the list of allowed Confluence spaces. |

Every record and source has a fixed web address that uses its stable ID, so Confluence and agents can link to it.

## 4. Confluence publishing

Confluence Cloud. The job signs in with one person's own account and API token, because no service account is available.

### 4.1 What is made

- One parent page per project.
- Under it, one page per area. Records are grouped by type, in tables.
- Project-wide pages for Rules and for the Glossary.
- Each record shows its owners. An Agreed record also shows who approved it and when.
- Comments are not published.
- All records are shown, whatever their status. Each one shows its status clearly, so a reader can tell Proposed from Agreed.
- Replaced and Withdrawn records are shown in a closed section at the bottom, so links to them still work.

### 4.2 Every page says

- "This page is generated. Do not edit it. Changes will be lost."
- The date and time it was generated.
- A link back to the same view in the portal. Each record ID links to its record in the portal.

### 4.3 When it runs

- A few minutes after a record changes, for the pages that change touches. Changes close together make one run.
- Once a night, a full rebuild of every page.
- On demand, from the Publishing screen or `POST /publish`.

### 4.4 How it runs

- The job reads the register and writes to Confluence. It never copies content from these pages back into the register.
- Pages are built from the register alone, so they can be deleted and rebuilt at any time.
- The job remembers the page ID for each project and area. It only touches pages it made, and it labels them as generated.
- If a page's content did not change, it is not written again.
- If Confluence is down, the run is marked failed and tried again later. The register keeps working.
- The generated pages are restricted so that only the publishing account can edit them.

### 4.5 Limits of using one person's account

- The pages show that person as the author.
- If that account is closed or the token ends, publishing stops until a new token is set. The Publishing screen shows this clearly.

## 5. Security

### 5.1 Sign-in

**Team version (AWS, Azure)**

- People sign in to the portal with Entra ID. There are no local passwords.
- The API accepts only tokens from the configured Entra tenant, made for this API.
- An agent signs in on behalf of a user. Its token names both the user and the agent. The agent gets that user's role and no more.
- The API tells a person from an agent by the client named in the token. This is how rule 1 in 1.8 is enforced: a sign-off is accepted only from the portal.
- Each agent tool is registered in Entra once, by hand. Entra does not let MCP clients register themselves.
- There are no shared API keys and no anonymous access.

**Local version (your own machine)**

- No sign-in. It listens only on the machine itself, not on the network.
- You are the only user and hold every role.
- Writes that come through the MCP server count as an agent. Writes in the portal count as a person. So the rules in 1.8 still work.

### 5.2 Roles

Roles are set in the portal, per project.

| Can do | Reader | Editor | Approver | Admin |
|---|---|---|---|---|
| Read records, links, history; search the knowledge base | Yes | Yes | Yes | Yes |
| Create and change records, add links | No | Yes | Yes | Yes |
| Add, refresh and withdraw knowledge base sources | No | Yes | Yes | Yes |
| Clear review flags | No | Yes | Yes | Yes |
| Promote an assumption to a fact | No | Yes | Yes | Yes |
| Start a publishing run | No | Yes | Yes | Yes |
| Comment on a record | Yes | Yes | Yes | Yes |
| Change a record's owners and approvers | No | Yes | Yes | Yes |
| Change approvers once a record is at Needs sign-off | No | No | Yes | No |
| Sign off as a named approver, or as a member of a named group (portal only) | Yes | Yes | Yes | Yes |
| Agree a record that names no approvers (portal only) | No | No | Yes | No |
| Record a sign-off on behalf of someone, with the source (portal only) | No | No | Yes | No |
| Manage groups | No | No | No | Yes |
| Withdraw an Agreed record | No | No | Yes | No |
| Read the audit log | No | No | Yes | Yes |
| Manage projects, areas, people, roles, Confluence spaces | No | No | No | Yes |

Everyone with a role on any project can search `shared` knowledge base sources.

Admin is a fourth role, added because roles are now set in the portal. The first admin is named in configuration. A person can hold Admin and Approver together.

### 5.3 Audit log

- One row for every write: when, which user, through which client (portal or which agent), which record or source and version, the action, and what changed (old and new values).
- Refused writes are logged too, with the reason.
- Rows can only be added. No role can change or remove them through the API.
- The audit log is separate from the version history. History shows what a record said; the audit log shows who did what.

### 5.4 Encryption at rest

The goal: someone who copies the data cannot use it elsewhere.

- The database file is encrypted as a whole. It cannot be opened without the key.
- Stored original files are encrypted with the same key before they are written.
- The search index holds only number lists (vectors), IDs and a few labels such as project and type. It holds no text. The text of each passage lives in the encrypted database.
- The key is never stored next to the data, and never in the repo:
  - AWS: in the AWS secret store, readable only by the server's own role.
  - Azure: in Key Vault.
  - Local: in the Windows, macOS or Linux credential store of your user account. This needs no admin rights.
- On AWS and Azure the disk is also encrypted by the cloud, as a second layer.
- Backups are made from the encrypted files, so a backup is also useless without the key.
- If the key is lost, the data is lost. The setup guide must say how to keep a safe copy of the key.

Known limit: with enough effort, some meaning can be guessed from vectors alone. On AWS and Azure the encrypted disk covers this. On a local machine without disk encryption, a copied index gives vectors but no text.

### 5.5 Keeping the public repo clean

- The repo holds code and made-up sample data only.
- Tenant ID, client IDs, addresses, the Confluence space names and all keys come from configuration and a secret store at run time.
- The repo has an example configuration file with empty values, and secret scanning turned on.
- Register and knowledge base content is never committed to the repo. The data folder is ignored by git.

### 5.6 Other

- All traffic to the team version is encrypted (HTTPS).
- A restore from backup is tested.
- The system stores only a name and an Entra ID for each person.

## 6. Knowledge base

### 6.1 What it is

- A search index that finds text by meaning, not only by exact words.
- It holds two kinds of content, and every search result is labelled as one or the other:
  - **Register records.** Each record's current version is put in automatically when it changes. One way only.
  - **Outside sources.** Policies, procedures, pages, files, notes. These are evidence, not truth.
- The whole index can be thrown away and rebuilt from the stored text at any time.

### 6.2 What a source is

| Field | Notes |
|---|---|
| `public_id` | For example `SRC-31`. Never reused. |
| `scope` | One project, or `shared` for things every project uses, such as company policies. |
| `kind` | File, Web page, Confluence page, Notes or transcript, Agent text. |
| `title`, `origin` | A name, and where it came from (link or file name). |
| `status` | Active, Out of date, Withdrawn. |
| `refresh` | Never, daily or weekly. For web and Confluence pages. |
| `last_read_at`, `last_result` | When it was last read and whether that worked. |
| `added_by`, `added_via`, `added_at` | Who added it, through the portal or which agent, and when. |

When a source's content changes, a new `kb_source_version` row is made. Search uses the newest version only. Old versions stay readable.

### 6.3 How things get in

| Kind | How |
|---|---|
| Files | Upload in the portal. PDF, Word, PowerPoint, Excel, text and Markdown are turned into plain text. |
| Web pages | Give a link. The page is fetched and turned into plain text. |
| Confluence pages | Pick a space or a page. Only spaces on the allowed list can be read. Pages generated by this system are skipped, so it never reads its own output. |
| Notes and transcripts | Paste text or upload a file. |
| Agent text | An agent sends text through MCP, with a title and where it came from. |

Then, for every kind:

1. The original is stored, encrypted.
2. The text is cut into passages, keeping headings so a passage makes sense alone.
3. Each passage is turned into a vector by ChromaDB's built-in model, on the server.
4. If the same content is added twice, it is stored once.

### 6.4 How search answers

- A search returns the best passages. Each one has its text, a score, its ID (`DEC-14` or `SRC-31`), its label, and a link.
- Register records also show their type and status. An Assumption is always marked "not checked".
- By default, Replaced and Withdrawn records and withdrawn sources are left out.
- When a record and a source say different things, the Agreed record wins. Results put Agreed records first when scores are close.
- The system does not write answers itself. The agent that asked does that.

### 6.5 Moving from today's knowledge base

- The old ChromaDB data is not copied over. The sources are added again here, so every source has an owner, an origin and a refresh setting.
- The old knowledge base stays in use until the new one holds the same sources.

## 7. MCP server

Agents use this to look things up and to propose changes. It is part of the same app and follows the same rules as the API.

### 7.1 How agents connect

- Team version: over HTTPS, signed in on behalf of a user.
- Local version: started by the agent tool on your machine, with no sign-in.

### 7.2 Tools

Kept few, so an agent picks the right one.

| Tool | Does |
|---|---|
| `get_context` | The main tool for writing a paper. Give a topic and a project. Returns the Agreed decisions, rules, facts and terms that match, open risks and questions, and the best passages from outside sources. |
| `search_records` | Finds records by type, area, status, owner, links and words. |
| `get_record` | One record with its links, flags, owners, approvers and sign-off progress. Can include history and comments. |
| `kb_search` | Finds passages by meaning across records and sources. |
| `kb_get_source` | The full text and details of one source. |
| `propose_record` | Creates a record. A decision starts as Proposed. Can name owners and approvers. |
| `update_record` | Changes a record. Needs the version it started from and a change note. |
| `set_status` | Changes status, within the rules. Cannot set Agreed or accept a risk, and there is no tool for signing off. |
| `add_comment` | Adds a comment or a reply to a record. |
| `link_records` | Adds a typed link. |
| `list_review_flags` | Records flagged for review. |
| `kb_add` | Sends text or a link to the knowledge base as a new source. |

### 7.3 Made for agents

- Answers are short. Lists return ID, title, type and status first; the agent asks for the full record only when it needs it.
- Every item carries its stable ID and a link to the portal, so the agent can cite it in a paper.
- Every result says what it is: Agreed record, unchecked assumption, or outside source.
- Errors say what to do next.
- Tool descriptions tell the agent the rules: never state an assumption as a fact, and prefer Agreed records over sources.

## 8. Stack and hosting

### 8.1 Stack

| Part | Choice | Why |
|---|---|---|
| Language | Python | ChromaDB runs inside the app, and Python has the best tools for reading files. |
| App | One Python web app that holds the API, the portal and the MCP server | One thing to start, on every host. |
| Portal | Pages made by the same app | No second program and no build step. |
| Database | SQLite, encrypted | One file. No database server to install. Enough for a team. |
| Search index | ChromaDB, inside the app, with its built-in model | Nothing leaves the server. |
| Original files | A folder on disk | Kept behind a small interface so it can move to cloud storage later. |

The exact Python libraries are chosen at build time and checked on Windows without admin rights first, because that is the strictest host.

Limit: SQLite and ChromaDB inside the app mean one running copy of the app. That is enough for a team. If it must grow later, the database and index can move to their own servers without changing the API.

### 8.2 Hosts

| Host | How it runs |
|---|---|
| Your machine | Python only. No admin rights, no Docker. One command to start. Data sits in a folder in your user profile. No sign-in. |
| AWS (main) | One Docker container on the Linux EC2 server, deployed by the pipeline. Data on an encrypted disk. Key from the AWS secret store. The pipeline provides a fixed web address and HTTPS. Sign-in with the Dev Entra tenant. Backups to encrypted storage. |
| Azure | The same container image. Data on mounted encrypted storage. Key from Key Vault. |
| Cloudflare | Later. It needs a different database and search store. The storage code is kept behind small interfaces so this stays possible. |

All settings come from environment values, so the same image runs everywhere.

## 9. Open questions

None are open. All answers so far:

- **Statuses.** The lists in 1.5 are used. An admin can add more when needed.
- **Sign-off.** Agreed on decisions, rules and terms, and Accepted on risks, are for people only.
- **Admin role.** Admin is a fourth role.
- **Small edits.** Allowed with a "small edit" tick. No flags are raised, and it is logged.
- **Confluence content.** All records are published, with the status shown.
- **Shared sources.** Everyone who signs in can search them.
- **Entra setup.** The app registrations are made in the Dev Entra tenant. This is a Dev tool, so the Dev tenant is the right place. People sign in with their Dev tenant accounts.
- **Web address.** The pipeline gives the AWS version its web address and HTTPS certificate. The address stays the same after every deploy, so sign-in is set up once. The address is a configuration value and is never written in the repo.

- **Approval.** Named approvers sign off in the portal. A project approver can also record a sign-off on behalf of a stakeholder, with the source.
- **No approvers named.** Any project approver can agree the record.
- **Sign-off note.** Optional, and a large text field with no length limit.
- **Comments.** Every record has a comment thread.

To check at build time: that the chosen Python libraries, mainly the database encryption, install and run on Windows with no admin rights.
