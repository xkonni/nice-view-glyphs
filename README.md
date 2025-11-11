# nice-view-glyphs module

Glyph-based pattern variant of the nice!view shield for ZMK. It provides a glyph pattern image region (1‑bit indexed LVGL images) plus status widgets.

## Features

- Ten selectable pattern images (`pattern1`..`pattern10`) generated from a Unicode glyph (default ★ `f005`).
- Config flag `CONFIG_NICE_VIEW_WIDGET_PATTERN` chooses which pattern to display.
- Optional inversion via `CONFIG_NICE_VIEW_WIDGET_INVERTED` (palette swap).
- Battery, connection, layer, WPM (central side) or simplified peripheral status.
- 1‑bit images keep RAM usage minimal (140x68 => 1224 bytes each).

## Directory Layout

```
boards/shields/nice_view_glyphs/
  CMakeLists.txt
  Kconfig.*
  nice_view_glyphs.overlay / .conf / .zmk.yml
  widgets/
    art.c (generated)
    bolt.c (icon) / peripheral_status.* / status.* / util.*
assets/
  generate_images.py (image generator)
```

## Generating Pattern Art

Orientation model (no explicit rotate flag): you design logically in portrait (`68x140`) or landscape (`140x68`). For portrait, the script internally rotates to the stored landscape descriptor size (`140x68`).

Setup a virtualenv and install Pillow:

```bash
virtualenv .venv
. .venv/bin/activate
pip install Pillow
```

Regenerate all pattern images (overwrites `widgets/art.c`):

```bash
# Portrait design (default) for glyph ★ (f005)
python3 assets/generate_images.py --glyph f005 --mode art --orientation portrait

# Landscape design (no rotation applied)
python3 assets/generate_images.py --glyph f005 --mode art --orientation landscape
```

Preview patterns as PNGs (saved in `previews/`):

```bash
python3 assets/generate_images.py --glyph f005 --mode previews --orientation portrait
python3 assets/generate_images.py --glyph f005 --mode previews --orientation landscape
```

Environment override: export `CONFIG_NICE_VIEW_WIDGET_GLYPH=f1e1` (for example) and omit `--glyph`; the script will use the env value. Use a plain hex string without a `0x` prefix.

Use any hex codepoint (e.g. `f005` for ★). Do not include `0x`; just the hex digits. Non-hex input falls back to `f005`.

## Configuration Options

Current default glyph previews (★ `f005`):

| Pattern | Image | | | | | | | | |
|---------|-------|---------|-------|---------|-------|---------|-------|---------|-------|
| 1 | ![pattern1](previews/f005_pattern1.png) | 2 | ![pattern2](previews/f005_pattern2.png) | 3 | ![pattern3](previews/f005_pattern3.png) | 4 | ![pattern4](previews/f005_pattern4.png) | 5 | ![pattern5](previews/f005_pattern5.png) |
| 6 | ![pattern6](previews/f005_pattern6.png) | 7 | ![pattern7](previews/f005_pattern7.png) | 8 | ![pattern8](previews/f005_pattern8.png) | 9 | ![pattern9](previews/f005_pattern9.png) | 10 | ![pattern10](previews/f005_pattern10.png) |

Add to your shield `.conf` or board config:

```conf
CONFIG_NICE_VIEW_WIDGET_STATUS=y
CONFIG_NICE_VIEW_WIDGET_PATTERN=3       # show pattern3
CONFIG_NICE_VIEW_WIDGET_GLYPH="f005"    # plain hex (no 0x) used to generate art
CONFIG_NICE_VIEW_WIDGET_AUTO_GEN=y      # regenerate art.c during build
CONFIG_NICE_VIEW_WIDGET_ORIENTATION="landscape" # optional, defaults to portrait
#CONFIG_NICE_VIEW_WIDGET_INVERTED=y     # optional invert
```

Switch patterns without recompiling the generator—just change `CONFIG_NICE_VIEW_WIDGET_PATTERN` and rebuild firmware.

Changing the glyph requires regenerating `art.c` externally. The `CONFIG_NICE_VIEW_WIDGET_GLYPH` value is advisory for now (documents which glyph the images represent).

If you enable `CONFIG_NICE_VIEW_WIDGET_AUTO_GEN`, the build system will call the generator script automatically with the glyph in `CONFIG_NICE_VIEW_WIDGET_GLYPH` (and optional `CONFIG_NICE_VIEW_WIDGET_ORIENTATION` exported in your env). This is convenient while iterating on patterns, but not recommended for CI unless fonts are guaranteed.

When AUTO_GEN runs it now creates a temporary virtualenv (`<build>/nice_view_glyphs_venv`), installs/upgrades `pip` and `Pillow`, and invokes the generator inside that environment. This keeps host Python clean and avoids dependency collisions.

To regenerate using the Kconfig glyph value:

```bash
export CONFIG_NICE_VIEW_WIDGET_GLYPH=f005
python3 assets/generate_images.py --mode art --orientation portrait
```

Or specify directly:

```bash
python3 assets/generate_images.py --glyph f11c --mode art
```

## Adding Module via west

In your `config/west.yml` add a project entry pointing to your fork:

```yml
manifest:
  remotes:
    - name: yourfork
      url-base: https://github.com/yourname
  projects:
    - name: zmk
      remote: zmkfirmware
      revision: main
      import: app/west.yml
  - name: nice-view-glyphs
      remote: yourfork
      revision: main
  self:
    path: config
```

Then in your `build.yaml` replace the shield line:

```yml
include:
  - board: nice_nano_v2
  shield: urchin_left nice_view_adapter nice_view_glyphs
  - board: nice_nano_v2
  shield: urchin_right nice_view_adapter nice_view_glyphs
```

## Fallback to Built-in Status Screen

Disable the custom widget:

```conf
CONFIG_ZMK_DISPLAY_STATUS_SCREEN_BUILT_IN=y
```

## Customizing Patterns Further

Edit `PATTERNS` in `assets/generate_images.py` (list of `(cx, cy, size)` tuples). Re-run art mode. Keep placements within the 140x68 bounds. Use consistent sizes for aesthetic balance.

## Troubleshooting

- Empty images? Ensure Pillow is installed and a Nerd/Cascadia/Caskaydia font exists in macOS font paths.
- Wrong glyph? Verify hex passed to `--glyph` (no leading `0x` needed).
- Inversion looks off? Toggle `CONFIG_NICE_VIEW_WIDGET_INVERTED`.

## CI (GitHub Actions) Setup

If you enable `CONFIG_NICE_VIEW_WIDGET_AUTO_GEN` in a GitHub Actions pipeline, ensure Python, Pillow, and a suitable font are present. Two approaches:

1. System package + download font:
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Python deps
        run: |
          python3 -m pip install --upgrade pip
          pip install Pillow
      - name: Install font
        run: |
          mkdir -p ~/.local/share/fonts
          curl -L -o ~/.local/share/fonts/CascadiaCodeNF.ttf https://github.com/ryanoasis/nerd-fonts/releases/latest/download/CascadiaCode.zip
          unzip CascadiaCode.zip -d nerd-fonts
          cp nerd-fonts/*.ttf ~/.local/share/fonts/ || true
          fc-cache -f || true
      - name: Regenerate art (optional pre-build)
        run: |
          python3 assets/generate_images.py --glyph f005 --mode art --orientation portrait
      - name: Zephyr/ZMK build
        run: |
          west build -b nice_nano_v2 -- -DSHIELD="urchin_left;nice_view_adapter;nice_view_glyphs"
```

2. Bundled font: commit a Nerd font (license permitting) into `assets/fonts/YourFont.ttf`. The script will find it automatically; just install Pillow:
```yaml
      - name: Install Pillow
        run: pip install Pillow
```

Notes:
- Keep AUTO_GEN disabled in CI if fonts are unreliable; pre-generate `art.c` locally and commit.
- Use caching (`actions/cache`) for west/Zephyr modules to speed builds.
- Avoid downloading large entire font archives; grab only needed .ttf files.

## License

MIT (inherits original nice!view licensing from ZMK Contributors).

## Next Steps

- Automate art regeneration in CI.
- Add more pattern presets or animation support.
- Provide multi-glyph selection via additional Kconfig options.
