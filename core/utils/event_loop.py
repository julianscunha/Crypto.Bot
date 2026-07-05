# -*- coding: utf-8 -*-

"""
Configura o event loop correto no Windows antes de asyncio.run().

aiohttp (usado pelo BinanceTradingClient) requer SelectorEventLoop
no Windows -- o Python 3.8+ mudou o padrão para ProactorEventLoop
que quebra conexões TCP/SSL com WinError 2 ("The system cannot find
the file specified"). Sem essa correção, toda chamada à API da
Binance falha silenciosamente no EventBus como FAILED ExecutionAgent.

Uso:
    from core.utils.event_loop import configure_event_loop
    configure_event_loop()
    asyncio.run(main())
"""

import sys


def configure_event_loop():

    import asyncio

    if sys.platform == "win32":

        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )
