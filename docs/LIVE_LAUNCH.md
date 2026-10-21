# Quantized phrase launch — host-side planner

Queue a phrase (or silence) for an individual track at the next row,
beat, bar or phrase boundary. Last request wins per track. A pure function
returns due launches; a future SLOOP integration must apply them at its
existing transport clock boundary.

The reference model assumes 4 rows/beat and 4 beats/bar by default.
Actual grid conversion must derive from SLOOP DIV and time settings.
No note-off management, audio scheduling, firmware integration or
hardware testing is implied by this module.
