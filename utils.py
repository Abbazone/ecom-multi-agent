import os
from typing import Any, Dict, List, Optional, Tuple, Callable
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential
)

from kb import STORAGES
from api import APIS
from routers import ROUTERS


client = OpenAI()


@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def completion_with_backoff(**kwargs):
    return client.responses.create(**kwargs)


@retry(wait=wait_random_exponential(min=1, max=5), stop=stop_after_attempt(3))
def embedding_with_backoff(model, input, timeout):
    return client.embeddings.create(input=input, model=model, timeout=timeout)


def lazy_external_import(module_name: str, class_name: str) -> Callable[..., Any]:
    """Lazily import a class from an external module based on the package of the caller."""
    # Get the caller's module and package
    import inspect

    caller_frame = inspect.currentframe().f_back
    module = inspect.getmodule(caller_frame)
    package = module.__package__ if module else None

    def import_class(*args: Any, **kwargs: Any):
        import importlib

        module = importlib.import_module(module_name, package=package)
        cls = getattr(module, class_name)
        return cls(*args, **kwargs)

    return import_class


def get_storage_class(storage_name: str) -> Callable[..., Any]:
    # Direct imports for default storage implementations
    import_path = STORAGES[storage_name]
    storage_class = lazy_external_import(import_path, storage_name)
    return storage_class


def get_api_class(api_name: str) -> Callable[..., Any]:
    # Direct imports for default api implementations
    import_path = APIS[api_name]
    api_class = lazy_external_import(import_path, api_name)
    return api_class


def get_router_class(router_name: str) -> Callable[..., Any]:
    # Direct imports for default router implementations
    import_path = ROUTERS[router_name]
    router_class = lazy_external_import(import_path, router_name)
    return router_class
