#!/bin/bash
# 1. 杀掉旧进程
pkill -f "src/api/main.py"
pkill -f "http.server 8222"

sleep 5

# 2. 环境变量与 Python 路径
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 3. 准备数据
echo "📝 检查知识库..."
# python3 scripts/ingest_docs.py

# 4. 启动后端 API (Port 8111)
echo "🚀 启动后端 API (Port 8111)..."
nohup python3 src/api/main.py > ./logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 后端 PID: $BACKEND_PID"

# 5. 启动前端 UI (Port 8222)
echo "🚀 启动前端静态服务 (Port 8222)..."
cd src/ui/static
nohup python3 -m http.server 8222 > ../../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../../../
echo "✅ 前端 PID: $FRONTEND_PID"

# 6. 完成
echo ""
echo "🎯 系统启动完成！"
echo "🌐 前端访问: http://localhost:8222"
echo "🔌 后端接口: http://localhost:8111"
echo "📊 日志查看: tail -f backend.log"