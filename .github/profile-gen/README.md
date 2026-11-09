# Profile panel generator

Rebuilds the animated SVG panels in `/assets` (all text is converted to outlines so it renders the same everywhere).

```bash
pip install fonttools
# fonts from github.com/google/fonts: ofl/anton, ofl/archivo, ofl/dmmono, ofl/caveat
FONT_DIR=path/to/google-fonts/ofl/ python gen.py ../../assets
```

Edit the text in the `hero()` function and the `REPOS` list, then re-run.
