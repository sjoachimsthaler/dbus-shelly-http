#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}"  )" &> /dev/null && pwd  )
DAEMON_NAME=${SCRIPT_DIR##*/}

rm /service/$DAEMON_NAME
pkill -f "python .*/$DAEMON_NAME.py"
pkill -f "supervise $DAEMON_NAME"
chmod a-x $SCRIPT_DIR/service/run
$SCRIPT_DIR/restart.sh
