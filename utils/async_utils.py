"""
Async Utilities for Streamlit
Fixes "Event loop is closed" errors by using a persistent event loop.
"""

import asyncio
import threading
from typing import Coroutine, TypeVar, Any
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')

# Global event loop and executor
_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_executor: ThreadPoolExecutor | None = None


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """
    Get or create a persistent event loop for async operations.
    
    This fixes the "Event loop is closed" error in Streamlit by maintaining
    a single event loop instead of creating/destroying loops with asyncio.run().
    
    Returns:
        Running event loop
    """
    global _loop, _loop_thread
    
    if _loop is None or _loop.is_closed():
        # Create new loop
        _loop = asyncio.new_event_loop()
        
        # Start loop in background thread
        def run_loop():
            asyncio.set_event_loop(_loop)
            _loop.run_forever()
        
        _loop_thread = threading.Thread(target=run_loop, daemon=True)
        _loop_thread.start()
    
    return _loop


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run async coroutine safely in Streamlit.
    
    This is a drop-in replacement for asyncio.run() that works in Streamlit
    without causing "Event loop is closed" errors.
    
    Args:
        coro: Async coroutine to run
        
    Returns:
        Result from coroutine
        
    Example:
        # Instead of:
        # result = asyncio.run(my_async_function())
        
        # Use:
        result = run_async(my_async_function())
    """
    loop = get_or_create_event_loop()
    
    # Run coroutine in the persistent loop
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    
    # Wait for result
    return future.result()


def shutdown_event_loop():
    """
    Shutdown the persistent event loop.
    Call this when the application is closing.
    """
    global _loop, _loop_thread
    
    if _loop and not _loop.is_closed():
        _loop.call_soon_threadsafe(_loop.stop)
        _loop = None
    
    if _loop_thread:
        _loop_thread.join(timeout=5)
        _loop_thread = None
