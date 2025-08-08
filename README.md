# 4607GMTI (gmti4607)

A Pydantic-first Python package for reading, writing, displaying (lightweight), and converting **STANAG 4607** Ground Moving Target Indicator (GMTI) data.

> Status: **Scaffold** (parsers and codecs are stubs). Intended for porting the Erlang [`s4607`](https://github.com/pentlandedge/s4607) library and adding XML read/write support.

## Features (planned)
- Binary ⇄ Pydantic models (round-trip for supported segments)
- XML ⇄ Pydantic models (via `pydantic-xml`), with XSD validation
- Minimal verification plots
- CLI utilities
- Type-checking, linting, tests, CI

## Install (dev)
```bash
pip install -e '.[dev,xml,viz]'
```

## CLI
```bash
gmti4607 info sample.bin
gmti4607 to-xml sample.bin out.xml --validate
gmti4607 from-xml sample.xml out.bin
gmti4607 to-json sample.bin out.json
gmti4607 plot sample.bin --mode detections
```

## Layout
```
src/gmti4607/
  models/      # Pydantic models
  binary/      # binary reader/writer codecs
  xmlio/       # XML bindings
  viz.py       # tiny matplotlib helpers
  cli.py       # argparse-based CLI
```
