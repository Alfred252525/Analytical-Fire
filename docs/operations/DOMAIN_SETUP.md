# Domain Setup Guide

Once you provide a domain, here's how we'll configure it:

## Step 1: Choose Domain

Share your list and I'll help pick the best one (or you choose!)

## Step 2: DNS Configuration

### Option A: Domain in Route 53 (Easiest)
- Create hosted zone in Route 53
- Update nameservers at domain registrar
- Automatic DNS management

### Option B: External DNS Provider
- Point A record to load balancer
- Add CNAME for www subdomain
- Update nameservers if needed

## Step 3: SSL Certificate

1. Request ACM certificate (free, managed by AWS)
2. Validate via DNS or email
3. Attach to load balancer
4. Enable HTTPS

## Step 4: Update Platform

1. Update CORS settings with new domain
2. Update load balancer listener for HTTPS
3. Redirect HTTP → HTTPS
4. Test API endpoints

## Benefits

- ✅ Professional domain name
- ✅ HTTPS encryption (free via ACM)
- ✅ Better branding
- ✅ Easier to remember/share
- ✅ SEO benefits (if public)

## Estimated Time

- DNS setup: 5-10 minutes
- Certificate: 5-15 minutes (validation)
- Load balancer config: 5 minutes
- **Total**: ~20-30 minutes

---

**Ready when you are!** Share the domain list and we'll get it set up! 🚀
