#  SpinEverydayBot
#  Copyright © 2016-2021 Evgeniy Filimonov <evgfilim1@yandex.ru>
#
#  This program is free software: you can redistribute it and/or modify it under the terms of the
#  GNU Affero General Public License as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#  even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Affero General Public License for more details.
#  You should have received a copy of the GNU Affero General Public License along with this program.
#  If not, see <http://www.gnu.org/licenses/>.

__all__ = ["main"]

import asyncio
import logging
from argparse import ArgumentParser, ArgumentTypeError
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Optional, Sequence, Union

from aiogram import Bot, Dispatcher
from pydantic import IPvAnyAddress
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from . import __version__, handlers, middlewares
from .config import Config, read_config
from .lang import gettext as _


@dataclass(frozen=True)
class Args:
    strategy: str
    loglevel: str
    config: Optional[Path]
    host: Optional[str] = None
    port: Optional[int] = None


def _existing_file(path: str) -> Path:
    if not (p := Path(path).resolve()).exists():
        raise ArgumentTypeError(_("No such file: {0!r}").format(path))
    if p.is_dir():
        raise ArgumentTypeError(_("Is a directory: {0!r}").format(path))
    return p


def _init_parser() -> ArgumentParser:
    loglevels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    parser = ArgumentParser(
        description=_("Telegram bot for everyday raffles"),
    )
    parser.add_argument(
        "-L",
        "--loglevel",
        default="INFO",
        choices=loglevels,
        metavar="LEVEL",
        help=_("log level, can be one of {0}").format(", ".join(loglevels)),
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("-c", "--config", type=_existing_file, help=_("full path to config file"))

    run_type = parser.add_subparsers(
        help=_("How to fetch updates, see https://core.telegram.org/bots/api#getting-updates"),
        dest="strategy",
    )
    run_type.add_parser("polling", help=_("run with polling (default)"))

    webhook = run_type.add_parser("webhook", help=_("run with webhooks (not supported yet)"))
    webhook.add_argument(
        "-H",
        "--host",
        type=IPvAnyAddress,
        default="127.0.0.1",
        help=_("host to listen at"),
    )
    webhook.add_argument("--port", "-p", type=int, default=8880, help=_("port to listen at"))

    return parser


def _parse_args(
    argv: Optional[Sequence[str]] = None,
) -> Args:
    parser = _init_parser()
    args = parser.parse_args(argv)
    return Args(**args.__dict__)


async def _main(args: Args, config: Config) -> None:
    engine = create_async_engine(config.db.dsn, future=True)
    session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True,
    )

    bot = Bot(config.telegram.token, parse_mode="HTML")
    dp = Dispatcher()

    handlers.register(dp)
    middlewares.register(dp)

    if args.strategy == "webhook":
        raise NotImplementedError(_("Getting updates via webhook is not implemented yet"))
    await dp.start_polling(
        bot,
        session_factory=session_factory,
        superuser_id=config.telegram.superuser_id,
    )


def main() -> None:
    args = _parse_args()
    config = read_config(args.config)

    logging.basicConfig(level=args.loglevel)
    return asyncio.run(_main(args, config))
