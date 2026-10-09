"""Run the web version: ``python -m anonymizer.web [--host H] [--port P] [--no-ner]``.

Uses waitress (production-grade, Windows and Linux) when installed,
otherwise the standard library threaded WSGI server.
"""
from __future__ import annotations

import argparse
import logging
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="ANONYMIZER ROSSILBER — веб-версия")
    parser.add_argument("--host", default=os.environ.get("ANONYMIZER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ANONYMIZER_PORT", "8080")))
    parser.add_argument("--no-ner", action="store_true", help="без нейросети (только правила)")
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.no_ner:
        os.environ["ANONYMIZER_USE_NER"] = "0"

    from anonymizer.web.app import create_app

    app = create_app()
    url = f"http://{args.host}:{args.port}/"
    try:
        from waitress import serve
    except ImportError:
        serve = None
    if serve is not None:
        logging.info("ANONYMIZER ROSSILBER web: %s (waitress)", url)
        serve(app, host=args.host, port=args.port, threads=args.threads)
        return

    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

    class _Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class _QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *a):  # noqa: A002 - stdlib signature
            # Log method/path/status only — never bodies.
            logging.info("%s %s", self.address_string(), format % a)

    logging.info("ANONYMIZER ROSSILBER web: %s (wsgiref)", url)
    with make_server(args.host, args.port, app, server_class=_Server,
                     handler_class=_QuietHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
