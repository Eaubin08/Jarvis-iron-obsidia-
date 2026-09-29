# Architecture status

Current state: DISCOVERY / ORGAN SELECTION

J1-D is intentionally PAUSED.

Reason:
The project first needs an organ-by-organ donor comparison. Running one donor
as the de facto product before that comparison would bias the architecture
toward that donor.

Current invariant:

EXTERNAL PROJECTS
       |
       v
DONOR AUDIT
       |
       v
ORGAN SELECTION
       |
       v
JARVIS-OWNED ARCHITECTURE
       |
       v
ADAPTERS / REIMPLEMENTATIONS
       |
       v
INTEGRATION TESTS

Personal Jarvis installation is retained as donor evidence and future test
fixture. It is not the architectural base.
