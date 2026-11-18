# rfikit analysis

The input is synthetic data.

## Summary

| Item | Count |
|---|---|
| RFIs read | 200 |
| Citations found | 324 |
| RFIs with at least one citation | 191 |

## Top base keys (up to 20)

NESC (no rule given) counts citations to the NESC, also written as ANSI C2 or IEEE C2, that give no rule, table or section, such as an edition alone. It is not a count of one rule.

| Base key | Citations |
|---|---|
| NESC (no rule given) | 64 |
| NESC Rule 238 | 7 |
| ANSI C84.1 | 6 |
| ASTM A153/A153M | 6 |
| NESC Rule 250B | 6 |
| IEC 62271-1 | 5 |
| ANSI C12.1 | 4 |
| ANSI C12.20 | 4 |
| ANSI C63.4 | 4 |
| IEC 61850-8-1 | 4 |
| IEEE 1547.1 | 4 |
| IEEE C57.12.00 | 4 |
| IEEE C57.12.90 | 4 |
| NEMA FB 1 | 4 |
| NEMA MG 1 | 4 |
| NEMA VE 1 | 4 |
| NESC Rule 234B | 4 |
| ANSI O5.1 | 3 |
| ASTM A123/A123M | 3 |
| ASTM D257 | 3 |

## Citations per body

| Body | Citations |
|---|---|
| NESC | 107 |
| IEEE | 68 |
| NEMA | 43 |
| ASTM | 39 |
| ANSI | 34 |
| IEC | 33 |

## Citations per RFI

How many RFIs have each number of citations.

| Citations | RFIs |
|---|---|
| 0 | 9 |
| 1 | 80 |
| 2 | 98 |
| 3 | 4 |
| 4 | 9 |

## RFIs with the most citations (up to 10)

| RFI id | Citations |
|---|---|
| R0044 | 4 |
| R0047 | 4 |
| R0068 | 4 |
| R0071 | 4 |
| R0075 | 4 |
| R0087 | 4 |
| R0109 | 4 |
| R0141 | 4 |
| R0168 | 4 |
| R0003 | 3 |

## Extraction rates, measured on synthetic data

Measured on synthetic data: generated sets A and B from rfikit.synth and the written set in heldout/.

| Method | Set | Level | Precision | Recall | F1 |
|---|---|---|---|---|---|
| rfikit | Family A, report seeds | strict span | 0.995 | 0.948 | 0.971 |
| rfikit | Family A, report seeds | overlap span | 1.000 | 0.952 | 0.976 |
| rfikit | Family A, report seeds | full key | 0.995 | 0.948 | 0.971 |
| rfikit | Family A, report seeds | base key | 0.999 | 0.952 | 0.975 |
| rfikit | Family A, report seeds | clause | 1.000 | 0.968 | 0.984 |
| naive baseline | Family A, report seeds | strict span | 0.362 | 0.385 | 0.373 |
| naive baseline | Family A, report seeds | overlap span | 0.688 | 0.732 | 0.709 |
| naive baseline | Family A, report seeds | full key | n/a | n/a | n/a |
| naive baseline | Family A, report seeds | base key | n/a | n/a | n/a |
| naive baseline | Family A, report seeds | clause | n/a | n/a | n/a |
| prototype regexes | Family A, report seeds | strict span | 0.529 | 0.289 | 0.374 |
| prototype regexes | Family A, report seeds | overlap span | 0.870 | 0.475 | 0.615 |
| prototype regexes | Family A, report seeds | full key | n/a | n/a | n/a |
| prototype regexes | Family A, report seeds | base key | n/a | n/a | n/a |
| prototype regexes | Family A, report seeds | clause | n/a | n/a | n/a |
| rfikit | Family B, report seeds | strict span | 0.992 | 0.919 | 0.954 |
| rfikit | Family B, report seeds | overlap span | 1.000 | 0.926 | 0.962 |
| rfikit | Family B, report seeds | full key | 0.991 | 0.918 | 0.953 |
| rfikit | Family B, report seeds | base key | 0.998 | 0.925 | 0.960 |
| rfikit | Family B, report seeds | clause | 1.000 | 0.932 | 0.965 |
| naive baseline | Family B, report seeds | strict span | 0.366 | 0.502 | 0.423 |
| naive baseline | Family B, report seeds | overlap span | 0.682 | 0.936 | 0.789 |
| naive baseline | Family B, report seeds | full key | n/a | n/a | n/a |
| naive baseline | Family B, report seeds | base key | n/a | n/a | n/a |
| naive baseline | Family B, report seeds | clause | n/a | n/a | n/a |
| prototype regexes | Family B, report seeds | strict span | 0.481 | 0.319 | 0.383 |
| prototype regexes | Family B, report seeds | overlap span | 0.880 | 0.583 | 0.702 |
| prototype regexes | Family B, report seeds | full key | n/a | n/a | n/a |
| prototype regexes | Family B, report seeds | base key | n/a | n/a | n/a |
| prototype regexes | Family B, report seeds | clause | n/a | n/a | n/a |
| rfikit | Written set | strict span | 0.994 | 0.957 | 0.975 |
| rfikit | Written set | overlap span | 1.000 | 0.962 | 0.981 |
| rfikit | Written set | full key | 0.994 | 0.957 | 0.975 |
| rfikit | Written set | base key | 1.000 | 0.962 | 0.981 |
| rfikit | Written set | clause | 1.000 | 1.000 | 1.000 |
| naive baseline | Written set | strict span | 0.585 | 0.611 | 0.598 |
| naive baseline | Written set | overlap span | 0.834 | 0.870 | 0.852 |
| naive baseline | Written set | full key | n/a | n/a | n/a |
| naive baseline | Written set | base key | n/a | n/a | n/a |
| naive baseline | Written set | clause | n/a | n/a | n/a |
| prototype regexes | Written set | strict span | 0.553 | 0.395 | 0.461 |
| prototype regexes | Written set | overlap span | 0.955 | 0.681 | 0.795 |
| prototype regexes | Written set | full key | n/a | n/a | n/a |
| prototype regexes | Written set | base key | n/a | n/a | n/a |
| prototype regexes | Written set | clause | n/a | n/a | n/a |

## License

All rights reserved. You may view the code and run it to evaluate it. Commercial use needs a paid license from Mehmet Tuzunkan: https://www.linkedin.com/in/mstuzunkan

## Disclaimer

Decision support only, not legal, engineering, tax, accounting or assurance advice. No guarantee of compliance. rfikit does not say whether a standard applies or what it requires; check every citation against the official standard. False positives and misses are expected; the measured rates are shown.

Body names such as IEEE, NESC, IEC, ANSI, ASTM, NEMA, NFPA, UL, ASME, ISA, TIA, CSA and EN are used only to identify their documents. The names belong to their owners. This project has no affiliation with or endorsement from any of them.
