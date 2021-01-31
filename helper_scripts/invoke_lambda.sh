set -ex

FN_NAME="data_producer_kinesis-tumbling-window-analytics-producer-stack"

aws lambda invoke \
    --cli-binary-format raw-in-base64-out \
    --function-name "${FN_NAME}" \
    --payload '{ "name": "KON" }' \
    response.json