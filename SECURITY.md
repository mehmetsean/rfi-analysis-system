# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

## Report a problem

Report privately with GitHub private vulnerability reporting. Open the Security tab of this repo and choose "Report a vulnerability". If that is not possible, send a message through https://www.linkedin.com/in/mstuzunkan and do not put details in it. Please do not open a public issue for a security problem.

## In scope

- Reading CSV and text files you point rfikit at, and the input limits that guard it.
- Reading the column map file.
- The output files and folders, and the rules that refuse to replace the input, the column map file or a symbolic link.
- The writers for citations.csv, analysis.md, analysis.html and README.txt, including how spreadsheet formulas and control characters in cells are handled.
- The demo page in site/ and its content security policy.

## Out of scope

- The synthetic data. It has no real secrets.
- Problems in Python, Pyodide or other third-party tools. Report those to their own projects.

Decision support only, not legal, engineering, tax, accounting or assurance advice. No guarantee of compliance.
