Publish demo — step-by-step

This file documents the minimal steps used to clean Python caches and publish this repository as a public demo on GitHub (or another Git host).



Cleanup performed in this branch:
- Remove all __pycache__ directories and .pyc files from working tree and disk.
- Ensure Git ignores Python caches in `.gitignore`.

Local git workflow to publish a public demo

1) Prepare local branch

- Create a fresh branch to contain your demo/publish changes:

  git checkout -b publish/demo-cleanup

2) Make only the cleanup & writeup changes

- If you haven't already created `PUBLISH.md` and updated `.gitignore`, add them now:

  git add PUBLISH.md .gitignore
  git commit -m "chore: add publish instructions and .gitignore rules"

Note: If other unrelated working-tree changes exist and you don't want to commit them, avoid `git add -A`.

3) Remove tracked Python cache files (if any)

- If any `.pyc` files or `__pycache__` directories were accidentally tracked, untrack them from git while keeping a clean history:

  # show tracked cache files (optional)
  git ls-files | grep -E "(__pycache__|\\.pyc$)"

  # untrack those files (this stages their removal)
  git ls-files | grep -E "(__pycache__|\\.pyc$)" | xargs -r git rm --cached

  git commit -m "chore: remove cached Python bytecode from git"

4) Push your branch to remote

  git push -u origin publish/demo-cleanup

5) Open a Pull Request on the Git host (GitHub/GitLab) to merge into `master` (or main). Review and merge.

6) Tag and create a release (optional)

  git tag -a v1.0-demo -m "Public demo release"
  git push origin v1.0-demo

7) Enable any demo hosting (optional)

- If the demo is a web demo, enable GitHub Pages on the repository settings and set the source branch.
- If the demo is a Dockerized app, build and push a Docker image to a registry.

Minimal safety notes

- Don't push secrets or large models/weights. Add them to `.gitignore` or use a release artifact.
- Review `git status` before committing to avoid including unrelated changes.

If you want, I can now:
- remove all `__pycache__` and `.pyc` files on disk,
- untrack any that are currently tracked, and
- create a single commit containing only those removals plus `PUBLISH.md`.

Reply "do it" and I'll run the cleanup and local commit (I will not push to remote without your confirmation).
