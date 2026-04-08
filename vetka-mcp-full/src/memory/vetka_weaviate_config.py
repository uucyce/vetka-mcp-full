#!/usr/bin/env python3
"""
VETKA Weaviate Configuration.

Dataclass-based configuration for Weaviate connection endpoints.

@status: active
@phase: 96
@depends: os, dataclasses
@used_by: vetka_weaviate_helper.py, weaviate_helper.py
"""

import os
from dataclasses import dataclass

@dataclass
class WeaviateConfig:
    host: str = os.getenv('WEAVIATE_HOST', 'localhost')
    port: int = int(os.getenv('WEAVIATE_PORT', '8080'))
    scheme: str = os.getenv('WEAVIATE_SCHEME', 'http')
    
    @property
    def base_url(self) -> str:
        return f'{self.scheme}://{self.host}:{self.port}'
    
    @property
    def api_endpoint(self) -> str:
        return f'{self.base_url}/v1'
    
    @property
    def collections_endpoint(self) -> str:
        return f'{self.api_endpoint}/collections'
    
    @property
    def objects_endpoint(self) -> str:
        return f'{self.api_endpoint}/objects'
    
    @property
    def graphql_endpoint(self) -> str:
        return f'{self.base_url}/graphql'

    def __repr__(self) -> str:
        return f'WeaviateConfig(url={self.base_url})'

if __name__ == '__main__':
    config = WeaviateConfig()
    print(f'Base: {config.base_url}')
    print(f'Collections: {config.collections_endpoint}')
    print(f'Objects: {config.objects_endpoint}')
    print(f'GraphQL: {config.graphql_endpoint}')
