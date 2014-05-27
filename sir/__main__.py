# Copyright (c) 2014 Wieland Hoffmann
# License: MIT, see LICENSE for details
import argparse
import logging
import multiprocessing


from . import config
from .indexing import reindex
from .schema import SCHEMA


logger = logging.getLogger("sir")


def watch(args):
    raise NotImplementedError


def main():
    loghandler = logging.StreamHandler()
    formatter = logging.Formatter(fmt="%(processName)s %(asctime)s  %(levelname)s: %(message)s")
    loghandler.setFormatter(formatter)
    logger.addHandler(loghandler)

    mplogger = multiprocessing.get_logger()
    mplogger.setLevel(logging.ERROR)
    mplogger.addHandler(loghandler)

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("--sqltimings", action="store_true")
    subparsers = parser.add_subparsers()

    reindex_parser = subparsers.add_parser("reindex", help="Reindexes all or a single entity type")
    reindex_parser.set_defaults(func=reindex)
    reindex_parser.add_argument('--entities', action='append', help="""Which
        entity types to index.

        Available are: %s""" % (", ".join(SCHEMA.keys())))

    watch_parser = subparsers.add_parser("watch", help="Watches for incoming messages on an AMQP queue")
    watch_parser.set_defaults(func=watch)

    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if args.sqltimings:
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        import time

        sqltimelogger = logging.getLogger("sqltimer")
        sqltimelogger.setLevel(logging.DEBUG)
        sqltimelogger.addHandler(loghandler)

        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement,
                                  parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
            sqltimelogger.debug("Start Query: %s" % statement)

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement,
                                 parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            sqltimelogger.debug("Query Complete!")
            sqltimelogger.debug("Total Time: %f" % total)

    config.read_config()
    func = args.func
    args = vars(args)
    func(args["entities"])

if __name__ == '__main__':
    main()