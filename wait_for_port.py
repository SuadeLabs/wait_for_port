#!/usr/bin/env python

import argparse
import socket
import sys
import time

import logging
from docker import Client
import psycopg2
from typing import Any, Dict, Optional  # NOQA


DEFAULT_INTERVAL = 0.2
DEFAULT_LOGLEVEL = "WARN"


class WaitForPort(object):
    """wait_for_port waits for a container to be listening on a tcp port."""

    def __init__(self, container, port, timeout, increment, loglevel):
        # type: (str, int, int, float, int) -> None
        """init"""
        self.configure_logger(loglevel)

        self.container = container
        self.container_ip = None  # type: Optional[str]
        self.port = port
        self.timeout = timeout
        self.increment = increment

        checks = {
            5432: self.is_port_open_postgres
        }
        setattr(
            self, "is_port_open",
            checks.get(self.port, self.is_port_open_default))

    def configure_logger(self, loglevel):
        # type: (int) -> None
        """configure the logger"""
        self.logger = logging.getLogger("wait_for_port")
        self.logger.setLevel(loglevel)

        strh = logging.StreamHandler(sys.stdout)
        strh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s"))
        self.logger.addHandler(strh)

    def is_port_open(self, **kwargs):
        # type: (...) -> bool
        """placeholder function, overwritten at runtime in __init__"""
        self.logger.error("This method should be overwritten.")
        return False

    def is_port_open_default(self, **kwargs):
        # type: (...) -> bool
        """Run a default TCP port check."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((self.container_ip, self.port))
        if result != 0:
            self.logger.debug("socket connect result: %d", result)

        return result == 0

    def is_port_open_postgres(self, **kwargs):
        # type: (...) -> bool
        """
        Check is postgres is listening, and if it's really accepting
        connections."""
        try:
            psycopg2.connect(
                host=self.container_ip,
                port=self.port,
                database=kwargs["pg_database"],
                user=kwargs["pg_user"],
                password=kwargs["pg_password"])
            return True
        except Exception, exc:
            self.logger.debug("Caught exception: %s", repr(exc))
            return False

    def wait_for_port(self, **kwargs):
        # type: (...) -> bool
        """
        Wait for the TCP port to become open. Fail fast (but only after 5
        seconds) if the container is not running."""
        try:
            docker = Client()  # type: Client
        except Exception, exc:
            print "Unable to connect to Docker daemon: {}".format(exc)
            return False

        no_newline_print("Waiting for {}".format(self.container))

        tick = 0.0  # type: float
        while tick < self.timeout:
            no_newline_print(".")

            # tick > timeout/2, to prevent a race where a container is still
            # starting
            if (tick > 5) and not is_container_running(docker, self.container):
                print "failed!"
                print "Container not running: {}".format(self.container)
                return False

            try:
                self.container_ip = container_ipaddress(docker, self.container)
            except Exception, exc:
                msg = (
                    "Unable to find container or extract IP address, for "
                    "container '{}': {}")
                print msg.format(self.container, repr(exc))
                self.container_ip = None

            if self.container_ip and self.is_port_open(**kwargs):
                print "ready."
                return True

            tick += self.increment
            time.sleep(self.increment)

        print "failed!"
        print "Timed out waiting for port {} to open.".format(self.port)
        return False


def no_newline_print(string):
    # type: (str) -> None
    """Print some text, but no newline"""
    sys.stdout.write(string)
    sys.stdout.flush()


def container_inspect(docker, container):
    # type: (Client, str) -> Any
    """Inspect a container"""
    return docker.inspect_container(container)


def is_container_running(docker, container):
    # type: (Client, str) -> bool
    """Check if a container is running"""
    return container_inspect(docker, container)["State"]["Running"]


def container_ipaddress(docker, container):
    # type: (Client, str) -> str
    """Get a container's IP address"""
    return container_inspect(docker, container)["NetworkSettings"]["IPAddress"]


def parse_args():
    # type: () -> argparse.Namespace
    """Parse cmdline args and return an argparse Namespace object."""
    parser = argparse.ArgumentParser(description=(
        "Tries to connect to a docker container's port until it succeeds or "
        "times out. In addition, extra checks are made depending on the port: "
        "5432: a postgres connection attempt is made."))

    parser.add_argument(
        "--container",
        help="Container name",
        type=str,
        required=True)

    parser.add_argument(
        "--interval",
        help="Interval between checks, in seconds [default: {}]".format(
            DEFAULT_INTERVAL),
        type=float,
        required=False,
        default=DEFAULT_INTERVAL)

    parser.add_argument(
        "--pg_user",
        help="Postgres username",
        type=str)

    parser.add_argument(
        "--pg_password",
        help="Postgres password",
        type=str)

    parser.add_argument(
        "--pg_database",
        help="Postgres database",
        type=str)

    parser.add_argument(
        "--loglevel",
        help="Set the log level [default: {}]".format(DEFAULT_LOGLEVEL),
        choices=[
            "FATAL",
            "ERROR",
            "WARN",
            "INFO",
            "DEBUG"
        ],
        default=DEFAULT_LOGLEVEL)

    parser.add_argument(
        "--port",
        help="TCP port to check",
        type=int,
        required=True)

    parser.add_argument(
        "--timeout",
        help="timeout in seconds",
        type=int,
        required=True)

    return parser.parse_args()


def run():
    # type: () -> None
    """Run the program"""
    args = parse_args()  # type: argparse.Namespace

    wfp = WaitForPort(
        args.container,
        args.port,
        args.timeout,
        args.interval,
        getattr(logging, args.loglevel))

    kwargs = {}  # type: Dict[str, str]
    if args.port == 5432:
        kwargs = {
            "pg_database": "postgres",
            "pg_user": "postgres",
            "pg_password": ""
        }
        if args.pg_database:
            kwargs["pg_database"] = args.pg_database
        if args.pg_user:
            kwargs["pg_user"] = args.pg_user
        if args.pg_password:
            kwargs["pg_password"] = args.pg_password

    try:
        if not wfp.wait_for_port(**kwargs):
            exit(1)
    except KeyboardInterrupt:
        exit(1)


if __name__ == "__main__":
    run()
