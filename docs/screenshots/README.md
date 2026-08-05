# Screenshots

Drop image files in this folder using the exact filenames below — the main [README.md](../../README.md) already links to them, so they'll appear there automatically once added. PNG or JPG both work; just keep the filename (extension included) matching.

## BREAD functionality (main README's "Screenshots" section)

| Filename | What to capture |
|---|---|
| `bread-browse.png` | `GET /calculations` returning the logged-in user's list (dashboard table, or the response in `/docs`) |
| `bread-read.png` | `GET /calculations/{id}` returning one calculation's details |
| `bread-edit.png` | `PUT /calculations/{id}` updating a calculation's inputs (before/after, or the request + updated result) |
| `bread-add.png` | `POST /calculations` creating a new calculation |
| `bread-delete.png` | `DELETE /calculations/{id}` removing a calculation (the 204 response, or the row disappearing from the dashboard) |

## CI/CD (main README's "CI/CD" section)

| Filename | What to capture |
|---|---|
| `github-actions-run.png` | A green run of the `CI/CD` workflow in the repo's **Actions** tab |
| `dockerhub-deployment.png` | The pushed image/tags on the repo's Docker Hub page |
