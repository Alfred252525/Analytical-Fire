# Setting Up Direct AWS Access for AI

## Option 1: AWS MCP Server (Recommended - Direct Control)

This gives me direct access to AWS through Model Context Protocol.

### Step 1: Install AWS MCP Server

```bash
# Install the AWS MCP server
npm install -g @modelcontextprotocol/server-aws
```

### Step 2: Configure in Cursor

Add to your Cursor MCP settings (`.cursor/mcp.json` or Cursor settings):

```json
{
  "mcpServers": {
    "aws": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-aws"
      ],
      "env": {
        "AWS_ACCESS_KEY_ID": "YOUR_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY": "YOUR_SECRET_ACCESS_KEY
        "AWS_DEFAULT_REGION": "us-east-1"
      }
    }
  }
}
```

### Step 3: Restart Cursor

After adding the MCP server, restart Cursor to load it.

**Result**: I'll have direct access to AWS and can deploy/manage everything autonomously!

---

## Option 2: Local AWS CLI + Scripts (Alternative)

If MCP server doesn't work, I'll create scripts you run:

### Step 1: Install AWS CLI

```bash
# macOS
brew install awscli

# Or download from: https://aws.amazon.com/cli/
```

### Step 2: Configure AWS CLI

```bash
aws configure
```

Enter:
- Access Key ID: `YOUR_ACCESS_KEY_ID`
- Secret Access Key: `YOUR_SECRET_ACCESS_KEY
- Region: `us-east-1`
- Output: `json`

### Step 3: Verify

```bash
aws sts get-caller-identity
```

Should return your account info.

**Result**: I'll create scripts you run, and I guide you through each step.

---

## Option 3: Environment Variables (Quick Test)

Set environment variables and I'll create scripts that use them:

```bash
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=us-east-1
```

Then run scripts I create.

---

## Which Option Should We Use?

**My Recommendation**: Try Option 1 (MCP Server) first - it gives me the most direct control.

If that doesn't work, Option 2 (AWS CLI + Scripts) is reliable and I can guide you through everything.

---

## Security Note

The credentials are currently in this file. After setup:
1. Remove them from this file
2. Use environment variables or AWS credentials file
3. Never commit credentials to git
