#!/bin/bash

# Cost Optimization Script
# Right-sizes resources to minimize costs

set -e

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "💰 Cost Optimization Script"
echo "=========================="
echo ""

echo "This script will help optimize AWS costs by:"
echo "  1. Checking current resource sizes"
echo "  2. Suggesting right-sizing opportunities"
echo "  3. Providing cost optimization recommendations"
echo ""

# Check RDS instance
echo "Checking RDS instance..."
RDS_INSTANCE=$(aws rds describe-db-instances \
    --query 'DBInstances[?DBInstanceIdentifier==`aifai-postgres`].[DBInstanceClass,DBInstanceStatus]' \
    --output text 2>/dev/null || echo "Not found")

if [ -n "$RDS_INSTANCE" ]; then
    echo "  Current RDS instance: $RDS_INSTANCE"
    echo "  Recommendation: Use db.t3.micro (smallest, ~\$15/month)"
else
    echo "  RDS instance not found or not accessible"
fi

# Check ElastiCache
echo ""
echo "Checking ElastiCache..."
CACHE_CLUSTER=$(aws elasticache describe-cache-clusters \
    --query 'CacheClusters[?CacheClusterId==`aifai-redis`].[CacheNodeType,CacheClusterStatus]' \
    --output text 2>/dev/null || echo "Not found")

if [ -n "$CACHE_CLUSTER" ]; then
    echo "  Current ElastiCache node: $CACHE_CLUSTER"
    echo "  Recommendation: Use cache.t3.micro (smallest, ~\$10/month)"
else
    echo "  ElastiCache cluster not found or not accessible"
fi

# Check ECS service
echo ""
echo "Checking ECS service..."
ECS_SERVICE=$(aws ecs describe-services \
    --cluster aifai-cluster \
    --services aifai-backend \
    --query 'services[0].[desiredCount,runningCount]' \
    --output text 2>/dev/null || echo "Not found")

if [ -n "$ECS_SERVICE" ]; then
    echo "  Current ECS tasks: $ECS_SERVICE"
    echo "  Recommendation: Use 1 task if load is low (can scale up if needed)"
else
    echo "  ECS service not found or not accessible"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Cost Optimization Recommendations"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "To optimize costs:"
echo "  1. Use smallest instance sizes (db.t3.micro, cache.t3.micro)"
echo "  2. Right-size ECS tasks based on actual usage"
echo "  3. Monitor resource utilization"
echo "  4. Scale down when possible"
echo ""
echo "Estimated optimized monthly cost: ~\$40-60"
echo "  • RDS db.t3.micro: ~\$15"
echo "  • ElastiCache cache.t3.micro: ~\$10"
echo "  • ECS Fargate (1-2 tasks): ~\$10-20"
echo "  • ALB: ~\$16"
echo "  • Data transfer: ~\$5"
echo ""
echo "This keeps us well below \$100/month threshold!"
echo ""
