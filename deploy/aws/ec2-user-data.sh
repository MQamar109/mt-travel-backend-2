#!/bin/bash
set -euxo pipefail

dnf update -y
dnf install -y docker git docker-compose-plugin
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

mkdir -p /home/ec2-user
cd /home/ec2-user
if [ ! -d mt-travel-backend-2 ]; then
  git clone __BACKEND_REPO__ mt-travel-backend-2
fi
chown -R ec2-user:ec2-user /home/ec2-user/mt-travel-backend-2

echo "EC2 bootstrap complete. Waiting for deploy script to configure .env and start Docker."
