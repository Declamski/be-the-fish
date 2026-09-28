# AI Usage Log

| Date/commit | Tool | Prompt | Disposition (Accepted/Modified/Rejected) | What changed & why (if modified) | In my own words, how this works |
|---|---|---|---|---|---|
| 2026-09-27 | Claude Code | Set up project docs structure, .gitignore, auth approach | Accepted | Added to the directory as per the prompt | I used claude to initialise my base structure |
| 2026-09-27 | Claude Code | Build day-1 skeleton: pyproject.toml, config.py, db.py, app.py, ADR.md, AI_USAGE.md | Modified | Added code as per the prompt | I had claude set up the skeleton of the assignment. This includes the files requested in sections 1, 3, 5 and 7 that are listed in the prompt. This keeps me accountable to keeping my project within the assignment scope. |
| 2026-09-28 | Claude Code | Build users domain: users.py (schema, create_user, authenticate, get_current_user), session-based login/signup/logout routes, base/signup/login/index templates; wire into app.py and db.py | Accepted |  Added code as per the prompt | **create_user()** applies normalization and  |
| 2026-09-28 | Claude Code | Build dives domain (schema, repository, service, routes, templates) per ADR-2/ADR-3: scuba direct entry, freedive/spearfishing session staged in flask.session until finish, descents child table, catches restricted to spearfishing; add login_required decorator; add pytest tests for dives.service | Accepted | Added code as per the prompt | TODO: write yourself |
