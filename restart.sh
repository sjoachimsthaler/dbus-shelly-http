#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
DAEMON_NAME=${SCRIPT_DIR##*/}

pkill -f "python .*/$DAEMON_NAME.py"