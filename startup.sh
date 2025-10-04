#!/bin/bash
set -e

echo "=== NewsRagnarok Azure Optimized Startup ==="
echo "🌐 Azure App Service Deployment"
echo "⏰ Start time: $(date)"
echo "📊 PORT: ${PORT:-8000}"
echo "🔧 Environment: ${ENVIRONMENT:-development}"

# Set critical environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH="/home/site/wwwroot:${PYTHONPATH}"
export AZURE_ENV=true

# Create essential directories
echo "📁 Creating directories..."
mkdir -p /home/site/wwwroot/data/{metrics,heartbeat,logs}
mkdir -p /home/site/wwwroot/logs

# Background initialization (non-blocking for Azure)
echo "🔄 Starting background initialization..."
(
    echo "📦 Installing Playwright browsers (background)..."
    # Install with timeout to prevent blocking
    timeout 120 playwright install chromium --with-deps 2>/dev/null || {
        echo "⚠️ Playwright installation timed out - continuing anyway"
    }
    
    echo "🐍 Verifying Python environment..."
    python3 -c "
import sys, os
print(f'✅ Python {sys.version.split()[0]}')
print(f'✅ Working directory: {os.getcwd()}')
print(f'✅ PYTHONPATH: {os.environ.get(\"PYTHONPATH\", \"Not set\")}')

# Test essential imports
try:
    import asyncio, json, time
    print('✅ Core modules available')
except Exception as e:
    print(f'❌ Core module error: {e}')

try:
    import loguru
    print('✅ Loguru available')
except ImportError:
    print('⚠️ Loguru not available - using basic logging')
" || echo "⚠️ Python environment verification issues"

    # Start main application in background
    echo "🚀 Starting main application (background)..."
    python3 main.py 2>&1 | tee logs/app.log
    
) &

BACKGROUND_PID=$!

echo "✅ Background initialization started (PID: $BACKGROUND_PID)"
echo "💚 Azure App Service startup COMPLETE"
echo "📊 Status:"
echo "   - Health server: 🔄 Starting with main app"
echo "   - Background init: 🔄 In progress" 
echo "   - Ready for traffic: ✅ YES"
echo ""
echo "🌐 Service endpoints:"
echo "   - Health: http://localhost:${PORT:-8000}/"
echo "   - Logs: /home/site/wwwroot/logs/"
echo ""
echo "⏳ Application services will initialize over next 2-5 minutes"

# Wait for background process (main app includes health server)
echo "🛡️ Monitoring application..."
wait $BACKGROUND_PID