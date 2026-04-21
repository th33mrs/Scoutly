"""
Add a skill to your resume in config.py.
Usage: python add_skill.py "Terraform" "Tools & Systems"
       python add_skill.py "FastAPI"   (defaults to Tools & Systems)
"""

import sys
import re

if len(sys.argv) < 2:
    print("Usage: python add_skill.py SKILL_NAME [SECTION]")
    print("Sections: 'Tools & Systems', 'NLP & Data', 'Cloud Platforms',")
    print("          'Databases', 'Languages', 'Security',")
    print("          'Notifications & Integrations'")
    sys.exit(1)

skill = sys.argv[1]
section = sys.argv[2] if len(sys.argv) > 2 else "Tools & Systems"

with open("config.py", "r") as f:
    content = f.read()

# Check if skill already exists
if skill.lower() in content.lower():
    print("'{}' is already in your resume.".format(skill))
    sys.exit(0)

# Find the section line and append the skill
lines = content.split("\n")
updated = False

for i, line in enumerate(lines):
    if line.strip().startswith(section):
        # Add skill to the end of this line
        lines[i] = line.rstrip() + ", " + skill
        updated = True
        break

if updated:
    with open("config.py", "w") as f:
        f.write("\n".join(lines))
    print("Added '{}' to '{}'".format(skill, section))
    print("Updated line: {}".format(lines[i].strip()[:80]))
else:
    print("Section '{}' not found in config.py".format(section))

