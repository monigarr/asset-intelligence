// Committed demo fixtures (public/fixtures/, shipped in the build).
// Each fixture: a real case image + note + the live pipeline's result JSON.

export function fixtureUrls(id) {
  return { json: `/fixtures/${id}.json`, image: `/fixtures/${id}.jpg` };
}

export async function loadFixtureIndex() {
  const res = await fetch('/fixtures/index.json');
  if (!res.ok) throw new Error(`fixture index failed: ${res.status}`);
  const list = await res.json();
  if (!Array.isArray(list) || !list.length) {
    throw new Error('fixture index is empty');
  }
  return list;
}

// See App.jsx: retain pending preloads against GC before load settles.
const pendingImages = new Set();

function imageDims(url) {
  return new Promise((resolve) => {
    const img = new Image();
    pendingImages.add(img);
    const done = (value) => {
      pendingImages.delete(img);
      resolve(value);
    };
    img.onload = () => done({ width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => done({ width: 800, height: 600 });
    img.src = url;
  });
}

export async function loadFixture(id) {
  const { json, image } = fixtureUrls(id);
  const res = await fetch(json);
  if (!res.ok) throw new Error(`fixture ${id} failed: ${res.status}`);
  const data = await res.json();
  const dims = await imageDims(image);
  return {
    data,
    imageUrl: image,
    width: dims.width || data.width || 800,
    height: dims.height || data.height || 600,
  };
}
