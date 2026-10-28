# Challenge 6 — Project Garden Gallery

This is the cross-platform Python edition of the Garden Gallery exercise.

- `evidence/` contains four synthetic candidate JPEGs and precomputed DCT histograms.
- `tools/` contains Python plotting, scoring, JPEG coefficient, extraction, and payload-decoding utilities.

## Student setup

No Linux-only executable or compiler is needed. Use Python 3.9–3.13 on Windows, macOS, or Linux. From the package root, install the dependencies with:

```text
python -m pip install -r requirements.txt
```

The core histogram investigation needs only NumPy and Matplotlib, because the coefficient CSVs are already provided. The optional JPEG coefficient extraction uses `pyjpegio`, installed from PyPI as `pyjpegio` and imported in Python as `jpegio`. PyPI provides prebuilt wheels for Windows, macOS, and Linux on common CPython 3.9–3.13 platforms; installing a wheel requires no compiler. See `requirements-extraction.txt` for that optional dependency.

Run the plotter:

```text
python tools/plot_histograms.py
```

Students can complete `tools/score_starter.py`. Once their forensic argument is accepted, install the optional extraction dependency and extract the teaching payload:

```text
python -m pip install -r requirements-extraction.txt
python tools/extract_payload.py img_0147.jpg recovered.bin
python tools/decode_container.py recovered.bin
```

The extraction script prompts for the passphrase supplied by the instructor.


a teaching implementation inspired by the matrix-encoding/shrinkage idea associated with F5. It is not an implementation byte-compatible with F5 and is not secure for real use.
