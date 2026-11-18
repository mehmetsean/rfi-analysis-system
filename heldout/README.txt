Written held-out set for rfikit (synthetic data)

All data in this folder is synthetic. The RFIs were written by hand for this
repository. Project codes, role ids and disciplines are invented. No real
company, facility, project or person appears, and nothing comes from any
employer. Only standard designations and clause numbers appear, never titles
or standard text.

Files
- input/rfis.csv: rfi_id, subject, question, response.
- labels/citations.csv, labels/negatives.csv, labels/rfis.csv: the labels.
  In labels/rfis.csv the template_id is empty and the family is "written".
- source.txt: the marked-up text the files above are built from.
- manifest.json: sha256 of every file and counts.
- CHANGES.md: label fixes made after the first commit.
Rules for the labels are in docs/annotation_guide.md. One annotator labeled
the set, so there is no agreement measure.
Rebuild and check with: python scripts/build_heldout.py --check

License
All rights reserved. You may view the code and run it to evaluate it. Commercial use needs a paid license from Mehmet Tuzunkan: https://www.linkedin.com/in/mstuzunkan

Disclaimer
Decision support only, not legal, engineering, tax, accounting or assurance advice. No guarantee of compliance. rfikit does not say whether a standard applies or what it requires; check every citation against the official standard. False positives and misses are expected; the measured rates are shown.
The names IEEE, NESC, IEC, ANSI, ASTM and NEMA are used only to identify their documents. The names belong to their owners. This project has no affiliation with or endorsement from any of them.
