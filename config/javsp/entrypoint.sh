#!/bin/sh
# Run JavSP, then fix ownership for Unraid (nobody:users = 99:100)
python /app/JavSP.py "$@"
EXIT_CODE=$?

if [ -d /media/output ]; then
    chown -R 99:100 /media/output
    chmod -R u=rwX,g=rwX,o=rwX /media/output
fi

exit $EXIT_CODE
