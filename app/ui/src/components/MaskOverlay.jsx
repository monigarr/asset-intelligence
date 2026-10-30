import { useEffect, useRef } from 'react';
import { decodeMaskRle } from '../rle.js';
import { MIN_TARGET_PX, confidenceLabel, dashForLabel, pickMask } from './masks.js';

const LABEL_COLORS = {
  crack: [239, 68, 68],
  corrosion: [249, 115, 22],
  spall: [234, 179, 8],
  vegetation: [34, 197, 94],
  'water seepage': [59, 130, 246],
  'water intrusion': [59, 130, 246],
};
const DEFAULT_COLOR = [148, 163, 184];

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

function drawSchematic(ctx, width, height) {
  ctx.fillStyle = '#8f959c';
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = '#3f444a';
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(width * 0.2, height * 0.32);
  ctx.lineTo(width * 0.45, height * 0.42);
  ctx.lineTo(width * 0.7, height * 0.5);
  ctx.stroke();
  ctx.font = '13px system-ui, sans-serif';
  ctx.fillStyle = '#fff';
  ctx.strokeStyle = '#000';
  ctx.lineWidth = 3;
  const label = 'DEMO SCHEMATIC -- no image loaded';
  ctx.strokeText(label, 10, 20);
  ctx.fillText(label, 10, 20);
}

function paintRleFill(ctx, seg, width, height) {
  let decoded;
  try {
    decoded = decodeMaskRle(seg.rle);
  } catch {
    return; // undecodable RLE: bboxes below still render
  }
  if (!decoded) return;
  const off = document.createElement('canvas');
  off.width = decoded.width;
  off.height = decoded.height;
  const octx = off.getContext('2d');
  const img = octx.createImageData(decoded.width, decoded.height);
  const [r, g, b] = LABEL_COLORS[seg.label.toLowerCase()] || DEFAULT_COLOR;
  for (let i = 0; i < decoded.pixels.length; i++) {
    if (decoded.pixels[i]) {
      img.data[i * 4] = r;
      img.data[i * 4 + 1] = g;
      img.data[i * 4 + 2] = b;
      img.data[i * 4 + 3] = 90;
    }
  }
  octx.putImageData(img, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(off, 0, 0, width, height);
  ctx.imageSmoothingEnabled = true;
}

export default function MaskOverlay({
  imageUrl,
  overlayUrl,
  apiKey,
  width,
  height,
  segmentations,
  selectedMaskId,
  onMaskClick,
}) {
  const ref = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const canvas = ref.current;
    if (!canvas) return;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    (async () => {
      if (imageUrl) {
        try {
          const img = await loadImage(imageUrl);
          if (!cancelled) ctx.drawImage(img, 0, 0, width, height);
        } catch {
          if (!cancelled) drawSchematic(ctx, width, height);
        }
      } else {
        drawSchematic(ctx, width, height);
      }
      if (cancelled) return;
      let overlayDrawn = false;
      if (overlayUrl) {
        // Server overlay requires X-API-Key; a bare Image load 401s (console
        // error). Fetch with auth, decode via blob URL, revoke after draw.
        let blobUrl = null;
        try {
          let src = overlayUrl;
          if (apiKey) {
            const res = await fetch(overlayUrl, {
              headers: { 'X-API-Key': apiKey },
            });
            if (!res.ok) throw new Error(`overlay ${res.status}`);
            blobUrl = URL.createObjectURL(await res.blob());
            src = blobUrl;
          }
          const ov = await loadImage(src);
          if (!cancelled) {
            ctx.drawImage(ov, 0, 0, width, height);
            overlayDrawn = true;
          }
        } catch {
          /* fall through to client-side fills */
        } finally {
          if (blobUrl) URL.revokeObjectURL(blobUrl);
        }
      }
      if (cancelled) return;
      if (!overlayDrawn) {
        for (const seg of segmentations) {
          if (seg.rle) paintRleFill(ctx, seg, width, height);
        }
      }
      drawBoxes();

      function drawBoxes() {
        ctx.font = '13px system-ui, sans-serif';
        for (const seg of segmentations) {
          const [r, g, b] = LABEL_COLORS[seg.label.toLowerCase()] || DEFAULT_COLOR;
          const [x1, y1, x2, y2] = seg.bbox;
          ctx.strokeStyle = `rgb(${r},${g},${b})`;
          ctx.setLineDash(dashForLabel(seg.label));
          ctx.lineWidth = seg.mask_id === selectedMaskId ? 5 : 3;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
          ctx.setLineDash([]);
          if (seg.mask_id === selectedMaskId) {
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1;
            ctx.strokeRect(x1 - 3, y1 - 3, x2 - x1 + 6, y2 - y1 + 6);
          }
          const text = confidenceLabel(seg.label, seg.confidence);
          const ty = Math.max(13, y1 - 4);
          const tx = Math.max(4, Math.min(x1, width - ctx.measureText(text).width - 4));
          ctx.lineWidth = 3;
          ctx.strokeStyle = '#000';
          ctx.strokeText(text, tx, ty);
          ctx.fillStyle = '#fff';
          ctx.fillText(text, tx, ty);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [imageUrl, overlayUrl, apiKey, width, height, segmentations, selectedMaskId]);

  function onClick(e) {
    const canvas = ref.current;
    const rect = canvas.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * width;
    const y = ((e.clientY - rect.top) / rect.height) * height;
    const slop = (MIN_TARGET_PX / 2) * (width / rect.width);
    onMaskClick(pickMask(segmentations, x, y, slop));
  }

  return (
    <div className="overlay-wrap" data-tether-origin="1">
      <canvas
        ref={ref}
        onClick={onClick}
        style={{ cursor: 'crosshair' }}
        role="img"
        aria-label={`Defect overlay with ${segmentations.length} annotated masks`}
      />
      <div className="hint">Click a mask to highlight its evidence. Masks require human measurement.</div>
    </div>
  );
}
