#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backward-compatible shared exports.

Protocol contracts now live in protocol_contracts_an.py.
Architecture guidance now lives in architecture_guidance_an.py.

Keep this file as a compatibility layer so existing imports from
.protocol_shared_an continue to work.
"""

from .protocol_contracts_an import *  # noqa: F401,F403
from .architecture_guidance_an import *  # noqa: F401,F403