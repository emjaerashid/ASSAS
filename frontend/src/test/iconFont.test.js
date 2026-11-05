import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

// index.html requests only a slice of the Material Symbols variable font
// (to keep the download small). Any font-variation-settings value outside
// that slice silently renders with the nearest available instance, so this
// test fails instead and points at the range to widen.

const ROOT = join(__dirname, '..', '..');

function requestedAxes() {
  const html = readFileSync(join(ROOT, 'index.html'), 'utf8');
  const match = html.match(/family=Material\+Symbols\+Outlined:([A-Za-z,]+)@([0-9.,-]+)/);
  if (!match) throw new Error('Material Symbols <link> not found in index.html');
  const names = match[1].split(',');
  const ranges = match[2].split(',').map((r) => {
    const [min, max = min] = r.split('..').map(Number);
    return { min, max };
  });
  return Object.fromEntries(names.map((name, i) => [name, ranges[i]]));
}

function sourceFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === 'test' ? [] : sourceFiles(path);
    return /\.(css|jsx?)$/.test(name) ? [path] : [];
  });
}

function usedSettings() {
  const used = [];
  for (const file of sourceFiles(join(ROOT, 'src'))) {
    const text = readFileSync(file, 'utf8');
    for (const [, value] of text.matchAll(/font-?[vV]ariation-?[sS]ettings['"]?\s*:\s*['"]?([^;}\n]+)/g)) {
      for (const [, axis, number] of value.matchAll(/'(\w+)'\s+(-?[\d.]+)/g)) {
        used.push({ file: file.slice(ROOT.length + 1), axis, value: Number(number) });
      }
    }
  }
  return used;
}

describe('Material Symbols font request', () => {
  it('covers every font-variation-settings value used in the app', () => {
    const axes = requestedAxes();
    const used = usedSettings();
    expect(used.length).toBeGreaterThan(0);

    const outside = used.filter(({ axis, value }) => {
      const range = axes[axis];
      return !range || value < range.min || value > range.max;
    });

    expect(
      outside.map(({ file, axis, value }) => `${file}: '${axis}' ${value} (requested ${JSON.stringify(axes[axis])})`),
      'Widen the Material Symbols axis ranges in index.html to include these values',
    ).toEqual([]);
  });
});
