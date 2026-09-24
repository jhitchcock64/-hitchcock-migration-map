#!/bin/bash
set -e
export PYTHONHASHSEED=0
cd /home/claude/project
python3 01_extract_ancestors.py > /tmp/p01.log 2>&1
python3 02_extract_events.py > /tmp/p02.log 2>&1
python3 03_build_legs.py > /tmp/p03.log 2>&1
python3 04_build_routes.py > /tmp/p04.log 2>&1
cd /home/claude/build2
python3 build_anchors.py > /tmp/p05.log 2>&1
python3 build_family_tags.py > /tmp/p06.log 2>&1
python3 rebuild_all_data.py > /tmp/p07.log 2>&1
tail -6 /tmp/p07.log
