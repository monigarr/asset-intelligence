# Review UI

Minimal human-review surface for Asset Intelligence: upload inspections,
view SAM overlays, read evidence-linked JSON, work the missing-info
checklist, and accept / edit / reject. React + Vite + Canvas. No Streamlit.

## Run

```bash
cd app/ui
npm install
npm run dev      # http://localhost:3000 (proxies /v1 to :8000)
```

`npm test` runs the vitest suite (RLE decoder + fixture validation). `npm run build` produces
`dist/` for the Day-7 container.

## Modes

- **Demo**: no backend needed. Pick a fixture from the dropdown; the UI loads
  its committed image + result JSON (`public/fixtures/`, shipped in the build)
  with client-side RLE fills — clearly marked as fixture data, and you can still
  run the same image live via API mode.
- **API**: uploads 1–5 images + note to the Day-7 backend
  (`POST /v1/inspections`, polls `GET /v1/inspections/{id}`), fetches the
  server overlay PNG when available, and posts review decisions to
  `POST /v1/inspections/{id}/review`. The form accepts incremental adds
  (browse or drag-and-drop) with per-file remove, and validates type/size/count.
## Overlay sources (in order)

1. Server-rendered PNG from `GET /v1/inspections/{id}/overlay?image=N`
   (preferred — same renderer as `app/sam_service/overlay.py`).
2. Client-side COCO RLE decode from `segmentations[].rle`
   (`src/rle.js`, tested against the same vectors as the Python decoder).
3. Bboxes + labels only, when a mask has no RLE.

Clicking a mask highlights every evidence chip citing that `mask_id`;
clicking a note-span chip highlights the span in the note.

## Windows network-share note

If this repo lives on a UNC path (`\\server\...`), run npm from a local
copy or a mapped drive — npm postinstall scripts (esbuild) fail when
`cmd.exe` starts in a UNC working directory:

```powershell
Copy-Item app\ui $env:TEMP\ai-ui -Recurse
cd $env:TEMP\ai-ui
npm install
npm run dev
```

## Header

Brand left (“Asset Intelligence / by ManageAssets.ca”), icon-only nav right
(contact, GitHub) plus a tab bar (Demo, New inspection, About). About copy lives in `src/components/about.js` —
paste the YouTube URL into `YOUTUBE_URL` when it ships.
