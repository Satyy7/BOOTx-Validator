"""ARM64 exception-level (EL) observation.

BOOTX does not fabricate EL values. What is directly observable, without
any firmware patch, is TF-A's own BL31 exit-path logging: at LOG_LEVEL
INFO, ``common/bl_common.c:print_entry_point_info()`` prints the SPSR
that will be restored on ``ERET`` out of EL3, immediately after
"BL31: Preparing for EL3 exit to <security-state> world". SPSR bits[3:0]
(the "M" field, AArch64 mode) directly encode the target exception level
and SP-select, per the Armv8-A architecture reference manual (SPSR_EL3
format): this project decodes that field from the real printed value.

What is NOT directly observed: EL2/EL1 transitions inside U-Boot or
Linux, and secure/non-secure world switches after the initial BL31 exit.
Those would require either instrumenting U-Boot/Linux to log their own
current EL (e.g. reading CurrentEL) or a debug connection (QEMU GDB stub
reading system registers). BOOTX does not currently do either -- this is
documented as a limitation, not inferred from log text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SPSR_RE = re.compile(r"SPSR\s*=\s*0x([0-9a-fA-F]+)")
_EXIT_CONTEXT_RE = re.compile(r"BL31: Preparing for EL3 exit to (\w+) world")

_M_FIELD_TO_EL: dict[int, str] = {
    0b0000: "EL0t",
    0b0100: "EL1t",
    0b0101: "EL1h",
    0b1000: "EL2t",
    0b1001: "EL2h",
    0b1100: "EL3t",
    0b1101: "EL3h",
}


def decode_spsr_mode(spsr: int) -> str:
    """Decode the AArch64 'M' field (SPSR bits[3:0]) into an EL/SP name."""
    m_field = spsr & 0xF
    return _M_FIELD_TO_EL.get(m_field, f"UNKNOWN(0b{m_field:04b})")


@dataclass(frozen=True)
class ExceptionLevelObservation:
    security_state: str
    spsr_hex: str
    target_el: str
    evidence_line: str


def observe_bl31_exit(log_text: str) -> ExceptionLevelObservation | None:
    """Scan a captured boot log for TF-A's BL31 EL3-exit trace.

    Returns None if the log was captured at a LOG_LEVEL below INFO (the
    lines simply won't be present) rather than guessing a value.
    """
    lines = log_text.splitlines()
    for i, line in enumerate(lines):
        ctx = _EXIT_CONTEXT_RE.search(line)
        if not ctx:
            continue
        # SPSR is printed on one of the next few lines by print_entry_point_info().
        for follow in lines[i : i + 6]:
            spsr_match = _SPSR_RE.search(follow)
            if spsr_match:
                spsr = int(spsr_match.group(1), 16)
                return ExceptionLevelObservation(
                    security_state=ctx.group(1),
                    spsr_hex=spsr_match.group(0),
                    target_el=decode_spsr_mode(spsr),
                    evidence_line=follow,
                )
    return None
