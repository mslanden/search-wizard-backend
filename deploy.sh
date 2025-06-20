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

# Set environment variables
railway variables set OPENAI_API_KEY="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"
railway variables set ANTHROPIC_API_KEY="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"
railway variables set GEMINI_API_KEY="AIzaSyAk1fo9S6cuyWUPdbcUKxlg_k1Efs6murs"
railway variables set NEXT_PUBLIC_SUPABASE_URL="https://giydkdmzwhmlnnfmdozf.supabase.co"
railway variables set NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdpeWRrZG16d2htbG5uZm1kb3pmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0ODU0NjQ2OSwiZXhwIjoyMDY0MTIyNDY5fQ.HoT_kPYSdRE6RffTRJB72_q9_aPE_o9Cifpqt_f-5TE"
railway variables set LLAMAPARSE_API_KEY="llx-tixLWsup8gpuEr4ZgrTqBJqScfLPsPM0GAsu2wiGFwa9Qa7j"
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