#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/Library/Python/3.13/bin:$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPT_DIR/../../mt-travel-frontend" ]]; then
  WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
elif [[ -d "$SCRIPT_DIR/../../../mt-travel-frontend" ]]; then
  WORKSPACE_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
else
  die "Cannot find mt-travel-frontend directory near $SCRIPT_DIR"
fi
FRONTEND_DIR="$WORKSPACE_DIR/mt-travel-frontend"
BACKEND_DIR="$WORKSPACE_DIR/mt-travel-backend-2"
KEYS_DIR="$SCRIPT_DIR/keys"
STATE_FILE="$SCRIPT_DIR/.deploy-state.env"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [command]

Commands:
  all          Full deploy: EC2 backend + S3/CloudFront frontend (default)
  backend      Launch/update EC2 backend only
  frontend     Build and publish frontend to S3/CloudFront
  status       Show deployed URLs and resource IDs
  destroy      Tear down AWS resources created by this script

Setup:
  1. cp config.env.example config.env
  2. aws configure
  3. ./deploy.sh all
EOF
}

load_config() {
  if [[ ! -f "$SCRIPT_DIR/config.env" ]]; then
    die "Missing config.env — copy config.env.example to config.env first."
  fi
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/config.env"
  : "${AWS_REGION:=us-east-1}"
  : "${PROJECT_NAME:=mt-travel}"
  : "${EC2_INSTANCE_TYPE:=t3.micro}"
  : "${EC2_KEY_NAME:=mt-travel-deploy-key}"
  : "${BACKEND_REPO:=https://github.com/MQamar109/mt-travel-backend-2.git}"
}

save_state() {
  mkdir -p "$SCRIPT_DIR"
  cat >"$STATE_FILE" <<EOF
INSTANCE_ID=${INSTANCE_ID:-}
PUBLIC_IP=${PUBLIC_IP:-}
PUBLIC_DNS=${PUBLIC_DNS:-}
SECURITY_GROUP_ID=${SECURITY_GROUP_ID:-}
S3_BUCKET=${S3_BUCKET:-}
CLOUDFRONT_ID=${CLOUDFRONT_ID:-}
CLOUDFRONT_DOMAIN=${CLOUDFRONT_DOMAIN:-}
OAC_ID=${OAC_ID:-}
KEY_PAIR_NAME=${KEY_PAIR_NAME:-}
EOF
}

load_state() {
  if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1091
    source "$STATE_FILE"
  fi
}

ensure_prereqs() {
  require_cmd aws
  require_cmd ssh
  require_cmd curl
  require_cmd openssl
  require_cmd yarn

  log "Checking AWS credentials..."
  AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
  export AWS_ACCOUNT_ID
  log "AWS account: $AWS_ACCOUNT_ID (region: $AWS_REGION)"
}

generate_secrets() {
  : "${SECRET_KEY:=$(openssl rand -hex 32)}"
  : "${DB_PASSWORD:=$(openssl rand -hex 16)}"
  export SECRET_KEY DB_PASSWORD
}

ensure_key_pair() {
  mkdir -p "$KEYS_DIR"
  KEY_FILE="$KEYS_DIR/${EC2_KEY_NAME}.pem"
  KEY_PAIR_NAME="$EC2_KEY_NAME"

  if aws ec2 describe-key-pairs --key-names "$EC2_KEY_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    log "Using existing key pair: $EC2_KEY_NAME"
  else
    log "Creating key pair: $EC2_KEY_NAME"
    aws ec2 create-key-pair \
      --key-name "$EC2_KEY_NAME" \
      --region "$AWS_REGION" \
      --query KeyMaterial \
      --output text >"$KEY_FILE"
    chmod 400 "$KEY_FILE"
  fi

  if [[ ! -f "$KEY_FILE" ]]; then
    die "Key file missing at $KEY_FILE. Delete the key pair in AWS and re-run, or place the .pem file there."
  fi
  export KEY_FILE
}

ensure_security_group() {
  if [[ -n "${SECURITY_GROUP_ID:-}" ]] && aws ec2 describe-security-groups --group-ids "$SECURITY_GROUP_ID" --region "$AWS_REGION" >/dev/null 2>&1; then
    log "Using existing security group: $SECURITY_GROUP_ID"
    return
  fi

  VPC_ID="$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text --region "$AWS_REGION")"
  SECURITY_GROUP_ID="$(aws ec2 create-security-group \
    --group-name "${PROJECT_NAME}-sg" \
    --description "MT Travel app security group" \
    --vpc-id "$VPC_ID" \
    --region "$AWS_REGION" \
    --query GroupId \
    --output text)"

  aws ec2 authorize-security-group-ingress --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0 --region "$AWS_REGION" >/dev/null || true
  aws ec2 authorize-security-group-ingress --group-id "$SECURITY_GROUP_ID" --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region "$AWS_REGION" >/dev/null || true

  log "Created security group: $SECURITY_GROUP_ID"
}

get_latest_amazon_linux_ami() {
  aws ec2 describe-images \
    --owners amazon \
    --filters Name=name,Values='al2023-ami-2023*-kernel-6.1-x86_64' Name=state,Values=available \
    --query 'sort_by(Images,&CreationDate)[-1].ImageId' \
    --output text \
    --region "$AWS_REGION"
}

launch_ec2() {
  if [[ -n "${INSTANCE_ID:-}" ]]; then
    STATE="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo terminated)"
    if [[ "$STATE" == "running" ]]; then
      PUBLIC_IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
      PUBLIC_DNS="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --query 'Reservations[0].Instances[0].PublicDnsName' --output text)"
      log "EC2 already running: $INSTANCE_ID ($PUBLIC_IP)"
      return
    fi
  fi

  AMI_ID="$(get_latest_amazon_linux_ami)"
  USER_DATA_FILE="$(mktemp)"
  sed \
    -e "s|__BACKEND_REPO__|$BACKEND_REPO|g" \
    "$SCRIPT_DIR/ec2-user-data.sh" >"$USER_DATA_FILE"

  log "Launching EC2 instance ($EC2_INSTANCE_TYPE)..."
  INSTANCE_ID="$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$EC2_INSTANCE_TYPE" \
    --key-name "$EC2_KEY_NAME" \
    --security-group-ids "$SECURITY_GROUP_ID" \
    --user-data "file://$USER_DATA_FILE" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT_NAME}-backend}]" \
    --region "$AWS_REGION" \
    --query 'Instances[0].InstanceId' \
    --output text)"
  rm -f "$USER_DATA_FILE"

  log "Waiting for EC2 instance to run: $INSTANCE_ID"
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$AWS_REGION"
  PUBLIC_IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
  PUBLIC_DNS="$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --query 'Reservations[0].Instances[0].PublicDnsName' --output text)"
  log "EC2 public IP: $PUBLIC_IP"
}

wait_for_ssh() {
  log "Waiting for SSH on $PUBLIC_IP..."
  for _ in $(seq 1 60); do
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "$KEY_FILE" "ec2-user@$PUBLIC_IP" "echo ok" >/dev/null 2>&1; then
      log "SSH is ready."
      return
    fi
    sleep 10
  done
  die "Timed out waiting for SSH on $PUBLIC_IP"
}

configure_backend_on_ec2() {
  [[ -n "${CLOUDFRONT_DOMAIN:-}" ]] || die "CloudFront domain required before configuring backend."

  CORS_ORIGIN="https://${CLOUDFRONT_DOMAIN}"
  EMAIL_USER="${EMAIL_HOST_USER:-}"
  EMAIL_PASS="${EMAIL_HOST_PASSWORD:-}"

  log "Writing backend .env and starting Docker on EC2..."
  ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@$PUBLIC_IP" bash -s <<EOF
set -euo pipefail
cd ~/mt-travel-backend-2
OLD_EMAIL=\$(grep -E '^EMAIL_HOST_USER=' .env 2>/dev/null | cut -d= -f2- || true)
OLD_PASS=\$(grep -E '^EMAIL_HOST_PASSWORD=' .env 2>/dev/null | cut -d= -f2- || true)
git fetch origin main
git reset --hard origin/main
EMAIL_USER="${EMAIL_USER}"
EMAIL_PASS="${EMAIL_PASS}"
if [[ -z "\$EMAIL_USER" && -n "\$OLD_EMAIL" ]]; then EMAIL_USER="\$OLD_EMAIL"; fi
if [[ -z "\$EMAIL_PASS" && -n "\$OLD_PASS" ]]; then EMAIL_PASS="\$OLD_PASS"; fi
cat > .env <<ENV
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${PUBLIC_DNS},${CLOUDFRONT_DOMAIN},${PUBLIC_IP}
DB_NAME=tms_db
DB_USER=tms_user
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=db
DB_PORT=5432
CORS_ALLOWED_ORIGINS=${CORS_ORIGIN}
CSRF_TRUSTED_ORIGINS=http://${PUBLIC_IP}:8000,http://${PUBLIC_DNS}:8000,https://${CLOUDFRONT_DOMAIN}
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
DJANGO_SETTINGS_MODULE=config.settings.prod
SECURE_SSL_REDIRECT=False
EMAIL_HOST_USER=\${EMAIL_USER}
EMAIL_HOST_PASSWORD=\${EMAIL_PASS}
DEFAULT_FROM_EMAIL=\${EMAIL_USER:-noreply@mtt.com}
ENV
sudo docker compose -f docker-compose.prod.yml up -d --build
sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput
sudo docker compose -f docker-compose.prod.yml exec -T web python manage.py showmigrations --plan 2>&1 | tail -20
echo "Backend containers started."
EOF
}

ensure_s3_bucket() {
  S3_BUCKET="${S3_BUCKET:-${PROJECT_NAME}-frontend-${AWS_ACCOUNT_ID}}"
  if aws s3api head-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" 2>/dev/null; then
    log "Using existing S3 bucket: $S3_BUCKET"
    return
  fi

  log "Creating S3 bucket: $S3_BUCKET"
  if [[ "$AWS_REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" \
      --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
  fi
  aws s3api put-public-access-block \
    --bucket "$S3_BUCKET" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true \
    --region "$AWS_REGION"
}

ensure_oac() {
  if [[ -n "${OAC_ID:-}" ]]; then
    return
  fi
  OAC_ID="$(aws cloudfront create-origin-access-control \
    --origin-access-control-config "Name=${PROJECT_NAME}-oac,Description=MT Travel frontend OAC,SigningProtocol=sigv4,SigningBehavior=always,OriginAccessControlOriginType=s3" \
    --query 'OriginAccessControl.Id' \
    --output text)"
  log "Created CloudFront OAC: $OAC_ID"
}

ensure_cloudfront() {
  if [[ -n "${CLOUDFRONT_ID:-}" ]]; then
    CLOUDFRONT_DOMAIN="$(aws cloudfront get-distribution --id "$CLOUDFRONT_ID" --query 'Distribution.DomainName' --output text)"
    log "Using existing CloudFront distribution: $CLOUDFRONT_ID ($CLOUDFRONT_DOMAIN)"
    return
  fi

  ensure_oac
  CALLER_REF="${PROJECT_NAME}-$(date +%s)"
  DIST_FILE="$(mktemp)"
  sed \
    -e "s|__CALLER_REF__|$CALLER_REF|g" \
    -e "s|__S3_BUCKET__|$S3_BUCKET|g" \
    -e "s|__OAC_ID__|$OAC_ID|g" \
    -e "s|__EC2_ORIGIN__|$PUBLIC_DNS|g" \
    "$SCRIPT_DIR/cloudfront-config.json" >"$DIST_FILE"

  log "Creating CloudFront distribution (takes 5-15 minutes)..."
  CLOUDFRONT_ID="$(aws cloudfront create-distribution \
    --distribution-config "file://$DIST_FILE" \
    --query 'Distribution.Id' \
    --output text)"
  rm -f "$DIST_FILE"
  CLOUDFRONT_DOMAIN="$(aws cloudfront get-distribution --id "$CLOUDFRONT_ID" --query 'Distribution.DomainName' --output text)"

  apply_bucket_policy_for_oac
  log "CloudFront domain: $CLOUDFRONT_DOMAIN"
}

apply_bucket_policy_for_oac() {
  POLICY="$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipal",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${S3_BUCKET}/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::${AWS_ACCOUNT_ID}:distribution/${CLOUDFRONT_ID}"
        }
      }
    }
  ]
}
EOF
)"
  aws s3api put-bucket-policy --bucket "$S3_BUCKET" --policy "$POLICY" --region "$AWS_REGION"
}

build_and_upload_frontend() {
  [[ -d "$FRONTEND_DIR" ]] || die "Frontend directory not found: $FRONTEND_DIR"

  log "Building frontend..."
  cp "$FRONTEND_DIR/.env.production.example" "$FRONTEND_DIR/.env.production"
  (
    cd "$FRONTEND_DIR"
    yarn install --frozen-lockfile 2>/dev/null || yarn install
    yarn build
  )

  log "Uploading frontend to s3://$S3_BUCKET/app/ ..."
  aws s3 sync "$FRONTEND_DIR/dist/" "s3://$S3_BUCKET/app/" --delete --region "$AWS_REGION"

  if [[ -n "${CLOUDFRONT_ID:-}" ]]; then
    log "Invalidating CloudFront cache..."
    aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_ID" --paths "/*" >/dev/null
  fi
}

cmd_status() {
  load_config
  load_state
  if [[ ! -f "$STATE_FILE" ]]; then
    log "No deployment state found. Run ./deploy.sh all first."
    exit 0
  fi
  cat <<EOF

Deployment status
-----------------
EC2 instance:     ${INSTANCE_ID:-n/a}
EC2 public IP:    ${PUBLIC_IP:-n/a}
S3 bucket:        ${S3_BUCKET:-n/a}
CloudFront ID:    ${CLOUDFRONT_ID:-n/a}
CloudFront URL:   ${CLOUDFRONT_DOMAIN:+https://${CLOUDFRONT_DOMAIN}/app/}
SSH key:          ${KEY_FILE:-$KEYS_DIR/${EC2_KEY_NAME}.pem}

EOF
}

cmd_destroy() {
  load_config
  load_state
  log "Destroying AWS resources..."

  if [[ -n "${CLOUDFRONT_ID:-}" ]]; then
    ETAG="$(aws cloudfront get-distribution-config --id "$CLOUDFRONT_ID" --query 'ETag' --output text)"
    DIST_CFG="$(aws cloudfront get-distribution-config --id "$CLOUDFRONT_ID" --query 'DistributionConfig' --output json)"
    DISABLED_CFG="$(echo "$DIST_CFG" | python3 -c 'import json,sys; c=json.load(sys.stdin); c["Enabled"]=False; print(json.dumps(c))')"
    TMP="$(mktemp)"
    echo "$DISABLED_CFG" >"$TMP"
    aws cloudfront update-distribution --id "$CLOUDFRONT_ID" --if-match "$ETAG" --distribution-config "file://$TMP" >/dev/null
    rm -f "$TMP"
    aws cloudfront wait distribution-deployed --id "$CLOUDFRONT_ID"
    ETAG="$(aws cloudfront get-distribution-config --id "$CLOUDFRONT_ID" --query 'ETag' --output text)"
    aws cloudfront delete-distribution --id "$CLOUDFRONT_ID" --if-match "$ETAG" >/dev/null
  fi

  if [[ -n "${S3_BUCKET:-}" ]]; then
    aws s3 rm "s3://$S3_BUCKET" --recursive --region "$AWS_REGION" || true
    aws s3api delete-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" || true
  fi

  if [[ -n "${INSTANCE_ID:-}" ]]; then
    aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" >/dev/null || true
  fi

  if [[ -n "${SECURITY_GROUP_ID:-}" ]]; then
    sleep 30
    aws ec2 delete-security-group --group-id "$SECURITY_GROUP_ID" --region "$AWS_REGION" >/dev/null || true
  fi

  rm -f "$STATE_FILE"
  log "Destroy complete."
}

cmd_all() {
  load_config
  load_state
  ensure_prereqs
  generate_secrets
  ensure_key_pair
  ensure_security_group
  launch_ec2
  save_state
  wait_for_ssh
  ensure_s3_bucket
  save_state
  ensure_cloudfront
  save_state
  configure_backend_on_ec2
  build_and_upload_frontend
  save_state
  cmd_status
  log "Deployment complete."
}

cmd_backend() {
  load_config
  load_state
  ensure_prereqs
  generate_secrets
  ensure_key_pair
  ensure_security_group
  launch_ec2
  save_state
  wait_for_ssh
  [[ -n "${CLOUDFRONT_DOMAIN:-}" ]] || die "CloudFront domain missing. Run full deploy first or set CLOUDFRONT_DOMAIN in .deploy-state.env"
  configure_backend_on_ec2
  save_state
  cmd_status
}

cmd_frontend() {
  load_config
  load_state
  ensure_prereqs
  [[ -n "${S3_BUCKET:-}" ]] || ensure_s3_bucket
  [[ -n "${CLOUDFRONT_ID:-}" ]] || ensure_cloudfront
  save_state
  build_and_upload_frontend
  save_state
  cmd_status
}

main() {
  COMMAND="${1:-all}"
  case "$COMMAND" in
    all) cmd_all ;;
    backend) cmd_backend ;;
    frontend) cmd_frontend ;;
    status) cmd_status ;;
    destroy) cmd_destroy ;;
    -h|--help|help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
