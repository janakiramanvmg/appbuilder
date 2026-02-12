import uvicorn
from fastapi import FastAPI
import sys
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/msg")
def health():
    return {"status": "running"}

def run_server(host, port):
    print(f"host====${host}--- prot===${port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    # host = sys.argv[1]
    host = "127.0.0.1"
    port = 5600

    print(f"[API] Starting on {host}:{port}", flush=True)
    run_server(host, port)
