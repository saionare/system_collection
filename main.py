import argparse, logging, threading, time
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request
from app.core import CollectionSystem
from app.api.routes import router
ROOT=Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s: %(message)s')
def create_app(system):
    app=FastAPI(title='System Collection API',version='1.0.0')
    app.state.system=system
    @app.middleware('http')
    async def inject_system(request:Request,call_next):
        request.state.system=system
        return await call_next(request)
    app.include_router(router)
    return app
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000);parser.add_argument('--retention-seconds',type=float,default=None);parser.add_argument('--load-test',action='store_true');parser.add_argument('--seconds',type=int,default=10);parser.add_argument('--no-wait',action='store_true');args=parser.parse_args()
    system=CollectionSystem(ROOT,args.retention_seconds)
    if args.load_test:
        end=time.monotonic()+args.seconds
        while time.monotonic()<end:
            system.process_snapshot();system.archive_old()
            if not args.no_wait:time.sleep(1)
        print(system.stats);return
    worker=threading.Thread(target=system.run_forever,daemon=True);worker.start()
    try:uvicorn.run(create_app(system),host='127.0.0.1',port=args.port)
    finally:system.stop()
if __name__=='__main__':main()
