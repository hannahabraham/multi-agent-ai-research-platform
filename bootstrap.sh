#!/bin/bash
set -e

REGION=$(1:-us-east-1)
BUCKET="research-agent-tfstate"
TABLE="research-agent-tf-locks"

echo "Creating S3 bucket: $BUCKET in region: $REGION"

if []

