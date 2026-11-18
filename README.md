# rfikit

rfikit will find standard citations in engineering RFIs and return normalized designation keys. RFI here means request for information, not radio-frequency interference.

## Status

Being rebuilt. Version 0.1 is not released. The design is in [docs/spec.md](docs/spec.md) and the decisions are in [docs/adr](docs/adr/README.md). The package has data types and a stub command line only.

## Development quickstart

```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Contributions

Outside code contributions are not accepted. Bug reports by issue are fine.

## License

All rights reserved. You may view the code and run it to evaluate it. Commercial use needs a paid license from Mehmet Tuzunkan: https://www.linkedin.com/in/mstuzunkan
