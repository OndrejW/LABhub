# User Guide

LABhub is an online lab notebook for linking measurements, samples, setups, projects, sessions, images, and collaborators.

## Core Concepts

- **Project**: a scientific goal or research thread.
- **Session**: a group of measurements inside a project, usually close together in time.
- **Log**: a measurement entry with setup, sample, structure, attributes, images, idea, comment, and data path.
- **Note**: an info, warning, or error entry attached to the same context as logs.
- **Analysis**: a result-oriented entry with idea, findings, path, images, and co-analysts.
- **Setup**: measurement equipment with reusable attributes and optional manuals/files.
- **Sample**: material or device under study.
- **Structure**: a named structure on a sample.
- **Drawer**: physical storage grouping for samples.
- **Attribute**: a name/value parameter such as laser power or field.
- **Remark**: a comment added to an existing log.
- **Cooperator**: another user linked to a log or analysis.

## Accounts

Users can register, log in, update email/username, and upload a profile photo. The current app has ordinary users and cooperators, but no separate admin role in the UI.

## Daily Workflow

1. Create or choose a project.
2. Create a session for a measurement campaign.
3. Add setups, samples, structures, and drawers as needed.
4. Add measurement logs to the session.
5. Attach images and attributes.
6. Add notes for warnings, errors, or contextual events.
7. Add analyses when results are interpreted.

## Logs, Notes, And Analyses

Logs are the main measurement record. Notes are categorized as info, warning, or error. Analyses capture interpretation and findings. These entries share navigation and project context, but their forms and displayed fields differ.

## Sessions

Session pages can display logs in ascending or descending order. Adding a log or note from a session can prefill values from the previous entry. The session view emphasizes changed fields so repeated measurement campaigns stay readable.

## Search And Filtering

The home page supports filtering logs by project, setup, sample, session, structure, user, and full-text search. Full-text search should be reindexed after major data imports or schema changes by using the `/reindex/` route as an authenticated user.

## Inventory

Samples can belong to drawers, have structures, track locations, and show related logs. Setup pages show equipment information, attributes, uploaded files/manuals, and related notes.

## Collaboration

Logs and analyses can include cooperators. Remarks can be added to logs.
