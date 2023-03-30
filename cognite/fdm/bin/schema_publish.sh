#!/bin/bash
set -e
cd "${0%/*}/../.."

. fdm/bin/_functions.sh "$1"


SCHEMA_FILE=$(cat "$CONFIG" | extract 'schema_file')
SPACE=$(cat "$CONFIG" | extract 'space')
DATAMODEL=$(cat "$CONFIG" | extract 'datamodel')
SCHEMA_VERSION=$(cat "$CONFIG" | extract 'schema_version')

#echo cdf data-models publish --file="$SCHEMA_FILE" --space="$SPACE" --external-id="$DATAMODEL" --version="$SCHEMA_VERSION"
exec cdf data-models publish --file="$SCHEMA_FILE" --space="$SPACE" --external-id="$DATAMODEL" --version="$SCHEMA_VERSION"
