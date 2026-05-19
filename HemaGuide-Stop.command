#!/bin/bash
# HemaGuide Stop Script
# Double-click to stop the HemaGuide server

echo "Stopping HemaGuide..."
KILLED=0
pkill -f "python backend/main.py" 2>/dev/null && KILLED=1
pkill -f "python.*process_query_input.py" 2>/dev/null && KILLED=1
pkill -f "python.*agent.py" 2>/dev/null && KILLED=1
if [ $KILLED -eq 1 ]; then echo "HemaGuide stopped."; else echo "HemaGuide is not running."; fi
echo ""
echo "Press any key to close..."
read -n 1
