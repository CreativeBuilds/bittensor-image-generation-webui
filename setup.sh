#!/bin/sh

# Install venv (if not already installed)
python -m pip install --user virtualenv

# Create virtual environment
python -m venv venv

# output string "source venv/bin/activate" to terminal
echo "\nVenv installed, please run\n\`source venv/bin/activate\` (linux)\n\`venv\\Scripts\\activate\` (windows)\nto activate the virtual environment\n"