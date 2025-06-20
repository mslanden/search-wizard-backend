#!/bin/bash

echo "🚀 Deploying Search Wizard Backend to Railway"
echo "==========================================="

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install: npm install -g @railway/cli"
    exit 1
fi

# Check if logged in
railway whoami &> /dev/null
if [ $? -ne 0 ]; then
    echo "📝 Please login to Railway:"
    railway login
fi

# Check if project is linked
railway status &> /dev/null
if [ $? -ne 0 ]; then
    echo "🔗 No project linked. Please select or create a project:"
    railway link
fi

echo ""
echo "📋 Setting environment variables..."

# Set environment variables (replace with your actual keys)
echo "⚠️  Please set these environment variables manually in Railway dashboard:"
echo "   - OPENAI_API_KEY"
echo "   - ANTHROPIC_API_KEY" 
echo "   - GEMINI_API_KEY"
echo "   - NEXT_PUBLIC_SUPABASE_URL"
echo "   - NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY"
echo "   - LLAMAPARSE_API_KEY"
railway variables set ENABLE_LLAMAPARSE="true"
railway variables set LLAMAPARSE_PRICING_TIER="premium"

echo "✅ Environment variables set"
echo ""
echo "🚂 Deploying to Railway..."
railway up

echo ""
echo "✅ Deployment initiated!"
echo ""
echo "📝 Next steps:"
echo "1. Check deployment logs: railway logs"
echo "2. Get deployment URL: railway open"
echo "3. Add Redis (optional): railway add"
echo ""
echo "🔗 Your backend will be available at the Railway-provided URL"