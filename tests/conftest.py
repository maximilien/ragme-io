# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings

# Filter out SWIG-related deprecation warnings
warnings.filterwarnings(
    "ignore",
    message="builtin type swigvarlink has no __module__ attribute",
    category=DeprecationWarning,
)

# Filter out other common deprecation warnings from dependencies
warnings.filterwarnings(
    "ignore",
    message=".*deprecated.*",
    category=DeprecationWarning,
)
