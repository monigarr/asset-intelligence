// COCO RLE decoder — JS port of app/sam_service decode_coco_rle.
// counts: uncompressed integer runs starting with background, column-major.
// Returns { width, height, pixels } with row-major 0/1 pixels.

export function decodeCocoRle(counts, height, width) {
  if (!Number.isInteger(height) || !Number.isInteger(width) || height <= 0 || width <= 0) {
    throw new Error(`invalid RLE size [${height}, ${width}]`);
  }
  if (!Array.isArray(counts)) throw new Error('RLE counts must be an array of ints');
  const total = height * width;
  const flat = new Uint8Array(total); // column-major work buffer
  let pos = 0;
  let foreground = 0;
  for (const run of counts) {
    if (!Number.isInteger(run) || run < 0) throw new Error(`invalid RLE run ${run}`);
    flat.fill(foreground, pos, pos + run);
    pos += run;
    foreground = foreground ? 0 : 1;
  }
  if (pos !== total) throw new Error(`RLE counts sum to ${pos}, expected ${total}`);
  // Transpose column-major -> row-major for canvas ImageData.
  const pixels = new Uint8Array(total);
  for (let c = 0; c < width; c++) {
    for (let r = 0; r < height; r++) {
      pixels[r * width + c] = flat[c * height + r];
    }
  }
  return { width, height, pixels };
}

export function decodeMaskRle(rle) {
  if (rle == null) return null;
  if (typeof rle === 'string') throw new Error('compressed RLE strings not supported');
  if (typeof rle !== 'object' || !Array.isArray(rle.size) || rle.size.length !== 2) {
    throw new Error('invalid RLE payload (want {size: [h, w], counts: [...]})');
  }
  const [height, width] = rle.size;
  if (typeof rle.counts === 'string') throw new Error('compressed RLE strings not supported');
  return decodeCocoRle(rle.counts, height, width);
}
