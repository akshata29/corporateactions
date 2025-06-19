cd .\mcp-rag\ ; py main.py --port 8000
cd .\mcp-websearch\ ; py main.py --port 8001

cd .\mcp-rag\ ; py main.py --sse --port 8003
cd .\mcp-websearch\ ; py main.py --sse --port 8004

cd .\clients\streamlit-ui\;  streamlit run app_mcp.py
cd .\clients\corporate-actions-agent\; npm run dev