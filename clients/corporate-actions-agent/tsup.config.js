/** @type {import('tsup').Options} */
module.exports = {
  dts: false, // Disable DTS generation temporarily
  minify: false,
  bundle: true,
  sourcemap: true,
  treeshake: true,
  splitting: false,
  clean: true,
  outDir: 'dist',
  entry: ['src/index.ts'],
  format: ['cjs'],
};
