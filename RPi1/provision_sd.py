#!/bin/bash
# kiosk-deploy.sh - Iterative Kiosk Asset Deployment

PI_USER="igg"
PI_HOST="SM-RPi1Ap-02"
SSH_TARGET="${PI_USER}@${PI_HOST}"
STAGING_DIR="/home/${PI_USER}/assets"

echo "Syncing local assets/ tree to staging on ${PI_HOST}..."
rsync -avz --delete assets/ ${SSH_TARGET}:${STAGING_DIR}/

echo "Ensuring execution permissions on the target..."
ssh ${SSH_TARGET} "chmod +x ${STAGING_DIR}/apply.sh"

echo "Executing deployment script as root. You will be prompted for igg's password."
ssh -t ${SSH_TARGET} "sudo ${STAGING_DIR}/apply.sh"
