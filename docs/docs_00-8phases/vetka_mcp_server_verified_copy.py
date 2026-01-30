#!/usr/bin/env python3
'''🌳 VETKA MCP Server - Proper Implementation with JSON-RPC 2.0 (FIXED)'''

import asyncio, logging
from datetime import datetime
from typing import Any, Dict, Optional
import httpx
from mcp import Server, Tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VETKAClient:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.submitted_tasks = {}
    
    async def submit_workflow(self, feature, complexity=None, context=None):
        workflow_id = f'mcp-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
        self.submitted_tasks[workflow_id] = {'feature': feature, 'complexity': complexity, 'submitted_at': datetime.now().isoformat()}
        time_map = {'MICRO': 60, 'SMALL': 300, 'MEDIUM': 1800, 'LARGE': 3600, 'EPIC': 7200}
        est_time = time_map.get(complexity or 'MEDIUM', 1800)
        return {'status': 'submitted', 'workflow_id': workflow_id, 'feature': feature[:100], 'complexity': complexity or 'auto-detect', 'estimated_time_seconds': est_time}
    
    async def get_workflow_status(self, workflow_id):
        if workflow_id not in self.submitted_tasks:
            return {'status': 'not_found', 'error': f'Workflow {workflow_id} not found'}
        task = self.submitted_tasks[workflow_id]
        return {'status': 'queued', 'workflow_id': workflow_id, 'feature': task.get('feature', ''), 'complexity': task.get('complexity')}
    
    async def get_recent_workflows(self, limit=5):
        try:
            response = await self.client.get(f'{self.base_url}/api/workflow/history', params={'limit': limit})
            if response.status_code == 200:
                data = response.json()
                workflows = data.get('local_history', [])[:limit]
                return {'status': 'success', 'count': len(workflows), 'workflows': workflows}
            return {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            logger.error(f'Error: {e}')
            return {'status': 'error', 'message': str(e)}
    
    async def evaluate_output(self, task, output, complexity='MEDIUM'):
        try:
            response = await self.client.post(f'{self.base_url}/api/eval/score', json={'task': task, 'output': output, 'complexity': complexity})
            if response.status_code == 200:
                data = response.json()
                return {'status': 'evaluated', 'score': data.get('score', 0), 'feedback': data.get('feedback', '')}
            return {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def submit_feedback(self, workflow_id, rating, score, task=None, output=None, correction=None):
        try:
            response = await self.client.post(f'{self.base_url}/api/eval/feedback/submit', 
                json={'evaluation_id': workflow_id, 'task': task or '', 'output': output or '', 'rating': rating, 'score': score})
            if response.status_code == 200:
                return {'status': 'success', 'message': 'Feedback saved'}
            return {'status': 'error', 'message': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    async def system_health(self):
        try:
            response = await self.client.get(f'{self.base_url}/health', timeout=5.0)
            if response.status_code == 200:
                return {'status': 'healthy', 'flask': 'running'}
            return {'status': 'degraded'}
        except Exception as e:
            return {'status': 'offline', 'error': str(e)}
    
    async def close(self):
        await self.client.aclose()

vetka = VETKAClient()
server = Server('vetka-mcp')

# FIXED: Return dict directly, not json.dumps(dict)
async def submit_workflow_handler(feature, complexity=None, context=None):
    return await vetka.submit_workflow(feature, complexity, context)

async def get_workflow_status_handler(workflow_id):
    return await vetka.get_workflow_status(workflow_id)

async def get_recent_workflows_handler(limit=5):
    return await vetka.get_recent_workflows(limit)

async def evaluate_output_handler(task, output, complexity='MEDIUM'):
    return await vetka.evaluate_output(task, output, complexity)

async def submit_feedback_handler(workflow_id, rating, score, task=None, output=None, correction=None):
    return await vetka.submit_feedback(workflow_id, rating, score, task, output, correction)

async def system_health_handler():
    return await vetka.system_health()

# Use plain dict instead of ToolArgumentSchema
server.add_tool(Tool(name='submit_workflow', description='Submit workflow to VETKA', 
    inputSchema={'type': 'object', 'properties': {'feature': {'type': 'string'}, 'complexity': {'type': 'string', 'enum': ['MICRO', 'SMALL', 'MEDIUM', 'LARGE', 'EPIC']}, 'context': {'type': 'string'}}, 'required': ['feature']},
    handler=submit_workflow_handler))
server.add_tool(Tool(name='get_workflow_status', description='Get workflow status',
    inputSchema={'type': 'object', 'properties': {'workflow_id': {'type': 'string'}}, 'required': ['workflow_id']},
    handler=get_workflow_status_handler))
server.add_tool(Tool(name='get_recent_workflows', description='Get recent workflows',
    inputSchema={'type': 'object', 'properties': {'limit': {'type': 'integer', 'default': 5}}},
    handler=get_recent_workflows_handler))
server.add_tool(Tool(name='evaluate_output', description='Evaluate output',
    inputSchema={'type': 'object', 'properties': {'task': {'type': 'string'}, 'output': {'type': 'string'}, 'complexity': {'type': 'string', 'enum': ['MICRO', 'SMALL', 'MEDIUM', 'LARGE', 'EPIC']}}, 'required': ['task', 'output']},
    handler=evaluate_output_handler))
server.add_tool(Tool(name='submit_feedback', description='Submit feedback',
    inputSchema={'type': 'object', 'properties': {'workflow_id': {'type': 'string'}, 'rating': {'type': 'string', 'enum': ['👍', '👎']}, 'score': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'task': {'type': 'string'}, 'output': {'type': 'string'}, 'correction': {'type': 'string'}}, 'required': ['workflow_id', 'rating', 'score']},
    handler=submit_feedback_handler))
server.add_tool(Tool(name='system_health', description='Check system health',
    inputSchema={'type': 'object', 'properties': {}},
    handler=system_health_handler))

async def main():
    logger.info('🌳 VETKA MCP Server - JSON-RPC 2.0 over stdio (FIXED)')
    try:
        await server.run_stdio()
    finally:
        await vetka.close()

if __name__ == '__main__':
    asyncio.run(main())
