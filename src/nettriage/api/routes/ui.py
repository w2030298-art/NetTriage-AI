"""Step 43: Minimal HTML UI — classify form, CSV upload form, and docs link."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import HTMLResponse

router = APIRouter(tags=["ui"])

_HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetTriage AI</title>
    <style>
        body {
            font-family: system-ui, sans-serif;
            max-width: 700px;
            margin: 2rem auto;
            padding: 0 1rem;
        }
        h1 { color: #1a365d; }
        section { margin: 2rem 0; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 8px; }
        label { display: block; margin-bottom: 0.25rem; font-weight: 600; }
        textarea, input[type="file"] { width: 100%; margin-bottom: 0.75rem; }
        textarea { min-height: 100px; }
        button { padding: 0.5rem 1.5rem; cursor: pointer; }
        .link { margin-top: 1rem; }
    </style>
</head>
<body>
    <h1>NetTriage AI &mdash; Network Fault Classification</h1>

    <section>
        <h2>Single Classification</h2>
        <form action="/api/v1/classify" method="post" enctype="application/x-www-form-urlencoded">
            <label for="desc">Fault Description</label>
            <textarea id="desc" name="description"
                placeholder="Describe the network fault..."
                required></textarea>
            <label for="tid">Ticket ID (optional)</label>
            <input type="text" id="tid" name="ticket_id">
            <button type="submit">Classify</button>
        </form>
    </section>

    <section>
        <h2>Batch CSV Upload</h2>
        <form action="/api/v1/batches" method="post" enctype="multipart/form-data">
            <label for="csvfile">CSV File (must contain a 'description' column)</label>
            <input type="file" id="csvfile" name="file" accept=".csv" required>
            <button type="submit">Upload &amp; Start Batch</button>
        </form>
    </section>

    <p class="link">
        <a href="/docs">Interactive API Docs (Swagger UI)</a>
    </p>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index() -> HTMLResponse:
    """Serve a minimal HTML page with classify and batch-upload forms."""
    return HTMLResponse(content=_HTML_PAGE)
