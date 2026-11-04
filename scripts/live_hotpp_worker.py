"""Website JSON-lines entry point for the HotPP inference bridge."""
import live_model_worker as previous
from hotpp_website.live_worker import HotPPWorker

if __name__ == '__main__':
    previous.Worker = HotPPWorker
    previous.main()
