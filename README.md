# SIH Module 1

Module 1 accepts a product-label image and returns OCR text plus structured
product information. It is a perception and extraction component only; it does
not make Legal Metrology, compliance, or enforcement decisions.

## Setup

Requirements:

- Python 3.14 or newer
- A working Tesseract executable on `PATH`
- Python dependencies from `requirements.txt`

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On macOS, install Tesseract with Homebrew:

```sh
brew install tesseract
```

Copy `.env.example` to `.env` and set `SIH_TESSERACT_CMD` if Tesseract is not
on `PATH`.

## Running

```sh
.venv/bin/uvicorn module1.main:app --host 127.0.0.1 --port 8000
```

Interactive documentation is available at `http://127.0.0.1:8000/docs`.

## Architecture

The request flows through these boundaries:

1. FastAPI receives a multipart image upload and reads it in bounded chunks.
2. The service validates the filename, byte size, image header, and pixel dimensions.
3. OpenCV decodes the image; quality is assessed and configured preprocessing runs.
4. Tesseract performs orientation-aware OCR with the existing conditional escalation.
5. The parser extracts the existing 16 canonical fields and validation assigns status and confidence.
6. The response includes OCR text, fields, evidence, geometry, quality, and timing metadata.

## Endpoints

- `GET /health` returns application and OCR-engine metadata.
- `POST /api/v1/extract` accepts a multipart field named `file`.

Example:

```sh
curl -F "file=@label.png" http://127.0.0.1:8000/api/v1/extract
```

Known structured errors include empty files, oversized files or images,
unsupported extensions, invalid images, unavailable OCR, and unexpected
processing failures. Unexpected failures return a generic message and do not
include stack traces or filesystem details.

## Limitations

- Supported filename extensions are `.jpg`, `.jpeg`, and `.png`.
- Maximum upload size is 20 MiB by default.
- Images with a shortest dimension below 100 pixels are rejected by the web collector.
- Maximum image dimension is 4096 pixels; images exceeding the corresponding pixel limit are rejected.
- OCR quality varies with blur, glare, perspective, dense packaging, and small text.
- Confidence is heuristic and is not a calibrated probability.
- Unknown text is retained as unmapped detections, but extraction is not complete field recognition.
- The current seven-image benchmark scores 30/36 verified values exactly (83.3%).

## Benchmark Interpretation

Run the local evaluation with:

```sh
.venv/bin/python -m tests.evaluation.evaluate
```

The benchmark uses independently transcribed values only where the source
image is legible. Omitted fields are unknown, not negative labels. Exact and
conservative normalized matches are reported separately from missing,
incorrect, and uncertain values. The small local benchmark is useful for
regression comparison, not a production accuracy guarantee.

## Web Dataset Collection

The standalone collector keeps downloaded images separate from `test_images/`
and does not change the Module 1 pipeline. Create a manifest such as:

```json
[
  {"url": "https://example.test/label.jpg", "category": "biscuits"}
]
```

Run it with:

```sh
.venv/bin/python scripts/collect_web_dataset.py urls.json --output-dir web
```

For automated discovery, set a SerpApi Google Images key and run, for example:

```sh
SERPAPI_API_KEY=... .venv/bin/python scripts/discover_web_dataset.py --dry-run --max-images 10
```

The discovery command requires that external provider credential; without it
the command reports `not_configured` and does not invent or download URLs.

Images are stored under `web/<category>/`. Duplicate downloads are identified
by SHA-256 and are not stored twice. `web/metadata.json` contains per-source
download, resolution, quality, OCR, detected-field, and timing metadata;
`web/report.json` contains aggregate counts. Only the existing `.jpg`, `.jpeg`,
and `.png` pipeline inputs are processed; unsupported or failed downloads are
reported without being silently converted. Usable images must pass the existing
resolution check and have a quality score of at least `0.35`; filename
collisions are renamed rather than overwritten.

## Deployment and Security

The application is intended to run behind a reverse proxy or API gateway that
enforces request-body limits, authentication, rate limiting, TLS, and bounded
concurrency. Module 1 does not implement authentication or rate limiting.
Keep it off the public internet without those controls. Tesseract and image
decoding are CPU and memory intensive; configure worker, timeout, and resource
limits appropriate to the deployment. Do not treat extracted values as
regulatory truth without independent review.
