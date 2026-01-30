#!/bin/bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
echo "Starting git push at $(date)"
git push -u origin main --force 2>&1
echo "Push completed at $(date)"
