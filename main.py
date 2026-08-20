#!/usr/bin/env python3
"""
HisiNve Main Entrypoint.
Automatically detects whether CLI arguments were provided or launches the interactive wizard.
"""
import sys
import os

if len(sys.argv) > 1:
    from hisi_nve_cli import main
    main()
else:
    from hisi_nve_interactive import main
    main()
